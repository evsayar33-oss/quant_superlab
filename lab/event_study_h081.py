"""H081 evidence-first final adjudication. No invented source timestamps or PIT caps."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.event_study import partition_event_timestamps, summarize


def source_evidence_audit(feed: pd.DataFrame) -> pd.DataFrame:
    """Keep all families; report missing evidence instead of upgrading ingestion timestamps."""
    columns = ["event_family", "category", "records", "historical_eligible",
               "forward_only", "excluded", "historical_pct", "decision"]
    if feed.empty:
        return pd.DataFrame(columns=columns)
    f = feed.copy()
    for c in ("event_family", "category"):
        f[c] = f[c].fillna("unclassified").astype(str)
    q = f["timestamp_quality"].fillna("unknown").astype(str).str.lower().str.strip()
    f["_historical"] = q.isin(["exact_utc", "date_only"]).astype(int)
    f["_forward"] = q.eq("first_seen_utc").astype(int)
    f["_excluded"] = (~q.isin(["exact_utc", "date_only", "first_seen_utc"])).astype(int)
    g = f.groupby(["event_family", "category"], dropna=False).agg(
        records=("_historical", "size"), historical_eligible=("_historical", "sum"),
        forward_only=("_forward", "sum"), excluded=("_excluded", "sum")).reset_index()
    g["historical_pct"] = 100 * g["historical_eligible"] / g["records"]
    g["decision"] = np.where(g["historical_eligible"].eq(0),
                             "SOURCE_TIMESTAMP_REQUIRED", "HISTORICAL_ELIGIBLE")
    return g[columns].sort_values(["event_family", "category"]).reset_index(drop=True)


def evidence_override(feed: pd.DataFrame, evidence: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Require independently supplied source evidence, never infer from first_seen/action_date.

    Evidence CSV: event_id, published_at_utc, evidence_url, verified.
    Exact UTC must include explicit timezone offset or Z; date-only is not silently promoted.
    """
    out = feed.copy()
    cols = ["event_id", "decision", "reason"]
    if evidence is None or evidence.empty:
        return out, pd.DataFrame(columns=cols)
    required = {"event_id", "published_at_utc", "evidence_url", "verified"}
    if required - set(evidence):
        raise ValueError(f"Evidence file missing: {sorted(required - set(evidence))}")
    if evidence["event_id"].duplicated().any():
        raise ValueError("Duplicate event_id in evidence file")
    e = evidence.copy()
    e["event_id"] = e["event_id"].astype(str)
    records = []
    for item in e.to_dict("records"):
        eid = item["event_id"]
        stamp = str(item.get("published_at_utc") or "").strip()
        url = str(item.get("evidence_url") or "").strip()
        verified = str(item.get("verified")).strip().lower() in ("true", "1", "yes")
        explicit_tz = stamp.endswith("Z") or bool(__import__("re").search(r"[+-]\d{2}:\d{2}$", stamp))
        dt = pd.to_datetime(stamp, utc=True, errors="coerce") if explicit_tz else pd.NaT
        match = out["event_id"].astype(str).eq(eid)
        if not match.any():
            decision, reason = "REJECT", "UNKNOWN_EVENT_ID"
        elif not verified or not url.startswith(("https://", "http://")) or pd.isna(dt):
            decision, reason = "REJECT", "UNVERIFIED_SOURCE_OR_TIMESTAMP"
        else:
            old_date = pd.to_datetime(out.loc[match, "event_date"], errors="coerce", utc=True)
            if old_date.notna().any() and (dt < old_date.min() - pd.Timedelta(days=366)):
                decision, reason = "REJECT", "DATE_DISCREPANCY_REVIEW"
            else:
                out.loc[match, "known_at"] = dt.isoformat()
                out.loc[match, "event_date"] = dt.date().isoformat()
                out.loc[match, "timestamp_quality"] = "exact_utc"
                decision, reason = "ACCEPT", "SOURCE_VERIFIED"
        records.append({"event_id": eid, "decision": decision, "reason": reason})
    return out, pd.DataFrame(records, columns=cols)


def spy_prior_regimes(spy_close: pd.Series, lookback: int = 200) -> pd.DataFrame:
    """Regime calculated using prior session's SPY close; no future data."""
    close = pd.to_numeric(spy_close, errors="coerce").sort_index()
    close.index = pd.to_datetime(close.index, utc=True).tz_convert(None).normalize()
    close = close[~close.index.duplicated(keep="last")]
    sma = close.rolling(lookback, min_periods=lookback).mean()
    # End-of-day signal only available to trade on following session.
    regime = np.where(close > sma, "RISK_ON", "RISK_OFF")
    out = pd.DataFrame({"available_at": close.index + pd.Timedelta(hours=23, minutes=59),
                        "regime": regime})
    return out.loc[sma.notna().to_numpy()].reset_index(drop=True)


def final_decisions(returns: pd.DataFrame, min_events: int = 50, min_split: int = 10,
                    min_holdout_hit: float = .52, q_limit: float = .10,
                    bootstrap_n: int = 2000, seed: int = 17) -> pd.DataFrame:
    """Reuse H078's chronological and multiple-testing gates; no relaxed thresholds."""
    if returns.empty:
        return pd.DataFrame(columns=["decision", "reason"])
    result = summarize(returns, min_events=min_events, min_split=min_split,
                       min_holdout_hit=min_holdout_hit, q_limit=q_limit,
                       bootstrap_n=bootstrap_n, seed=seed)
    if result.empty:
        return result
    # Preserve upstream verdict; H081 never invents a passing candidate.
    return result


def evidence_report(audit: pd.DataFrame, decisions: pd.DataFrame,
                    overrides: pd.DataFrame, pit_n: int, regime_n: int) -> str:
    lines = ["# H081 — Final evidence and statistical adjudication", "",
             "**Research only. No live trades, no automatic signal authorization.**", "",
             f"Verified source timestamp upgrades: {int(overrides['decision'].eq('ACCEPT').sum()) if not overrides.empty else 0}",
             f"PIT market-cap matched return rows: {pit_n}",
             f"Prior-regime matched return rows: {regime_n}", "",
             "## All-sector timestamp evidence", audit.to_markdown(index=False), "",
             "## Statistical gates (unchanged from H078)", 
             decisions.to_markdown(index=False) if not decisions.empty else "No measurable events.", "",
             "## Source-evidence adjudication",
             overrides.to_markdown(index=False) if not overrides.empty else "No verified external source-evidence file supplied.", "",
             "## Interpretation", 
             "A successful workflow is not a statistically validated alpha.",
             "If source timestamps or historical market caps are absent, H081 cannot produce a final",
             "answer for those subgroups. Do not replace missing data with today's values.",
             "Source URLs in a supplied CSV are claims until independently checked against source content.",
             ""]
    return "\n".join(lines)
