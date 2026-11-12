"""USD fundamental macro research synthesis with frozen expectations and audit.

NEVER merges synthetic projections with market consensus; NEVER broadcasts BUY/SELL.
No H083/H084 trading result enters this USD model or validation gate.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    from . import sources as S
except ImportError:
    import sources as S

INDICATORS = {
    "cpi_all_yoy_pct":("cpi_all","yoy_pct_current_vintage","PCT_YOY","INFLATION"),
    "cpi_core_yoy_pct":("cpi_core","yoy_pct_current_vintage","PCT_YOY","INFLATION"),
    "nonfarm_change_k":("nonfarm","change_1m_raw","THOUSANDS","LABOR"),
    "unemployment_pct":("unemployment","value","PERCENT","LABOR"),
    "ahe_yoy_pct":("ahe","yoy_pct_current_vintage","PCT_YOY","LABOR"),
}
REQUIRED_EXP_COLS = {
    "indicator_id","period","expected_value","unit",
    "release_at_utc","provider","source_url",
}
MAX_OBS = 800
MAX_EVENTS = 1000


def _read_json(path: Path, default):
    if not path.exists():
        return default
    data=json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not type(default):
        raise ValueError(f"Unexpected JSON state shape at {path}")
    return data


def _write(path: Path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False,
                               sort_keys=True)+"\n",encoding="utf-8")
    temp.replace(path)


def _datetime(value: str) -> datetime:
    stamp=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Timezone-aware UTC timestamp required")
    return stamp.astimezone(timezone.utc)


def load_expectations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig",newline="") as f:
        rdr=csv.DictReader(f)
        if not rdr.fieldnames or not REQUIRED_EXP_COLS.issubset(rdr.fieldnames):
            raise ValueError("Missing consensus CSV fields")
        rows=list(rdr)
    return [r for r in rows if r.get("indicator_id","").strip()]


def _lock_expectations(raw: list[dict], previous: list[dict], now: datetime):
    """Immutable first-observed expectation, not author-declared recorded_at timestamp."""
    locks={p["key"]:dict(p) for p in previous}
    seen=set()
    for r in raw:
        ident=r.get("indicator_id","").strip()
        period=r.get("period","").strip()
        key=f"{ident}|{period}"
        if key in seen:
            raise ValueError("Duplicate expectation key "+key)
        seen.add(key)
        if ident not in INDICATORS:
            raise ValueError("Unknown USD indicator "+ident)
        if len(period)!=7 or period[4]!="-" or not period[:4].isdigit() or not period[5:].isdigit() or not 1<=int(period[5:])<=12:
            raise ValueError("Expectation period must be YYYY-MM")
        try:
            amount=float(r["expected_value"])
        except (ValueError,TypeError,KeyError):
            raise ValueError("Expected value not numeric") from None
        if not math.isfinite(amount):
            raise ValueError("Nonfinite consensus")
        unit=INDICATORS[ident][2]
        if str(r.get("unit","")).strip()!=unit:
            raise ValueError("Expectation unit mismatch "+key)
        provider=str(r.get("provider","")).strip()
        url=str(r.get("source_url","")).strip()
        if not provider or urlparse(url).scheme!="https" or not urlparse(url).hostname:
            raise ValueError("Consensus provider and public HTTPS source URL required")
        release=_datetime(r["release_at_utc"])
        canonical={
            "key":key,"indicator_id":ident,"period":period,
            "expected_value":amount,"unit":unit,"provider":provider,
            "source_url":url,"release_at_utc":release.isoformat(),
        }
        if key in locks:
            former=locks[key]
            frozen={k:former.get(k) for k in canonical}
            if canonical!=frozen:
                raise ValueError("Locked expectation immutable; do not edit after first snapshot: "+key)
            continue
        canonical["first_seen_utc"]=now.isoformat()
        canonical["status"]=(
            "LOCKED_BEFORE_RELEASE" if now<release else
            "REJECTED_ENTERED_AFTER_RELEASE")
        locks[key]=canonical
    return sorted(locks.values(),key=lambda x:(x["period"],x["indicator_id"]))


def _observations(bls: dict, previous: list[dict], now: datetime):
    """Preserve first as-observed BLS value; log revisions without repaint."""
    index={r["key"]:dict(r) for r in previous}
    for indicator,(series,value_field,unit,_) in INDICATORS.items():
        r=bls.get(series)
        if r is None or r.get(value_field) is None:
            continue
        period=r["period"]
        key=indicator+"|"+period
        value=float(r[value_field])
        if not math.isfinite(value):
            continue
        if key not in index:
            index[key]={
                "key":key,"indicator_id":indicator,"period":period,
                "value_first_observed":value,"value_latest_observed":value,
                "first_seen_utc":now.isoformat(),"last_seen_utc":now.isoformat(),
                "revisions":[],"unit":unit,
                "source_series":r["series_id"],
            }
        else:
            old=index[key]
            if old.get("source_series")!=r["series_id"] or old.get("unit")!=unit:
                raise ValueError("BLS source series changed for same observation")
            if abs(float(old["value_latest_observed"])-value)>1e-9:
                old.setdefault("revisions",[]).append({
                    "from":old["value_latest_observed"],"to":value,
                    "detected_utc":now.isoformat()})
                old["value_latest_observed"]=value
            old["last_seen_utc"]=now.isoformat()
    return sorted(index.values(),key=lambda x:(x["period"],x["indicator_id"]))[-MAX_OBS:]


def _actual_surprises(locks: list[dict], observations: list[dict], now: datetime):
    facts={p["key"]:p for p in observations}
    evaluated=[]
    for p in locks:
        val=dict(p)
        seen=facts.get(p["key"])
        val["actual_first_observed"]=None
        val["surprise_actual_minus_expected"]=None
        val["evaluation"]="PENDING_OR_INVALID"
        if (p["status"]=="LOCKED_BEFORE_RELEASE" and
            _datetime(p["release_at_utc"])<=now and seen and
            _datetime(seen["first_seen_utc"])>=_datetime(p["release_at_utc"])):
            val["actual_first_observed"]=seen["value_first_observed"]
            val["surprise_actual_minus_expected"]=round(
                seen["value_first_observed"]-p["expected_value"],4)
            val["evaluation"]="EX_ANTE_LOCKED_FIRST_OBSERVED_SURPRISE"
        evaluated.append(val)
    return evaluated


def _enrich_events(incoming: list[dict], old: list[dict], now: datetime,
                   *, bootstrap: bool):
    existing={r["event_id"]:dict(r) for r in old}
    newcomers=[]
    for r in incoming:
        k=r["event_id"]
        if k in existing:
            continue
        raw=dict(r)
        pub=_datetime(raw["published_utc"])
        raw["discovery_status"]=(
            "BOOTSTRAP_NOT_NEW" if bootstrap or now-pub>timedelta(hours=48)
            else "FORWARD_NEWLY_DETECTED"
        )
        existing[k]=raw
        if raw["discovery_status"]=="FORWARD_NEWLY_DETECTED":
            newcomers.append(raw)
    out=sorted(existing.values(),key=lambda x:(x["published_utc"],x["event_id"]))
    return out[-MAX_EVENTS:],newcomers


def _regime(data: dict, sources: dict):
    fx=data.get("fx_ecb",{})
    nominal=data.get("nominal_treasury",{})
    real=data.get("real_treasury",{})
    reasons=[]
    fx5=fx.get("proxy_return_5d_pct") if fx.get("fresh") else None
    two=nominal.get("nominal_2y_5d_change_bp") if nominal.get("fresh") else None
    real5=real.get("real_10y_5d_change_bp") if real.get("fresh") else None
    if fx5 is not None:
        reasons.append(f"ECB 4-döviz USD vekili 5g: {fx5:+.2f}% (DXY değil)")
    if two is not None:
        reasons.append(f"ABD 2y nominal getiri 5g: {two:+.1f} bp")
    if real5 is not None:
        reasons.append(f"ABD 10y reel getiri 5g: {real5:+.1f} bp")
    if fx5 is None or two is None:
        view="INSUFFICIENT_EVIDENCE"
    elif fx5>=.35 and two>=8:
        view="MARKET_CONFIGURATION_USD_SUPPORTIVE"
    elif fx5<=-.35 and two<=-8:
        view="MARKET_CONFIGURATION_USD_UNSUPPORTIVE"
    else:
        view="MIXED_NO_DIRECTION"
    if view.startswith("MARKET_") and real5 is not None and ((fx5>0) != (real5>0)):
        view="MIXED_REAL_YIELD_DIVERGENCE"
    return {
        "label":view,"confidence":"LOW_RESEARCH_ONLY",
        "context":reasons,
        "not_forecast":True,"not_dxy":True,"not_trade_signal":True,
        "rate_differentials_available":False,
        "implied_fed_futures_available":False,
        "explanation":"ABD getirilerinin tek başına yükselmesi USD kârını kanıtlamaz. "
                      "ECB döviz bileşimi DXY değildir; dış faiz farkı, siyasi risk ve "
                      "beklenti ayrışması ayrıca incelenmelidir.",
    }


def _pillars(data: dict, sources: dict, locks: list, surprises: list) -> list[dict]:
    bls=data.get("bls_actuals",{})
    def b(x,field):
        return bls.get(x,{}).get(field)
    latest={
        "INFLATION":{
            "core_cpi_yoy_pct":b("cpi_core","yoy_pct_current_vintage"),
            "headline_cpi_yoy_pct":b("cpi_all","yoy_pct_current_vintage"),
            "latest_core_period":b("cpi_core","period"),
            "context":"Çekirdek CPI / manşet CPI trendleri; daha yüksek enflasyon otomatik USD-pozitif değildir.",
        },
        "LABOR":{
            "payroll_monthly_change_thousands":b("nonfarm","change_1m_raw"),
            "unemployment_pct":b("unemployment","value"),
            "ahe_yoy_pct":b("ahe","yoy_pct_current_vintage"),
            "context":"BLS cari revizyon; önceki açıklama dönemi yeniden yazılmış olabilir.",
        },
        "FED_POLICY":{
            "headline_events":len(data.get("fed_news",[])),
            "context":"Fed açıklama başlıkları etki alanına ayrılır; tam metin ve faiz yolu çıkarımı yok.",
        },
        "NOMINAL_AND_REAL_RATES":{
            "treasury_2y_pct":data.get("nominal_treasury",{}).get("nominal_2y_pct"),
            "treasury_10y_pct":data.get("nominal_treasury",{}).get("nominal_10y_pct"),
            "treasury_real_10y_pct":data.get("real_treasury",{}).get("real_10y_pct"),
            "ten_minus_two_bp":data.get("nominal_treasury",{}).get("curve_10y_minus_2y_bp"),
            "context":"Gerçek faiz, eğri ve vade primi ayrıştırılmadan kesin USD yönü atanmaz.",
        },
        "CROSS_FX":{
            "ecb_eurusd":data.get("fx_ecb",{}).get("eurusd"),
            "ecb_usdjpy":data.get("fx_ecb",{}).get("usdjpy"),
            "usd_proxy_5d_pct":data.get("fx_ecb",{}).get("proxy_return_5d_pct"),
            "context":"ECB 4 döviz USD proxy: EUR/JPY/GBP/CHF; DXY veya işlem gören endeks değildir.",
        },
        "RISK_FISCAL_TRADE":{
            "headline_events":sum(e["category"]=="FISCAL_RISK"
                                  for e in data.get("fed_news",[])+data.get("bls_news",[])),
            "context":"Tarife/borç/ticaret/jeopolitik ve global risk kaynağı henüz yeterli değil.",
        },
    }
    for p in latest.values():
        p["validated_alpha"]=False
        p["consensus_coverage"]=sum(x["evaluation"]=="EX_ANTE_LOCKED_FIRST_OBSERVED_SURPRISE"
                                    for x in surprises)
    return [{"pillar":k,**v} for k,v in latest.items()]


def _summary(data, source_states, expectations, observations, events, new_events, now):
    successes=sum(s["state"]=="OK" for s in source_states.values())
    fresh=sum(bool(data.get(k,{}).get("fresh"))
              for k in ("fx_ecb","nominal_treasury","real_treasury"))
    evaluated=_actual_surprises(expectations,observations,now)
    status=("UNAVAILABLE" if successes==0 else
            "PARTIAL" if successes<6 or fresh<2 else
            "OBSERVED_RESEARCH")
    evidence={
        "required_market_consensus":"NOT_AVAILABLE_BY_DEFAULT",
        "confirmed_ex_ante_surprises":sum(
            x["evaluation"]=="EX_ANTE_LOCKED_FIRST_OBSERVED_SURPRISE" for x in evaluated),
        "warning":"CPI/PCE/NFP piyasa konsensüsü yoksa sürpriz uydurulmaz. "
                  "FedWatch veya resmi faiz olasılığı hesaplanmaz.",
    }
    report={
        "schema_version":"USD_MACRO_V1_2026_11",
        "generated_utc":now.isoformat(),
        "status":status,"coverage_ok_sources":successes,
        "coverage_total_sources":len(source_states),
        "sources":source_states,
        "market":{k:v for k,v in data.items() if k in ("fx_ecb","nominal_treasury","real_treasury")},
        "bls_latest":data.get("bls_actuals",{}),
        "regime":_regime(data,source_states),
        "pillars":_pillars(data,source_states,expectations,evaluated),
        "surprises":evaluated[-30:],
        "expectation_coverage":evidence,
        "recent_events":events[-30:][::-1],
        "new_forward_events":len(new_events),
        "upcoming_expectations":[{k:v for k,v in p.items()
                                  if k not in ("expected_value",)}
            for p in expectations if p["status"]=="LOCKED_BEFORE_RELEASE" and
            _datetime(p["release_at_utc"])>now][:12],
        "limitations":[
            "Fed official communication is headline-classified; not a model of central-bank language.",
            "No licensed survey consensus, ECB/OIS relative policy curve, CFTC positions or full BEA PCE/GDP source in v1.",
            "Official series can revise; backfilled old data is not point-in-time.",
            "USD proxy is not DXY; scoring not validated against forward USD returns.",
        ],
        "scenarios":[
            {"name":"USD supportive conditional","when":"2-year nominal and real yields rise alongside broad FX confirmation; external differential must also support."},
            {"name":"USD weakening conditional","when":"Real/short yields and USD FX proxy decline together; watch foreign monetary policies."},
            {"name":"Risk-off bifurcation","when":"Systemic stress can strengthen safe-haven USD despite falling US yields or weaken USD on US-specific stress."},
            {"name":"Inflation surprise ambiguity","when":"Hot CPI can reprice Fed higher but also weaken real growth and increase US risk premia."},
        ],
        "approved_alpha":False,"trade_authorization":False,
        "broker_execution":False,"telegram_trade_signals":False,
    }
    return report


def _format_telegram(report: dict, events: list[dict], *, launch=False) -> str:
    e=html.escape
    s=report["regime"]
    lines=[
        "<b>🇺🇸 USD MAKRO RADAR | TEMEL ANALİZ</b>",
        "<b>Durum:</b> "+e(s["label"]),
        f"Kaynak: {report['coverage_ok_sources']}/{report['coverage_total_sources']} resmî akış",
        "Sürpriz: "+str(report["expectation_coverage"]["confirmed_ex_ante_surprises"])+
        " önceden kilitlenmiş beklenti karşılaştırması",
        "","<b>Piyasa çapraz kontrolü:</b>",
    ]
    lines.extend("• "+e(x) for x in s["context"][:4])
    if launch:
        lines.append("İlk gözlem: geçmiş haberler YENİ SİNYAL sayılmadı.")
    else:
        for r in events[:4]:
            lines.append("• "+e(r["category"])+": "+e(r["headline"][:125]))
            lines.append("  "+e(r["url"]))
    lines.extend(["","<b>Beklenti ve sınırlar:</b>",
        "Piyasa konsensüsü yoksa sürpriz yok. ABD verisi tek başına USD yönü kanıtlamaz.",
        "Haber başlığı ≠ Fed tonu ≠ işlem sinyali. Bu araştırma/izleme bültenidir.",
        "<i>AL/SAT YOK · Otomatik emir YOK · Kanıtlanmış alpha YOK.</i>"])
    msg="\n".join(lines)
    if len(msg)>3600:
        raise ValueError("Telegram digest too long")
    return msg


def _telegram_send(msg: str) -> bool:
    token=os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat=os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    response=requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id":chat,"text":msg,"parse_mode":"HTML",
              "disable_web_page_preview":"true"},
        timeout=(10,20))
    response.raise_for_status()
    if response.json().get("ok") is not True:
        raise ValueError("Telegram refused macro digest")
    return True


def run(*, mode: str, output: Path, expectations_csv: Path,
        now: datetime | None=None, fetch=S.safe_request, send=_telegram_send) -> dict:
    if mode not in {"smoke","scheduled"}:
        raise ValueError(mode)
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    output.mkdir(parents=True,exist_ok=True)
    old_latest=_read_json(output/"latest.json",{}) if mode=="scheduled" else {}
    prior_events=_read_json(output/"events.json",[]) if mode=="scheduled" else []
    old_obs=_read_json(output/"observations.json",[]) if mode=="scheduled" else []
    old_locks=_read_json(output/"expectations_lock.json",[]) if mode=="scheduled" else []
    notifications=_read_json(output/"notifications.json",[]) if mode=="scheduled" else []
    raw=load_expectations(expectations_csv)
    locks=_lock_expectations(raw,old_locks,now)
    data,sources=S.collect(now,fetch=fetch)
    events,new_events=_enrich_events(data.get("fed_news",[])+data.get("bls_news",[]),
                                      prior_events,now,bootstrap=not bool(old_latest))
    observations=_observations(data.get("bls_actuals",{}),old_obs,now)
    latest=_summary(data,sources,locks,observations,events,new_events,now)
    if mode=="scheduled":
        # Never replace old good data with stale lookalikes: publish degraded status.
        _write(output/"latest.json",latest)
        _write(output/"events.json",events)
        _write(output/"observations.json",observations)
        _write(output/"expectations_lock.json",locks)
        _write(output/"surprises.json",_actual_surprises(locks,observations,now))
        history=_read_json(output/"history.json",[])
        history.append({
            "run_utc":now.isoformat(),"status":latest["status"],
            "regime":latest["regime"]["label"],
            "usd_proxy_5d_pct":latest["market"].get("fx_ecb",{}).get("proxy_return_5d_pct"),
            "nominal_2y_pct":latest["market"].get("nominal_treasury",{}).get("nominal_2y_pct"),
            "source_success_count":latest["coverage_ok_sources"],
        })
        _write(output/"history.json",history[-800:])
        # Exactly-one successful report per UTC day; urgent forward high-priority
        # events can generate an additional immediate bulletin.
        today=now.date().isoformat()
        sent_keys={r["key"] for r in notifications}
        first_run=not old_latest
        urgent=[x for x in new_events if x["priority"]=="HIGH"]
        is_daily=now.hour>=20
        key=(f"USD|BOOTSTRAP|{today}" if first_run else
             f"USD|HIGH|{today}|"+"|".join(x["event_id"] for x in urgent) if urgent else
             f"USD|DAILY|{today}")
        already_daily=any(
            x in sent_keys for x in (f"USD|BOOTSTRAP|{today}",f"USD|DAILY|{today}")
        )
        # A successful launch bulletin already counts as today's digest.
        should_send=(
            (first_run or bool(urgent) or (is_daily and not already_daily))
            and latest["status"]!="UNAVAILABLE"
        )
        if should_send and key not in sent_keys:
            try:
                sent=send(_format_telegram(latest,urgent,launch=first_run))
                latest["telegram_state"]="SENT" if sent else "NOT_CONFIGURED"
                if sent:
                    notifications.append({"key":key,"sent_utc":now.isoformat()})
                    _write(output/"notifications.json",notifications[-300:])
            except Exception as exc:
                latest["telegram_state"]="SEND_FAILED"
                latest["telegram_error"]=type(exc).__name__
            _write(output/"latest.json",latest)
    else:
        _write(output/"latest.json",latest)
        _write(output/"events.json",events)
        _write(output/"surprises.json",_actual_surprises(locks,observations,now))
    print(json.dumps({
        "mode":mode,"status":latest["status"],
        "source_ok":latest["coverage_ok_sources"],
        "sources":{k:v["state"] for k,v in sources.items()},
        "news_events":len(events),"new_events":len(new_events),
        "expectations_locked":sum(p["status"]=="LOCKED_BEFORE_RELEASE" for p in locks),
        "actual_surprises":latest["expectation_coverage"]["confirmed_ex_ante_surprises"],
        "regime":latest["regime"]["label"],"approved_alpha":False,
        "telegram":latest.get("telegram_state","NO_SEND"),
    },ensure_ascii=False))
    return latest


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["smoke","scheduled"],default="smoke")
    parser.add_argument("--output",default="results/usd_macro")
    parser.add_argument("--expectations",default="research/usd_macro/expectations.csv")
    args=parser.parse_args()
    result=run(mode=args.mode,output=Path(args.output),
               expectations_csv=Path(args.expectations))
    # Smoke checks real primary-source reachability. No fake green when all blocked.
    if args.mode=="smoke" and result["coverage_ok_sources"]<3:
        sys.exit("USD macro official-source live smoke failed minimum 3/6")
