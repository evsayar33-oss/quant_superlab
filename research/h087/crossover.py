"""H087: 70 frozen H085 x H086 cross-family overlays and chance controls.

External research inputs are ALREADY EXPOSED in H085/H086, not sealed new OOS.
H085 contains US equity rotation model NAV returns net of its own costs;
H086 provides Fama/Cboe prior-close risk exposures and Fama RF. Different
underlyings: monthly risk overlay is a descriptive proxy, NOT broker replay.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"results"/"h087"
INPUT=ROOT/"results"
CFG=ROOT/"research"/"h087"/"FROZEN_PROTOCOL.yaml"


def calc_total(x):
    a=np.asarray(x,float)
    if not np.isfinite(a).all() or np.any(a<=-1):
        raise ValueError("Missing/non-compoundable returns")
    return float(np.prod(1+a)-1)


def load_inputs(c):
    h85=INPUT/"h085"
    h86=INPUT/"h086"
    if not (h85/"H085_REPORT.json").exists():
        raise FileNotFoundError("Missing archived H085 GitHub Action artifact")
    if not (h86/"H086_COMPLETE_RESULTS.json").exists():
        raise FileNotFoundError("Missing archived H086 GitHub Action artifact")
    j85=json.loads((h85/"H085_REPORT.json").read_text())
    j86=json.loads((h86/"H086_COMPLETE_RESULTS.json").read_text())
    if j85["study"]!="H085" or j86["study"]!="H086":
        raise ValueError("External archive identifiers mismatch")
    if j85["meta"]["excluded_partial_last_month"] is not True:
        raise ValueError("H085 partial November needs exclusion")
    sources={}
    suffix="_25bp.csv"
    for fp in sorted(h85.glob("monthly_*"+suffix)):
        name=fp.name[len("monthly_"):-len(suffix)]
        df=pd.read_csv(fp,parse_dates=["month"]).set_index("month").sort_index()
        if df.index.duplicated().any() or not df.index.is_monotonic_increasing:
            raise ValueError(f"Month order invalid for {name}")
        if set(df.columns)<{"return_net","spy_return","cash_weight","turnover"}:
            raise ValueError(f"Missing costed H085 fields for {name}")
        sources[name]=df
    if len(sources)!=14:
        raise ValueError(f"Exactly 14 pre-registered monthly parents required; saw {len(sources)}")
    dates=next(iter(sources.values())).index
    for name,df in sources.items():
        if not dates.equals(df.index):
            raise ValueError(f"Mixed or missing H085 calendar {name}")
        if not np.allclose(df.spy_return.to_numpy(),
                           next(iter(sources.values())).spy_return.to_numpy()):
            raise ValueError(f"SPY benchmark mismatch in {name}")
    raw=pd.read_csv(h86/"H086_DAILY_RETURNS.csv",parse_dates=["date"])
    if set(raw)<{"date","hypothesis","weight","rf"}:
        raise ValueError("Missing H086 daily funding/weight fields")
    if raw.duplicated(["hypothesis","date"]).any():
        raise ValueError("H086 duplicate dated weights")
    if set(raw.hypothesis)!={"H086A","H086B","H086C","H086D","H086E"}:
        raise ValueError("Expected exactly five separately frozen H086 controls")
    # Last risk exposure of previous completed month determines weight next month.
    raw["month"]=raw.date.dt.to_period("M").dt.to_timestamp("M")
    daily=raw[raw.hypothesis=="H086A"].copy()
    rf=daily.groupby("month").rf.apply(calc_total)
    risk={}
    for name,x in raw.groupby("hypothesis",sort=True):
        end=x.sort_values("date").groupby("month").weight.last()
        end.index=pd.DatetimeIndex(end.index)
        next_month_weights=end.shift(1)  # position at end t-1, NOT same-month close
        risk[name]=next_month_weights
    risk=pd.DataFrame(risk)
    all_dates=dates[(dates >= pd.Timestamp(c["cross_family"]["source_monthly_window"][0])) &
                    (dates <= pd.Timestamp(c["cross_family"]["source_monthly_window"][1]))]
    if len(all_dates)<36:
        raise ValueError("Too few months for frozen cross-family study")
    if risk.reindex(all_dates).isna().any().any():
        raise ValueError("Risk filter missing first prior month; no lookahead substitute")
    if rf.reindex(all_dates).isna().any():
        raise ValueError("Risk-free months unavailable")
    inputs={
        "H085_source_zip_identifier":"GitHub run 43571747386",
        "H086_source_zip_identifier":"GitHub run 43576823624",
        "H085_hash":j85["meta"]["nav_source_sha256"],
        "H086_raw_source_hashes":j86["source_sha256"],
        "start":str(all_dates.min().date()),"end":str(all_dates.max().date()),
        "aligned_months":len(all_dates),
        "parent_variants":len(sources),"filters":len(risk.columns),
    }
    return sources,risk.loc[all_dates],rf.loc[all_dates],all_dates,inputs


def overlay(pr:np.ndarray, risk:np.ndarray, rf:np.ndarray, extra_bp:int):
    """Monthly investment in H085 proxy + RF on cash; turnover at stated bp.

    Each risk[i] decided from previous month's last published H086 weight.
    """
    a=np.asarray(pr,float); w=np.asarray(risk,float); safe=np.asarray(rf,float)
    if not (len(a)==len(w)==len(safe)):
        raise ValueError("Series length mismatch")
    if not np.isfinite(np.c_[a,w,safe]).all() or ((w<0)|(w>1)).any():
        raise ValueError("Missing or levered overlay inputs")
    prev=np.r_[1.,w[:-1]]
    turn=np.abs(w-prev)
    out=w*a+(1-w)*safe-turn*extra_bp/10000.
    return out,turn


def stationary_max_stat(active:np.ndarray, reps=2000, block=3, seed=87031):
    """White-style centered max-mean stationary bootstrap across all variants.

    This approximates a familywise null for existing reused history, not
    independent forward alpha. No moving strategy-specific target thresholds.
    """
    a=np.asarray(active,float)
    T,K=a.shape
    if T<36 or K<5 or not np.isfinite(a).all():
        return {"familywise_p":None,"note":"insufficient_finite_months"}
    observed=a.mean(axis=0)
    obs=float(observed.max())
    centered=a-observed
    rng=np.random.default_rng(seed)
    maxima=np.empty(reps)
    for j in range(reps):
        ix=np.empty(T,dtype=int);ix[0]=rng.integers(0,T)
        for t in range(1,T):
            ix[t]=rng.integers(0,T) if rng.random()<1./block else (ix[t-1]+1)%T
        maxima[j]=float(centered[ix].mean(axis=0).max())
    p=(1+np.sum(maxima>=obs))/(reps+1)
    return {"familywise_p":float(p),"max_observed_active_mean":obs,
            "n_models":K,"n_months":T,"bootstrap_repetitions":reps,
            "mean_block_months":block}


def summarize_model(ret:np.ndarray, spy:np.ndarray, start:int, end:int):
    x=ret[start:end]; b=spy[start:end]
    d=x-b
    nav=np.cumprod(1.+x)
    peak=np.maximum.accumulate(np.r_[1.,nav])[1:]
    return {"months":len(x),"cumulative_net":calc_total(x),
            "spy_total":calc_total(b),
            "active_total_gap":calc_total(x)-calc_total(b),
            "active_mean_month":float(d.mean()),
            "max_dd":float((nav/peak-1).min()),
            "active_total_ex_best_two_months":float(d.sum()-np.sort(d)[-2:].sum())}


def perform(c:dict):
    sources,risk,rf,dates,meta=load_inputs(c)
    cost_bps=c["cross_family"]["extra_oneway_turnover_cost_bps"]
    train_end=pd.Timestamp(c["cross_family"]["early_diagnostic_window"][1])
    late_start=pd.Timestamp(c["cross_family"]["late_diagnostic_window"][0])
    full_n=len(dates)
    split=int(np.searchsorted(dates.values,np.datetime64(late_start)))
    if split<18 or full_n-split<18:
        raise ValueError(f"Too few split dates: {split} early {full_n-split} late")
    frozen={}
    rows=[]
    benchmark=next(iter(sources.values())).loc[dates].spy_return.to_numpy(float)
    rf_arr=rf.to_numpy(float)
    for parent,frame in sorted(sources.items()):
        base=frame.loc[dates].return_net.to_numpy(float)
        for name in sorted(risk):
            w=risk[name].to_numpy(float)
            ret1,turn=overlay(base,w,rf_arr,cost_bps[0])
            ret2,_=overlay(base,w,rf_arr,cost_bps[1])
            # Evaluation controls: constant exposure fixed from PRE-2025
            # training data only. Not optimized on 2025+ outcomes.
            constant=float(np.mean(w[:split]))
            constant_late=constant*base[split:]+(1-constant)*rf_arr[split:]
            mid=parent+"|"+name
            frozen[mid]={"ret":ret1,"ret2":ret2,"parent":parent,
                         "risk":name,"w":w,"base":base,"turn":turn}
            early=summarize_model(ret1,benchmark,0,split)
            late=summarize_model(ret1,benchmark,split,full_n)
            late_stress=summarize_model(ret2,benchmark,split,full_n)
            late_const=calc_total(constant_late)
            gates={
                "late_net_above_spy":late["active_total_gap"]>0,
                "late_2x_cost_net_above_spy":late_stress["active_total_gap"]>0,
                "early_positive_active_mean":early["active_mean_month"]>0,
                "late_positive_active_mean":late["active_mean_month"]>0,
                "late_delete_best_two_positive":late["active_total_ex_best_two_months"]>0,
                "late_above_training_only_static_exposure":late["cumulative_net"]>late_const,
                "late_min_18_months":late["months"]>=18,
            }
            rows.append({
                "id":mid,"parent":parent,"overlay":name,
                "early_months":early["months"],"late_months":late["months"],
                "early_return":early["cumulative_net"],
                "early_spy":early["spy_total"],
                "late_net_return":late["cumulative_net"],
                "late_spy_return":late["spy_total"],
                "late_active_gap":late["active_total_gap"],
                "late_2x_cost_return":late_stress["cumulative_net"],
                "late_2x_cost_active_gap":late_stress["active_total_gap"],
                "late_max_dd":late["max_dd"],
                "late_constant_weight_control_return":late_const,
                "train_only_static_weight":constant,
                "mean_exposure":float(w.mean()),
                "late_active_mean":late["active_mean_month"],
                "late_active_minus_best_two_sum":late["active_total_ex_best_two_months"],
                "extra_overlay_turnover":float(turn.sum()),
                "local_gate_pass_count":int(sum(gates.values())),
                "local_gate_total":len(gates),
                **{"gate_"+g:bool(v) for g,v in gates.items()},
            })
    if len(frozen)!=70:raise ValueError("Exactly 70 independent meta variants needed")
    df=pd.DataFrame(rows)
    df.to_csv(OUT/"H087_SYNTHESIS_70.csv",index=False)
    active=np.stack([v["ret"]-benchmark for v in frozen.values()],axis=1)
    familywise=stationary_max_stat(active,
        reps=int(c["cross_family"]["inferential"]["familywise_bootstrap_iterations"]),
        block=int(c["cross_family"]["inferential"]["familywise_white_reality_check_block_months"]),
        seed=int(c["cross_family"]["inferential"]["bootstrap_seed"]))
    # Labelled timing placebo: circular phase-shifts preserve the exposure sequence,
    # destroy its actual calendar alignment and test whether timing helped on average.
    # Use SAME shift across all five controls to preserve contemporaneous dependence.
    observed_max=float(np.max(active[split:].mean(axis=0)))
    shifts=[]
    parents=sorted(sources)
    keys=sorted(risk)
    for s in range(1,full_n):
        maximum=-np.inf
        for parent in parents:
            original=sources[parent].loc[dates].return_net.to_numpy(float)
            for name in keys:
                w=np.roll(risk[name].to_numpy(float),s)
                ret,_=overlay(original,w,rf_arr,cost_bps[0])
                maximum=max(maximum,float((ret[split:]-benchmark[split:]).mean()))
        shifts.append(float(maximum))
    placebo_p=float((1+sum(v>=observed_max for v in shifts))/(len(shifts)+1))
    # Research-only top choice from pre-2025, tested on LATE REUSED history.
    ranked=sorted((float(v["ret"][:split].mean()-benchmark[:split].mean()),k)
                  for k,v in frozen.items())
    pre_pick=ranked[-1][1]
    pre_pick_late=summarize_model(frozen[pre_pick]["ret"],benchmark,split,full_n)
    best=df.sort_values("late_active_gap",ascending=False).iloc[0].to_dict()
    worst=df.sort_values("late_active_gap",ascending=True).iloc[0].to_dict()
    sig=familywise["familywise_p"] is not None and familywise["familywise_p"]<=.05
    gate_full=(df["gate_late_net_above_spy"]&
               df["gate_late_2x_cost_net_above_spy"]&
               df["gate_early_positive_active_mean"]&
               df["gate_late_positive_active_mean"]&
               df["gate_late_delete_best_two_positive"]&
               df["gate_late_above_training_only_static_exposure"]&
               df["gate_late_min_18_months"])
    approved=int((gate_full & sig & (placebo_p<=.05)).sum())
    report={
        "study":"H087","provenance":"FROZEN_PROTOCOL.yaml committed before cross-family study",
        "source_exposure":"EXPLORATORY_REUSED_TEST_NOT_UNTOUCHED_HOLDOUT",
        "input_provenance":meta,"number_cross_models":len(frozen),
        "cost_rates_bps":cost_bps,"split_date":str(dates[split].date()),
        "full_month_count":full_n,"early_month_count":split,"late_month_count":full_n-split,
        "late_spy_total":calc_total(benchmark[split:]),
        "number_above_SPY_late":int(df["gate_late_net_above_spy"].sum()),
        "number_above_SPY_late_2x":int(df["gate_late_2x_cost_net_above_spy"].sum()),
        "number_meeting_local_gates":int(gate_full.sum()),
        "familywise_bootstrap":familywise,
        "phase_shift_placebo":{"max_over_70_observed_mean":observed_max,
                              "placebo_p":placebo_p,
                              "exact_nonzero_circular_shifts":len(shifts),
                              "shifted_max_mean_quantiles":np.quantile(shifts,[0.05,0.50,0.95]).tolist(),
                              "note":"Heuristic timing null; data were already exposed, non-exchangeable regime shifts possible"},
        "pre_2025_selected_id":pre_pick,
        "pre_2025_selected_late_excess":pre_pick_late["active_total_gap"],
        "best_late_REUSED_TEST":{k:v for k,v in best.items() if
                k in ["id","late_net_return","late_spy_return","late_active_gap",
                      "late_2x_cost_return","late_constant_weight_control_return",
                      "late_active_minus_best_two_sum","mean_exposure"]},
        "worst_late_REUSED_TEST":{"id":worst["id"],"late_active_gap":worst["late_active_gap"]},
        "diagnostic_passed_not_live":approved,
        "new_live_accepts":0,
        "disqualifiers":[
            "All 2023-2026 source returns reused and public to earlier H085/H086 studies",
            "Overlay monthly return model not a funded executable daily share/lot portfolio",
            "Proxy SPY for H085 and research FF RF for cash are not identical securities",
            "70 hypotheses evaluated together with familywise max; cannot pick individual uncorrected winner",
            "Cross-family H083 original security selection also survivorship/PIT limited",
        ],
    }
    (OUT/"H087_STAT_TESTS.json").write_text(json.dumps(report,indent=2,default=str))
    print(json.dumps({k:report[k] for k in
        ["number_cross_models","full_month_count","number_above_SPY_late",
         "number_above_SPY_late_2x","number_meeting_local_gates",
         "familywise_bootstrap","phase_shift_placebo",
         "pre_2025_selected_id","pre_2025_selected_late_excess",
         "best_late_REUSED_TEST","diagnostic_passed_not_live"]},indent=2,default=str))
    return report


if __name__=="__main__":
    c=yaml.safe_load(CFG.read_text())
    perform(c)
