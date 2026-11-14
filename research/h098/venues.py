"""Independent USDT perpetual market candles. Read-only, never relabel spot as perp.

Provider errors remain visible. Alternate providers are independent venues,
not alternate hostnames of the same exchange.
"""
from __future__ import annotations
import json
import math
from datetime import datetime,timezone
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

TF={"5m":300000,"15m":900000,"1H":3600000,"4H":14400000,"1D":86400000}
SYMBOLS={"BTC":"BTCUSDT","ETH":"ETHUSDT"}
VENUES=("binance","bybit","gate","bitget","mexc")
BINANCE="https://fapi.binance.com/fapi/v1/klines"
BYBIT="https://api.bybit.com/v5/market/kline"
GATE="https://api.gateio.ws/api/v4/futures/usdt/candlesticks"
BITGET="https://api.bitget.com/api/v2/mix/market/candles"
MEXC="https://contract.mexc.com/api/v1/contract/kline"
BYBIT_TF={"5m":"5","15m":"15","1H":"60","4H":"240","1D":"D"}
BINANCE_TF={"5m":"5m","15m":"15m","1H":"1h","4H":"4h","1D":"1d"}
GATE_TF={"5m":"5m","15m":"15m","1H":"1h","4H":"4h","1D":"1d"}
BITGET_TF={"5m":"5m","15m":"15m","1H":"1H","4H":"4H","1D":"1D"}
MEXC_TF={"5m":"Min5","15m":"Min15","1H":"Min60","4H":"Hour4","1D":"Day1"}

class ProviderError(ValueError):
    def __init__(self,category,venue,detail=""):
        self.category=category
        self.venue=venue
        self.detail=str(detail)[:160]
        super().__init__(f"{venue}:{category}:{self.detail}")

def http(url):
    req=Request(url,headers={"User-Agent":"quant-superlab-h098-research/1.1",
                             "Accept":"application/json"})
    try:
        with urlopen(req,timeout=18) as r:
            if r.status!=200:raise ProviderError("HTTP_STATUS","unknown",r.status)
            return json.load(r)
    except HTTPError as e:
        raise ProviderError("HTTP_"+str(e.code),"unknown",e.reason) from e
    except (URLError,TimeoutError) as e:
        raise ProviderError("NETWORK","unknown",type(e).__name__) from e

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
    if venue not in VENUES or symbol not in SYMBOLS or tf not in TF:
        raise ValueError("INVALID_INSTRUMENT")
    if not isinstance(limit,int) or not 100<=limit<=1000:raise ValueError("INVALID_LIMIT")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("NAIVE_TIME")
    now_ms=int(now.timestamp()*1000)
    sym=SYMBOLS[symbol]
    if venue=="binance":
        url=BINANCE+"?"+urlencode({"symbol":sym,"interval":BINANCE_TF[tf],"limit":limit})
    elif venue=="bybit":
        url=BYBIT+"?"+urlencode({"category":"linear","symbol":sym,
                                 "interval":BYBIT_TF[tf],"limit":limit})
    elif venue=="gate":
        url=GATE+"?"+urlencode({"contract":symbol+"_USDT","interval":GATE_TF[tf],
                                "limit":min(limit,1000)})
    elif venue=="bitget":
        url=BITGET+"?"+urlencode({"symbol":sym,"productType":"USDT-FUTURES",
                                  "granularity":BITGET_TF[tf],"limit":min(limit,1000)})
    else:
        url=MEXC+"/"+symbol+"_USDT?"+urlencode({"interval":MEXC_TF[tf],
                                                "start":int(now_ms/1000)-TF[tf]//1000*limit,
                                                "end":int(now_ms/1000)})
    try:payload=get(url)
    except ProviderError as e:raise ProviderError(e.category,venue,e.detail) from e
    except Exception as e:raise ProviderError("TRANSPORT",venue,type(e).__name__) from e
    try:
        if venue=="binance":
            if not isinstance(payload,list):raise ValueError("BINANCE_RESPONSE_INVALID")
            rows=[{"ts":r[0],"open":r[1],"high":r[2],"low":r[3],"close":r[4]} for r in payload]
        elif venue=="bybit":
            if str(payload.get("retCode"))!="0":raise ValueError("BYBIT_CODE_"+str(payload.get("retCode")))
            rows=[{"ts":r[0],"open":r[1],"high":r[2],"low":r[3],"close":r[4]}
                  for r in payload["result"]["list"]]
        elif venue=="gate":
            if not isinstance(payload,list):raise ValueError("GATE_RESPONSE_INVALID")
            rows=[{"ts":int(r["t"])*1000,"open":r["o"],"high":r["h"],
                   "low":r["l"],"close":r["c"]} for r in payload]
        elif venue=="bitget":
            if str(payload.get("code"))!="00000":raise ValueError("BITGET_CODE_"+str(payload.get("code")))
            rows=[{"ts":r[0],"open":r[1],"high":r[2],"low":r[3],"close":r[4]}
                  for r in payload["data"]]
        else:
            if not payload.get("success"):raise ValueError("MEXC_RESPONSE_INVALID")
            d=payload["data"]
            rows=[{"ts":int(t)*1000,"open":o,"high":h,"low":l,"close":c}
                  for t,o,h,l,c in zip(d["time"],d["open"],d["high"],d["low"],d["close"])]
            if len({len(d[k]) for k in ("time","open","high","low","close")})!=1:
                raise ValueError("MEXC_ARRAY_LENGTH_MISMATCH")
        data=validate(rows,tf,now_ms)
    except (KeyError,IndexError,TypeError,ValueError,OverflowError) as e:
        raise ProviderError("INVALID_RESPONSE",venue,str(e)) from e
    return {"schema":"H098.independent_candles.v2","venue":venue,"symbol":symbol,
            "instrument":sym if venue not in ("gate","mexc") else symbol+"_USDT",
            "market_type":"USDT_PERPETUAL","tf":tf,"source":url,
            "retrieved_at_utc":now.isoformat(),"bars":data,"count":len(data),
            "gap_count":sum(y["ts"]-x["ts"]!=TF[tf] for x,y in zip(data,data[1:])),
            "execution_verified":False}
