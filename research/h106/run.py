"""Read-only H106 fixed cross-asset hypothesis using fresh H104 source evidence."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"research"/"h106"))
from engine import evaluate
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
    p.write_bytes(raw);return hashlib.sha256(raw).hexdigest()
def run(source,out):
    h104=json.loads((source/"summary.json").read_text())
    if h104["schema"]!="h104.long_history.v1":raise ValueError("INVALID_H104_SCHEMA")
    results=[];errors={}
    for venue in ("okx","gate"):
        bars={}
        for symbol in ("BTC","ETH"):
            key=f"{symbol}_{venue}"
            try:
                m=h104["sources"][key];p=source/"bars"/f"{key}.json"
                raw=p.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=m["bars_sha256"]:raise ValueError("HASH_MISMATCH")
                bars[symbol]=json.loads(raw)
            except Exception as e:errors[key]=type(e).__name__
        if len(bars)!=2:continue
        r=evaluate(bars["BTC"],bars["ETH"])
        trades=r.pop("trades")
        r["ledger_sha256"]=save(out/"ledgers"/f"{venue}.json",trades)
        r["venue"]=venue
        results.append(r)
    if len(results)!=2:raise ValueError("TWO_VENUES_REQUIRED")
    summary={"schema":"h106.cross_asset_relative_strength.v1",
      "hypothesis":"24-bar BTC minus ETH return crosses +1% (BTC long) or -1% (ETH long), 48-bar max hold",
      "results":results,"errors":errors,
      "both_n30":all(r["eligible_n30"] for r in results),
      "both_positive_20bps":all(r["eligible_n30"] and r["mean_net_r"]["20"]>0 for r in results),
      "alpha_accepted":False,"prospective_oos_verified":False,"real_execution_verified":False,
      "funding_verified":False,"multiple_testing_adjusted":False,
      "research_only":True,
      "limitations":["BTC/ETH share market risk and venues are dependent",
        "24-bar relative momentum is a fixed exploratory hypothesis, not portfolio market-neutral spread",
        "Long-only winner selection can have directional market beta",
        "Historical tail is reused, not prospective OOS; funding and fills unverified"]}
    save(out/"summary.json",summary)
    print(json.dumps({"venues":len(results),"both_n30":summary["both_n30"],
      "both_positive_20bps":summary["both_positive_20bps"],"errors":errors}))
    return summary
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--source",default="results/h104");a.add_argument("--out",default="results/h106")
    x=a.parse_args();run(Path(x.source),Path(x.out))
