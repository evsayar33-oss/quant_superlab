"""H090 non-executing multi-strategy decision arbitration.

This is a *research candidate* router, not an exchange order manager. It never
chooses a winner by backtest result, predicts fills, or mutates live positions.
Same-symbol opposing signals are abstained; risk budget is explicitly bounded.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from .engine import evaluate_recipe, utc


def route(candidates: list[dict], *, max_total_risk: float = 0.02,
          max_symbol_risk: float = 0.01, per_signal_risk: float = 0.005) -> dict:
    """Deterministic no-lookahead risk-intent overlay; never actual orders."""
    caps=(max_total_risk,max_symbol_risk,per_signal_risk)
    if any(not isinstance(v,(float,int)) or not math.isfinite(v) or v<=0 or v>1 for v in caps):
        raise ValueError("risk caps must be finite and in (0,1]")
    if per_signal_risk>max_symbol_risk or max_symbol_risk>max_total_risk:
        raise ValueError("risk caps out of order")
    keys=set()
    by_symbol=defaultdict(list)
    for row in candidates:
        if row.get("kind")!="RESEARCH_SIGNAL_NOT_ORDER_NOT_BACKTEST":
            raise ValueError("only research signals accepted")
        for key in ("recipe_id","symbol","side","entry_at_utc","event_ids"):
            if key not in row:raise ValueError("incomplete candidate")
        if row["side"] not in ("long","short"):
            raise ValueError("direction must be explicit")
        uid=(row["recipe_id"],row["symbol"],tuple(row["event_ids"]))
        if uid in keys:raise ValueError("duplicate strategy trigger")
        keys.add(uid)
        utc(row["entry_at_utc"])
        by_symbol[row["symbol"]].append(row)
    accepted=[];rejected=[];used_total=0.
    # Equal-risk deterministic arbitration independent of profitability.
    for symbol in sorted(by_symbol):
        group=by_symbol[symbol]
        if len({x["side"] for x in group})>1:
            rejected.extend({**x,"reason":"OPPOSING_SIGNALS_ABSTAIN"} for x in group)
            continue
        used_symbol=0.
        for x in sorted(group,key=lambda y:(y["entry_at_utc"],y["recipe_id"])):
            if used_symbol+per_signal_risk>max_symbol_risk+1e-12 or used_total+per_signal_risk>max_total_risk+1e-12:
                rejected.append({**x,"reason":"RISK_BUDGET_EXHAUSTED"})
                continue
            accepted.append({**x,"research_risk_fraction":per_signal_risk})
            used_symbol+=per_signal_risk
            used_total+=per_signal_risk
    return {"schema":"H090.arbitration.v1","kind":"RESEARCH_INTENTS_NOT_ORDERS",
            "accepted_research_intents":accepted,"rejected_research_intents":rejected,
            "total_risk_intent_fraction":used_total,"risk_budget_fraction":max_total_risk,
            "executed_orders":0,"broker_fills_verified":False,
            "portfolio_strategy_edge_verified":False}


def scan(raw_events: list[dict], recipes: list[dict], *, asof: str,
         max_total_risk: float = 0.02, max_symbol_risk: float = 0.01,
         per_signal_risk: float = 0.005) -> dict:
    """Compose all registered research recipes, then abstain on conflicts."""
    found=[]
    for recipe in recipes:
        found.extend(evaluate_recipe(raw_events,recipe,asof=asof))
    res=route(found,max_total_risk=max_total_risk,
              max_symbol_risk=max_symbol_risk,per_signal_risk=per_signal_risk)
    res["asof_utc"]=utc(asof).isoformat()
    res["evaluated_recipes"]=len(recipes)
    return res
