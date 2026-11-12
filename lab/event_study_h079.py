"""H079 diagnostics: retain every event family and require point-in-time fundamentals.

This is exploratory research only. No new trading rule is selected or activated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEYS = ["event_id", "ticker"]
GROUPS = ["event_family", "category", "sector_etf", "horizon"]
REQUIRED_CAP = {"ticker", "asof_date", "market_cap_usd"}


def attach_point_in_time_cap(returns: pd.DataFrame, fundamentals: pd.DataFrame | None) -> pd.DataFrame:
    """Backward as-of join, strictly before event date; never forward-fill future cap."""
    out = returns.copy()
    out["market_cap_usd_pit"] = np.nan
    out["cap_asof_date"] = pd.NaT
    out["amount_to_cap"] = np.nan
    if out.empty or fundamentals is None or fundamentals.empty:
        return out
    missing = REQUIRED_CAP - set(fundamentals.columns)
    if missing:
        raise ValueError(f"Missing PIT fundamentals columns: {sorted(missing)}")
    cap = fundamentals.copy()
    cap["ticker"] = cap["ticker"].astype(str).str.upper().str.strip()
    cap["asof_date"] = pd.to_datetime(cap["asof_date"], errors="coerce").astype("datetime64[ns]")
    cap["market_cap_usd"] = pd.to_numeric(cap["market_cap_usd"], errors="coerce")
    cap = cap.dropna(subset=["asof_date", "market_cap_usd"])
    cap = cap[cap["market_cap_usd"] > 0]
    cap = cap.sort_values("asof_date")
    out["ticker"] = out["ticker"].astype(str).str.upper().str.strip()
    out["_event_dt"] = pd.to_datetime(out["event_date"], errors="coerce").astype("datetime64[ns]")
    # The as-of timestamp must precede the event calendar day, not merely the
    # trade entry. This avoids using same-day fundamentals released after news.
    out["_lookup_dt"] = out["_event_dt"] - pd.Timedelta(nanoseconds=1)
    left = out.reset_index(names="_row").sort_values("_lookup_dt")
    valid = left.dropna(subset=["_lookup_dt"])
    if not valid.empty and not cap.empty:
        merged = pd.merge_asof(
            valid, cap[["ticker", "asof_date", "market_cap_usd"]],
            left_on="_lookup_dt", right_on="asof_date", by="ticker",
            direction="backward", allow_exact_matches=True,
        ).set_index("_row")
        out.loc[merged.index, "market_cap_usd_pit"] = merged["market_cap_usd"].to_numpy()
        out.loc[merged.index, "cap_asof_date"] = merged["asof_date"].to_numpy()
    out = out.drop(columns=["_event_dt", "_lookup_dt"])
    amount = pd.to_numeric(out.get("amount_usd"), errors="coerce")
    out["amount_to_cap"] = amount / out["market_cap_usd_pit"]
    out.loc[(amount <= 0) | ~np.isfinite(out["amount_to_cap"]), "amount_to_cap"] = np.nan
    return out


def coverage_table(feed: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    """Report all feed families/categories, including those with zero measured returns."""
    keys = ["event_family", "category"]
    f = feed.copy()
    if f.empty:
        return pd.DataFrame(columns=keys + ["feed_rows", "measured_events", "status"])
    for key in keys:
        f[key] = f[key].fillna("unclassified").astype(str)
    base = f.groupby(keys, dropna=False).size().rename("feed_rows").reset_index()
    if returns is None or returns.empty:
        base["measured_events"] = 0
    else:
        r = returns.drop_duplicates(["event_id", "ticker"]).groupby(keys).size().rename("measured_events").reset_index()
        base = base.merge(r, on=keys, how="left")
        base["measured_events"] = base["measured_events"].fillna(0).astype(int)
    base["status"] = np.where(base["measured_events"] == 0, "NO_MEASURABLE_EVENTS", "RETAIN_FOR_RESEARCH")
    return base.sort_values(keys).reset_index(drop=True)


def diagnostics(returns: pd.DataFrame, min_group: int = 30) -> pd.DataFrame:
    """Descriptive only: no post-hoc significance claims or live-trading gates."""
    columns = GROUPS + ["n", "mean_net_stock_2x", "mean_spy_excess_2x",
                        "stock_hit_rate", "pit_cap_coverage", "normalized_amount_n",
                        "median_amount_to_cap", "status"]
    if returns is None or returns.empty:
        return pd.DataFrame(columns=columns)
    r = returns.copy()
    for k in GROUPS:
        if k not in r:
            r[k] = "unknown"
    r["sector_etf"] = r["sector_etf"].fillna("unknown").replace("", "unknown")
    r["net_stock_return_2x"] = pd.to_numeric(r["net_stock_return_2x"], errors="coerce")
    r["net_spy_excess_2x"] = pd.to_numeric(r["net_spy_excess_2x"], errors="coerce")
    r["amount_to_cap"] = pd.to_numeric(r.get("amount_to_cap"), errors="coerce")
    r["market_cap_usd_pit"] = pd.to_numeric(r.get("market_cap_usd_pit"), errors="coerce")
    g = r.groupby(GROUPS, dropna=False)
    result = g.agg(
        n=("event_id", "size"),
        mean_net_stock_2x=("net_stock_return_2x", "mean"),
        mean_spy_excess_2x=("net_spy_excess_2x", "mean"),
        stock_hit_rate=("net_stock_return_2x", lambda x: float((x > 0).mean())),
        pit_cap_coverage=("market_cap_usd_pit", lambda x: float(x.notna().mean())),
        normalized_amount_n=("amount_to_cap", "count"),
        median_amount_to_cap=("amount_to_cap", "median"),
    ).reset_index()
    result["status"] = np.where(result["n"] < min_group, "INSUFFICIENT_SAMPLE", "EXPLORATORY_ONLY")
    return result[columns].sort_values(GROUPS).reset_index(drop=True)


def report(coverage: pd.DataFrame, stats: pd.DataFrame, has_cap: bool) -> str:
    return "\n".join([
        "# H079 — Cross-sector event diagnostics",
        "",
        "**Research only. No live strategy or approved candidate.**",
        "",
        "All event families and categories remain in the coverage report; zero-count and",
        "insufficient-sample groups are not discarded or described as failed strategies.",
        "H078 timestamp integrity and existing execution-cost assumptions are retained.",
        "",
        f"- Point-in-time market-cap file supplied: {has_cap}.",
        "- Market-cap values must be historical, available before the event, and in USD.",
        "- Without validated PIT fundamentals, amount/market-cap is intentionally missing.",
        "- Positive descriptive averages are not statistical evidence or a trade signal.",
        "- Any later threshold, sector selection or ranking requires a preregistered",
        "  discovery/validation/untouched holdout design with multiplicity correction.",
        "",
        "## Coverage by family/category",
        coverage.to_markdown(index=False) if not coverage.empty else "No feed rows.",
        "",
        "## Descriptive family/category/sector/horizon diagnostics",
        stats.to_markdown(index=False) if not stats.empty else "No measurable events.",
        "",
    ]) + "\n"
