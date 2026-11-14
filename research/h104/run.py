"""H104 longer-history fixed-parameter replication, research only."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h104"))
from history import gate_history,manifest,canonical,HOUR
sys.path.insert(0,str(ROOT/"research"/"h096"))
from market import fetch as okx_fetch
from engine import aggregate
spec=importlib.util.spec_from_file_location("h103_engine",ROOT/"research"/"h103"/"engine.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
evaluate=module.evaluate
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()
def run(out,days=180,okx_pages=60):
    if not 1<=days<=365 or not 1<=okx_pages<=80:raise ValueError("INVALID_ARGS")
    results=[];sources={};errors={}
    for symbol in ("BTC","ETH"):
        for venue in ("okx","gate"):
            key=f"{symbol}_{venue}"
            try:
                if venue=="gate":
                    p=gate_history(symbol,lookback_days=days,max_pages=12)
                else:
                    o=okx_fetch(symbol,"1H",pages=okx_pages)
                    rows,gaps=canonical(o["bars"])
                    p={"venue":"okx","symbol":symbol,"bars":rows,"gaps":gaps,
                       "pages":okx_pages,"coverage_ratio":len(rows)/(days*24),
                       "complete_window":len(rows)>=days*24 and not gaps}
                sources[key]=manifest(p)
                sources[key]["bars_sha256"]=save(out/"bars"/f"{key}.json",p["bars"])
                for tf,series,step in (("1H",p["bars"],HOUR),("4H",aggregate(p["bars"],"4H"),4*HOUR)):
                    if len(series)<90:continue
                    for row in evaluate(series,step):
                        trades=row.pop("trades")
                        row["ledger_sha256"]=save(out/"ledgers"/f"{key}_{tf}_{row['family']}_{row['side']}.json",trades)
                        row.update({"venue":venue,"symbol":symbol,"timeframe":tf,
                           "historical_tail_is_prospective":False})
                        results.append(row)
            except Exception as exc:
                errors[key]={"type":type(exc).__name__,"detail":str(exc)[:200]}
    if not any(x["venue"]=="okx" for x in results) or not any(x["venue"]=="gate" for x in results):
        raise SystemExit("H104_BOTH_VENUES_REQUIRED")
    report={"schema":"h104.long_history.v1","requested_days":days,"sources":sources,"errors":errors,
      "cells":results,"cell_count":len(results),
      "n30_cells":sum(x["eligible_n30"] for x in results),
      "n30_positive_20bps":sum(x["eligible_n30"] and x["net_mean_r"]["20"] is not None and x["net_mean_r"]["20"]>0 for x in results),
      "alpha_accepted":False,"prospective_oos_verified":False,"execution_verified":False,
      "multiple_testing_adjusted":False,"research_only":True,
      "limitations":["Gate and OKX are dependent crypto markets, not independent prospective samples",
       "Different venue coverage lengths; no equal-period causal comparison enforced",
       "Historical 70/30 tail is not untouched prospective OOS",
       "No measured fill costs, funding, portfolio accounting or familywise correction"]}
    save(out/"summary.json",report)
    print(json.dumps({"cells":report["cell_count"],"n30":report["n30_cells"],
        "n30_positive_20bps":report["n30_positive_20bps"],"sources":sources,"errors":errors},sort_keys=True))
    return report
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--days",type=int,default=180)
    a.add_argument("--okx-pages",type=int,default=60);a.add_argument("--out",default="results/h104")
    v=a.parse_args();run(ROOT/v.out,v.days,v.okx_pages)
