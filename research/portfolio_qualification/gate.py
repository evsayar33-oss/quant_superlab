"""Strict staged evidence passport validator; NEVER a live execution approval."""
from __future__ import annotations
import re
from datetime import datetime, timezone

SHA = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = (
    "asof_only", "quality_verified", "universe_bias_accounted",
    "registered_before_outcomes", "matched_controls_verified",
    "independent_oos_verified", "cost_stress_verified",
    "realistic_fill_assumptions_verified", "multi_testing_adjusted",
    "regime_robustness_verified", "prospective_outcomes_matured",
)


def _time(value):
    if not isinstance(value, str):
        raise ValueError("MISSING_PASSPORT_TIMESTAMP")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("PASSPORT_TIMESTAMP_NO_TIMEZONE")
    return t.astimezone(timezone.utc)


def review(passport):
    """Fail-closed checklist: passing only permits *manual independent review*."""
    blockers = []
    for name in REQUIRED:
        if passport.get(name) is not True:
            blockers.append(name)
    for key in ("methodology_sha256", "source_evidence_sha256", "hypothesis_id",
                "source_repository", "benchmark", "strategy_definition"):
        value = passport.get(key)
        if not isinstance(value, str) or not value.strip():
            blockers.append("missing_" + key)
    for key in ("methodology_sha256", "source_evidence_sha256"):
        if passport.get(key) and not SHA.fullmatch(str(passport[key])):
            blockers.append("bad_" + key)
    try:
        registered = _time(passport.get("registered_utc"))
        train = _time(passport.get("train_end_utc"))
        oos_begin = _time(passport.get("oos_start_utc"))
        oos_end = _time(passport.get("oos_end_utc"))
        result_at = _time(passport.get("latest_outcome_at_utc"))
        if not (registered <= train < oos_begin <= oos_end <= result_at):
            blockers.append("INVALID_TEMPORAL_OR_PREREGISTRATION_ORDER")
    except (TypeError, ValueError, OverflowError):
        blockers.append("MISSING_OR_INVALID_EXPIRY_CLOCK")
    try:
        if int(passport.get("distinct_time_blocks", 0)) < 8:
            blockers.append("INSUFFICIENT_TIME_BLOCKS")
        if int(passport.get("completed_trades_or_events", 0)) < 30:
            blockers.append("INSUFFICIENT_COMPLETED_EVENTS")
    except (ValueError, TypeError, OverflowError):
        blockers.append("INVALID_SAMPLE_COUNTS")
    if passport.get("read_only_research") is not True:
        blockers.append("RESEARCH_ONLY_REQUIRED")
    return {"hypothesis_id": passport.get("hypothesis_id"),
            "status": "READY_FOR_INDEPENDENT_PAPER_REVIEW" if not blockers
                      else "NOT_ELIGIBLE_FOR_PAPER_REVIEW",
            "blockers": blockers,
            "independent_reproduction_performed": False,
            "paper_approved": False, "live_approved": False,
            "trade_authorized": False}


def no_automatic_promotion(*_args, **_kwargs):
    raise PermissionError("AUTOMATIC_PAPER_OR_LIVE_PROMOTION_IS_PROHIBITED")
