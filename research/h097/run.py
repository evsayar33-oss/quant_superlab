"""H097 evidence artifacts: real OHLC + funding observations; no production writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h095"))
from detectors import detect
from audit import audit,regimes
from funding import fetch as fetch_funding
sys.path.insert(0,str(ROOT/"research"/"h096"))
from market import fetch as fetch_bars,save
from engine import aggregate,PARENT


def emit(path,record):
    raw=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def run(out,pages=12):
    out.mkdir(parents=True,exist_ok=True)
    report={"schema":"H097.evidence.v1","status":"INDEPENDENT_ALPHA_NOT_VERIFIED",
            "errors":{},"source_manifests":{},"audits":{},"funding":{},
            "research_complete":False,"alpha_accepted":False,
            "production_modified":False,"h089_modified":False,
            "measured_execution_costs_verified":False,
            "fresh_oos_verified":False,"independent_venue_verified":False,
            "prospective_verified":False}
    for symbol in ("BTC","ETH"):
        inputs={};manifests={}
        for tf in ("5m","15m","1H","1D"):
            try:
                r=fetch_bars(symbol,tf,pages=pages)
                manifests[tf]=save(r,out/"sources")
                inputs[tf]=r["bars"]
                report["source_manifests"][f"{symbol}_{tf}"]=manifests[tf]
            except Exception as e:
                report["errors"][f"{symbol}_{tf}"]={"type":type(e).__name__,"detail":str(e)[:200]}
        try:
            f=fetch_funding(symbol)
            sha=emit(out/f"{symbol}_funding.json",f)
            report["funding"][symbol]={"status":"OBSERVED_NOT_EXECUTION_COST",
                                       "count":f["count"],"sha256":sha}
        except Exception as e:
            report["funding"][symbol]={"status":"NOT_VERIFIED_PROVIDER_ERROR",
                                       "type":type(e).__name__,"detail":str(e)[:200]}
        if "1H" in inputs:
            inputs["4H"]=aggregate(inputs["1H"],"4H")
            manifests["4H"]={"sha256":emit(out/f"{symbol}_4H_derived.json",inputs["4H"]),
                              "derived_from":manifests["1H"]["sha256"]}
        events={}
        for tf,bars in inputs.items():
            if len(bars)<100:continue
            try:events[tf]=detect(bars,symbol,tf)["events"]
            except Exception as e:
                report["errors"][f"{symbol}_{tf}_events"]={"type":type(e).__name__,
                                                            "detail":str(e)[:200]}
        for tf,parent in PARENT.items():
            if tf not in events or parent not in events:continue
            try:
                data=audit(inputs[tf],events[tf],events[parent],tf,manifests[tf])
                data["volatility_regimes"]=regimes(inputs[tf],events[tf],events[parent],tf)
                sha=emit(out/f"{symbol}_{tf}_walk_forward.json",data)
                report["audits"][f"{symbol}_{tf}"]={
                    "sha256":sha,"configs":data["configuration_count"],
                    "folds":len(data["folds"]),
                    "candidates_accepted":0,"status":"DESCRIPTIVE_ONLY"}
            except Exception as e:
                report["errors"][f"{symbol}_{tf}_audit"]={"type":type(e).__name__,
                                                          "detail":str(e)[:200]}
    emit(out/"summary.json",report)
    if report["errors"] or not report["audits"]:
        raise SystemExit("H097_DATA_OR_AUDIT_INCOMPLETE")
    print(json.dumps({"audits":report["audits"],"funding":report["funding"],
                      "alpha_accepted":False,"errors":report["errors"]},sort_keys=True))
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pages",type=int,default=12)
    p.add_argument("--out",default="results/h097")
    a=p.parse_args()
    run(ROOT/a.out,a.pages)
