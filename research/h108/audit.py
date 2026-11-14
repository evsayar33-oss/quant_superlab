"""H108 fixed weekly-block bootstrap and aggregate break-even diagnostics."""
from __future__ import annotations
import argparse,hashlib,json,math,random
from pathlib import Path
from statistics import mean
WEEK_MS=7*86400000
def read_checked(path,expected):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError("SHA256_MISMATCH")
    return json.loads(data)
def metrics(trades):
    if not trades:return {"n":0,"gross_mean_r":None,"net20_mean_r":None,"aggregate_break_even_bps":None}
    g=[float(t["gross_r"]) for t in trades]
    n=[float(t["net_r"]["20"]) for t in trades]
    drag=[a-b for a,b in zip(g,n)]
    if any(not math.isfinite(v) for v in g+n+drag) or any(v<=0 for v in drag):
        raise ValueError("INVALID_COST_OR_RETURN")
    return {"n":len(trades),"gross_mean_r":mean(g),"net20_mean_r":mean(n),
      "aggregate_break_even_bps":20*sum(g)/sum(drag),
      "mean_cost_drag_r":mean(drag)}
def block_bootstrap(trades,replicates=2000,seed=108):
    if not trades:return {"ci95":None,"p_mean_le_zero":None,"weekly_blocks":0}
    weeks={}
    for t in trades:
        w=int(t["entry_ms"])//WEEK_MS
        weeks.setdefault(w,[]).append(float(t["net_r"]["20"]))
    # Include calendar weeks with no entries as zero-trade blocks.
    blocks=[weeks.get(w,[]) for w in range(min(weeks),max(weeks)+1)]
    rng=random.Random(seed);out=[]
    for _ in range(replicates):
        sample=[v for _ in blocks for v in blocks[rng.randrange(len(blocks))]]
        if sample:out.append(mean(sample))
    if not out:return {"ci95":None,"p_mean_le_zero":None,"weekly_blocks":len(blocks)}
    out.sort();n=len(out)
    return {"ci95":[out[int(.025*n)],out[min(n-1,int(.975*n))]],
      "p_mean_le_zero":sum(v<=0 for v in out)/n,"weekly_blocks":len(blocks),
      "bootstrap_replicates":n}
def run(source,out):
    s=json.loads((source/"summary.json").read_text())
    if s.get("schema")!="h106.cross_asset_relative_strength.v1":raise ValueError("WRONG_SCHEMA")
    venues={};ledgers={}
    for r in s["results"]:
        v=r["venue"]
        if v not in ("okx","gate") or v in venues:raise ValueError("BAD_VENUE")
        trades=read_checked(source/"ledgers"/f"{v}.json",r["ledger_sha256"])
        if len(trades)!=r["n"]:raise ValueError("COUNT_MISMATCH")
        ledgers[v]=trades
        venues[v]={"full_history":metrics(trades),"weekly_block_bootstrap":block_bootstrap(trades)}
    if set(venues)!={"okx","gate"}:raise ValueError("TWO_VENUES_REQUIRED")
    common={}
    if all(ledgers.values()):
        lo=max(min(t["entry_ms"] for t in ts) for ts in ledgers.values())
        hi=min(max(t["exit_ms"] for t in ts) for ts in ledgers.values())
        if lo<hi:
            for v,ts in ledgers.items():
                selected=[t for t in ts if lo<=t["entry_ms"] and t["exit_ms"]<=hi]
                common[v]={"metrics":metrics(selected),"weekly_block_bootstrap":block_bootstrap(selected)}
    report={"schema":"h108.dependence_aware.v1","venue_results":venues,"common_window":common,
      "both_common_positive":len(common)==2 and all(v["metrics"]["net20_mean_r"] is not None and v["metrics"]["net20_mean_r"]>0 for v in common.values()),
      "alpha_accepted":False,"prospective_oos_verified":False,"real_execution_verified":False,
      "research_only":True,"multiple_testing_adjusted":False,
      "limitations":["Weekly calendar-block bootstrap is descriptive; limited blocks and nonstationarity can invalidate intervals",
        "Venues share market drivers and are not independent observations",
        "Aggregate break-even bps is an ex-post gross-to-cost ratio, not a feasible execution threshold",
        "No measured fill costs, funding, portfolio NAV, prospective OOS or multiplicity correction"]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"common":{v:x["metrics"] for v,x in common.items()},"alpha_accepted":False}))
    return report
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",default="results/h106")
    p.add_argument("--out",default="results/h108/summary.json")
    a=p.parse_args();run(Path(a.source),Path(a.out))
