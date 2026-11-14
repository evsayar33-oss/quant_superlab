"""H107 cost and exposure decomposition of H106, no new strategy selection."""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
from statistics import mean,median
def checked(path,digest):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("LEDGER_SHA256_MISMATCH")
    return json.loads(raw)
def analyze(trades):
    if not trades:return {"n":0,"mean_gross_r":None,"mean_net20_r":None,"mean_cost_drag20_r":None,"break_even_bps":None}
    costs=[];break_even=[];durations=[];causes={};gross=[];net=[]
    for t in trades:
        g=float(t["gross_r"]);n=float(t["net_r"]["20"]);n40=float(t["net_r"]["40"]);n80=float(t["net_r"]["80"])
        if not all(math.isfinite(v) for v in (g,n,n40,n80)):raise ValueError("NONFINITE_R")
        drag=g-n
        if drag<=0 or not math.isclose(n40,g-2*drag,abs_tol=1e-8) or not math.isclose(n80,g-4*drag,abs_tol=1e-8):
            raise ValueError("COST_LINEARITY_VIOLATION")
        if t["exit_ms"]<t["entry_ms"]:raise ValueError("NEGATIVE_HOLD")
        costs.append(drag);break_even.append(20*g/drag)
        durations.append((t["exit_ms"]-t["entry_ms"])/3600000+1)
        causes[t["cause"]]=causes.get(t["cause"],0)+1
        gross.append(g);net.append(n)
    return {"n":len(trades),"mean_gross_r":mean(gross),"mean_net20_r":mean(net),
       "mean_cost_drag20_r":mean(costs),"mean_trade_break_even_bps":mean(break_even),
       "median_trade_break_even_bps":median(break_even),
       "mean_holding_hours":mean(durations),"exit_causes":causes,
       "net20_positive_fraction":sum(x>0 for x in net)/len(net)}
def run(source,out):
    s=json.loads((source/"summary.json").read_text())
    if s.get("schema")!="h106.cross_asset_relative_strength.v1":raise ValueError("WRONG_SOURCE_SCHEMA")
    venues={};ledgers={}
    for r in s["results"]:
        v=r["venue"]
        if v in venues or v not in ("okx","gate"):raise ValueError("INVALID_VENUE")
        trades=checked(source/"ledgers"/f"{v}.json",r["ledger_sha256"])
        if len(trades)!=r["n"]:raise ValueError("COUNT_MISMATCH")
        stat=analyze(trades)
        if stat["n"] and not math.isclose(stat["mean_net20_r"],r["mean_net_r"]["20"],abs_tol=1e-10):
            raise ValueError("SUMMARY_MISMATCH")
        venues[v]=stat;ledgers[v]=trades
    if set(venues)!={"okx","gate"}:raise ValueError("MISSING_VENUE")
    # Restrict comparison to overlapping trade timestamps, without claiming independent samples.
    starts=[min(t["entry_ms"] for t in ts) for ts in ledgers.values() if ts]
    ends=[max(t["exit_ms"] for t in ts) for ts in ledgers.values() if ts]
    common={}
    if len(starts)==2 and len(ends)==2:
        lo=max(starts);hi=min(ends)
        if lo<hi:
            common={v:analyze([t for t in ts if lo<=t["entry_ms"] and t["exit_ms"]<=hi])
                    for v,ts in ledgers.items()}
    report={"schema":"h107.cost_exposure_audit.v1","venue_diagnostics":venues,
      "common_trade_window":common,
      "both_net20_positive":all(x["mean_net20_r"] is not None and x["mean_net20_r"]>0 for x in venues.values()),
      "alpha_accepted":False,"research_only":True,"prospective_oos_verified":False,
      "real_execution_verified":False,"multiple_testing_adjusted":False,
      "limitations":["Trade-window matching does not create independent OOS",
        "Break-even bps is a gross outcome diagnostic, not a forecast of attainable execution",
        "No portfolio cash exposure, funding, borrow, market impact or realized fills",
        "H106 is directional BTC/ETH winner selection, not a market-neutral hedge"]}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"venues":{k:{"n":v["n"],"net20":v["mean_net20_r"]} for k,v in venues.items()},
        "alpha_accepted":False}))
    return report
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",default="results/h106")
    p.add_argument("--out",default="results/h107/summary.json")
    a=p.parse_args();run(Path(a.source),Path(a.out))
