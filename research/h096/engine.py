"""H096 causal higher-timeframe context and single-instrument proxy execution.

This is descriptive research, not independently validated trading alpha.
HTF candles must have fully closed before entry. All trade outcomes use
strict next-open proxy and stop-first same-candle ordering. No intrabar fills.
"""
from __future__ import annotations
from collections import Counter
from statistics import mean
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h095"))
from detectors import detect,TF_MS
from market import BARS

FAMILIES=("LIQ_SWEEP","MSS","BOS","OB_TOUCH","FVG_TOUCH","IFVG_CONFIRMED")
TARGETS=("1R","2R","PIVOT")
COST_BPS=(10.,20.,40.)
MAX_HOLD=24
PARENT={"5m":"15m","15m":"1H","1H":"4H","4H":"1D"}


def aggregate(rows,tf):
    """Strict UTC-aligned complete groups, no gap-filled resampling."""
    step=TF_MS[tf]
    groups={}
    for r in rows:groups.setdefault(r["ts"]//step,[]).append(r)
    result=[]
    for key,group in sorted(groups.items()):
        group=sorted(group,key=lambda r:r["ts"])
        unit=group[1]["ts"]-group[0]["ts"] if len(group)>1 else 0
        if unit!=3600000 or len(group)!=step//3600000:continue
        if [r["ts"] for r in group]!=list(range(key*step,(key+1)*step,3600000)):continue
        result.append({"ts":key*step,"open":group[0]["open"],
                       "high":max(r["high"] for r in group),
                       "low":min(r["low"] for r in group),
                       "close":group[-1]["close"]})
    return result


def parent_asof(event_ms,parents,context):
    """Only parent events observed at or before signal close."""
    if not parents:return {"status":"NOT_TESTABLE_NO_PARENT_BARS"}
    recent=[p for p in parents if p["observed_at_ms"]<=event_ms and
            p["kind"] in ("MSS","BOS","LIQ_SWEEP","IFVG_CONFIRMED") and
            event_ms-p["observed_at_ms"]<=8*TF_MS[context]]
    if not recent:return {"status":"NOT_TESTABLE_NO_CONFIRMED_PARENT_EVENT"}
    item=max(recent,key=lambda x:x["observed_at_ms"])
    return {"status":"KNOWN","kind":item["kind"],"side":item["side"],
            "observed_at_ms":item["observed_at_ms"],
            "event_id":item["event_id"]}


def setup(bars,events,parent_events,tf):
    result=[]
    for e in events:
        if e["kind"] not in FAMILIES or e["side"] not in ("long","short"):continue
        i=e["bar_index"]
        if i+1>=len(bars):continue
        if e["observed_at_ms"]!=bars[i]["ts"]+TF_MS[tf]:raise ValueError("EVENT_TIMESTAMP_NOT_CAUSAL")
        parent=parent_asof(e["observed_at_ms"],parent_events,tf)
        if parent["status"]!="KNOWN":continue
        # Two cohorts: unconditional and HTF aligned. A neutral parent cannot confirm.
        d=1 if e["side"]=="long" else -1
        recent=bars[max(0,i-14):i+1]
        if len(recent)<10:continue
        ranges=[r["high"]-r["low"] for r in recent]
        atr=mean(ranges)
        if atr<=0:continue
        entry=bars[i+1]["open"]
        reference=e["attrs"].get("low" if d==1 else "high")
        if reference is None:reference=e["attrs"].get("level")
        if reference is None:reference=e["attrs"].get("broken_level")
        if reference is None:reference=min(x["low"] for x in recent) if d==1 else max(x["high"] for x in recent)
        risk=max(atr,abs(entry-reference))
        if not 0<risk<entry*.25:continue
        # Historic confirmed opposing pivot, not future liquidity.
        confirmed=[x for x in events if x["observed_at_ms"]<=e["observed_at_ms"] and
                   x["kind"]==("SWING_HIGH" if d==1 else "SWING_LOW")]
        pivot=confirmed[-1]["attrs"]["price"] if confirmed else None
        result.append({"signal":e,"signal_index":i,"side":e["side"],
                       "entry_index":i+1,"risk":risk,"pivot_target":pivot,
                       "parent":parent,"aligned":parent["side"]==e["side"],
                       "entry_reference":entry})
    return result


def simulate(bars,signal,target,fee_bps,tf):
    i=signal["entry_index"];d=1 if signal["side"]=="long" else -1
    if i>=len(bars):return None
    entry=bars[i]["open"];risk=signal["risk"];stop=entry-d*risk
    if target=="PIVOT":
        tp=signal["pivot_target"]
        if tp is None or d*(tp-entry)<risk*.25:return None
    else:tp=entry+d*(1 if target=="1R" else 2)*risk
    last=min(i+MAX_HOLD-1,len(bars)-1)
    price=bars[last]["close"];exit_i=last;cause="TIME"
    for j in range(i,last+1):
        b=bars[j]
        if j>i and b["ts"]-bars[j-1]["ts"]!=TF_MS[tf]:return None
        if d*(b["open"]-stop)<=0:
            price=b["open"];exit_i=j;cause="STOP_GAP";break
        if (b["low"]<=stop if d==1 else b["high"]>=stop):
            price=stop;exit_i=j;cause="STOP";break
        if d*(b["open"]-tp)>=0:
            price=tp;exit_i=j;cause="TARGET_GAP_CAPPED";break
        if (b["high"]>=tp if d==1 else b["low"]<=tp):
            price=tp;exit_i=j;cause="TARGET";break
    gross=d*(price-entry)/risk
    return {"entry_ms":bars[i]["ts"],"exit_ms":bars[exit_i]["ts"],
            "net_r":gross-fee_bps/10000*entry/risk,
            "cause":cause,"family":signal["signal"]["kind"],
            "side":signal["side"],"target":target,"cost_bps":fee_bps,
            "htf_aligned":signal["aligned"]}


def exclusive(trades):
    selected=[];end=-1
    for t in sorted(trades,key=lambda x:(x["entry_ms"],x["exit_ms"])):
        if t["entry_ms"]<=end:continue
        selected.append(t);end=t["exit_ms"]
    return selected


def summarize(trades):
    if not trades:return {"n":0,"mean_net_r":None,"win_rate":None,"max_drawdown_r":None}
    pnl=[t["net_r"] for t in trades];nav=0.;peak=0.;dd=0.
    for p in pnl:
        nav+=p;peak=max(peak,nav);dd=max(dd,peak-nav)
    return {"n":len(pnl),"mean_net_r":mean(pnl),
            "win_rate":mean(p>0 for p in pnl),"max_drawdown_r":dd,
            "sum_net_r":sum(pnl)}


def evaluate(bars,events,parents,tf):
    signals=setup(bars,events,parents,tf)
    split=int(len(bars)*.7)
    rows=[]
    for fam in FAMILIES:
        for side in ("long","short"):
            for cohort in ("all","htf_aligned"):
                cand=[s for s in signals if s["signal"]["kind"]==fam and s["side"]==side
                      and (cohort=="all" or s["aligned"])]
                for target in TARGETS:
                    for cost in COST_BPS:
                        trades=exclusive([t for s in cand if
                            (t:=simulate(bars,s,target,cost,tf)) is not None])
                        # Purge crossing split. Never optimize the split based on performance.
                        train=[t for t in trades if t["exit_ms"]<bars[split]["ts"]]
                        hold=[t for t in trades if t["entry_ms"]>=bars[split]["ts"]]
                        rows.append({"family":fam,"side":side,"cohort":cohort,
                                     "target":target,"assumed_roundtrip_bps":cost,
                                     "train":summarize(train),"historical_hold":summarize(hold),
                                     "untouched_oos":False,"funding_verified":False,
                                     "real_execution_verified":False})
    return {"schema":"H096.performance_proxy.v1","timeframe":tf,
            "signal_count":len(signals),"trial_count":len(rows),"trials":rows,
            "holdout_is_unseen":False,"independent_alpha_verified":False,
            "candidate_accepted":False,"multiple_testing_adjusted":False,
            "portfolio_nav_verified":False}
