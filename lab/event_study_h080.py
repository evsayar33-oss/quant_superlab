"""H080: research coverage and point-in-time-safe diagnostics across all sectors.

No profitability certification, automatic candidate selection or live execution.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ["event_family", "category"]
QUALITY = ["exact_utc", "date_only", "first_seen_utc", "action_date_proxy", "unknown"]


def timestamp_audit(feed: pd.DataFrame, measured: pd.DataFrame) -> pd.DataFrame:
    """Preserve all categories, including those without any historical returns."""
    if feed.empty:
        return pd.DataFrame(columns=CATEGORIES + QUALITY + ["total", "measured", "readiness"])
    f = feed.copy()
    for col in CATEGORIES:
        f[col] = f[col].fillna("unclassified").astype(str)
    f["timestamp_quality"] = f["timestamp_quality"].fillna("unknown").astype(str).str.lower()
    counts = f.groupby(CATEGORIES + ["timestamp_quality"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=QUALITY, fill_value=0).reset_index()
    counts["total"] = counts[QUALITY].sum(axis=1)
    if measured is not None and not measured.empty:
        n = measured.drop_duplicates(["event_id", "ticker"]).groupby(CATEGORIES).size().rename("measured")
        counts = counts.merge(n.reset_index(), on=CATEGORIES, how="left")
        counts["measured"] = counts["measured"].fillna(0).astype(int)
    else:
        counts["measured"] = 0
    counts["readiness"] = np.select(
        [counts["measured"] > 0, counts["exact_utc"] + counts["date_only"] > 0],
        ["MEASURED", "PRICE_OR_MAPPING_GAP"], default="TIMESTAMP_GAP"
    )
    return counts.sort_values(CATEGORIES).reset_index(drop=True)


def enrich_with_verified_fundamentals(returns: pd.DataFrame, fundamentals: pd.DataFrame | None) -> pd.DataFrame:
    """Only use observations published before the event day, never revised future values.

    Required fields: ticker, market_cap_usd, asof_date, available_at.
    available_at is the timestamp the historical market cap was publicly accessible.
    """
    out = returns.copy().reset_index(drop=True)
    out["pit_market_cap_usd"] = np.nan
    out["pit_available_at"] = pd.NaT
    out["amount_to_pit_cap"] = np.nan
    if fundamentals is None or fundamentals.empty or out.empty:
        return out
    required = {"ticker", "market_cap_usd", "asof_date", "available_at"}
    missing = required - set(fundamentals.columns)
    if missing:
        raise ValueError(f"PIT dataset missing: {sorted(missing)}")
    cap = fundamentals.copy()
    cap["ticker"] = cap["ticker"].astype(str).str.strip().str.upper()
    cap["market_cap_usd"] = pd.to_numeric(cap["market_cap_usd"], errors="coerce")
    for field in ("asof_date", "available_at"):
        cap[field] = pd.to_datetime(cap[field], errors="coerce", utc=True).dt.tz_convert(None).astype("datetime64[ns]")
    cap = cap.dropna(subset=["asof_date", "available_at", "market_cap_usd"])
    cap = cap[(cap["market_cap_usd"] > 0) & (cap["asof_date"] <= cap["available_at"])]
    cap = cap.sort_values("available_at")
    out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
    dates = pd.to_datetime(out["event_date"], errors="coerce", utc=True).dt.tz_convert(None).astype("datetime64[ns]")
    out["_lookup"] = dates.dt.normalize() - pd.Timedelta(nanoseconds=1)
    valid = out.reset_index(names="_row").dropna(subset=["_lookup"]).sort_values("_lookup")
    if not valid.empty and not cap.empty:
        m = pd.merge_asof(valid, cap[["ticker", "available_at", "market_cap_usd"]],
                          left_on="_lookup", right_on="available_at",
                          by="ticker", direction="backward").set_index("_row")
        out.loc[m.index, "pit_market_cap_usd"] = m["market_cap_usd"].to_numpy()
        out.loc[m.index, "pit_available_at"] = m["available_at"].to_numpy()
    out = out.drop(columns=["_lookup"])
    amount = pd.to_numeric(out["amount_usd"], errors="coerce")
    out["amount_to_pit_cap"] = amount / out["pit_market_cap_usd"]
    out.loc[(amount <= 0) | ~np.isfinite(out["amount_to_pit_cap"]), "amount_to_pit_cap"] = np.nan
    return out


def attach_prior_regimes(returns: pd.DataFrame, regimes: pd.DataFrame | None) -> pd.DataFrame:
    """Regime labels must have an explicit availability date before the event."""
    out = returns.copy().reset_index(drop=True)
    out["prior_regime"] = "UNAVAILABLE"
    if regimes is None or regimes.empty or out.empty:
        return out
    required = {"available_at", "regime"}
    if not required.issubset(regimes):
        raise ValueError(f"Regime file missing {sorted(required - set(regimes))}")
    r = regimes.copy()
    r["available_at"] = pd.to_datetime(r["available_at"], errors="coerce", utc=True).dt.tz_convert(None).astype("datetime64[ns]")
    r = r.dropna(subset=["available_at", "regime"]).sort_values("available_at")
    if r.empty:
        return out
    dates = pd.to_datetime(out["event_date"], errors="coerce", utc=True).dt.tz_convert(None).astype("datetime64[ns]")
    out["_lookup"] = dates.dt.normalize() - pd.Timedelta(nanoseconds=1)
    valid = out.reset_index(names="_row").dropna(subset=["_lookup"]).sort_values("_lookup")
    if not valid.empty:
        m = pd.merge_asof(valid, r[["available_at", "regime"]], left_on="_lookup",
                          right_on="available_at", direction="backward").set_index("_row")
        out.loc[m.index, "prior_regime"] = m["regime"].fillna("UNAVAILABLE").astype(str).to_numpy()
    return out.drop(columns=["_lookup"])


def regime_diagnostics(returns: pd.DataFrame, minimum: int = 30) -> pd.DataFrame:
    cols = ["event_family", "category", "prior_regime", "horizon", "n",
            "mean_net_stock_2x", "mean_spy_excess_2x", "pit_cap_n", "normalized_amount_n", "status"]
    if returns.empty:
        return pd.DataFrame(columns=cols)
    r = returns.copy()
    for c in ("event_family", "category", "prior_regime"):
        r[c] = r[c].fillna("UNAVAILABLE")
    for c in ("net_stock_return_2x", "net_spy_excess_2x", "amount_to_pit_cap", "pit_market_cap_usd"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    result = r.groupby(["event_family", "category", "prior_regime", "horizon"], dropna=False).agg(
        n=("event_id", "size"),
        mean_net_stock_2x=("net_stock_return_2x", "mean"),
        mean_spy_excess_2x=("net_spy_excess_2x", "mean"),
        pit_cap_n=("pit_market_cap_usd", "count"),
        normalized_amount_n=("amount_to_pit_cap", "count"),
    ).reset_index()
    result["status"] = np.where(result["n"] < minimum, "INSUFFICIENT_SAMPLE", "DESCRIPTIVE_ONLY")
    return result[cols].sort_values(cols[:4]).reset_index(drop=True)


def report(audit: pd.DataFrame, groups: pd.DataFrame, has_pit: bool, has_regime: bool) -> str:
    lines = [
        "# H080 — All-sector timestamp, size and regime research",
        "",
        "**Research only; no approved strategy or live signal.**",
        "",
        f"- Verified point-in-time market-cap input: {has_pit}.",
        f"- Historically available regime input: {has_regime}.",
        "- Missing data is reported as missing, never filled with current fundamentals.",
        "- Every category remains in the timestamp audit, even if no return is measurable.",
        "- H078 execution assumptions and 2x costs remain unchanged.",
        "- Group averages are descriptive; they are not independent holdout validation.",
        "- Follow-up tests require precommitted hypotheses, chronological validation,",
        "  untouched holdout, costs and multiplicity correction.",
        "",
        "## Source timing and category coverage",
        audit.to_markdown(index=False) if not audit.empty else "No events.",
        "",
        "## Prior-regime and point-in-time size diagnostics",
        groups.to_markdown(index=False) if not groups.empty else "No measurable returns.",
    ]
    return "\n".join(lines) + "\n"
