"""H101: immutable fixed-spec trade-level cost and sample diagnostics.

All outcomes are OHLC proxies; neither historical tail nor independent venue
proves untouched prospective trading or executable costs. No strategy selection.
"""
from __future__ import annotations
from collections import Counter
from statistics import mean
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h099"))
from replicate import signals
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h096"))
from engine import FAMILIES,simulate,exclusive

COSTS=(20.,40.,80.)
COHORTS=("all","htf_aligned")
MIN_N=30

def instrument_audit(bars,parent_bars,symbol,tf,cutoff_ms):
    """Use strictly past-confirmed signals and frozen 1R proxy for each venue."""
    setups=signals(bars,parent_bars,symbol,tf)
    outputs={};ledger=[]
    for fam in FAMILIES:
        for side in ("long","short"):
            for cohort in COHORTS:
                name=f"{fam}:{side}:{cohort}"
                cand=[x for x in setups if x["signal"]["kind"]==fam
                      and x["side"]==side and (cohort=="all" or x["aligned"])]
                # Simulate once: trade selection is identical across all cost levels.
                chosen=[]
                for s in cand:
                    result=simulate(bars,s,"1R",20.,tf)
                    if result is not None:
                        chosen.append((result,s))
                selected=[];end=-1
                for t,s in sorted(chosen,key=lambda v:(v[0]["entry_ms"],v[0]["exit_ms"])):
                    if t["entry_ms"]<=end:continue
                    selected.append((t,s));end=t["exit_ms"]
                cost_stats={}
                for cost in COSTS:
                    values=[];tail=[]
                    for t,s in selected:
                        entry=bars[s["entry_index"]]["open"]
                        risk=s["risk"]
                        # Exact fixed-risk R conversion of additional assumed round-trip bps.
                        # H096 net_r already includes 20bps at entry/risk scaling.
                        value=t["net_r"]-(cost-20.)/10000.*entry/risk
                        values.append(value)
                        if t["entry_ms"]>=cutoff_ms:tail.append(value)
                    cost_stats[str(int(cost))]={
                        "n":len(values),"mean_net_r":mean(values) if values else None,
                        "positive_fraction":mean(v>0 for v in values) if values else None,
                        "historical_tail_n":len(tail),
                        "historical_tail_mean_net_r":mean(tail) if tail else None,
                        "eligible_for_descriptive_sample":len(values)>=MIN_N}
                for t,s in selected:
                    entry=bars[s["entry_index"]]["open"]
                    ledger.append({"config":name,"entry_ms":t["entry_ms"],
                                   "exit_ms":t["exit_ms"],"family":fam,"side":side,
                                   "cohort":cohort,"entry_price":entry,"risk_price":s["risk"],
                                   "stop_first_exit_cause":t["cause"],
                                   "net_r_20bps":t["net_r"],
                                   "net_r_40bps":t["net_r"]-.002*entry/s["risk"],
                                   "net_r_80bps":t["net_r"]-.006*entry/s["risk"],
                                   "historical_tail":t["entry_ms"]>=cutoff_ms})
                a=cost_stats["20"];b=cost_stats["80"]
                outputs[name]={
                    "cost_assumptions_bps":cost_stats,
                    "break_even_20bps":a["mean_net_r"] is not None and a["mean_net_r"]>0,
                    "survives_80bps":b["mean_net_r"] is not None and b["mean_net_r"]>0,
                    "historical_tail_at_80bps_positive":(
                        b["historical_tail_mean_net_r"] is not None
                        and b["historical_tail_mean_net_r"]>0),
                    "enough_trades_30":a["n"]>=MIN_N,
                    "alpha_accepted":False}
    return {"symbol":symbol,"tf":tf,"bar_count":len(bars),
            "first_bar_ms":bars[0]["ts"] if bars else None,
            "last_bar_ms":bars[-1]["ts"] if bars else None,
            "historical_tail_cutoff_ms":cutoff_ms,
            "configurations":outputs,"ledger":ledger,
            "count_ledger_records":len(ledger),
            "real_fill_verified":False,"funding_included":False,"alpha_accepted":False}

def aggregate_report(records,errors):
    by_config={}
    for symbol in ("BTC","ETH"):
        for tf in ("15m","1H"):
            for fam in FAMILIES:
                for side in ("long","short"):
                    for cohort in COHORTS:
                        key=f"{symbol}:{tf}:{fam}:{side}:{cohort}"
                        r=[]
                        for venue in ("gate","bitget","mexc"):
                            k=f"{symbol}_{tf}_{venue}"
                            if k in records:
                                v=records[k]["configurations"][f"{fam}:{side}:{cohort}"]
                                r.append({"venue":venue,"n":v["cost_assumptions_bps"]["20"]["n"],
                                    "tail_n":v["cost_assumptions_bps"]["20"]["historical_tail_n"],
                                    "mean_20":v["cost_assumptions_bps"]["20"]["mean_net_r"],
                                    "mean_80":v["cost_assumptions_bps"]["80"]["mean_net_r"],
                                    "tail_mean_80":v["cost_assumptions_bps"]["80"]["historical_tail_mean_net_r"]})
                        complete=len(r)==3 and all(x["n"]>=MIN_N for x in r)
                        by_config[key]={"venues":r,"fully_sampled_three_venues":complete,
                            "descriptive_all_venues_net_positive_80bps":bool(
                                complete and all(x["mean_80"] is not None and x["mean_80"]>0 for x in r)),
                            "descriptive_tail_positive_80bps":bool(
                                complete and all(x["tail_n"]>=MIN_N
                                and x["tail_mean_80"] is not None and x["tail_mean_80"]>0 for x in r)),
                            "alpha_accepted":False}
    return {"schema":"H101.trade_level_cost_sample_audit.v1",
      "status":"RESEARCH_ONLY","cost_stress_assumption_roundtrip_bps":list(COSTS),
      "configs_total":len(by_config),"configs_three_venue_n30":sum(v["fully_sampled_three_venues"] for v in by_config.values()),
      "configs_three_venue_positive_at_80bps":sum(v["descriptive_all_venues_net_positive_80bps"] for v in by_config.values()),
      "configs_tail_positive_at_80bps":sum(v["descriptive_tail_positive_80bps"] for v in by_config.values()),
      "configurations":by_config,"venue_errors":errors,
      "trade_level_cost_conversion":"EXACT_ASSUMED_ROUNDTRIP_BPS_TIMES_ENTRY_DIVIDED_BY_INITIAL_RISK",
      "historical_tail_is_fresh_oos":False,
      "same_market_multi_venue_is_independent_statistical_evidence":False,
      "multiple_testing_adjusted":False,
      "real_execution_cost_verified":False,"funding_settlement_verified":False,
      "prospective_verified":False,"alpha_accepted":False,"research_complete":False}
