"""H095 real closed-candle event inventory, read-only Actions artifact."""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h091"))
from market import fetch_okx,save_snapshot
from baseline import compress
from detectors import detect

def run(out:Path,pages=12):
    out.mkdir(parents=True,exist_ok=True)
    summary={"schema":"H095.research.v1","status":"EVENT_INVENTORY_NOT_BACKTEST",
             "real_data_errors":{},"instruments":{},"event_profits_verified":False,
             "live_orders":0,"production_modified":False,
             "missing_timeframes":["5m","15m","1D"],
             "missing_work":["cross_timeframe_alignment","event_family_target_fill_backtest",
                             "point_in_time_macro_fundamental_join","independent_oos",
                             "prospective_first_seen_trades"]}
    for symbol in ("BTC","ETH"):
        try:
            source=fetch_okx(symbol,pages=pages)
            manifest=save_snapshot(source,out/"source")
            entries={}
            for hours in (1,4):
                bars=compress(source["bars"],hours)
                tf=f"{hours}H"
                record=detect(bars,symbol,tf)
                raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
                path=out/f"{symbol}_{tf}_events.json"
                path.write_bytes(raw)
                entries[tf]={"bars":len(bars),"events":record["event_count"],
                             "counts":dict(sorted(Counter(e["kind"] for e in record["events"]).items())),
                             "sha256":hashlib.sha256(raw).hexdigest(),
                             "source_hash":manifest["sha256"]}
            summary["instruments"][symbol]={"source":manifest,"timeframes":entries,
                                             "data_gaps":len(source["gaps"])}
        except Exception as exc:
            summary["real_data_errors"][symbol]={"type":type(exc).__name__,"reason":str(exc)[:240]}
    (out/"summary.json").write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n")
    if summary["real_data_errors"] or len(summary["instruments"])!=2:
        raise SystemExit("H095_PROVIDER_OR_DATA_INCOMPLETE")
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pages",type=int,default=12)
    p.add_argument("--out",default="results/h095")
    args=p.parse_args()
    result=run(ROOT/args.out,args.pages)
    print(json.dumps({"status":result["status"],"instruments":{
        k:v["timeframes"] for k,v in result["instruments"].items()},
        "real_data_errors":result["real_data_errors"]},sort_keys=True))
