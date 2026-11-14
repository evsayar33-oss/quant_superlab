"""Run H100 from H099 summary without mutating the original evidence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from audit import screen

def run(source,out):
    if not source.is_file():raise SystemExit("H100_H099_SOURCE_MISSING")
    raw=source.read_bytes()
    data=json.loads(raw)
    result=screen(data)
    result["h099_summary_sha256"]=hashlib.sha256(raw).hexdigest()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"configurations":result["configuration_count"],
                      "status_counts":result["status_counts"],
                      "alpha_accepted":False,
                      "untouched_oos_verified":False},sort_keys=True))
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="results/h099/summary.json")
    p.add_argument("--out",default="results/h100/summary.json")
    a=p.parse_args()
    run(Path(a.source),Path(a.out))
