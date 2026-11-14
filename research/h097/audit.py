"""H097 deterministic, fail-closed historical evidence and multiple-testing audit.

Research only: no selection on historical test folds, no claimed live fills.
"""
from __future__ import annotations
from math import sqrt,erfc
from statistics import mean,stdev
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h096"))
from engine import setup,simulate,exclusive,FAMILIES,TARGETS,COST_BPS,MAX_HOLD

MIN_TRAIN=100
MIN_TEST=60
EMBARGO=MAX_HOLD
MIN_TRADES_PER_FOLD=20
MIN_FOLDS=3
MIN_TRADES_TOTAL=100


def folds(n,train=MIN_TRAIN,test=MIN_TEST,embargo=EMBARGO):
    """Anchored expanding train, fixed test, purged boundary with 24-bar embargo."""
    if n<=0 or train<=0 or test<=0 or embargo<0:raise ValueError("INVALID_FOLD_ARGS")
    result=[];start=train+embargo
    while start+test<=n:
        result.append({"train_start":0,"train_end":start-embargo,
                       "test_start":start,"test_end":start+test,
                       "embargo_bars":embargo})
        start+=test
    return result


def configuration():
    return [(fam,side,cohort,target,cost) for fam in FAMILIES
            for side in ("long","short") for cohort in ("all","htf_aligned")
            for target in TARGETS for cost in COST_BPS]


def trials(bars,events,parents,tf):
    configs=configuration()
    setups=setup(bars,events,parents,tf)
    fs=folds(len(bars))
    out=[]
    for fam,side,cohort,target,cost in configs:
        eligible=[s for s in setups if s["signal"]["kind"]==fam and
                  s["side"]==side and (cohort=="all" or s["aligned"])]
        trades=exclusive([t for s in eligible
                          if (t:=simulate(bars,s,target,cost,tf)) is not None])
        tested=[]
        for f in fs:
            start=bars[f["test_start"]]["ts"]
            end=bars[f["test_end"]-1]["ts"]
            # exit_ms is bar-open timestamp; prohibit spill past test boundary
            sample=[t for t in trades if start<=t["entry_ms"]<=t["exit_ms"]<=end]
            values=[t["net_r"] for t in sample]
            tested.append({"test_start_ms":start,"test_end_ms":end,
                           "n":len(values),"mean_net_r":mean(values) if values else None,
                           "positive_net_r_count":sum(x>0 for x in values),
                           "trade_values":values})
        out.append({"family":fam,"side":side,"cohort":cohort,"target":target,
                    "assumed_roundtrip_bps":cost,"folds":tested,
                    "tested_trades":sum(f["n"] for f in tested)})
    return {"configs":out,"folds":fs,"config_count":len(out)}


def bonferroni_one_sided(values,comparisons):
    """Conservative one-sided normal-tail heuristic; not a valid serial-correlation p-value."""
    if comparisons<1:raise ValueError("INVALID_COMPARISONS")
    if len(values)<2 or len(set(values))==1:
        return {"status":"NOT_TESTABLE_INSUFFICIENT_VARIANCE","p_heuristic":None,
                "p_bonferroni_heuristic":None}
    sd=stdev(values)
    z=mean(values)/(sd/sqrt(len(values)))
    p=.5*erfc(z/sqrt(2))
    return {"status":"HEURISTIC_ONLY_NOT_DEPENDENCE_ROBUST",
            "p_heuristic":p,"p_bonferroni_heuristic":min(1.,p*comparisons)}


def audit(bars,events,parents,tf,source_manifest):
    data=trials(bars,events,parents,tf)
    count=data["config_count"]
    results=[]
    for c in data["configs"]:
        values=[v for f in c["folds"] for v in f["trade_values"]]
        usable=sum(f["n"]>=MIN_TRADES_PER_FOLD for f in c["folds"])
        stats=bonferroni_one_sided(values,count)
        status="INSUFFICIENT_WALK_FORWARD_EVIDENCE"
        if len(values)>=MIN_TRADES_TOTAL and usable>=MIN_FOLDS:
            status="DESCRIPTIVE_WALK_FORWARD_ONLY"
        results.append({k:c[k] for k in ("family","side","cohort","target",
                                         "assumed_roundtrip_bps","tested_trades")}|
                       {"folds":[{k:v for k,v in f.items() if k!="trade_values"}
                                 for f in c["folds"]],
                        "mean_net_r":mean(values) if values else None,
                        "positive_folds":sum(f["mean_net_r"] is not None and
                                             f["mean_net_r"]>0 for f in c["folds"]),
                        "heuristic_multiple_testing":stats,"evidence_status":status,
                        "alpha_accepted":False})
    return {"schema":"H097.walk_forward.v1","timeframe":tf,
            "source_sha256":source_manifest.get("sha256"),
            "folds":data["folds"],"configuration_count":count,
            "multiple_testing_comparisons":count,"results":results,
            "cost_status":"ASSUMED_NOT_EXECUTION_VERIFIED",
            "p_values_status":"HEURISTIC_NOT_VALID_FOR_AUTOCORRELATED_TRADES",
            "train_selection_performed":False,
            "fresh_out_of_sample":False,"independent_venue_confirmed":False,
            "prospective_first_seen_confirmed":False,
            "live_fills_confirmed":False,"alpha_accepted":False}


def regimes(bars,events,parents,tf):
    """Descriptive volatility buckets, classified using ONLY past completed bars."""
    setups=setup(bars,events,parents,tf)
    buckets={"lower_half":[],"upper_half":[]}
    for s in setups:
        i=s["signal_index"]
        if i<60:continue
        history=[bars[j]["high"]-bars[j]["low"] for j in range(i-60,i)]
        baseline=sorted(history)[len(history)//2]
        current=mean(history[-10:])
        bucket="upper_half" if current>=baseline else "lower_half"
        trade=simulate(bars,s,"1R",20.,tf)
        if trade is not None:buckets[bucket].append(trade["net_r"])
    return {k:{"n":len(v),"mean_net_r":mean(v) if v else None}
            for k,v in buckets.items()}
