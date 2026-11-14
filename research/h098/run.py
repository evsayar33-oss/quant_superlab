"""H098 read-only cross-venue, funding and prospective snapshot audit."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h095"))
from detectors import detect,TF_MS
sys.path.insert(0,str(ROOT/"research"/"h096"))
from market import fetch as okx_fetch
sys.path.insert(0,str(ROOT/"research"/"h097"))
from funding import fetch as funding_fetch
from venues import fetch as independent_fetch
from evidence import compare,event_concordance,evidence_gate,snapshot,cost_sensitivity

def write(path,obj):
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def run(out,pages=8):
    out.mkdir(parents=True,exist_ok=True)
    report={"schema":"H098.independent_evidence.v1","status":"RESEARCH_ONLY",
            "comparisons":{},"funding":{},"errors":{},"snapshots":{},
            "sources":{},"cost_scenarios":{},
            "alpha_accepted":False,"h089_modified":False,"production_modified":False}
    valid=[];funding_ok=[];snaps=[]
    for symbol in ("BTC","ETH"):
        try:
            f=funding_fetch(symbol)
            report["funding"][symbol]={"count":f["count"],"sha256":write(out/f"{symbol}_funding.json",f),
                                       "status":"OBSERVED_NOT_APPLIED"}
            funding_ok.append(symbol)
        except Exception as e:
            report["funding"][symbol]={"status":"NOT_VERIFIED","error":type(e).__name__}
        for tf in ("15m","1H"):
            key=f"{symbol}_{tf}"
            try:
                primary=okx_fetch(symbol,tf,pages=pages)
                p=primary["bars"]
                sha=write(out/"sources"/f"{key}_OKX.json",primary)
                report["sources"][key]={"okx_sha256":sha,"bars":len(p)}
                events=detect(p,symbol,tf)["events"]
                snap=snapshot(symbol,tf,events,sha,p[-1]["ts"]+TF_MS[tf])
                report["snapshots"][key]={"sha256":write(out/"snapshots"/f"{key}.json",snap),
                                          "persistent_first_seen_verified":False}
                snaps.append(snap)
            except Exception as e:
                report["errors"][f"{key}_okx"]={"type":type(e).__name__,"detail":str(e)[:180]}
                continue
            for venue in ("binance","bybit"):
                k=f"{key}_{venue}"
                try:
                    secondary=independent_fetch(venue,symbol,tf)
                    bars=secondary["bars"]
                    vsha=write(out/"sources"/f"{k}.json",secondary)
                    stats=compare(p,bars,TF_MS[tf])
                    stats["independent_source_sha256"]=vsha
                    stats["detector_concordance"]=event_concordance(
                        events,detect(bars,symbol,tf)["events"])
                    report["comparisons"][k]=stats
                    valid.append(stats)
                except Exception as e:
                    report["comparisons"][k]={"status":"NOT_VERIFIED_PROVIDER_ERROR",
                                               "error_type":type(e).__name__,
                                               "detail":str(e)[:180],
                                               "comparable":False}
    for label,params in {"low":(4,2,2,0),"medium":(8,5,5,2),
                         "stress":(16,12,12,10)}.items():
        report["cost_scenarios"][label]=cost_sensitivity(
            100,101,"long",*params)
    report["gates"]=evidence_gate(valid,funding_ok,snaps)
    write(out/"summary.json",report)
    if report["errors"] or not snaps:
        raise SystemExit("H098_PRIMARY_SOURCE_INCOMPLETE")
    print(json.dumps({"comparisons":{k:v["status"] for k,v in report["comparisons"].items()},
                      "gates":report["gates"],"funding":report["funding"],
                      "errors":report["errors"]},sort_keys=True))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pages",type=int,default=8)
    p.add_argument("--out",default="results/h098")
    a=p.parse_args()
    run(ROOT/a.out,a.pages)
