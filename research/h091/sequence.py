"""H092 chronology-based *exploratory* price action sequences from real closed bars.

No MSS/iFVG/OB-touch claim: OB_BREAK is a simple previous-range break
with recent contrary body. Every sequence explicitly identifies proxies.
"""
from __future__ import annotations
from statistics import mean
from baseline import compress,features,trade,nonoverlapping,metrics,COST_BPS_PER_ROUNDTRIP

WINDOW_BARS=24
RECIPES=("LIQ_THEN_OB_BREAK","LIQ_THEN_OB_BREAK_THEN_FVG",
         "CERTIFIED_UNSWEPT_OB_BREAK_THEN_FVG")


def _ordered(triggers:list[dict],mode:str,bars:list[dict])->list[dict]:
    by_index={}
    for sig in triggers:by_index.setdefault(sig["signal_index"],[]).append(sig)
    found=[]
    for i in range(40,len(bars)-1):
        right=by_index.get(i,[])
        for entry in right:
            side=entry["side"]
            if mode=="LIQ_THEN_OB_BREAK" and entry["family"]!="OB_BREAK":continue
            if mode in ("LIQ_THEN_OB_BREAK_THEN_FVG",
                        "CERTIFIED_UNSWEPT_OB_BREAK_THEN_FVG") and entry["family"]!="FVG":
                continue
            ob=[x for x in triggers if x["family"]=="OB_BREAK" and x["side"]==side and
                i-WINDOW_BARS <= x["signal_index"] < i]
            liq=[x for x in triggers if x["family"]=="LIQ_SWEEP" and x["side"]==side and
                 i-WINDOW_BARS <= x["signal_index"] < i]
            if mode=="LIQ_THEN_OB_BREAK":
                ob=[entry]
                liq=[x for x in liq if x["signal_index"]<i]
                if not liq:continue
                preceding=max(liq,key=lambda x:x["signal_index"])
                ids=[preceding["signal_index"],i]
            elif mode=="LIQ_THEN_OB_BREAK_THEN_FVG":
                pairs=[(l,o) for l in liq for o in ob if l["signal_index"]<o["signal_index"]]
                if not pairs:continue
                l,o=max(pairs,key=lambda x:(x[1]["signal_index"],x[0]["signal_index"]))
                ids=[l["signal_index"],o["signal_index"],i]
            else:
                # NO_SWEEP is an observed complete window, not missing LIQ log.
                # This branch requires contiguous actual OHLC and explicit scan of
                # the previous range's low/high on every bar of the window.
                if not ob:continue
                o=max(ob,key=lambda x:x["signal_index"])
                if any(x["signal_index"]>=o["signal_index"] for x in liq):continue
                span=bars[o["signal_index"]-WINDOW_BARS:o["signal_index"]]
                if len(span)!=WINDOW_BARS:continue
                prior=bars[o["signal_index"]-WINDOW_BARS-20:o["signal_index"]-WINDOW_BARS]
                if len(prior)!=20:continue
                lo=min(x["low"] for x in prior);hi=max(x["high"] for x in prior)
                if any(x["low"]<lo or x["high"]>hi for x in span):continue
                ids=[o["signal_index"],i]
            out=dict(entry)
            out["proxy_sequence"]=mode
            out["event_bar_ids"]=ids
            out["not_proven_ict_structure"]=True
            found.append(out)
    return found


def chronology_research(raw_bars:list[dict],symbol:str)->dict:
    rows=[];coverage=[]
    for tf in (1,4):
        bars=compress(raw_bars,tf)
        if len(bars)<140:
            coverage.append({"tf_hours":tf,"status":"NOT_TESTABLE_SHORT_HISTORY"})
            continue
        trig=features(bars)
        cut=int(len(bars)*.7)
        for mode in RECIPES:
            signals=_ordered(trig,mode,bars)
            for side in ("long","short"):
                eligible=[x for x in signals if x["side"]==side]
                for target in ("fixed_1r","fixed_2r","structural"):
                    trades=[trade(bars,s,tf,target,COST_BPS_PER_ROUNDTRIP[symbol])
                            for s in eligible]
                    trades=nonoverlapping([t for t in trades if t is not None])
                    ins=[t for t in trades if t["exit_ms"]<bars[cut]["ts"]]
                    hold=[t for t in trades if t["entry_ms"]>=bars[cut]["ts"]]
                    rows.append({"tf_hours":tf,"sequence":mode,"side":side,
                        "target_type":target,"train_n":len(ins),"hold_n":len(hold),
                        "train_mean_net_R":mean(t["net_R"] for t in ins) if ins else None,
                        "hold_mean_net_R":mean(t["net_R"] for t in hold) if hold else None,
                        "train_statistics":metrics(ins),
                        "hold_statistics":metrics(hold),
                        "out_of_sample_independent":False,
                        "event_sequences_proxy_only":True})
    return {"schema":"H092.chronology_proxy.v1","symbol":symbol,
            "kind":"REAL_BAR_EXPLORATORY_EVENT_ORDER_NOT_MSS_CONFIRMED",
            "trial_count":len(rows),"rows":rows,"coverage":coverage,
            "model_selection_verdict":"NO_DECISION",
            "forward_alpha_verified":False}
