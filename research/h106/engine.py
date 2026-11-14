"""H106 fixed cross-asset relative-strength hypothesis, causal research only."""
from __future__ import annotations
from statistics import mean
HOUR=3600000
COSTS=(20,40,80)
def align(btc,eth,step=HOUR):
    a={b["ts"]:b for b in btc};b={x["ts"]:x for x in eth}
    return [(t,a[t],b[t]) for t in sorted(a.keys()&b.keys())]
def signals(pairs,step=HOUR):
    out=[]
    for i in range(49,len(pairs)-1):
        w=pairs[i-48:i+2]
        if any(w[j][0]-w[j-1][0]!=step for j in range(1,len(w))):continue
        now=pairs[i];past=pairs[i-24]
        # completed close-to-close 24-bar relative momentum, no future candle
        bret=now[1]["close"]/past[1]["close"]-1
        eret=now[2]["close"]/past[2]["close"]-1
        prev=pairs[i-1];pp=pairs[i-25]
        old=prev[1]["close"]/pp[1]["close"]-prev[2]["close"]/pp[2]["close"]
        spread=bret-eret
        # fixed 1% spread threshold and crossover, not tuned on returns
        if old<=.01 and spread>.01:out.append((i+1,"BTC","long"))
        if old>=-.01 and spread<-.01:out.append((i+1,"ETH","long"))
    return out
def simulate(pairs,i,symbol,side,step=HOUR):
    ix=1 if symbol=="BTC" else 2
    entry=pairs[i][ix]["open"]
    prior=[p[ix] for p in pairs[i-14:i]]
    atr=mean(p["high"]-p["low"] for p in prior)
    risk=2*atr
    if entry<=0 or not 0<risk<entry*.25:return None
    stop=entry-risk;target=entry+3*atr
    limit=min(i+48,len(pairs))
    if limit-i<2:return None
    price=pairs[limit-1][ix]["close"];exit_i=limit-1;cause="TIME"
    for j in range(i,limit):
        if j>i and pairs[j][0]-pairs[j-1][0]!=step:return None
        b=pairs[j][ix]
        if b["open"]<=stop:price=b["open"];exit_i=j;cause="STOP_GAP";break
        if b["low"]<=stop:price=stop;exit_i=j;cause="STOP";break
        if b["open"]>=target:price=target;exit_i=j;cause="TARGET_GAP_CAPPED";break
        if b["high"]>=target:price=target;exit_i=j;cause="TARGET";break
    gross=(price-entry)/risk
    return {"entry_ms":pairs[i][0],"exit_ms":pairs[exit_i][0],
       "symbol":symbol,"side":side,"gross_r":gross,"cause":cause,
       "net_r":{str(c):gross-c/10000*entry/risk for c in COSTS}}
def evaluate(btc,eth):
    pairs=align(btc,eth)
    trades=[];last_exit=-1
    for i,symbol,side in signals(pairs):
        if pairs[i][0]<=last_exit:continue
        t=simulate(pairs,i,symbol,side)
        if t is None:continue
        trades.append(t);last_exit=t["exit_ms"]
    n=len(trades)
    split=pairs[int(len(pairs)*.7)][0] if pairs else None
    tail=[t for t in trades if t["entry_ms"]>=split] if split is not None else []
    return {"common_bars":len(pairs),"n":n,"tail_n":len(tail),
       "eligible_n30":n>=30,"mean_net_r":{str(c):mean(t["net_r"][str(c)] for t in trades) if trades else None for c in COSTS},
       "tail_mean_net_r_20bps":mean(t["net_r"]["20"] for t in tail) if tail else None,
       "trades":trades}
