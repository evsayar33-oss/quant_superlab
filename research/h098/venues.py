"""H098 read-only independent Binance USD-M and Bybit linear candle adapters.

Sources are NEVER substituted for OKX execution evidence. Fail closed when
provider inaccessible. All observations must be finalized, UTC aligned.
"""
from __future__ import annotations
import json
import math
from datetime import datetime,timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen

TF={"5m":300000,"15m":900000,"1H":3600000,"4H":14400000,"1D":86400000}
SYMBOLS={"BTC":"BTCUSDT","ETH":"ETHUSDT"}
BINANCE="https://fapi.binance.com/fapi/v1/klines"
BYBIT="https://api.bybit.com/v5/market/kline"
BYBIT_TF={"5m":"5","15m":"15","1H":"60","4H":"240","1D":"D"}
BINANCE_TF={"5m":"5m","15m":"15m","1H":"1h","4H":"4h","1D":"1d"}


def http(url):
    req=Request(url,headers={"User-Agent":"quant-superlab-h098-research/1.0",
                             "Accept":"application/json"})
    with urlopen(req,timeout=18) as r:
        if r.status!=200:raise ValueError("HTTP_NOT_OK")
        return json.load(r)


def validate(rows,tf,now_ms):
    step=TF[tf];out={}
    for r in rows:
        ts=int(r["ts"]);o,h,l,c=[float(r[k]) for k in ("open","high","low","close")]
        if ts%step or not all(math.isfinite(x) and x>0 for x in (o,h,l,c)):
            raise ValueError("BAD_PRICE_OR_TIMESTAMP")
        if l>min(o,c) or h<max(o,c):raise ValueError("BAD_OHLC")
        if ts+step>now_ms:continue
        b={"ts":ts,"open":o,"high":h,"low":l,"close":c}
        if ts in out and out[ts]!=b:raise ValueError("DUPLICATE_CONFLICT")
        out[ts]=b
    result=sorted(out.values(),key=lambda x:x["ts"])
    if not result:raise ValueError("NO_CLOSED_BARS")
    return result


def fetch(venue,symbol,tf,limit=800,get=http,now=None):
    if venue not in ("binance","bybit") or symbol not in SYMBOLS or tf not in TF:
        raise ValueError("INVALID_INSTRUMENT")
    if not isinstance(limit,int) or not 100<=limit<=1000:raise ValueError("INVALID_LIMIT")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("NAIVE_TIME")
    now_ms=int(now.timestamp()*1000)
    if venue=="binance":
        url=BINANCE+"?"+urlencode({"symbol":SYMBOLS[symbol],"interval":BINANCE_TF[tf],
                                   "limit":limit})
        payload=get(url)
        if not isinstance(payload,list):raise ValueError("BINANCE_RESPONSE_INVALID")
        rows=[{"ts":r[0],"open":r[1],"high":r[2],"low":r[3],"close":r[4]} for r in payload]
    else:
        url=BYBIT+"?"+urlencode({"category":"linear","symbol":SYMBOLS[symbol],
                                 "interval":BYBIT_TF[tf],"limit":limit})
        payload=get(url)
        if str(payload.get("retCode"))!="0":raise ValueError("BYBIT_RESPONSE_INVALID")
        rows=[{"ts":r[0],"open":r[1],"high":r[2],"low":r[3],"close":r[4]}
              for r in payload["result"]["list"]]
    data=validate(rows,tf,now_ms)
    return {"schema":"H098.independent_candles.v1","venue":venue,"symbol":symbol,
            "instrument":SYMBOLS[symbol],"tf":tf,"source":url,
            "retrieved_at_utc":now.isoformat(),"bars":data,"count":len(data),
            "gap_count":sum(y["ts"]-x["ts"]!=TF[tf] for x,y in zip(data,data[1:])),
            "execution_verified":False}
