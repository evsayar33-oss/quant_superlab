"""H103 read-only fixed-hypothesis exploratory scan."""
from __future__ import annotations
import argparse,hashlib,json,sys,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h096"))
from market import fetch as okx_fetch
from engine import aggregate
sys.path.insert(0,str(ROOT/"research"/"h098"))
from venues import fetch as venue_fetch
spec=importlib.util.spec_from_file_location('h103_engine',ROOT/'research'/'h103'/'engine.py')
h103_engine=importlib.util.module_from_spec(spec)
spec.loader.exec_module(h103_engine)
HOUR=h103_engine.HOUR
evaluate=h103_engine.evaluate

def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def run(out,pages=8):
    if pages<1:raise ValueError("INVALID_PAGES")
    results=[];sources={};errors={}
    for symbol in ("BTC","ETH"):
        for venue in ("okx","gate","bitget","mexc"):
            key=f"{symbol}_{venue}"
            try:
                payload=okx_fetch(symbol,"1H",pages=pages) if venue=="okx" else venue_fetch(venue,symbol,"1H")
                bars=payload["bars"]
                if len(bars)<150:raise ValueError("INSUFFICIENT_HISTORY")
                sources[key]={"sha256":write(out/"sources"/f"{key}.json",{
                    "symbol":symbol,"venue":venue,"source":payload.get("source"),
                    "retrieved_at_utc":payload.get("retrieved_at_utc"),
                    "first_ms":bars[0]["ts"],"last_ms":bars[-1]["ts"],
                    "bars":len(bars),"gap_count":payload.get("gap_count")}),
                    "bars":len(bars),"gap_count":payload.get("gap_count")}
                for tf,series,step in (("1H",bars,HOUR),("4H",aggregate(bars,"4H"),4*HOUR)):
                    if len(series)<90:raise ValueError("INSUFFICIENT_"+tf)
                    for row in evaluate(series,step):
                        trades=row.pop("trades")
                        row["ledger_sha256"]=write(out/"ledgers"/f"{symbol}_{venue}_{tf}_{row['family']}_{row['side']}.json",trades)
                        row.update({"symbol":symbol,"venue":venue,"timeframe":tf,
                                    "historical_tail_is_prospective":False})
                        results.append(row)
            except Exception as exc:
                errors[key]={"type":type(exc).__name__,"detail":str(exc)[:180]}
    if not any(x["venue"]=="okx" for x in results) or not any(x["venue"]!="okx" for x in results):
        raise SystemExit("H103_PRIMARY_AND_SECONDARY_DATA_REQUIRED")
    report={"schema":"h103.preregistered.v1","research_only":True,
      "fixed_hypotheses":["TREND_24_72","BREAKOUT_24"],"candidate_family_relative_strength":"DEFERRED_NO_CAUSAL_CROSS_ASSET_ALIGNMENT",
      "assumed_roundtrip_bps":[20,40,80],"source_manifests":sources,"errors":errors,"cells":results,
      "cell_count":len(results),"n30_cells":sum(x["eligible_n30"] for x in results),
      "n30_net20_positive_cells":sum(x["eligible_n30"] and x["net_mean_r"]["20"] is not None and x["net_mean_r"]["20"]>0 for x in results),
      "n30_net80_positive_cells":sum(x["eligible_n30"] and x["net_mean_r"]["80"] is not None and x["net_mean_r"]["80"]>0 for x in results),
      "alpha_accepted":False,"real_execution_cost_verified":False,
      "prospective_oos_verified":False,"multiple_testing_adjusted":False,"research_complete":False,
      "limitations":["1H and 4H are derived from overlapping historical candles",
        "No prospective holdout, no funding or measured fill costs",
        "Dependent venues and hypotheses; descriptive outcomes only",
        "Non-overlap enforced per family and side, not across families or symbols"]}
    write(out/"summary.json",report)
    print(json.dumps({"cells":report["cell_count"],"n30":report["n30_cells"],
       "n30_positive_20bps":report["n30_net20_positive_cells"],"errors":errors,
       "alpha_accepted":False},sort_keys=True))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pages",type=int,default=8)
    p.add_argument("--out",default="results/h103")
    a=p.parse_args()
    run(ROOT/a.out,a.pages)
