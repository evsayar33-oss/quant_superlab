"""H099 independent venue signal/trade replication; descriptive, never alpha approval."""
from __future__ import annotations
from statistics import mean
from math import sqrt
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h095"))
from detectors import detect,TF_MS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h096"))
from engine import setup,simulate,exclusive,aggregate

def signals(bars,parent_bars,symbol,tf):
    events=detect(bars,symbol,tf)["events"]
    pevents=detect(parent_bars,symbol,{"15m":"1H","1H":"4H"}[tf])["events"]
    return setup(bars,events,pevents,tf)

def trades(bars,parent_bars,symbol,tf,family,side,target="1R",cost=20.,aligned=False):
    s=signals(bars,parent_bars,symbol,tf)
    selected=[x for x in s if x["signal"]["kind"]==family and x["side"]==side
              and (not aligned or x["aligned"])]
    t=exclusive([v for x in selected if (v:=simulate(bars,x,target,cost,tf)) is not None])
    return t

def pair(primary,secondary):
    """Exact entry timestamp + family + side, never nearest-event matching."""
    def key(t):return (t["entry_ms"],t["family"],t["side"])
    a={key(t):t for t in primary};b={key(t):t for t in secondary}
    shared=sorted(set(a)&set(b))
    diffs=[b[k]["net_r"]-a[k]["net_r"] for k in shared]
    n=len(shared)
    return {"primary_n":len(a),"secondary_n":len(b),"matched_n":n,
            "primary_only":len(a)-n,"secondary_only":len(b)-n,
            "match_fraction_primary":n/len(a) if a else None,
            "mean_primary_matched_net_r":mean(a[k]["net_r"] for k in shared) if n else None,
            "mean_secondary_matched_net_r":mean(b[k]["net_r"] for k in shared) if n else None,
            "mean_secondary_minus_primary_r":mean(diffs) if n else None,
            "positive_matched_secondary_fraction":mean(b[k]["net_r"]>0 for k in shared) if n else None,
            "independent_replication_descriptive":n>=20,
            "alpha_accepted":False,"statistical_significance_verified":False,
            "real_execution_cost_verified":False}

def bootstrap_ci(values,block=5,reps=400,seed=99):
    """Moving block bootstrap for mean, descriptive CI only; no selection correction."""
    import random
    if len(values)<30 or block<1 or reps<100:return {"status":"INSUFFICIENT_SAMPLE"}
    rng=random.Random(seed);n=len(values);blocks=[values[i:i+block] for i in range(n-block+1)]
    out=[]
    for _ in range(reps):
        sample=[]
        while len(sample)<n:sample.extend(blocks[rng.randrange(len(blocks))])
        out.append(mean(sample[:n]))
    out.sort()
    return {"status":"DESCRIPTIVE_BLOCK_BOOTSTRAP_NOT_MULTIPLE_TESTING_ADJUSTED",
            "mean":mean(values),"ci_95":[out[int(.025*reps)],out[int(.975*reps)-1]],
            "n":n,"block":block,"reps":reps,"alpha_accepted":False}

def compare_trades(primary,secondary):
    result=pair(primary,secondary)
    keys={(t["entry_ms"],t["family"],t["side"]):t for t in secondary}
    matched=[keys[(t["entry_ms"],t["family"],t["side"])]["net_r"] for t in primary
             if (t["entry_ms"],t["family"],t["side"]) in keys]
    result["secondary_bootstrap"]=bootstrap_ci(matched)
    return result
