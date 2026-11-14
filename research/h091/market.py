"""H091 independently timestamped REAL OHLC from public OKX history-candles.

No synthetic fallback; return explicit errors if venue unreachable. Stable
hourly *closed* candles, no account credentials or live order API used.
"""
from __future__ import annotations
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path

SYMBOLS={"BTC":"BTC-USDT-SWAP","ETH":"ETH-USDT-SWAP"}
HOUR_MS=3600000
URL="https://www.okx.com/api/v5/market/history-candles"


def now_utc():
    return datetime.now(timezone.utc)


def get_json(url: str, timeout: int=18) -> dict:
    req=urllib.request.Request(url,headers={"User-Agent":"quant-superlab-h091-research/1.0",
                                          "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        if r.status!=200:raise ValueError("non-200 upstream")
        return json.load(r)


def parse_okx(payload: dict) -> list[dict]:
    if str(payload.get("code"))!="0" or not isinstance(payload.get("data"),list):
        raise ValueError("OKX_RESPONSE_INVALID")
    bars=[]
    for row in payload["data"]:
        if len(row)<9 or str(row[8])!="1":continue
        ts=int(row[0])
        if ts%HOUR_MS:raise ValueError("NON_HOURLY_TIMESTAMP")
        o,h,l,c=(float(v) for v in row[1:5])
        if not all(math.isfinite(v) and v>0 for v in (o,h,l,c)) or l>min(o,c) or h<max(o,c):
            raise ValueError("INVALID_OHLC")
        bars.append({"ts":ts,"open":o,"high":h,"low":l,"close":c})
    if len({x["ts"] for x in bars})!=len(bars):raise ValueError("DUPLICATE_IN_PAGE")
    return bars


def fetch_okx(symbol: str, *, pages: int=12, get=get_json, now=None,
              pause:float=0.08) -> dict:
    if symbol not in SYMBOLS:raise ValueError("UNSUPPORTED_SYMBOL")
    if not isinstance(pages,int) or not 1<=pages<=100:raise ValueError("INVALID_PAGES")
    now=now or now_utc()
    if now.tzinfo is None:raise ValueError("NOW_NOT_AWARE")
    cursor=None;captured={};seen=set()
    for _ in range(pages):
        params={"instId":SYMBOLS[symbol],"bar":"1H","limit":"100"}
        if cursor is not None:params["after"]=str(cursor)
        url=URL+"?"+urllib.parse.urlencode(params)
        rows=parse_okx(get(url))
        if not rows:break
        oldest=min(r["ts"] for r in rows)
        if cursor is not None and oldest>=cursor:
            raise ValueError("PAGINATION_NOT_MOVING")
        if oldest in seen:raise ValueError("PAGINATION_CYCLE")
        seen.add(oldest)
        for row in rows:
            if row["ts"]+HOUR_MS<=int(now.timestamp()*1000):
                if row["ts"] in captured and captured[row["ts"]]!=row:
                    raise ValueError("CONFLICTING_CANDLE")
                captured[row["ts"]]=row
        cursor=oldest
        if len(rows)<80:break
        if pause:time.sleep(pause)
    bars=sorted(captured.values(),key=lambda r:r["ts"])
    if not bars:raise ValueError("NO_CONFIRMED_BARS")
    holes=[(a["ts"],b["ts"]) for a,b in zip(bars,bars[1:]) if b["ts"]-a["ts"]!=HOUR_MS]
    return {"schema":"H091.ohlc.v1","symbol":symbol,"instrument":SYMBOLS[symbol],
            "venue":"OKX","source":URL,"bar":"1H","retrieved_at_utc":now.isoformat(),
            "real_public_exchange_bars":True,"max_pages":pages,"bar_count":len(bars),
            "earliest_utc":datetime.fromtimestamp(bars[0]["ts"]/1000,timezone.utc).isoformat(),
            "latest_utc":datetime.fromtimestamp(bars[-1]["ts"]/1000,timezone.utc).isoformat(),
            "gaps":holes,"bars":bars,
            "independent_price_source_count":1,
            "execution_fills_verified":False}


def parse_bitget(payload:dict)->list[dict]:
    if str(payload.get("code"))!="00000" or not isinstance(payload.get("data"),list):
        raise ValueError("BITGET_RESPONSE_INVALID")
    result=[]
    for row in payload["data"]:
        if len(row)<7:raise ValueError("BITGET_CANDLE_SHAPE")
        ts=int(row[0])
        if ts%HOUR_MS:raise ValueError("NON_HOURLY_TIMESTAMP")
        o,h,l,c=(float(v) for v in row[1:5])
        if not all(math.isfinite(v) and v>0 for v in (o,h,l,c)) or l>min(o,c) or h<max(o,c):
            raise ValueError("INVALID_BITGET_OHLC")
        result.append({"ts":ts,"open":o,"high":h,"low":l,"close":c})
    if len({r["ts"] for r in result})!=len(result):
        raise ValueError("DUPLICATE_BITGET_CANDLE")
    return result


def fetch_bitget_recent(symbol:str, *, get=get_json, now=None)->dict:
    """Independent 100 last 1H USDT futures bars, not full historical replication."""
    if symbol not in SYMBOLS:raise ValueError("UNSUPPORTED_SYMBOL")
    now=now or now_utc()
    url="https://api.bitget.com/api/v3/market/history-candles?"+urllib.parse.urlencode({
        "category":"USDT-FUTURES","symbol":symbol+"USDT","interval":"1H",
        "type":"market","limit":"100"})
    bars=sorted((r for r in parse_bitget(get(url))
                 if r["ts"]+HOUR_MS<=int(now.timestamp()*1000)),key=lambda x:x["ts"])
    return {"symbol":symbol,"venue":"BITGET","instrument":symbol+"USDT",
            "bar":"1H","bars":bars,"bar_count":len(bars),
            "retrieved_at_utc":now.isoformat(),"source":url,
            "real_public_exchange_bars":True}


def compare_venues(primary:list[dict],secondary:list[dict])->dict:
    a={r["ts"]:r for r in primary};b={r["ts"]:r for r in secondary}
    common=sorted(set(a)&set(b))
    if not common:return {"matched_closed_bars":0,"max_close_divergence_bps":None,
                          "independent_venue_overlap_verified":False}
    diffs=[abs(a[t]["close"]-b[t]["close"])/((a[t]["close"]+b[t]["close"])/2)*10000 for t in common]
    return {"matched_closed_bars":len(common),"max_close_divergence_bps":max(diffs),
            "median_close_divergence_bps":sorted(diffs)[len(diffs)//2],
            "independent_venue_overlap_verified":True,
            "same_underlying_independent_economic_market":False,
            "notes":"cross-venue bar check only, not independent alpha nor executable arbitrage"}


def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()


def save_snapshot(record:dict,dirpath:Path)->dict:
    dirpath.mkdir(parents=True,exist_ok=True)
    symbol=record["symbol"]
    blob=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    path=dirpath/(symbol+"_OKX_1H.json")
    path.write_bytes(blob)
    return {"file":str(path),"sha256":digest(blob),"bars":record["bar_count"],
            "gaps":len(record["gaps"])}
