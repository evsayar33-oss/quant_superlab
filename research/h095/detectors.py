"""H095: causal, explicit-definition ICT-style price events from closed OHLC.

Research definitions, not universal discretionary ICT truth. All swings are
confirmed with right-hand bars; no event may be acted upon before confirmation.
No broker fills, model selection, future information or production writes.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import math

HOUR=3600000
TF_MS={"1H":HOUR,"4H":4*HOUR}
KINDS={"SWING_HIGH","SWING_LOW","LIQ_SWEEP","MSS","BOS","OB_FORMED",
       "OB_TOUCH","FVG_FORMED","FVG_TOUCH","IFVG_CONFIRMED","FIB_POSITION"}


def check_bars(bars, tf):
    if tf not in TF_MS:raise ValueError("unsupported timeframe")
    step=TF_MS[tf]
    previous=None
    for b in bars:
        if b["ts"]%step:raise ValueError("unaligned bar")
        vals=[float(b[k]) for k in ("open","high","low","close")]
        o,h,l,c=vals
        if not all(math.isfinite(x) and x>0 for x in vals) or l>min(o,c) or h<max(o,c):
            raise ValueError("invalid OHLC")
        if previous is not None and b["ts"]<=previous:raise ValueError("duplicate/out of order")
        previous=b["ts"]


def event(symbol,tf,kind,side,bar_index,bars,attrs,source="OKX_1H_CLOSED"):
    observed=bars[bar_index]["ts"]+TF_MS[tf]
    stable={"symbol":symbol,"timeframe":tf,"kind":kind,"side":side,
            "bar_index":bar_index,"observed_at_ms":observed,
            "source":source,"attrs":attrs}
    raw=json.dumps(stable,sort_keys=True,separators=(",",":"))
    return {"event_id":hashlib.sha256(raw.encode()).hexdigest()[:20],**stable}


def segments(bars,tf):
    step=TF_MS[tf]
    start=0
    for i in range(1,len(bars)):
        if bars[i]["ts"]-bars[i-1]["ts"]!=step:
            if i>start:yield start,i
            start=i
    if start<len(bars):yield start,len(bars)


def detect(bars,symbol,tf="1H",left=2,right=2,ob_lookback=8):
    if symbol not in ("BTC","ETH"):raise ValueError("unsupported symbol")
    if not 1<=left<=10 or not 1<=right<=10 or not 2<=ob_lookback<=30:
        raise ValueError("invalid research parameters")
    check_bars(bars,tf)
    out=[]
    for start,end in segments(bars,tf):
        pivots={"high":[],"low":[]}
        zones=[];gaps=[]
        for i in range(start,end):
            b=bars[i]
            # Pivot at i-right is only usable once the right-hand bar i closes.
            p=i-right
            if p-left>=start:
                window=bars[p-left:i+1]
                high=bars[p]["high"];low=bars[p]["low"]
                if all(high>x["high"] for j,x in enumerate(window) if j!=left):
                    pivots["high"].append((p,high,i))
                    out.append(event(symbol,tf,"SWING_HIGH","neutral",i,bars,
                                     {"pivot_bar":p,"price":high,"confirmation_bars":right}))
                if all(low<x["low"] for j,x in enumerate(window) if j!=left):
                    pivots["low"].append((p,low,i))
                    out.append(event(symbol,tf,"SWING_LOW","neutral",i,bars,
                                     {"pivot_bar":p,"price":low,"confirmation_bars":right}))
            if i==start:continue
            previous=bars[i-1]
            for side,level_name in (("long","high"),("short","low")):
                choices=[p for p in pivots[level_name] if p[2]<i]
                if not choices:continue
                pivot,price,confirmed=max(choices,key=lambda x:x[2])
                # A wick through a known pivot that closes back inside is a sweep.
                swept=(b["high"]>price and b["close"]<price) if side=="long" else (
                    b["low"]<price and b["close"]>price)
                if swept:
                    out.append(event(symbol,tf,"LIQ_SWEEP",side,i,bars,
                                     {"pivot_bar":pivot,"level":price,"confirmed_bar":confirmed}))
                crossed=(previous["close"]<=price<b["close"]) if side=="long" else (
                    previous["close"]>=price>b["close"])
                if crossed:
                    # MSS requires a prior opposite sweep after the known pivot was confirmed.
                    opposing="short" if side=="long" else "long"
                    sweep=next((x for x in reversed(out)
                                if x["kind"]=="LIQ_SWEEP" and x["side"]==opposing
                                and confirmed<=x["bar_index"]<i),None)
                    kind="MSS" if sweep else "BOS"
                    out.append(event(symbol,tf,kind,side,i,bars,
                                     {"broken_pivot_bar":pivot,"broken_level":price,
                                      "sweep_event_id":sweep["event_id"] if sweep else None}))
                    contrary=[j for j in range(max(start,i-ob_lookback),i)
                              if (bars[j]["close"]<bars[j]["open"] if side=="long"
                                  else bars[j]["close"]>bars[j]["open"])]
                    if contrary:
                        j=contrary[-1];ob=bars[j]
                        z={"zone_id":f"OB:{tf}:{j}:{i}:{side}","side":side,
                           "low":ob["low"],"high":ob["high"],"formed_bar":i,
                           "origin_bar":j,"source_break":kind,"touched":False}
                        zones.append(z)
                        out.append(event(symbol,tf,"OB_FORMED",side,i,bars,dict(z)))
            if i>=start+2:
                a=bars[i-2]
                if b["low"]>a["high"]:
                    gap={"zone_id":f"FVG:{tf}:{i}:long","side":"long",
                         "low":a["high"],"high":b["low"],"formed_bar":i,
                         "touched":False,"inverted":False}
                elif b["high"]<a["low"]:
                    gap={"zone_id":f"FVG:{tf}:{i}:short","side":"short",
                         "low":b["high"],"high":a["low"],"formed_bar":i,
                         "touched":False,"inverted":False}
                else:gap=None
                if gap:
                    gaps.append(gap)
                    out.append(event(symbol,tf,"FVG_FORMED",gap["side"],i,bars,dict(gap)))
            for zone in zones:
                if zone["formed_bar"]>=i or zone["touched"]:continue
                if b["low"]<=zone["high"] and b["high"]>=zone["low"]:
                    zone["touched"]=True
                    out.append(event(symbol,tf,"OB_TOUCH",zone["side"],i,bars,
                                     {"zone_id":zone["zone_id"],"low":zone["low"],
                                      "high":zone["high"],"formed_bar":zone["formed_bar"]}))
            for gap in gaps:
                if gap["formed_bar"]>=i:continue
                if not gap["touched"] and b["low"]<=gap["high"] and b["high"]>=gap["low"]:
                    gap["touched"]=True
                    out.append(event(symbol,tf,"FVG_TOUCH",gap["side"],i,bars,
                                     {"zone_id":gap["zone_id"],"low":gap["low"],
                                      "high":gap["high"],"formed_bar":gap["formed_bar"]}))
                if not gap["inverted"]:
                    invert=(b["close"]<gap["low"]) if gap["side"]=="long" else (
                        b["close"]>gap["high"])
                    if invert:
                        gap["inverted"]=True
                        side="short" if gap["side"]=="long" else "long"
                        out.append(event(symbol,tf,"IFVG_CONFIRMED",side,i,bars,
                                         {"zone_id":gap["zone_id"],"low":gap["low"],
                                          "high":gap["high"],"formed_bar":gap["formed_bar"],
                                          "original_side":gap["side"]}))
            # The last CONFIRMED high/low anchors only; no future extrema.
            highs=[p for p in pivots["high"] if p[2]<i]
            lows=[p for p in pivots["low"] if p[2]<i]
            if highs and lows:
                hi=highs[-1];lo=lows[-1]
                if hi[1]>lo[1]:
                    midpoint=(hi[1]+lo[1])/2
                    pos="above_05" if b["close"]>midpoint else "below_05" if b["close"]<midpoint else "at_05"
                    out.append(event(symbol,tf,"FIB_POSITION","neutral",i,bars,
                                     {"range_high":hi[1],"range_low":lo[1],
                                      "high_pivot_bar":hi[0],"low_pivot_bar":lo[0],
                                      "midpoint":midpoint,"position":pos}))
    out.sort(key=lambda x:(x["observed_at_ms"],x["event_id"]))
    return {"schema":"H095.events.v1","symbol":symbol,"timeframe":tf,
            "definition":"CONFIRMED_PIVOT_CANDLE_RULES_RESEARCH_NOT_DISCRETIONARY_ICT",
            "bar_count":len(bars),"events":out,"event_count":len(out),
            "first_seen_prospective":False,"real_fill_verified":False,
            "historical_alpha_verified":False}
