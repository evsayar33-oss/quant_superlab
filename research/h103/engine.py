"""H103 fixed, causal, non-overlapping exploratory strategy tests. Not trading advice."""
from __future__ import annotations
import math
from statistics import mean
HOUR=3600000
FAMILIES=("TREND_24_72","BREAKOUT_24")
COSTS=(20,40,80)
def signals(bars,step):
    out=[]
    for i in range(73,len(bars)-1):
        window=bars[i-72:i+1]
        if any(window[j]["ts"]-window[j-1]["ts"]!=step for j in range(1,len(window))):continue
        close=bars[i]["close"];prev=bars[i-1]["close"]
        fast=mean(b["close"] for b in bars[i-23:i+1])
        slow=mean(b["close"] for b in bars[i-71:i+1])
        previous_fast=mean(b["close"] for b in bars[i-24:i])
        previous_slow=mean(b["close"] for b in bars[i-72:i])
        atr=mean(b["high"]-b["low"] for b in bars[i-13:i+1])
        if atr<=0:continue
        if previous_fast<=previous_slow and fast>slow:
            out.append((i+1,"TREND_24_72","long",atr))
        elif previous_fast>=previous_slow and fast<slow:
            out.append((i+1,"TREND_24_72","short",atr))
        prev_high=max(b["high"] for b in bars[i-24:i])
        prev_low=min(b["low"] for b in bars[i-24:i])
        if prev<=prev_high and close>prev_high:
            out.append((i+1,"BREAKOUT_24","long",atr))
        elif prev>=prev_low and close<prev_low:
            out.append((i+1,"BREAKOUT_24","short",atr))
    return out

def simulate(bars,entry_i,side,atr,step):
    direction=1 if side=="long" else -1
    if entry_i>=len(bars) or bars[entry_i]["ts"]-bars[entry_i-1]["ts"]!=step:return None
    entry=bars[entry_i]["open"];risk=2*atr
    if not all(math.isfinite(v) for v in (entry,risk)) or entry<=0 or not 0<risk<entry*.25:return None
    stop=entry-direction*risk;target=entry+direction*3*atr
    limit=min(entry_i+(48 if step==HOUR else 12),len(bars))
    if limit-entry_i<2:return None
    price=bars[limit-1]["close"];exit_i=limit-1;cause="TIME"
    for j in range(entry_i,limit):
        b=bars[j]
        if j>entry_i and b["ts"]-bars[j-1]["ts"]!=step:return None
        if direction*(b["open"]-stop)<=0:
            price=b["open"];exit_i=j;cause="STOP_GAP";break
        if b["low"]<=stop if direction==1 else b["high"]>=stop:
            price=stop;exit_i=j;cause="STOP";break
        if direction*(b["open"]-target)>=0:
            price=target;exit_i=j;cause="TARGET_GAP_CAPPED";break
        if b["high"]>=target if direction==1 else b["low"]<=target:
            price=target;exit_i=j;cause="TARGET";break
    gross=direction*(price-entry)/risk
    return {"entry_ms":bars[entry_i]["ts"],"exit_ms":bars[exit_i]["ts"],
        "gross_r":gross,"net_r":{str(c):gross-c/10000*entry/risk for c in COSTS},
        "entry":entry,"risk":risk,"exit_cause":cause,"side":side}

def evaluate(bars,step):
    split=bars[int(len(bars)*.7)]["ts"]
    grouped={(fam,side):[] for fam in FAMILIES for side in ("long","short")}
    last_exit={(fam,side):-1 for fam,side in grouped}
    for i,fam,side,atr in signals(bars,step):
        key=(fam,side)
        if bars[i]["ts"]<=last_exit[key]:continue
        trade=simulate(bars,i,side,atr,step)
        if trade is None:continue
        grouped[key].append(trade);last_exit[key]=trade["exit_ms"]
    result=[]
    for (fam,side),trades in sorted(grouped.items()):
        tail=[t for t in trades if t["entry_ms"]>=split]
        def avg(xs,k):return mean(t[k] for t in xs) if xs else None
        result.append({"family":fam,"side":side,"n":len(trades),"tail_n":len(tail),
          "gross_mean_r":avg(trades,"gross_r"),
          "net_mean_r":{str(c):mean(t["net_r"][str(c)] for t in trades) if trades else None for c in COSTS},
          "tail_net_mean_r_20bps":mean(t["net_r"]["20"] for t in tail) if tail else None,
          "eligible_n30":len(trades)>=30,"tail_eligible_n30":len(tail)>=30,
          "median_holding_bars":sorted((t["exit_ms"]-t["entry_ms"])/step+1 for t in trades)[len(trades)//2] if trades else None,
          "trades":trades})
    return result
