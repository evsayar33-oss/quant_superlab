"""H109 preregistered fixed-sign null diagnostic, NOT an executable short strategy."""
from __future__ import annotations
import argparse,hashlib,json,math,random
from pathlib import Path
from statistics import mean
def checked(p,sha):
    b=p.read_bytes()
    if hashlib.sha256(b).hexdigest()!=sha:raise ValueError("HASH_MISMATCH")
    return json.loads(b)
def null_test(trades,iterations=2000,seed=109):
    if not trades:return {"n":0,"observed_mean_net20_r":None,"null_p_ge_observed":None,"null_ci95":None}
    gross=[];cost=[]
    for t in trades:
        g=float(t["gross_r"]);n=float(t["net_r"]["20"])
        if not math.isfinite(g) or not math.isfinite(n) or g-n<=0:raise ValueError("INVALID_TRADE")
        gross.append(g);cost.append(g-n)
    observed=mean(g-c for g,c in zip(gross,cost))
    rng=random.Random(seed)
    # Random sign of gross R, keeping each realized cost. This is a
    # diagnostic symmetry null, NOT a tradable reversed-entry backtest.
    samples=sorted(mean((g if rng.randrange(2) else -g)-c for g,c in zip(gross,cost))
                   for _ in range(iterations))
    return {"n":len(trades),"observed_mean_net20_r":observed,
      "null_mean_net20_r":mean(samples),
      "null_ci95":[samples[int(.025*iterations)],samples[min(iterations-1,int(.975*iterations))]],
      "null_p_ge_observed":sum(v>=observed for v in samples)/iterations,
      "null_p_le_observed":sum(v<=observed for v in samples)/iterations,
      "null_iterations":iterations}
def run(source,out):
    summary=json.loads((source/"summary.json").read_text())
    if summary.get("schema")!="h106.cross_asset_relative_strength.v1":raise ValueError("WRONG_SCHEMA")
    venues={}
    for row in summary["results"]:
        venue=row["venue"]
        if venue in venues or venue not in ("okx","gate"):raise ValueError("INVALID_VENUE")
        trades=checked(source/"ledgers"/f"{venue}.json",row["ledger_sha256"])
        if len(trades)!=row["n"]:raise ValueError("COUNT_MISMATCH")
        result=null_test(trades)
        if result["n"] and not math.isclose(result["observed_mean_net20_r"],row["mean_net_r"]["20"],abs_tol=1e-10):
            raise ValueError("MEAN_MISMATCH")
        venues[venue]=result
    if set(venues)!={"okx","gate"}:raise ValueError("TWO_VENUES_REQUIRED")
    report={"schema":"h109.negative_control.v1","venues":venues,
      "null":"independent sign-flips of realized gross trade R, preserving each observed cost",
      "alpha_accepted":False,"prospective_oos_verified":False,"real_execution_verified":False,
      "research_only":True,"multiple_testing_adjusted":False,
      "limitations":["Sign-flipped gross R is a symmetry diagnostic, not a causal counterfactual or executable short strategy",
        "Independent trade sign flips ignore serial dependence, market regime and correlated venues",
        "Null p-values are descriptive and do not correct research selection or multiple testing",
        "No funding, market impact, portfolio NAV or prospective validation"]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"venues":{v:{"n":r["n"],"observed":r["observed_mean_net20_r"],"null_p_ge":r["null_p_ge_observed"]} for v,r in venues.items()}}))
    return report
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--source",default="results/h106")
    a.add_argument("--out",default="results/h109/summary.json")
    p=a.parse_args();run(Path(p.source),Path(p.out))
