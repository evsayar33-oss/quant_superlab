"""H096 direct real OKX native 5m, 15m, 1H and 1D UTC closed bars.

No resampling hourly to 5m. Strict monotonic cursor, dedup, integrity,
last closed bar, and explicit provenance. Fail closed; no synthetic fallback.
"""
from __future__ import annotations
import hashlib
import json
import math
import time
from datetime import datetime,timezone
from urllib.parse import urlencode
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h091"))
from market import get_json,SYMBOLS

BARS={"5m":("5m",300000),"15m":("15m",900000),"1H":("1H",3600000),
      "1D":("1Dutc",86400000)}
URL="https://www.okx.com/api/v5/market/history-candles"


def parse(payload,tf):
    if tf not in BARS:raise ValueError("unsupported tf")
    if str(payload.get("code"))!="0" or not isinstance(payload.get("data"),list):
        raise ValueError("OKX_INVALID_RESPONSE")
    step=BARS[tf][1];rows=[]
    for r in payload["data"]:
        if len(r)<9:raise ValueError("OKX_SHORT_ROW")
        if str(r[8])!="1":continue
        ts=int(r[0]);o,h,l,c=map(float,r[1:5])
        if ts%step or not all(math.isfinite(x) and x>0 for x in (o,h,l,c)) or l>min(o,c) or h<max(o,c):
            raise ValueError("OKX_BAD_BAR")
        rows.append({"ts":ts,"open":o,"high":h,"low":l,"close":c})
    if len({r["ts"] for r in rows})!=len(rows):raise ValueError("OKX_DUPLICATE_PAGE")
    return rows


def fetch(symbol,tf,pages=12,get=get_json,now=None,pause=.08):
    if symbol not in SYMBOLS or tf not in BARS or not isinstance(pages,int) or not 1<=pages<=80:
        raise ValueError("INVALID_FETCH_ARGS")
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("NAIVE_NOW")
    step=BARS[tf][1];cursor=None;data={};seen=set()
    for _ in range(pages):
        params={"instId":SYMBOLS[symbol],"bar":BARS[tf][0],"limit":"100"}
        if cursor is not None:params["after"]=str(cursor)
        rows=parse(get(URL+"?"+urlencode(params)),tf)
        if not rows:break
        oldest=min(x["ts"] for x in rows)
        if cursor is not None and oldest>=cursor:raise ValueError("PAGINATION_STALLED")
        if oldest in seen:raise ValueError("PAGINATION_LOOP")
        seen.add(oldest)
        for b in rows:
            if b["ts"]+step>int(now.timestamp()*1000):continue
            if b["ts"] in data and data[b["ts"]]!=b:raise ValueError("CONFLICTING_CANDLES")
            data[b["ts"]]=b
        cursor=oldest
        if len(rows)<80:break
        if pause:time.sleep(pause)
    rows=sorted(data.values(),key=lambda x:x["ts"])
    if not rows:raise ValueError("NO_CLOSED_CANDLES")
    gaps=sum(y["ts"]-x["ts"]!=step for x,y in zip(rows,rows[1:]))
    return {"schema":"H096.real_market.v1","symbol":symbol,"tf":tf,
            "venue":"OKX","instrument":SYMBOLS[symbol],
            "source":URL,"bar_request":BARS[tf][0],"retrieved_at_utc":now.isoformat(),
            "bars":rows,"count":len(rows),"gap_count":gaps,
            "true_fills":False,"funding_costs_verified":False}


def save(record,out):
    out.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    path=out/f"{record['symbol']}_{record['tf']}_OKX.json"
    path.write_bytes(data)
    return {"path":str(path),"sha256":hashlib.sha256(data).hexdigest(),
            "count":record["count"],"gaps":record["gap_count"]}
