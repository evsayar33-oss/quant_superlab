"""H089 H056 *source overlap diagnostic*, not strategy replication or alpha.

Fetch recent historical BTC/ETH funding settlements independently from OKX
and Bitget. Align on exchange timestamp, never interpolate missing timestamps.
Funding intervals / contract listing histories may differ: no automatic PnL.
"""
from __future__ import annotations
import argparse
import math
import statistics
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"research"/"h088"))
from evidence import append_chain,canonical,stamp,utcnow
from venues import get,SYMBOLS

OUT=ROOT/"decisions"/"evidence"/"h089_funding_overlap.jsonl"


def parse_history(venue,symbol,raw):
    if venue=="okx":
        if str(raw.get("code"))!="0":raise ValueError("OKX history API")
        rows=raw.get("data",[])
        out=[]
        for r in rows:
            t=int(r["fundingTime"]);rate=float(r["realizedRate"] if r.get("realizedRate") not in (None,"") else r["fundingRate"])
            out.append((t,rate))
    elif venue=="bitget":
        if str(raw.get("code"))!="00000":raise ValueError("Bitget history API")
        rows=raw.get("data",[])
        if isinstance(rows,dict):rows=rows.get("resultList") or rows.get("list") or []
        out=[]
        for r in rows:
            t=int(r["fundingTime"])
            rate=float(r["fundingRate"])
            out.append((t,rate))
    else:raise ValueError("unsupported venue")
    if not isinstance(rows,list):raise ValueError("bad funding rows")
    if len(out)!=len(set(t for t,_ in out)):raise ValueError("duplicate funding timestamp")
    if any(t<=0 or not math.isfinite(v) or abs(v)>0.1 for t,v in out):
        raise ValueError("invalid funding row")
    return dict(out)


def fetch_history(venue,symbol,fetch=get):
    base=symbol.removesuffix("USDT")
    if venue=="okx":
        url="https://www.okx.com/api/v5/public/funding-rate-history?instId="+base+"-USDT-SWAP&limit=100"
    elif venue=="bitget":
        url="https://api.bitget.com/api/v2/mix/market/history-fund-rate?symbol="+symbol+"&productType=USDT-FUTURES&pageSize=100&pageNo=1"
    else:raise ValueError("unknown venue")
    return parse_history(venue,symbol,fetch(url))


def compare(okx,bitget):
    common=sorted(set(okx)&set(bitget))
    if not common:return {"overlap_count":0,"overlap_timestamps":[],"mean_diff":None,
                           "max_abs_diff":None,"source_agreement_verified":False}
    diffs=[okx[t]-bitget[t] for t in common]
    return {"overlap_count":len(common),"overlap_timestamps":common,
            "mean_diff":statistics.mean(diffs),
            "max_abs_diff":max(abs(v) for v in diffs),
            "positive_diff_count":sum(v>0 for v in diffs),
            "source_agreement_verified":False,
            "notes":"different venues have legitimately different funding; no PnL inferred"}


def collect(fetch=get,now=None):
    now=now or utcnow()
    rec={"schema":"H089.funding_overlap.v1","collected_at_utc":stamp(now),
         "kind":"RECENT_HISTORICAL_CROSS_VENUE_FUNDING_DIAGNOSTIC_NOT_H056_BACKTEST",
         "source_rows":{},"source_records":{},"comparisons":{},"errors":{},
         "H056_independent_strategy_replay_verified":False}
    for symbol in SYMBOLS:
        sources={}
        for venue in ("okx","bitget"):
            key=venue+":"+symbol
            try:
                sources[venue]=fetch_history(venue,symbol,fetch)
                rec["source_rows"][key]=len(sources[venue])
                rec["source_records"][key]=[{"funding_time_ms":t,"rate":v}
                                             for t,v in sorted(sources[venue].items())]
            except Exception as e:
                rec["errors"][key]=type(e).__name__+": "+str(e)[:150]
        if len(sources)==2:rec["comparisons"][symbol]=compare(sources["okx"],sources["bitget"])
    rec["two_source_overlap_present"]=all(
        rec["comparisons"].get(s,{}).get("overlap_count",0)>0 for s in SYMBOLS)
    return rec


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--path",default=str(OUT))
    args=p.parse_args()
    r=collect()
    h=append_chain(r,args.path)
    print(canonical({"hash":h,"source_rows":r["source_rows"],
        "overlap":{k:v["overlap_count"] for k,v in r["comparisons"].items()},
        "errors":r["errors"],"independent_H056_replay":False}))
    if not r["two_source_overlap_present"]:
        raise SystemExit("NO_INDEPENDENT_FUNDING_OVERLAP: evidence saved, no backtest claim")


if __name__=="__main__":main()
