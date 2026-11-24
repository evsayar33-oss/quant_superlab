"""H104 deterministic long-history integrity checks; no synthetic bars."""
from __future__ import annotations
import hashlib,json,math,time
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

def gate_history(symbol,lookback_days=180,get=None,now=None,page_size=900,max_pages=10,
                 page_attempts=3,sleep=time.sleep):
    if symbol not in ("BTC","ETH") or not 1<=lookback_days<=365 or not 1<=page_size<=1000 or not 1<=max_pages<=100:
        raise ValueError("INVALID_HISTORY_ARGS")
    if not 1<=page_attempts<=3:raise ValueError("INVALID_PAGE_ATTEMPTS")
    if get is None:
        from urllib.request import Request,urlopen
        def get(url):
            with urlopen(Request(url,headers={"User-Agent":"quant-superlab-h104-research/1.0",
                                             "Cache-Control":"no-cache"}),timeout=20) as r:
                return json.load(r)
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("NAIVE_TIME")
    end=(int(now.timestamp()*1000)//HOUR)*HOUR
    start=end-lookback_days*24*HOUR
    all_rows=[];cursor=start;pages=0;retried_pages=[]
    while cursor<end and pages<max_pages:
        page_end=min(end,cursor+page_size*HOUR)
        failures=[]
        for attempt in range(page_attempts):
            try:
                # A repeated URL can return the same stale page. The last attempt
                # uses two smaller exact windows; never filter invalid rows away.
                step=((page_size+1)//2)*HOUR if attempt==2 else page_size*HOUR
                parsed=[]
                for lo in range(cursor,page_end,step):
                    hi=min(lo+step,page_end)
                    url=GATE_URL+"?"+urlencode({"contract":symbol+"_USDT","interval":"1h",
                         "from":lo//1000,"to":hi//1000-1})
                    raw=get(url)
                    if not isinstance(raw,list):raise ValueError("GATE_RESPONSE_INVALID")
                    part=[{"ts":int(r["t"])*1000,"open":r["o"],"high":r["h"],
                           "low":r["l"],"close":r["c"]} for r in raw]
                    if any(not lo<=int(r["ts"])<hi for r in part):
                        times=[r['ts'] for r in part]
                        raise ValueError(f"GATE_OUT_OF_WINDOW requested={lo}:{hi} received={min(times)}:{max(times)}")
                    part,gaps=canonical(part)
                    if (gaps or len(part)!=(hi-lo)//HOUR
                            or part[0]["ts"]!=lo or part[-1]["ts"]!=hi-HOUR):
                        raise ValueError("GATE_INCOMPLETE_PAGE")
                    parsed.extend(part)
                parsed,gaps=canonical(parsed)
                if (gaps or len(parsed)!=(page_end-cursor)//HOUR
                        or parsed[0]["ts"]!=cursor or parsed[-1]["ts"]!=page_end-HOUR):
                    raise ValueError("GATE_INCOMPLETE_PAGE")
                break
            except (ValueError,KeyError,TypeError,OSError) as exc:
                failures.append(type(exc).__name__+":"+str(exc)[:160])
                if attempt+1==page_attempts:raise
                sleep(2**attempt)
        if failures:
            retried_pages.append({"from_ms":cursor,"to_ms":page_end,
                                  "attempts":len(failures)+1,"failures":failures})
        all_rows.extend(parsed)
        cursor=page_end;pages+=1
    rows,gaps=canonical(all_rows)
    if not rows:raise ValueError("NO_HISTORY")
    return {"venue":"gate","symbol":symbol,"bars":rows,"gaps":gaps,"pages":pages,
            "retried_pages":retried_pages,
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
       "pages":payload.get("pages"),"retried_pages":payload.get("retried_pages",[]),
       "research_only":True}
