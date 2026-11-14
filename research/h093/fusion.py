"""H093 point-in-time optional factor join, no guessed historical observations.

OHLC technical signals and audited *availability* (not economic event date)
must be in the same symbol/instrument and use only data observed before entry.
Ablation must use identical trade cohorts; this module makes masks only.
"""
from __future__ import annotations
import math
from datetime import datetime,timezone


def dt(s:str):
    x=datetime.fromisoformat(s.replace("Z","+00:00"))
    if x.tzinfo is None:raise ValueError("naive release timestamp")
    return x.astimezone(timezone.utc)


def asof_context(entry_iso:str, observations:list[dict], *, symbol:str,
                 required:list[dict])->dict:
    """Return eligible or NOT_TESTABLE; never substitutes a future macro print."""
    entry=dt(entry_iso)
    used={}
    for condition in required:
        field=condition["field"]; max_age=float(condition["max_age_hours"])
        if not math.isfinite(max_age) or max_age<=0:raise ValueError("invalid age")
        valid=[o for o in observations if o.get("symbol")==symbol and
               o.get("field")==field and dt(o["available_at"])<=entry and
               0<=(entry-dt(o["available_at"])).total_seconds()/3600<=max_age]
        if not valid:
            return {"status":"NOT_TESTABLE_NO_POINT_IN_TIME_FACTOR",
                    "missing_field":field,"observations_used":used}
        observed=max(valid,key=lambda o:(dt(o["available_at"]),str(o.get("source_id",""))))
        if not observed.get("source_id"):raise ValueError("missing factor provenance")
        used[field]={"value":observed.get("value"),
                     "available_at":observed["available_at"],
                     "source_id":observed["source_id"]}
        if observed.get("value")!=condition.get("equals"):
            return {"status":"FILTER_REJECT","observations_used":used}
    return {"status":"ELIGIBLE","observations_used":used,
            "research_only":True,"causal_lookahead_verified_by_timestamp":True}


def same_cohort_ablation(records:list[dict],*,variant:str)->dict:
    """Never assert uplift if one arm lacks outcomes for same trade IDs."""
    if variant not in ("technical","fundamental","macro","technical_fundamental",
                       "technical_macro","full"):
        raise ValueError("unknown ablation arm")
    for r in records:
        if not r.get("trade_id") or not r.get("source_hash"):
            raise ValueError("unidentified trade evidence")
    ids=[r["trade_id"] for r in records]
    if len(set(ids))!=len(ids):raise ValueError("duplicate trade")
    present=sum(variant in r.get("arms",{}) for r in records)
    if present!=len(records) or not records:
        return {"variant":variant,"status":"NOT_TESTABLE_INCOMPLETE_IDENTICAL_COHORT",
                "n":present,"total":len(records),"confirmed_alpha":False}
    return {"variant":variant,"status":"COHORT_PRESENT_NEEDS_PIT_AND_OOS_REVIEW",
            "n":present,"total":len(records),"confirmed_alpha":False}
