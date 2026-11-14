"""H101 read-only market research. Never mutate production or H089."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h096"))
from market import fetch as okx_fetch
from engine import aggregate
sys.path.insert(0,str(ROOT/"research"/"h098"))
from venues import fetch as venue_fetch
from audit import instrument_audit,aggregate_report

def emit(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def run(out,pages=8):
    out.mkdir(parents=True,exist_ok=True)
    results={};errors={};sources={}
    for sym in ("BTC","ETH"):
        for venue in ("okx","gate","bitget","mexc"):
            base={}
            for tf in ("15m","1H"):
                k=f"{sym}_{tf}_{venue}"
                try:
                    payload=okx_fetch(sym,tf,pages=pages) if venue=="okx" else venue_fetch(venue,sym,tf)
                    base[tf]=payload["bars"]
                    sources[k]={"sha256":emit(out/"source_manifests"/f"{k}.json",{
                        "venue":venue,"symbol":sym,"tf":tf,
                        "source_url":payload.get("source"),
                        "count":payload.get("count"),"gap_count":payload.get("gap_count"),
                        "retrieved_at_utc":payload.get("retrieved_at_utc"),
                        "first_bar_ms":base[tf][0]["ts"],"last_bar_ms":base[tf][-1]["ts"]}),
                        "count":len(base[tf]),"gap_count":payload.get("gap_count")}
                except Exception as e:
                    errors[k]={"type":type(e).__name__,"category":getattr(e,"category","OTHER"),
                               "detail":str(e)[:180]}
            if not all(x in base for x in ("15m","1H")):continue
            parents={"15m":base["1H"],"1H":aggregate(base["1H"],"4H")}
            for tf in ("15m","1H"):
                k=f"{sym}_{tf}_{venue}"
                try:
                    bars=base[tf]
                    if len(bars)<100 or len(parents[tf])<30:raise ValueError("INSUFFICIENT_BAR_HISTORY")
                    # Fixed historical split by timestamp within each venue.
                    split_ms=bars[int(len(bars)*.70)]["ts"]
                    result=instrument_audit(bars,parents[tf],sym,tf,split_ms)
                    ledger=result.pop("ledger")
                    result["ledger_sha256"]=emit(out/"trade_ledgers"/f"{k}.json",ledger)
                    results[k]=result
                except Exception as e:
                    errors[k]={"type":type(e).__name__,"category":"ANALYSIS",
                               "detail":str(e)[:180]}
    summary=aggregate_report(results,errors)
    summary["sources"]=sources
    summary["venue_results"]={k:{x:y for x,y in v.items() if x!="configurations"} for k,v in results.items()}
    summary["venue_configurations"]={k:v["configurations"] for k,v in results.items()}
    summary["independent_venue_comparison_sets"]=sum(k.endswith(("_gate","_bitget","_mexc")) for k in results)
    emit(out/"summary.json",summary)
    if summary["independent_venue_comparison_sets"]==0 or not any(k.endswith("_okx") for k in results):
        raise SystemExit("H101_NO_PRIMARY_OR_INDEPENDENT_DATA")
    print(json.dumps({"independent_venue_comparison_sets":summary["independent_venue_comparison_sets"],
      "configs_three_venue_n30":summary["configs_three_venue_n30"],
      "configs_three_venue_positive_at_80bps":summary["configs_three_venue_positive_at_80bps"],
      "configs_tail_positive_at_80bps":summary["configs_tail_positive_at_80bps"],
      "alpha_accepted":summary["alpha_accepted"],"errors":errors},sort_keys=True))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pages",type=int,default=8)
    p.add_argument("--out",default="results/h101")
    a=p.parse_args()
    run(ROOT/a.out,a.pages)
