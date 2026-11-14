"""H105 paired common-window and trade-level uncertainty audit. Descriptive only."""
from __future__ import annotations
import argparse,hashlib,json,math,random
from pathlib import Path
from statistics import mean
def read_checked(path,sha):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError("SHA256_MISMATCH:"+str(path))
    return json.loads(raw)
def summarize(trades,cost="20",replicates=1000):
    values=[t["net_r"][cost] for t in trades]
    n=len(values)
    if not n:return {"n":0,"mean_r":None,"bootstrap_ci95":None,"positive_fraction":None}
    rng=random.Random(105)
    # Naive IID bootstrap is descriptive and not valid for serial dependence.
    means=sorted(mean(values[rng.randrange(n)] for _ in range(n)) for _ in range(replicates))
    return {"n":n,"mean_r":mean(values),"bootstrap_ci95":[means[int(.025*replicates)],means[int(.975*replicates)]],
       "positive_fraction":sum(x>0 for x in values)/n}
def audit(source,out):
    report=json.loads((source/"summary.json").read_text())
    if report.get("schema")!="h104.long_history.v1":raise ValueError("WRONG_SCHEMA")
    sources=report["sources"]
    bykey={(r["symbol"],r["venue"],r["timeframe"],r["family"],r["side"]):r for r in report["cells"]}
    rows=[];coverage={}
    for symbol in ("BTC","ETH"):
        keys=[symbol+"_okx",symbol+"_gate"]
        if any(k not in sources for k in keys):continue
        bars={}
        for k in keys:
            bars[k]=read_checked(source/"bars"/(k+".json"),sources[k]["bars_sha256"])
        start=max(b[0]["ts"] for b in bars.values())
        end=min(b[-1]["ts"] for b in bars.values())
        coverage[symbol]={"start_ms":start,"end_ms":end,"common_hours":(end-start)//3600000+1}
        if end<=start:continue
        for tf in ("1H","4H"):
            for family in ("BREAKOUT_24","TREND_24_72"):
                for side in ("long","short"):
                    pair={}
                    for venue in ("okx","gate"):
                        key=(symbol,venue,tf,family,side)
                        if key not in bykey:continue
                        r=bykey[key]
                        path=source/"ledgers"/f"{symbol}_{venue}_{tf}_{family}_{side}.json"
                        ledger=read_checked(path,r["ledger_sha256"])
                        selected=[t for t in ledger if start<=t["entry_ms"] and t["exit_ms"]<=end]
                        pair[venue]=summarize(selected)
                    if len(pair)!=2:continue
                    a,b=pair["okx"],pair["gate"]
                    rows.append({"symbol":symbol,"timeframe":tf,"family":family,"side":side,
                       "venues":pair,"both_n30":a["n"]>=30 and b["n"]>=30,
                       "both_positive_20bps":a["n"]>=30 and b["n"]>=30 and a["mean_r"]>0 and b["mean_r"]>0,
                       "replicated_positive_ci":a["n"]>=30 and b["n"]>=30 and
                           a["bootstrap_ci95"][0]>0 and b["bootstrap_ci95"][0]>0})
    result={"schema":"h105.paired_venue.v1","common_windows":coverage,"comparisons":rows,
      "both_n30":sum(r["both_n30"] for r in rows),
      "both_positive_20bps":sum(r["both_positive_20bps"] for r in rows),
      "replicated_positive_ci":sum(r["replicated_positive_ci"] for r in rows),
      "alpha_accepted":False,"prospective_oos_verified":False,"execution_verified":False,
      "research_only":True,"multiple_testing_adjusted":False,
      "limitations":["H104 ledger entries are filtered to shared UTC window; indicators were warmed on venue-specific earlier bars, not recomputed on identical starting histories",
      "Naive IID bootstrap ignores serial dependence, overlapping market regimes and multiple testing",
      "Two venues share market drivers and are not independent OOS replications",
      "20bps is assumed, not measured; funding and portfolio NAV unverified"]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("both_n30","both_positive_20bps","replicated_positive_ci")}))
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",default="results/h104");p.add_argument("--out",default="results/h105/summary.json")
    args=p.parse_args();audit(Path(args.source),Path(args.out))
