"""H091/H092 price-only exploratory independent entry families on REAL OKX bars.

Only completed OHLC candles. Signals at end of bar t, fill next bar open.
All limits, targets, gaps and financing not verifiable => proxies, never fills.
No model selection from later results. No parameter tuning or ACCEPT.
"""
from __future__ import annotations
import math
from datetime import datetime,timezone
from statistics import mean

HOUR=3600000
COST_BPS_PER_ROUNDTRIP={"BTC":10.,"ETH":10.}
HOLD_BARS=24
ENTRY_FAMILIES=("LIQ_SWEEP","OB_BREAK","FVG")
TARGETS=("fixed_1r","fixed_2r","structural")
TIMEFRAMES=(1,4)


def compress(src:list[dict],factor:int)->list[dict]:
    if factor not in TIMEFRAMES:raise ValueError("unsupported TF")
    if not src:return []
    result=[];groups={}
    for x in src:
        if x["ts"]%HOUR:raise ValueError("invalid hour")
        key=x["ts"]//(HOUR*factor)
        groups.setdefault(key,[]).append(x)
    for key,rows in sorted(groups.items()):
        rows=sorted(rows,key=lambda x:x["ts"])
        expected=[(key*factor+j)*HOUR for j in range(factor)]
        if [r["ts"] for r in rows]!=expected:continue
        result.append({"ts":rows[0]["ts"],"open":rows[0]["open"],
                       "high":max(x["high"] for x in rows),
                       "low":min(x["low"] for x in rows),"close":rows[-1]["close"]})
    return result


def features(bars:list[dict],lookback:int=20)->list[dict]:
    """Fixed, nonoptimized hindsight-free baselines, no future swing confirmation."""
    out=[]
    for i in range(lookback,len(bars)-1):
        current=bars[i];history=bars[i-lookback:i]
        tf_ms=bars[1]["ts"]-bars[0]["ts"]
        if tf_ms not in (HOUR,4*HOUR):
            raise ValueError("unknown timeframe spacing")
        if any(bars[k+1]["ts"]-bars[k]["ts"]!=tf_ms
               for k in range(i-lookback,i)):
            # missing candle invalidates rolling lookback
            continue
        hh=max(x["high"] for x in history)
        ll=min(x["low"] for x in history)
        ranges=[max(x["high"]-x["low"],abs(x["high"]-bars[k-1]["close"]),
                    abs(x["low"]-bars[k-1]["close"]))
                for k,x in enumerate(bars[i-14:i],start=i-14)]
        atr=mean(ranges)
        if not atr or not math.isfinite(atr):continue
        candidates=[]
        if current["low"]<ll and current["close"]>ll:
            candidates.append(("LIQ_SWEEP","long",current["low"]))
        if current["high"]>hh and current["close"]<hh:
            candidates.append(("LIQ_SWEEP","short",current["high"]))
        # OB_BREAK: a structure break and most recent contrary body in previous five.
        if current["close"]>hh and any(bars[k]["close"]<bars[k]["open"]
                                       for k in range(i-5,i)):
            candidates.append(("OB_BREAK","long",min(bars[k]["low"] for k in range(i-5,i))))
        if current["close"]<ll and any(bars[k]["close"]>bars[k]["open"]
                                       for k in range(i-5,i)):
            candidates.append(("OB_BREAK","short",max(bars[k]["high"] for k in range(i-5,i))))
        if current["low"]>bars[i-2]["high"] and current["low"]-bars[i-2]["high"]>0.1*atr:
            candidates.append(("FVG","long",min(bars[i-2]["low"],current["low"])))
        if current["high"]<bars[i-2]["low"] and bars[i-2]["low"]-current["high"]>0.1*atr:
            candidates.append(("FVG","short",max(bars[i-2]["high"],current["high"])))
        for family,side,extreme in candidates:
            out.append({"signal_index":i,"signal_time_ms":current["ts"],
                        "family":family,"side":side,"stop_reference":extreme,
                        "atr":atr,"previous_high":hh,"previous_low":ll})
    return out


