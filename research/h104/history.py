"""H104 deterministic long-history integrity checks; no synthetic bars."""
from __future__ import annotations
import hashlib,json,math
from datetime import datetime,timezone
from urllib.parse import urlencode
HOUR=3600000
GATE_URL="https://api.gateio.ws/api/v4/futures/usdt/candlesticks"
def canonical(rows,step=HOUR):
    found={}
    for b in rows:
        t=int(b["ts"]);o,h,l,c=(float(b[k]) for k in ("open","high","low","close"))
        if t%step or not all(math.isfinite(v) and v>0 for v in (o,h,l,c)) or l>min(o,c) or h<max(o,c):
            raise ValueError("INVALID_OHLC_OR_TIMESTAMP")
        item={"ts":t,"open":o,"high":h,"low":l,"close":c}
        if t in found and found[t]!=item:raise ValueError("CONFLICTING_OVERLAP")
        found[t]=item
    ordered=sorted(found.values(),key=lambda x:x["ts"])
    gaps=[{"after_ms":a["ts"],"before_ms":b["ts"],"missing_bars":(b["ts"]-a["ts"])//step-1}
          for a,b in zip(ordered,ordered[1:]) if b["ts"]-a["ts"]!=step]
    return ordered,gaps

def gate_history(symbol,lookback_days=180,get=None,now=None,page_size=900,max_pages=10):
    if symbol not in ("BTC","ETH") or not 1<=lookback_days<=365 or not 1<=page_size<=1000 or not 1<=max_pages<=100:
        raise ValueError("INVALID_HISTORY_ARGS")
    if get is None:
        from urllib.request import Request,urlopen
        def get(url):
            with urlopen(Request(url,headers={"User-Agent":"quant-superlab-h104-research/1.0"}),timeout=20) as r:
                return json.load(r)
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("NAIVE_TIME")
    end=(int(now.timestamp()*1000)//HOUR)*HOUR
    start=end-lookback_days*24*HOUR
    all_rows=[];cursor=start;pages=0
    while cursor<end and pages<max_pages:
        page_end=min(end,cursor+page_size*HOUR)
        url=GATE_URL+"?"+urlencode({"contract":symbol+"_USDT","interval":"1h",
             "from":cursor//1000,"to":page_end//1000-1})
        raw=get(url)
        if not isinstance(raw,list):raise ValueError("GATE_RESPONSE_INVALID")
        parsed=[]
        for r in raw:
            parsed.append({"ts":int(r["t"])*1000,"open":r["o"],"high":r["h"],
                           "low":r["l"],"close":r["c"]})
        if any(not cursor<=int(r["ts"])<page_end for r in parsed):
            raise ValueError("GATE_OUT_OF_WINDOW")
        all_rows.extend(parsed)
        cursor=page_end;pages+=1
    rows,gaps=canonical(all_rows)
    if not rows:raise ValueError("NO_HISTORY")
    return {"venue":"gate","symbol":symbol,"bars":rows,"gaps":gaps,"pages":pages,
            "requested_start_ms":start,"requested_end_ms":end,
            "complete_window":cursor>=end and rows[0]["ts"]<=start and rows[-1]["ts"]>=end-HOUR and not gaps,
            "coverage_ratio":len(rows)/(lookback_days*24),
            "last_cursor_ms":cursor,"source":"Gate futures USDT 1h timestamp pagination"}

def manifest(payload):
    rows,gaps=canonical(payload["bars"])
    raw=json.dumps(rows,sort_keys=True,separators=(",",":")).encode()
    return {"venue":payload["venue"],"symbol":payload["symbol"],"bar_count":len(rows),
       "first_ms":rows[0]["ts"],"last_ms":rows[-1]["ts"],"gap_count":len(gaps),
       "missing_bars":sum(g["missing_bars"] for g in gaps),
       "sha256":hashlib.sha256(raw).hexdigest(),
       "coverage_ratio":payload.get("coverage_ratio"),
       "complete_window":payload.get("complete_window",False),
       "pages":payload.get("pages"),"research_only":True}
