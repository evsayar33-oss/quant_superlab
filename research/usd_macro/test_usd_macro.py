"""USD Macro Radar acceptance tests: all synthetic, no internet, no signals."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import math
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import sources as S
import engine as E

NOW=datetime(2026,11,12,21,0,tzinfo=timezone.utc)


def ecb_sample():
    days=[]
    for n in range(30):
        d=date(2026,10,14)+timedelta(days=n)
        if d>NOW.date():break
        usd=1.18 - .002*n
        days.append(
            f'<Cube time="{d}"><Cube currency="USD" rate="{usd:.5f}"/>'
            f'<Cube currency="GBP" rate=".86"/><Cube currency="JPY" rate="160"/>'
            f'<Cube currency="CHF" rate=".98"/></Cube>')
    return '<?xml version="1.0"?><gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01" xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref"><Cube>'+''.join(days)+'</Cube></gesmes:Envelope>'


def treasury_sample(real=False):
    start="Date,5 Yr,10 Yr" if real else "Date,2 Yr,10 Yr"
    rows=[start]
    for i in range(10):
        day=date(2026,11,2)+timedelta(days=i)
        rows.append((f"{day:%m/%d/%Y},2.50,{2.9+i*.02:.2f}" if real else
                     f"{day:%m/%d/%Y},{4.2+i*.03:.2f},{4.5+i*.02:.2f}"))
    return "\n".join(rows)


def bls_sample():
    def line(value,period,year):
        return {"year":str(year),"period":f"M{period:02d}","value":str(value)}
    data=[
        ("CUUR0000SA0", [line(321,10,2026),line(320,9,2026),line(304,10,2025)]),
        ("CUUR0000SA0L1E", [line(315,10,2026),line(314,9,2026),line(302,10,2025)]),
        ("CES0000000001", [line(164100,10,2026),line(164000,9,2026)]),
        ("LNS14000000",[line(4.2,10,2026),line(4.1,9,2026)]),
        ("CES0500000003",[line(38,10,2026),line(37.9,9,2026),line(36.8,10,2025)]),
    ]
    return {"status":"REQUEST_SUCCEEDED","Results":{"series":[
        {"seriesID":k,"data":v} for k,v in data]}}


def rss_sample(origin="FED"):
    if origin=="FED":
        title="Federal Reserve issues FOMC statement"
        url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20261112a.htm"
    else:
        title="Consumer Price Index"
        url="https://www.bls.gov/news.release/cpi.htm"
    return f'<rss><channel><item><title>{title}</title><link>{url}</link><pubDate>Thu, 12 Nov 2026 14:00:00 GMT</pubDate></item></channel></rss>'


def mock_fetch(url,post):
    if url==S.ECB_FX:
        return ecb_sample()
    if "real_yield" in url:
        return treasury_sample(True)
    if "daily_treasury_yield_curve" in url:
        return treasury_sample(False)
    if url==S.BLS_API:
        assert post and len(post["seriesid"])==5
        return json.dumps(bls_sample())
    if url==S.FED_RSS:return rss_sample()
    if url==S.BLS_RSS:return rss_sample("BLS")
    raise ValueError("Unexpected URL")


def expectation_csv(tmp_path,release="2026-11-20T13:30:00Z"):
    p=tmp_path/"expectations.csv"
    p.write_text("indicator_id,period,expected_value,unit,release_at_utc,provider,source_url\n"+
     "nonfarm_change_k,2026-10,175,THOUSANDS,"+release+
     ",Example_Survey,https://example.org/consensus\n",encoding="utf-8")
    return p


def test_ecb_usd_basket_is_not_dxy():
    d=S.parse_ecb(ecb_sample(),NOW.date())
    assert d["label"].endswith("NOT_DXY")
    assert d["proxy_return_5d_pct"]>0
    assert d["points"]>=25
    assert math.isclose(d["gbpusd"],d["eurusd"]/.86,rel_tol=1e-4)


def test_ecb_future_dated_rows_are_excluded():
    original=ecb_sample()
    forged=original.replace("</Cube></gesmes:Envelope>",
       '<Cube time="2027-01-01"><Cube currency="USD" rate=".55"/>'
       '<Cube currency="GBP" rate=".86"/><Cube currency="JPY" rate="160"/>'
       '<Cube currency="CHF" rate=".98"/></Cube></Cube></gesmes:Envelope>')
    # The forged extra item is embedded inside the non-date wrapper.
    d=S.parse_ecb(forged,NOW.date())
    assert d["date"]<=str(NOW.date())


def test_treasury_nominal_and_real_are_not_mixed():
    n=S.parse_treasury(treasury_sample(False),NOW.date())
    r=S.parse_treasury(treasury_sample(True),NOW.date(),real=True)
    assert n["nominal_2y_pct"]>0
    assert n["curve_10y_minus_2y_bp"]>0
    assert "nominal_2y_pct" not in r
    assert r["real_10y_pct"]>0


def test_treasury_rejects_future_and_html():
    body=treasury_sample(False)+"\n11/20/2026,20,20"
    assert S.parse_treasury(body,NOW.date())["date"]=="2026-11-11"
    with pytest.raises(ValueError):
        S.parse_treasury("<html>blocked</html>",NOW.date())


def test_bls_actuals_are_current_vintage_not_historical_truth():
    r=S.parse_bls(bls_sample(),NOW)
    assert r["nonfarm"]["change_1m_raw"]==100
    assert 0<r["cpi_core"]["yoy_pct_current_vintage"]<10
    assert r["nonfarm"]["first_seen"]=="UNKNOWN_UNTIL_STORED"


def test_bls_error_is_no_data():
    with pytest.raises(ValueError):
        S.parse_bls({"status":"REQUEST_FAILED","Results":{"series":[]}},NOW)


def test_rss_headlines_only_no_directional_signal():
    news=S.parse_rss(rss_sample(),origin="FED",observed=NOW,
                     allowed_host="www.federalreserve.gov")
    assert news[0]["category"]=="FED_POLICY"
    assert news[0]["priority"]=="HIGH"
    assert news[0]["direction"].startswith("UNASSESSED")


def test_rss_rejects_invalid_host_and_future_news():
    assert not S.parse_rss(rss_sample(),origin="FED",observed=NOW,
                           allowed_host="www.bls.gov")
    late=rss_sample().replace("12 Nov 2026","13 Nov 2026")
    assert not S.parse_rss(late,origin="FED",observed=NOW,
                           allowed_host="www.federalreserve.gov")


def test_official_hosts_allowlist_blocks_ssrf():
    assert not S.checked_https("https://evil.example/robots")
    assert not S.checked_https("http://www.bls.gov")
    assert S.checked_https(S.ECB_FX)


def test_economic_expectation_is_only_locked_before_release(tmp_path):
    path=expectation_csv(tmp_path)
    raw=E.load_expectations(path)
    a=E._lock_expectations(raw,[],NOW)
    assert a[0]["status"]=="LOCKED_BEFORE_RELEASE"
    b=E._lock_expectations(raw,[],datetime(2026,11,21,tzinfo=timezone.utc))
    assert b[0]["status"]=="REJECTED_ENTERED_AFTER_RELEASE"


def test_sealed_expectation_cannot_be_repainted(tmp_path):
    path=expectation_csv(tmp_path)
    first=E._lock_expectations(E.load_expectations(path),[],NOW)
    path.write_text(path.read_text().replace("175,THOUSANDS","300,THOUSANDS"))
    with pytest.raises(ValueError,match="immutable"):
        E._lock_expectations(E.load_expectations(path),first,NOW+timedelta(days=1))


def test_consensus_units_enforced(tmp_path):
    path=expectation_csv(tmp_path)
    path.write_text(path.read_text().replace("THOUSANDS","PERCENT"))
    with pytest.raises(ValueError,match="unit mismatch"):
        E._lock_expectations(E.load_expectations(path),[],NOW)


def test_immutable_first_bls_observation_and_revision_log():
    initial=S.parse_bls(bls_sample(),NOW)
    first=E._observations(initial,[],NOW)
    t=[x for x in first if x["indicator_id"]=="nonfarm_change_k"][0]
    assert t["value_first_observed"]==100
    changed=S.parse_bls(bls_sample(),NOW)
    changed["nonfarm"]["change_1m_raw"]=40
    new=E._observations(changed,first,NOW+timedelta(days=1))
    updated=[x for x in new if x["key"]=="nonfarm_change_k|2026-10"][0]
    assert updated["value_first_observed"]==100
    assert updated["value_latest_observed"]==40
    assert len(updated["revisions"])==1


def test_surprise_requires_sealed_pre_release_and_first_seeing_after(tmp_path):
    path=expectation_csv(tmp_path,release="2026-11-13T13:30:00Z")
    lock=E._lock_expectations(E.load_expectations(path),[],NOW)
    actuals=S.parse_bls(bls_sample(),NOW)
    before=E._observations(actuals,[],NOW)
    assert E._actual_surprises(lock,before,NOW+timedelta(days=2))[0]["actual_first_observed"] is None
    after=E._observations(actuals,[],NOW+timedelta(days=2))
    got=E._actual_surprises(lock,after,NOW+timedelta(days=2))[0]
    assert got["surprise_actual_minus_expected"]==-75


def test_event_bootstrap_never_pretends_backfill_is_breaking():
    raw=S.parse_rss(rss_sample(),origin="FED",observed=NOW,
                    allowed_host="www.federalreserve.gov")
    old,new=E._enrich_events(raw,[],NOW,bootstrap=True)
    assert len(old)==1 and not new and old[0]["discovery_status"]=="BOOTSTRAP_NOT_NEW"
    assert not E._enrich_events(raw,old,NOW+timedelta(hours=1),bootstrap=False)[1]


def test_forward_news_first_seen_only_after_baseline():
    raw=S.parse_rss(rss_sample(),origin="FED",observed=NOW,
                    allowed_host="www.federalreserve.gov")
    _,new=E._enrich_events(raw,[],NOW,bootstrap=False)
    assert len(new)==1 and new[0]["discovery_status"]=="FORWARD_NEWLY_DETECTED"


def test_market_direction_cannot_use_only_bond_yields():
    data={"nominal_treasury":{"fresh":True,"nominal_2y_5d_change_bp":15}}
    assert E._regime(data,{})["label"]=="INSUFFICIENT_EVIDENCE"
    data["fx_ecb"]={"fresh":True,"proxy_return_5d_pct":.8}
    assert E._regime(data,{})["label"]=="MARKET_CONFIGURATION_USD_SUPPORTIVE"
    data["real_treasury"]={"fresh":True,"real_10y_5d_change_bp":-10}
    assert E._regime(data,{})["label"]=="MIXED_REAL_YIELD_DIVERGENCE"


def test_source_failures_never_create_fabricated_metrics(tmp_path):
    def broken(url,post):raise RuntimeError("blocked")
    d=E.run(mode="smoke",output=tmp_path/"smoke",
            expectations_csv=tmp_path/"missing.csv",now=NOW,fetch=broken)
    assert d["status"]=="UNAVAILABLE"
    assert d["regime"]["label"]=="INSUFFICIENT_EVIDENCE"
    assert not d["trade_authorization"]


def test_offline_synthetic_six_source_smoke_research_only(tmp_path):
    d=E.run(mode="smoke",output=tmp_path/"out",
            expectations_csv=tmp_path/"missing.csv",now=NOW,fetch=mock_fetch)
    assert d["coverage_ok_sources"]==6
    assert d["market"]["fx_ecb"]["label"].endswith("NOT_DXY")
    assert len(d["pillars"])==6
    assert d["new_forward_events"]==0
    assert d["expectation_coverage"]["confirmed_ex_ante_surprises"]==0
    assert not d["approved_alpha"] and not d["telegram_trade_signals"]


def test_scheduled_bootstrap_sends_only_research_digest(tmp_path):
    sent=[]
    d=E.run(mode="scheduled",output=tmp_path/"store",
            expectations_csv=tmp_path/"missing.csv",now=NOW,fetch=mock_fetch,
            send=lambda x:(sent.append(x) or True))
    assert len(sent)==1 and "AL/SAT YOK" in sent[0]
    assert "geçmiş haberler" in sent[0].lower()
    assert d["telegram_state"]=="SENT"
    assert len(json.loads((tmp_path/"store"/"notifications.json").read_text()))==1


def test_telegram_send_disabled_if_sources_unavailable(tmp_path):
    sent=[]
    E.run(mode="scheduled",output=tmp_path/"store",
          expectations_csv=tmp_path/"missing.csv",now=NOW,
          fetch=lambda url,post: (_ for _ in ()).throw(RuntimeError("down")),
          send=lambda x:(sent.append(x) or True))
    assert sent==[]


def test_no_trade_authorization_ever_from_macro_engine(tmp_path):
    d=E.run(mode="smoke",output=tmp_path/"out",
            expectations_csv=tmp_path/"missing.csv",now=NOW,fetch=mock_fetch)
    assert d["approved_alpha"] is False
    assert d["trade_authorization"] is False
    assert d["broker_execution"] is False


def test_smoke_does_not_modify_scheduled_store(tmp_path):
    store=tmp_path/"live"
    E.run(mode="smoke",output=tmp_path/"dry",expectations_csv=tmp_path/"none.csv",
          now=NOW,fetch=mock_fetch)
    assert not store.exists()


def test_bootstrap_bulletin_is_not_resend_as_daily_same_utc_date(tmp_path):
    sent=[]
    location=tmp_path/"store"
    fn=lambda text:(sent.append(text) or True)
    E.run(mode="scheduled",output=location,
          expectations_csv=tmp_path/"missing.csv",now=NOW,
          fetch=mock_fetch,send=fn)
    E.run(mode="scheduled",output=location,
          expectations_csv=tmp_path/"missing.csv",now=NOW+timedelta(minutes=10),
          fetch=mock_fetch,send=fn)
    assert len(sent)==1
    assert len(json.loads((location/"notifications.json").read_text()))==1


def test_failed_delivery_is_retried_not_false_success(tmp_path):
    sent=[]
    location=tmp_path/"store"
    E.run(mode="scheduled",output=location,
          expectations_csv=tmp_path/"missing.csv",now=NOW,
          fetch=mock_fetch,send=lambda text:False)
    assert not (location/"notifications.json").exists()
    E.run(mode="scheduled",output=location,
          expectations_csv=tmp_path/"missing.csv",now=NOW+timedelta(minutes=10),
          fetch=mock_fetch,send=lambda text:(sent.append(text) or True))
    assert len(sent)==1
