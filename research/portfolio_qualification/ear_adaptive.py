"""Independent Quant Superlab statistical checks over raw observation/outcome rows.

The workflow imports the pinned real Quant Superlab metrics package.
No official ACCEPT registry changes. No fabricated performance or missing-return zeros.
"""
from __future__ import annotations
from collections import defaultdict
import math
import hashlib
import json

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),
                                    allow_nan=False).encode("utf8")).hexdigest()

COST={"BIST":2.0,"US":1.0,"CRYPTO":0.6}

def validate(rule, rows, *, stage, n_trials, lock=None):
    import pandas as pd
    from scipy.stats import fisher_exact, binomtest
    from lab import metrics  # pinned Quant Superlab, independent of EAR evaluation
    if stage not in ("DISCOVERY","FORWARD") or n_trials<1:
        raise ValueError("V18_BAD_VALIDATION_CONTRACT")
    if stage=="FORWARD" and (not lock or lock["rule"]!=rule):
        raise ValueError("V18_LOCK_REQUIRED")
    true,false=[],[]
    days=defaultdict(lambda:[[],[]])
    cross=defaultdict(lambda:[[],[]])
    ids=set()
    for row in rows:
        if row["id"] in ids or row["market"]!=rule["market"]:
            raise ValueError("V18_DUPLICATE_OR_WRONG_MARKET")
        ids.add(row["id"])
        o=row["outcome"]
        if o["status"]!="COMPLETE_MARK_ONLY" or not o["entry"]<o["end"]:
            raise ValueError("V18_INVALID_PRICE_OUTCOME")
        if stage=="FORWARD":
            if row["kind"]!="FIRST_SEEN" or not lock["start"]<=row["seen"]<lock["end"] or o["entry"]<=row["seen"]:
                raise ValueError("V18_HOLDOUT_LEAK")
        if row["anchor"]>row["seen"] or o["entry"]<row["anchor"]:
            raise ValueError("V18_LOOKAHEAD")
        price_return=100*(o["exit_close"]/o["entry_open"]-1)
        if not math.isclose(price_return,o["gross_pct"],abs_tol=1e-6):
            raise ValueError("V18_RETURN_MISMATCH")
        # Reconstruct actual observed extrema and marks from the immutable
        # underlying bar window, instead of trusting producer summary fields.
        bars=o.get("bars")
        expected=16 if row["market"]=="CRYPTO" else 5
        if not isinstance(bars,list) or len(bars)!=expected or digest(bars)!=o["bars_sha"]:
            raise ValueError("V18_RAW_BAR_DIGEST_OR_LENGTH")
        if bars[0]["start"]!=o["entry"] or bars[-1]["end"]!=o["end"] or bars[0]["open"]!=o["entry_open"] or bars[-1]["close"]!=o["exit_close"]:
            raise ValueError("V18_RAW_BAR_MARK_MISMATCH")
        for b in bars:
            if not all(math.isfinite(b[k]) for k in ("open","high","low","close","volume")) or min(b[k] for k in ("open","high","low","close"))<=0 or b["volume"]<0 or b["low"]>min(b["open"],b["close"]) or b["high"]<max(b["open"],b["close"]):
                raise ValueError("V18_INVALID_RAW_OHLC")
        for a,b in zip(bars,bars[1:]):
            if b["start"]<=a["start"] or (row["market"]=="CRYPTO" and b["start"]!=a["end"]) or abs(b["open"]/a["close"]-1)>.75:
                raise ValueError("V18_RAW_BAR_GAP")
        target=15 if row["market"]=="US" else 12
        u,d=(100*(max(b["high"] for b in bars)/o["entry_open"]-1),
             100*(min(b["low"] for b in bars)/o["entry_open"]-1)) if row["market"]=="CRYPTO" else (price_return,price_return)
        if not math.isclose(u,o["up_pct"],abs_tol=1e-6) or not math.isclose(d,o["down_pct"],abs_tol=1e-6):
            raise ValueError("V18_RAW_BAR_EXTREMA_MISMATCH")
        label="BOTH" if u>=target and d<=-target else "UP" if u>=target else "DOWN" if d<=-target else "NONE"
        if label!=o["label"]:
            raise ValueError("V18_EVENT_LABEL_MISMATCH")
        features=row["features"]
        vals=[features.get(k) for k,_ in rule["terms"]]
        if not all(type(x) is bool for x in vals):
            continue
        match=[v==wanted for v,(_,wanted) in zip(vals,rule["terms"])]
        signal=all(match) if rule["operator"]=="all" else any(match)
        side=1 if rule["direction"]=="UP" else -1
        stressed=side*price_return-2*COST[row["market"]]
        item=(row,label==rule["direction"],stressed)
        (true if signal else false).append(item)
        day=row["anchor"]//86_400_000
        period=row["anchor"]//(14_400_000 if row["market"]=="CRYPTO" else 86_400_000)
        cross[(day,period,row["liquidity"])][0 if signal else 1].append(stressed)
    tp=sum(x[1] for x in true);fp=len(true)-tp;fn=sum(x[1] for x in false);tn=len(false)-fn
    valid=len(true)+len(false);cases=tp+fn;controls=fp+tn
    precision=tp/len(true) if true else 0
    recall=tp/cases if cases else 0
    fpr=fp/controls if controls else 1
    baseline=cases/valid if valid else 0
    lift=precision/baseline if baseline else 0
    fisher=float(fisher_exact([[tp,fp],[fn,tn]],alternative="greater").pvalue) if cases and controls else 1.
    for (day,_,_), (a,b) in cross.items():
        if a and b:
            days[day][0].append(sum(a)/len(a)-sum(b)/len(b))
            days[day][1].append(sum(a)/len(a))
    # Aggregate correlated contracts on each UTC day before testing. Signs are
    # a conservative diagnostic, not an independent-sample guarantee.
    matched=[sum(a)/len(a) for a,_ in days.values() if a]
    positive=sum(x>0 for x in matched);n=len(matched)
    p=float(binomtest(positive,n,.5,alternative="greater").pvalue) if n else 1.
    correction=max(1,n_trials) if stage=="DISCOVERY" else 1
    dsr=None
    ordered=pd.Series([sum(days[k][0])/len(days[k][0])/100 for k in sorted(days) if days[k][0]],dtype=float)
    if len(ordered)>=30 and ordered.std()>0:
        estimate=metrics.dsr(ordered,max(n_trials,1))
        if math.isfinite(estimate):dsr=float(estimate)
    case_symbols=len({r["symbol"] for r,is_case,_ in true+false if is_case})
    stress_mean=sum(x[2] for x in true)/len(true) if true else None
    matched_mean=sum(matched)/n if n else None
    checks={
        "coverage":valid>=.8*len(rows) and cases>=30 and controls>=200 and case_symbols>=5,
        "detection":tp>=5 and recall>=.1 and fpr<=.15 and lift>=1.5,
        "stress":stress_mean is not None and stress_mean>0 and matched_mean is not None and matched_mean>0,
        "multiplicity":min(1.,fisher*correction)<=.05,
        "day_block":n>=10 and min(1.,p*correction)<=.05,
    }
    return {"schema":"QS.ear_adaptive_diagnostic_receipt.v1","stage":stage,
            "rule_sha":digest(rule),"dataset_sha":digest(sorted((r["id"],r["outcome"]["bars_sha"]) for r in rows)),
            "trial_count":n_trials,"rows":len(rows),"valid":valid,"tp":tp,"fp":fp,"fn":fn,"tn":tn,
            "precision":precision,"recall":recall,"fpr":fpr,"lift":lift,"stress_mean":stress_mean,
            "matched_stress_mean":matched_mean,"matched_days":n,"corrected_fisher_p":min(1.,fisher*correction),
            "corrected_day_sign_p":min(1.,p*correction),"dsr_daily_matched_diagnostic":dsr,
            "pbo":None,"pbo_reason":"REQUIRES_FULL_ALIGNED_VARIANT_MATRIX_NOT_SPARSE_EVENT_ROWS",
            "checks":checks,"verdict":"SCREEN_PASSED" if all(checks.values()) else "SCREEN_NOT_PASSED",
            "official_gate":"NOT_RUN","trade_authorized":False,"paper_approved":False}
