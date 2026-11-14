"""H094 fixed evidence gate: observational screens cannot become accepted alpha.

The research pipeline deliberately produces an INCOMPLETE verdict until there
is independent OOS, genuine new prospective trade outcomes, cost/carry/fill
proof and multiplicity-adjusted confidence, with pre-registration.
"""
from __future__ import annotations
import json
from collections import Counter


def classify(result:dict,requirements:dict|None=None)->dict:
    r=requirements or {
        "min_forward_trades":100,
        "min_independent_price_venues":2,
        "requires_pit_macro_fundamental_ablation":True,
        "requires_verified_execution_costs":True,
        "requires_unseen_prospective_start":True,
        "requires_multiple_testing_control":True,
        "requires_nonoverlap_portfolio_simulation":True,
    }
    if result.get("schema")!="H091_H092.exploratory.v1":
        raise ValueError("research schema mismatch")
    issues=[]
    if result.get("historical_oos_is_new_unseen_data") is not True:
        issues.append("HISTORICAL_OOS_ALREADY_RESEARCHED")
    if result.get("independent_price_source_count",1)<r["min_independent_price_venues"]:
        issues.append("SINGLE_MARKET_PRICE_SOURCE")
    if not result.get("funding_verified") or not result.get("slippage_verified"):
        issues.append("TRUE_FINANCING_SLIPPAGE_COST_UNVERIFIED")
    if not result.get("fill_verified"):
        issues.append("REAL_EXECUTION_FILL_UNVERIFIED")
    if not result.get("fundamental_macro_integrated_backtest"):
        issues.append("TECHNICAL_FUNDAMENTAL_MACRO_ABLATION_NOT_TESTED")
    if not result.get("multiplicity_adjusted_significance"):
        issues.append("MULTIPLE_TESTING_NOT_VERIFIED")
    if not result.get("nonoverlapping_portfolio_nav_verified"):
        issues.append("PORTFOLIO_CONCURRENT_RISK_NOT_VERIFIED")
    if result.get("prospective_completed_trades",0)<r["min_forward_trades"]:
        issues.append("PROSPECTIVE_SAMPLE_INSUFFICIENT")
    if not result.get("prospective_snapshot_timestamp_chain_verified"):
        issues.append("FORWARD_FIRST_SEEN_CHAIN_NOT_VERIFIED")
    return {"schema":"H094.acceptance.v1","symbol":result["symbol"],
            "verdict":"NOT_VERIFIED" if issues else "EVIDENCE_REVIEW_REQUIRED",
            "risk_gates_passed":False,"live_trading_authorized":False,
            "candidate_recommendation":False,"reasons":sorted(set(issues)),
            "research_trials":result.get("trial_count",0),
            "research_trades_are_not_independent":True,
            "notes":"Never write main strategy ACCEPT from this research script."}


def coverage(outputs:list[dict],gate_outputs:list[dict])->dict:
    if len(outputs)!=len(gate_outputs):raise ValueError("missing paired evidence")
    return {"schema":"H094.program_snapshot.v1","kind":"RESEARCH_REPORT_NOT_ALPHA",
            "trials":sum(x.get("trial_count",0) for x in outputs),
            "symbols":[x["symbol"] for x in outputs],
            "outcomes":Counter(g["verdict"] for g in gate_outputs),
            "verified_alpha_claims":0,"production_registry_modified":False,
            "stages":{"H091":"EXPLORATORY_OHLC_BASELINES",
                      "H092":"EXPLORATORY_ENTRY_TARGET_MATRIX",
                      "H093":"POINT_IN_TIME_FUSION_CONTRACT_ONLY",
                      "H094":"EVIDENCE_GATES_AND_NO_ACCEPT"}}
