"""H098 conservative cost ledger, time-aligned cross-venue checks, and evidence gates."""
from __future__ import annotations
from math import isfinite
from statistics import mean
import hashlib
import json

def compare(okx,other,tf_ms,max_close_bps=100):
    """Compare *only* exact UTC bar starts; never nearest-neighbor join."""
    a={x["ts"]:x for x in okx};b={x["ts"]:x for x in other}
    common=sorted(set(a)&set(b))
    if len(common)<30:
        return {"status":"NOT_TESTABLE_INSUFFICIENT_OVERLAP",
                "overlap":len(common),"comparable":False}
    deltas=[abs(a[t]["close"]/b[t]["close"]-1)*10000 for t in common]
    gap_a=sum(y["ts"]-x["ts"]!=tf_ms for x,y in zip(okx,okx[1:]))
    gap_b=sum(y["ts"]-x["ts"]!=tf_ms for x,y in zip(other,other[1:]))
    return {"status":"CROSS_VENUE_PRICE_CHECK_ONLY","overlap":len(common),
            "median_close_difference_bps":sorted(deltas)[len(deltas)//2],
            "mean_close_difference_bps":mean(deltas),
            "maximum_close_difference_bps":max(deltas),
            "within_100bps_count":sum(x<=max_close_bps for x in deltas),
            "okx_gap_count":gap_a,"independent_gap_count":gap_b,
            "comparable":True,"strategy_replicated":False,
            "execution_verified":False}


def funding_observed(trade,observations):
    """Observed cashflow sensitivity; exact settlement completeness not established.

    For linear USD-M perps, funding debit for a long is positive rate times
    notional, short is opposite. Notional drift / mark price not available,
    so this is only a unit-notional approximation, never a verified cost.
    """
    if trade["side"] not in ("long","short"):raise ValueError("INVALID_SIDE")
    sign=1 if trade["side"]=="long" else -1
    points=[x for x in observations if
            trade["entry_ms"]<x["funding_time_ms"]<=trade["exit_ms"]]
    rates=[float(x["realized_rate"]) for x in points]
    if any(not isfinite(r) for r in rates):raise ValueError("INVALID_FUNDING")
    return {"observed_count":len(points),
            "estimated_unit_notional_debit":sign*sum(rates),
            "status":"SENSITIVITY_ONLY_INCOMPLETE_SETTLEMENT_COVERAGE",
            "exact_funding_verified":False}


def cost_sensitivity(entry,exit_price,side,fee_bps,spread_bps,slippage_bps,
                     impact_bps,funding_unit_notional=0):
    if side not in ("long","short") or not 0<entry or not 0<exit_price:
        raise ValueError("INVALID_TRADE")
    vals=(fee_bps,spread_bps,slippage_bps,impact_bps,funding_unit_notional)
    if any(not isfinite(v) for v in vals) or min(vals[:4])<0:
        raise ValueError("INVALID_COST")
    d=1 if side=="long" else -1
    gross=d*(exit_price/entry-1)
    all_in=(fee_bps+spread_bps+slippage_bps+impact_bps)/10000
    return {"gross_return":gross,"assumed_net_return":gross-all_in-funding_unit_notional,
            "fee_bps_assumed":fee_bps,"spread_bps_assumed":spread_bps,
            "slippage_bps_assumed":slippage_bps,"impact_bps_assumed":impact_bps,
            "funding_sensitivity":funding_unit_notional,
            "measured_execution_costs":False}


def evidence_gate(venue_results,funding_available,prospective_snapshots):
    verified=[x for x in venue_results if x.get("comparable")]
    return {"cross_venue_candle_comparisons":len(verified),
            "funding_observations_available":bool(funding_available),
            "prospective_snapshots_in_this_run":len(prospective_snapshots),
            "prospective_persistence_verified":False,
            "independent_strategy_replicated":False,
            "actual_execution_costs_verified":False,
            "dependence_robust_significance_verified":False,
            "alpha_accepted":False,"research_complete":False}


def snapshot(symbol,tf,events,source_hash,asof_ms):
    """First-seen *candidate* snapshot. Persist across runs externally to prove first-seen."""
    eligible=sorted([e for e in events if e["observed_at_ms"]<=asof_ms],
                    key=lambda x:(x["observed_at_ms"],x["event_id"]))
    last=eligible[-20:]
    payload={"schema":"H098.prospective_candidate.v1","symbol":symbol,"tf":tf,
             "asof_ms":asof_ms,"source_sha256":source_hash,
             "events":[{"event_id":e["event_id"],"observed_at_ms":e["observed_at_ms"],
                        "kind":e["kind"],"side":e["side"]} for e in last],
             "persistent_first_seen_verified":False,
             "forward_performance_verified":False}
    payload["sha256"]=hashlib.sha256(json.dumps(payload,sort_keys=True,
                                              separators=(",",":")).encode()).hexdigest()
    return payload

def event_concordance(primary_events,secondary_events):
    """Descriptive detector repeatability, not matched trades or alpha."""
    def key(e):return (e["observed_at_ms"],e["kind"],e["side"])
    a={key(e) for e in primary_events};b={key(e) for e in secondary_events}
    overlap=a&b
    return {"primary_events":len(a),"independent_events":len(b),
            "exact_timestamp_kind_side_matches":len(overlap),
            "jaccard":len(overlap)/len(a|b) if a|b else None,
            "strategy_return_replication_verified":False}
