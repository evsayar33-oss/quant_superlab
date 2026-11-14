"""H100 predeclared cross-venue robustness screen over H099 immutable summary.

A *descriptive* screen, not fresh out-of-sample, cost execution, or alpha approval.
"""
from __future__ import annotations
from collections import defaultdict
from statistics import median
from math import isfinite

MIN_VENUES=3
MIN_MATCHED_PER_VENUE=30
MIN_MATCH_FRACTION=.50
REQUIRED_VENUES=("gate","bitget","mexc")
FAMILIES=("LIQ_SWEEP","MSS","BOS","OB_TOUCH","FVG_TOUCH","IFVG_CONFIRMED")
SIDES=("long","short")
COHORTS=("all","htf_aligned")
# Fixed assumptions inherited from H099: 1R, 20 bps round-trip. No reoptimization.

def screen(report):
    if report.get("schema")!="H099.independent_trade_proxy.v1":
        raise ValueError("INVALID_H099_SCHEMA")
    if report.get("alpha_accepted") is not False:
        raise ValueError("H099_ALPHA_GATE_NOT_CLOSED")
    results=report.get("results")
    if not isinstance(results,dict):raise ValueError("MISSING_RESULTS")
    output={}
    for symbol in ("BTC","ETH"):
        for tf in ("15m","1H"):
            scope=f"{symbol}_{tf}"
            for family in FAMILIES:
                for side in SIDES:
                    for cohort in COHORTS:
                        config=f"{family}:{side}:{cohort}"
                        rows=[];failures={}
                        for venue in REQUIRED_VENUES:
                            item=results.get(f"{scope}_{venue}",{})
                            if item.get("status")!="DESCRIPTIVE_TRADE_PROXY_COMPARISON":
                                failures[venue]="PROVIDER_OR_DATA_UNAVAILABLE"
                                continue
                            c=item.get("configurations",{}).get(config)
                            if not isinstance(c,dict):
                                failures[venue]="CONFIG_MISSING"
                                continue
                            n=c.get("matched_n",0)
                            frac=c.get("match_fraction_primary")
                            value=c.get("mean_secondary_matched_net_r")
                            boot=c.get("secondary_bootstrap",{})
                            ci=boot.get("ci_95") if isinstance(boot,dict) else None
                            if (not isinstance(n,int) or n<MIN_MATCHED_PER_VENUE
                                or frac is None or not isfinite(frac)
                                or frac<MIN_MATCH_FRACTION or value is None
                                or not isfinite(value) or not isinstance(ci,list)
                                or len(ci)!=2 or any(not isinstance(x,(int,float))
                                or not isfinite(x) for x in ci)):
                                failures[venue]="INSUFFICIENT_MATCHED_SAMPLE_OR_BOOTSTRAP"
                                continue
                            rows.append({"venue":venue,"matched_n":n,
                                         "match_fraction":frac,"mean_net_r":value,
                                         "ci_low":ci[0],"ci_high":ci[1],
                                         "mean_primary_matched_net_r":c.get("mean_primary_matched_net_r")})
                        enough=len(rows)>=MIN_VENUES
                        # All venues required; no favorable-venue selection.
                        consistent=enough and all(r["mean_net_r"]>0 for r in rows)
                        all_ci_positive=enough and all(r["ci_low"]>0 for r in rows)
                        output[f"{scope}:{config}"]={
                            "status":("DESCRIPTIVE_CONSISTENT_POSITIVE" if consistent else
                                      "DESCRIPTIVE_MIXED_OR_NEGATIVE" if enough else
                                      "INSUFFICIENT_INDEPENDENT_REPLICATION"),
                            "venue_count":len(rows),"required_venue_count":MIN_VENUES,
                            "venue_rows":rows,"failures":failures,
                            "all_venues_positive":bool(consistent),
                            "all_venue_bootstrap_lower_bounds_positive":bool(all_ci_positive),
                            "median_venue_mean_net_r":median(r["mean_net_r"] for r in rows) if rows else None,
                            "minimum_venue_mean_net_r":min(r["mean_net_r"] for r in rows) if rows else None,
                            "cost_stress_verified":False,
                            "untouched_oos_verified":False,
                            "multiple_testing_adjusted":False,
                            "alpha_accepted":False}
    counts=defaultdict(int)
    for r in output.values():counts[r["status"]]+=1
    return {"schema":"H100.crossvenue_robustness.v1",
            "source_schema":report["schema"],
            "fixed_configuration":"H099_1R_20BPS_ASSUMED",
            "required_venues":list(REQUIRED_VENUES),
            "minimum_matched_trades_per_venue":MIN_MATCHED_PER_VENUE,
            "minimum_primary_match_fraction":MIN_MATCH_FRACTION,
            "configuration_count":len(output),"status_counts":dict(counts),
            "configurations":output,
            "historical_selection_risk":"HIGH_SHARED_MARKET_AND_REUSED_HISTORICAL_SAMPLE",
            "bootstrap_interpretation":"DESCRIPTIVE_NOT_MULTIPLE_TESTING_OR_DEPENDENCE_ROBUST",
            "cost_stress_status":"NOT_TESTABLE_FROM_H099_SUMMARY_REQUIRES_TRADE_LEVEL_ENTRY_RISK",
            "untouched_oos_verified":False,
            "prospective_verified":False,
            "independent_execution_verified":False,
            "alpha_accepted":False,
            "research_complete":False}
