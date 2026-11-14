"""Fixed descriptive research statistics; no prospectively valid alpha p-values."""
from __future__ import annotations
from collections import Counter
from statistics import mean
import math,random
from campaign_core import COSTS,HOUR
BOOTSTRAPS=1000
def metrics(trades):
    n=len(trades)
    if not n:
        return {"n":0,"net_mean_r":{str(c):None for c in COSTS},
                "gross_mean_r":None,"win_rate20":None,"drawdown40_r":None}
    pnl=[t["net_r"]["40"] for t in trades]
    nav=0;peak=0;dd=0
    for v in pnl:
        nav+=v;peak=max(peak,nav);dd=max(dd,peak-nav)
    return {"n":n,"net_mean_r":{str(c):mean(t["net_r"][str(c)] for t in trades) for c in COSTS},
            "gross_mean_r":mean(t["gross_r"] for t in trades),
            "win_rate20":sum(t["net_r"]["20"]>0 for t in trades)/n,
            "drawdown40_r":dd,"sum_net40_r":nav,
            "exits":dict(Counter(t["cause"] for t in trades))}
def time_splits(trades,train_end,val_end):
    # Entry and exit must BOTH lie within their split, otherwise discard.
    train=[t for t in trades if t["exit_ms"]<train_end]
    valid=[t for t in trades if train_end<=t["entry_ms"] and t["exit_ms"]<val_end]
    hold=[t for t in trades if t["entry_ms"]>=val_end]
    return {"train":metrics(train),"validation":metrics(valid),"historical_tail":metrics(hold),
            "purged_cross_boundary":len(trades)-len(train)-len(valid)-len(hold)}
def blocks(trades):
    if not trades:return []
    week=7*24*HOUR
    weekly={}
    for t in trades:
        w=t["entry_ms"]//week
        weekly.setdefault(w,[]).append(t["net_r"]["40"])
    return [weekly.get(w,[]) for w in range(min(weekly),max(weekly)+1)]
def weekly_bootstrap(trades,trials=BOOTSTRAPS):
    sets=blocks(trades)
    if len(sets)<6:return {"weeks":len(sets),"ci95":None,"p_mean_nonpositive":None}
    rng=random.Random(109)
    values=[]
    for _ in range(trials):
        sample=[v for _ in sets for v in sets[rng.randrange(len(sets))]]
        if sample:values.append(mean(sample))
    if not values:return {"weeks":len(sets),"ci95":None,"p_mean_nonpositive":None}
    values.sort()
    return {"weeks":len(sets),
            "ci95":[values[int(.025*len(values))],values[int(.975*len(values))]],
            "p_mean_nonpositive":sum(x<=0 for x in values)/len(values)}
def weekly_signflip(trades,trials=BOOTSTRAPS):
    if len(trades)<30:return None
    sets=blocks(trades)
    if len(sets)<8:return None
    totals=[sum(b) for b in sets]
    observed=sum(totals)
    rng=random.Random(109)
    exceed=0
    for _ in range(trials):
        exceed+=sum(v if rng.randrange(2) else -v for v in totals)>=observed
    return (exceed+1)/(trials+1)
def bh(pairs):
    ordered=sorted(((key,p) for key,p in pairs if p is not None),key=lambda x:x[1])
    result={key:None for key,_ in pairs}
    count=len(ordered);best=1.
    for k in range(count,0,-1):
        key,p=ordered[k-1];best=min(best,p*count/k);result[key]=best
    return result
def pair_decision(x):
    if x["control"]:return "CONTROL_EXCLUDED"
    if not x["paired_n30_and_tail10"]:return "INSUFFICIENT_SAMPLE"
    if not x["positive40_both"]:return "REJECT_40BPS"
    if not x["positive80_both"]:return "REJECT_80BPS_STRESS"
    if not x["positive_tail40_both"]:return "REJECT_HISTORICAL_TAIL"
    if not x["weekly_bootstrap_lower_positive_both"]:return "REJECT_WEEKLY_UNCERTAINTY"
    if not x["bh_q_under005_both"]:return "REJECT_MULTIPLE_TESTING"
    return "WATCHLIST_ONLY_NOT_ALPHA"
