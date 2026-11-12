"""USD Macro Radar — official primary-source collectors (research-only).

BLS observations are CURRENT VINTAGE until first captured. ECB basket is not DXY.
No scraped financial-calendar consensus or speculative FedWatch probabilities.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from io import StringIO
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests

USER_AGENT = "quant_superlab-usd-macro/1.0 (noncommercial research; github.com/evsayar33-oss/quant_superlab)"
ECB_FX = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
TREASURY_BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv"
FED_RSS = "https://www.federalreserve.gov/feeds/press_monetary.xml"
BLS_RSS = "https://www.bls.gov/feed/bls_latest.rss"
BLS_API = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
SERIES = {
    "cpi_all": ("CUUR0000SA0", "CPI-U all items, NSA index", "INDEX"),
    "cpi_core": ("CUUR0000SA0L1E", "CPI-U less food & energy, NSA index", "INDEX"),
    "nonfarm": ("CES0000000001", "US nonfarm payroll employment, SA", "THOUSANDS"),
    "unemployment": ("LNS14000000", "US unemployment rate, SA", "PERCENT"),
    "ahe": ("CES0500000003", "Private average hourly earnings, SA", "USD_HOURLY"),
}
ALLOWED_DOMAINS = {
    "www.ecb.europa.eu", "home.treasury.gov", "www.federalreserve.gov",
    "www.bls.gov", "api.bls.gov",
}


def checked_https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_DOMAINS


def safe_request(url: str, *, post=None, get=None):
    if not checked_https(url):
        raise ValueError("Official source whitelist rejection")
    if get is not None:
        return get(url, post)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/xml,text/xml,text/csv,application/json,*/*"}
    r = (requests.post(url, json=post, headers=headers, timeout=(12, 35))
         if post is not None else
         requests.get(url, headers=headers, timeout=(12, 35)))
    r.raise_for_status()
    if len(r.content) > 5_000_000:
        raise ValueError("Oversized official payload")
    return r.text


def parse_ecb(xml_text: str, today: date) -> dict:
    root = ET.fromstring(xml_text)
    days = {}
    for cube in root.iter():
        d = cube.attrib.get("time")
        if not d:
            continue
        try:
            day = date.fromisoformat(d)
        except ValueError:
            continue
        if day > today or day < today - timedelta(days=120):
            continue
        rates = {}
        for item in cube:
            c = item.attrib.get("currency")
            try:
                val = float(item.attrib.get("rate", "nan"))
                if c in {"USD", "JPY", "GBP", "CHF"} and val > 0:
                    rates[c] = val
            except ValueError:
                continue
        if set(rates) == {"USD", "JPY", "GBP", "CHF"}:
            days[day] = rates
    ordered = sorted(days)
    if not ordered:
        raise ValueError("No complete ECB reference-rate days")
    # ECB quotes CURRENCY per EUR. Basket: currency-per-USD =
    # currency-per-EUR / USD-per-EUR; USD strengthens when this rises.
    weights = {"JPY": .25, "GBP": .20, "CHF": .10, "EUR": .45}
    levels = []
    import math
    for d in ordered:
        rate = days[d]
        values = {"EUR": 1 / rate["USD"],
                  "JPY": rate["JPY"] / rate["USD"],
                  "GBP": rate["GBP"] / rate["USD"],
                  "CHF": rate["CHF"] / rate["USD"]}
        levels.append(sum(weight * math.log(values[c]) for c, weight in weights.items()))
    recent = ordered[-1]
    def change(n):
        return round((math.exp(levels[-1] - levels[-1-n])-1)*100, 4) if len(levels)>n else None
    return {
        "source": ECB_FX, "date": recent.isoformat(),
        "age_calendar_days": (today-recent).days,
        "eurusd": days[recent]["USD"],
        "usdjpy": round(days[recent]["JPY"]/days[recent]["USD"], 4),
        "gbpusd": round(days[recent]["USD"]/days[recent]["GBP"], 5),
        "usdchf": round(days[recent]["CHF"]/days[recent]["USD"], 5),
        "proxy_return_1d_pct": change(1),
        "proxy_return_5d_pct": change(5),
        "proxy_return_20d_pct": change(20),
        "basket_weights": weights,
        "label": "ECB_REFERENCES_4CCY_USD_PROXY_NOT_DXY",
        "fresh": (today-recent).days <= 5,
        "points": len(ordered),
    }


def treasury_url(year: int, real: bool = False) -> str:
    category = "daily_treasury_real_yield_curve" if real else "daily_treasury_yield_curve"
    return (f"{TREASURY_BASE}/{year}/all?type={category}&field_tdr_date_value={year}&page&_format=csv")


def parse_treasury(csv_text: str, today: date, *, real: bool = False) -> dict:
    if csv_text.lstrip().startswith("<"):
        raise ValueError("Treasury CSV endpoint returned HTML")
    values = []
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames is None or "Date" not in reader.fieldnames:
        raise ValueError("Treasury CSV missing Date header")
    for r in reader:
        try:
            d = datetime.strptime(r["Date"].strip(), "%m/%d/%Y").date()
        except (ValueError, AttributeError):
            try:
                d = date.fromisoformat(r["Date"].strip())
            except (ValueError, AttributeError):
                continue
        if d > today:
            continue
        try:
            v10 = float(r["10 Yr"])
            v2 = float(r["2 Yr"]) if not real else None
            if not (-5 < v10 < 30 and (real or -5 < v2 < 30)):
                continue
        except (KeyError, ValueError, TypeError):
            continue
        values.append((d, v2, v10))
    values.sort()
    if not values:
        raise ValueError("Treasury data has no recognized rate rows")
    last = values[-1]
    prev = values[-6] if len(values)>=6 else None
    source = treasury_url(today.year, real=real)
    return {
        "source": source,"date": last[0].isoformat(),
        "age_calendar_days": (today-last[0]).days,
        "fresh": (today-last[0]).days <= 5,
        "points":len(values),
        "real_10y_pct" if real else "nominal_10y_pct":last[2],
        "real_10y_5d_change_bp" if real else "nominal_10y_5d_change_bp":
            round((last[2]-prev[2])*100,2) if prev else None,
        **({} if real else {
            "nominal_2y_pct":last[1],
            "nominal_2y_5d_change_bp":round((last[1]-prev[1])*100,2) if prev else None,
            "curve_10y_minus_2y_bp":round((last[2]-last[1])*100,2),
        }),
    }


def parse_bls(response: dict, observed_at: datetime) -> dict:
    if response.get("status")!="REQUEST_SUCCEEDED":
        raise ValueError("BLS API did not confirm success")
    rows = response.get("Results",{}).get("series",[])
    indexes={}
    for series in rows:
        series_id=series.get("seriesID")
        if series_id not in {x[0] for x in SERIES.values()}:
            continue
        periods={}
        for r in series.get("data",[]):
            year = str(r.get("year",""))
            p = str(r.get("period",""))
            if not (len(year)==4 and year.isdigit() and len(p)==3 and p.startswith("M")
                    and p[1:].isdigit() and 1<=int(p[1:])<=12):
                continue
            try:
                value = float(str(r["value"]).replace(",",""))
            except (KeyError,ValueError,TypeError):
                continue
            periods[f"{year}-{int(p[1:]):02d}"]=value
        if periods:
            indexes[series_id]=periods
    latest={}
    for key,(sid,title,unit) in SERIES.items():
        values=indexes.get(sid,{})
        if not values:
            continue
        period=max(values)
        current=values[period]
        year,month=map(int,period.split("-"))
        prior_year=f"{year-1}-{month:02d}"
        previous=f"{year-1}-12" if month==1 else f"{year}-{month-1:02d}"
        prev=values.get(previous)
        py=values.get(prior_year)
        monthly_change = (current-prev if prev is not None else None)
        yoy = (current/py -1)*100 if py and key in {"cpi_all","cpi_core","ahe"} else None
        latest[key] = {
            "id": key,"series_id":sid,"name":title,"unit":unit,
            "period":period,"value":current,
            "prior_month_value":prev,"prior_year_value":py,
            "change_1m_raw":round(monthly_change,4) if monthly_change is not None else None,
            "yoy_pct_current_vintage":round(yoy,3) if yoy is not None else None,
            "first_seen": "UNKNOWN_UNTIL_STORED",
            "retrieved_utc":observed_at.isoformat(),
            "vintage_warning":"Historical series may have been revised; only first future snapshot is auditable.",
            "source":"https://www.bls.gov/developers/",
        }
    if len(latest)<3:
        raise ValueError("BLS returned too few relevant series")
    return latest


def _rss_date(s: str):
    if not s:
        return None
    try:
        d=parsedate_to_datetime(s)
        return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError,ValueError,IndexError):
        try:
            d=datetime.fromisoformat(s.replace("Z","+00:00"))
            return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def classify_headline(text: str, origin: str) -> tuple[str,str]:
    low=text.casefold()
    if any(w in low for w in ("consumer price", "inflation", "producer price", "cpi", "pce")):
        return "INFLATION","HIGH"
    if any(w in low for w in ("employment situation","nonfarm","payroll","unemployment",
                                "labor market","job opening")):
        return "LABOR","HIGH"
    if any(w in low for w in ("fomc","federal open market committee","monetary policy",
                                "interest rate decision","policy statement")):
        return "FED_POLICY","HIGH"
    if any(w in low for w in ("gross domestic product","gdp","retail sales","industrial production")):
        return "GROWTH","MEDIUM"
    if any(w in low for w in ("tariff","trade","treasury","debt","financial stability")):
        return "FISCAL_RISK","MEDIUM"
    return ("FED_COMMUNICATION" if origin=="FED" else "OTHER_MACRO"),"LOW"


def parse_rss(xml_text: str, *, origin: str, observed: datetime, allowed_host: str,
              max_age_days: int=35) -> list[dict]:
    root=ET.fromstring(xml_text)
    result=[]
    for item in root.iter():
        if item.tag.split("}")[-1] not in {"item","entry"}:
            continue
        fields={}
        for n in item:
            key=n.tag.split("}")[-1]
            val=(n.text or "").strip()
            if key=="link" and not val:
                val=n.attrib.get("href","")
            fields[key]=val
        title=fields.get("title","").strip()[:300]
        link=fields.get("link","").strip()
        published=_rss_date(fields.get("pubDate",fields.get("published","")))
        if (not title or not link or published is None or
            published>observed or
            observed-published>timedelta(days=max_age_days)):
            continue
        parsed=urlparse(link)
        if parsed.scheme!="https" or parsed.hostname!=allowed_host:
            continue
        category,impact=classify_headline(title,origin)
        import hashlib
        identifier=hashlib.sha256((origin+"|"+link+"|"+published.isoformat()).encode()).hexdigest()[:20]
        result.append({
            "event_id":identifier,"source":origin,"headline":title,
            "url":link,"published_utc":published.isoformat(),
            "first_seen_utc":observed.isoformat(),"category":category,
            "priority":impact,"direction":"UNASSESSED_NEWS_NOT_TRADE_SIGNAL",
        })
    return result[:100]


def collect(now: datetime, *, fetch=safe_request) -> tuple[dict,dict]:
    """Independent fail-closed sources, never quietly fill missing with guesses."""
    today=now.date()
    sources={}
    result={}
    tasks=[
        ("fx_ecb",ECB_FX,lambda s:parse_ecb(s,today),None),
        ("nominal_treasury",treasury_url(today.year),lambda s:parse_treasury(s,today),None),
        ("real_treasury",treasury_url(today.year,real=True),
             lambda s:parse_treasury(s,today,real=True),None),
        ("bls_actuals",BLS_API,lambda s:parse_bls(__import__("json").loads(s),now),
             {"seriesid":[item[0] for item in SERIES.values()]}),
        ("fed_news",FED_RSS,lambda s:parse_rss(s,origin="FED",observed=now,
                                                allowed_host="www.federalreserve.gov"),None),
        ("bls_news",BLS_RSS,lambda s:parse_rss(s,origin="BLS",observed=now,
                                                allowed_host="www.bls.gov"),None),
    ]
    for name,url,parse,payload in tasks:
        try:
            text=fetch(url,post=payload)
            data=parse(text)
            result[name]=data
            sources[name]={"state":"OK","url":url,"asof_utc":now.isoformat(),
                           "records":len(data) if isinstance(data,list) else 1}
        except Exception as exc:
            sources[name]={"state":"ERROR","url":url,
                           "error":type(exc).__name__+":"+str(exc)[:140]}
    return result,sources