def trade(bars:list[dict],s:dict,tf:int,target_type:str,
          cost_bps:float,max_hold:int=HOLD_BARS)->dict|None:
    """Market proxy fills at next OPEN; stop-first intrabar, gap opens pessimistic."""
    i=s["signal_index"];d=1 if s["side"]=="long" else -1
    if i+1>=len(bars):return None
    entry=float(bars[i+1]["open"])
    risk=max(s["atr"],abs(entry-s["stop_reference"]))
    stop=entry-d*risk
    if target_type=="structural":
        # opposite historical range side MUST be positive favorable move;
        # otherwise no admissible target, never invent a new future liquidity level.
        target=s["previous_high"] if d==1 else s["previous_low"]
        if d*(target-entry)<=risk*.3:return None
    else:
        rr=1 if target_type=="fixed_1r" else 2 if target_type=="fixed_2r" else None
        if rr is None:raise ValueError("bad target family")
        target=entry+d*rr*risk
    last=min(i+max_hold,len(bars)-1)
    xp=bars[last]["close"];exit_i=last;exit_cause="TIME"
    for j in range(i+1,last+1):
        b=bars[j]
        if j>i+1 and b["ts"]-bars[j-1]["ts"]!=tf*HOUR:
            return None  # no interpolation through data gaps
        # stop first (also when stop & TP both touched)
        if (d==1 and b["open"]<=stop) or (d==-1 and b["open"]>=stop):
            xp=b["open"];exit_i=j;exit_cause="STOP_GAP";break
        if (d==1 and b["low"]<=stop) or (d==-1 and b["high"]>=stop):
            xp=stop;exit_i=j;exit_cause="STOP";break
        if (d==1 and b["open"]>=target) or (d==-1 and b["open"]<=target):
            xp=target;exit_i=j;exit_cause="TARGET_GAP_CAPPED";break
        if (d==1 and b["high"]>=target) or (d==-1 and b["low"]<=target):
            xp=target;exit_i=j;exit_cause="TARGET";break
    gross_r=d*(xp-entry)/risk
    net_r=gross_r-(cost_bps/10000)*entry/risk
    return {"entry_ms":bars[i+1]["ts"],"exit_ms":bars[exit_i]["ts"],
            "family":s["family"],"side":s["side"],"tf_hours":tf,
            "target_type":target_type,"entry_proxy":entry,"exit_proxy":xp,
            "risk_proxy":risk,"net_R":net_r,"exit_cause":exit_cause}


def research(bars:list[dict],symbol:str)->dict:
    if symbol not in COST_BPS_PER_ROUNDTRIP:raise ValueError("unknown market")
    if any(bars[j+1]["ts"]<=bars[j]["ts"] for j in range(len(bars)-1)):
        raise ValueError("unsorted/duplicate data")
    output={"schema":"H091_H092.exploratory.v1","symbol":symbol,
            "source":"OKX_PUBLIC_1H_USDT_SWAP_HISTORY","research_only":True,
            "model_family":"OHLC_PRICE_ONLY_INDEPENDENT_ENTRIES",
            "parameter_search_count":0,"selected_winner":None,
            "historical_oos_is_new_unseen_data":False,
            "fundamental_macro_integrated_backtest":False,
            "fill_verified":False,"funding_verified":False,"slippage_verified":False,
            "trials":[],"missing":[]}
    for tf in TIMEFRAMES:
        b=compress(bars,tf)
        if len(b)<90:
            output["missing"].append({"tf":str(tf)+"H","status":"NOT_TESTABLE","reason":"LESS_THAN_90_COMPLETE_BARS"})
            continue
        signals=features(b)
        # Split is fixed per TF, not optimized; historical exploratory only.
        cut=int(len(b)*.7)
        for fam in ENTRY_FAMILIES:
            for side in ("long","short"):
                cand=[x for x in signals if x["family"]==fam and x["side"]==side]
                for target in TARGETS:
                    tr=[trade(b,s,tf,target,COST_BPS_PER_ROUNDTRIP[symbol])
                        for s in cand]
                    tr=[x for x in tr if x is not None]
                    # Purge trades crossing split: prevent training/validation contamination
                    train=[x for x in tr if x["exit_ms"]<b[cut]["ts"]]
                    hold=[x for x in tr if x["entry_ms"]>=b[cut]["ts"]]
                    output["trials"].append({"tf_hours":tf,"family":fam,"side":side,
                        "target":target,"train_n":len(train),"hold_n":len(hold),
                        "train_mean_net_R":mean(x["net_R"] for x in train) if train else None,
                        "hold_mean_net_R":mean(x["net_R"] for x in hold) if hold else None,
                        "hold_win_rate":mean(x["net_R"]>0 for x in hold) if hold else None,
                        "hold_net_R_sum":sum(x["net_R"] for x in hold) if hold else None,
                        "hold_unvalidated":True,
                        "why_unvalidated":"historical periods already researched, 1 venue, no funding/true slippage, overlapping concurrent signals"})
    output["trial_count"]=len(output["trials"])
    output["trials_with_30_hold_entries"]=sum(t["hold_n"]>=30 for t in output["trials"])
    return output
