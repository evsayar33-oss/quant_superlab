"""H096 real multi-timeframe research runner. Artifact-only; no ACCEPT."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h095"))
from detectors import detect
from market import fetch,save
from engine import evaluate,aggregate,PARENT

def run(out,pages=12):
    out.mkdir(parents=True,exist_ok=True)
    report={"schema":"H096.program.v1","status":"RESEARCH_ONLY_NOT_VERIFIED",
            "sources":{},"results":{},"errors":{},"research_complete":False,
            "alpha_accepted":False,"production_modified":False,
            "costs":"assumed 10/20/40bps roundtrip; funding/spread/impact unverified",
            "holdout":"descriptive historical 70/30, not fresh OOS",
            "timeframe_limitations":[]}
    for symbol in ("BTC","ETH"):
        inputs={}
        for tf in ("5m","15m","1H","1D"):
            try:
                raw=fetch(symbol,tf,pages=pages)
                manifest=save(raw,out/"sources")
                inputs[tf]=raw["bars"]
                report["sources"][f"{symbol}_{tf}"]=manifest
            except Exception as e:
                report["errors"][f"{symbol}_{tf}"]={"type":type(e).__name__,"reason":str(e)[:240]}
        if "1H" in inputs:
            inputs["4H"]=aggregate(inputs["1H"],"4H")
            if inputs["4H"]:
                blob=(json.dumps(inputs["4H"],sort_keys=True,separators=(",",":"))+"\n").encode()
                report["sources"][f"{symbol}_4H"]={"derived_from":f"{symbol}_1H",
                                                     "sha256":hashlib.sha256(blob).hexdigest(),
                                                     "count":len(inputs["4H"])}
        events={}
        for tf,bars in inputs.items():
            try:
                if len(bars)<30:
                    report["timeframe_limitations"].append(f"{symbol}_{tf}: LESS_THAN_30_CLOSED_BARS")
                    continue
                record=detect(bars,symbol,tf)
                events[tf]=record["events"]
                blob=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
                (out/f"{symbol}_{tf}_events.json").write_bytes(blob)
                report["results"][f"{symbol}_{tf}"]={"bars":len(bars),
                    "events":record["event_count"],
                    "event_counts":dict(Counter(x["kind"] for x in record["events"])),
                    "event_sha256":hashlib.sha256(blob).hexdigest(),
                    "performance_status":"NOT_TESTABLE_NO_PARENT_OR_INSUFFICIENT_BARS"}
            except Exception as e:
                report["errors"][f"{symbol}_{tf}_detector"]={"type":type(e).__name__,
                                                            "reason":str(e)[:240]}
        for tf,parent in PARENT.items():
            if tf not in events or parent not in events:continue
            bars=inputs[tf]
            if len(bars)<100:
                report["timeframe_limitations"].append(f"{symbol}_{tf}: LESS_THAN_100_BARS_FOR_SPLIT")
                continue
            result=evaluate(bars,events[tf],events[parent],tf)
            raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
            (out/f"{symbol}_{tf}_proxy_performance.json").write_bytes(raw)
            report["results"][f"{symbol}_{tf}"].update({
                "performance_status":"DESCRIPTIVE_NOT_VALIDATED",
                "trial_count":result["trial_count"],"signals":result["signal_count"],
                "performance_sha256":hashlib.sha256(raw).hexdigest()})
    (out/"summary.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    if report["errors"] or not report["results"]:
        raise SystemExit("H096_SOURCE_OR_DETECTION_INCOMPLETE")
    print(json.dumps({"results":{k:{"bars":v["bars"],"events":v["events"],
                    "status":v["performance_status"]} for k,v in report["results"].items()},
                      "errors":report["errors"],"alpha_accepted":False},sort_keys=True))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pages",type=int,default=12)
    p.add_argument("--out",default="results/h096")
    args=p.parse_args()
    run(ROOT/args.out,args.pages)
