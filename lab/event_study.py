"""Point-in-time event study for the Federal Incentive Radar feed.

This is a fixed, pre-registered event study, not a parameter optimizer and not
a live signal generator. It uses daily OHLC bars and conservative next-open fills.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from lab.panel import Panel

HORIZONS = (1, 5, 20, 60)
BENCHMARK = "SPY"


def entry_index(known_at, event_date, index: pd.DatetimeIndex,
                market_tz: str = "America/New_York", market_open: str = "09:30") -> int | None:
    """First executable daily open after the event was public.

    Exact timestamps before 09:30 ET can enter at that session's open.
    Intraday/after-close timestamps enter at the next session open because
    daily bars cannot support an intraday fill. Date-only events also wait
    until the next session. This deliberately avoids same-day look-ahead.
    """
    if index is None or len(index) == 0:
        return None
    idx = pd.DatetimeIndex(index).tz_localize(None).normalize()
    raw = str(known_at or "").strip()
    ts = pd.to_datetime(raw, utc=True, errors="coerce")
    if not pd.isna(ts) and ("T" in raw or " " in raw):
        local = ts.tz_convert(market_tz)
        d = pd.Timestamp(local.date())
        open_h, open_m = map(int, market_open.split(":"))
        before_open = (local.hour, local.minute, local.second) < (open_h, open_m, 0)
        target = d if before_open else d + pd.Timedelta(days=1)
    else:
        d = pd.to_datetime(event_date, errors="coerce")
        if pd.isna(d):
            return None
        target = d.normalize() + pd.Timedelta(days=1)
    pos = int(idx.searchsorted(target, side="left"))
    return pos if pos < len(idx) else None


def _beta(asset_close: pd.Series, bench_close: pd.Series, entry: int,
          lookback: int = 252, min_obs: int = 60) -> float | None:
    lo = max(1, entry - lookback)
    a_now = asset_close.iloc[lo:entry].to_numpy(dtype=float)
    a_prev = asset_close.iloc[lo - 1:entry - 1].to_numpy(dtype=float)
    b_now = bench_close.iloc[lo:entry].to_numpy(dtype=float)
    b_prev = bench_close.iloc[lo - 1:entry - 1].to_numpy(dtype=float)
    a = np.log(a_now / a_prev)
    b = np.log(b_now / b_prev)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < min_obs or np.var(b[ok]) <= 1e-12:
        return None
    return float(np.clip(np.cov(a[ok], b[ok], ddof=1)[0, 1] / np.var(b[ok], ddof=1), 0.0, 3.0))


def _path_log_returns(open_px: pd.Series, close_px: pd.Series, start: int, end: int) -> np.ndarray | None:
    """Daily log returns for an open-to-close first session, then close-to-close."""
    if end >= len(close_px) or start < 0:
        return None
    o = float(open_px.iloc[start])
    c0 = float(close_px.iloc[start])
    if not np.isfinite(o) or not np.isfinite(c0) or o <= 0 or c0 <= 0:
        return None
    out = [math.log(c0 / o)]
    for j in range(start + 1, end + 1):
        prev, cur = float(close_px.iloc[j - 1]), float(close_px.iloc[j])
        if not np.isfinite(prev) or not np.isfinite(cur) or prev <= 0 or cur <= 0:
            return None
        out.append(math.log(cur / prev))
    return np.asarray(out, dtype=float)


def _net_return(gross: float, per_side_cost: float, multiplier: float = 1.0) -> float:
    cost = max(0.0, float(per_side_cost)) * multiplier
    if cost >= 1:
        return -1.0
    return (1.0 + gross) * (1.0 - cost) ** 2 - 1.0


def thin_events(events: pd.DataFrame, cooldown_days: int = 60) -> pd.DataFrame:
    """Keep the first event per ticker in each cooldown window to reduce overlap."""
    if events is None or events.empty:
        return pd.DataFrame() if events is None else events.copy()
    e = events.copy()
    e["_time"] = pd.to_datetime(e.get("known_at", e.get("event_date")), utc=True, errors="coerce")
    e["_time"] = e["_time"].fillna(pd.to_datetime(e.get("event_date"), utc=True, errors="coerce"))
    e = e.dropna(subset=["_time"]).sort_values(["ticker", "_time", "event_id"])
    keep, last = [], {}
    for row in e.to_dict("records"):
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        stamp = row["_time"]
        if ticker in last and (stamp - last[ticker]).days < cooldown_days:
            continue
        keep.append(row)
        last[ticker] = stamp
    return pd.DataFrame(keep).drop(columns=["_time"], errors="ignore").reset_index(drop=True)


def measure_events(events: pd.DataFrame, panel: Panel, per_side_cost: float = 0.0005,
                   horizons: tuple[int, ...] = HORIZONS, benchmark: str = BENCHMARK,
                   cooldown_days: int = 60) -> pd.DataFrame:
    """Measure market-model abnormal returns from the first executable open."""
    if events is None or events.empty or benchmark not in panel.columns:
        return pd.DataFrame()
    e = thin_events(events, cooldown_days)
    rows = []
    idx = pd.DatetimeIndex(panel.index).tz_localize(None).normalize()
    bench_open, bench_close = panel.o[benchmark], panel.c[benchmark]

    for event in e.to_dict("records"):
        ticker = str(event.get("ticker") or "").strip().upper()
        if ticker not in panel.columns:
            continue
        k = entry_index(event.get("known_at"), event.get("event_date"), idx)
        if k is None:
            continue
        beta = _beta(panel.c[ticker], bench_close, k)
        if beta is None:
            continue
        sector_etf = str(event.get("sector_etf") or "").strip().upper()
        sector_ok = sector_etf in panel.columns
        sector_beta = _beta(panel.c[ticker], panel.c[sector_etf], k) if sector_ok else None
        if sector_ok and sector_beta is None:
            sector_ok = False

        for horizon in horizons:
            end = k + int(horizon) - 1
            asset_lr = _path_log_returns(panel.o[ticker], panel.c[ticker], k, end)
            bench_lr = _path_log_returns(bench_open, bench_close, k, end)
            if asset_lr is None or bench_lr is None or len(asset_lr) != horizon:
                continue
            if not np.isfinite(asset_lr).all() or not np.isfinite(bench_lr).all():
                continue
            gross_spy = float(np.expm1(np.sum(asset_lr - beta * bench_lr)))
            row = {
                "event_id": str(event.get("event_id") or ""),
                "event_family": str(event.get("event_family") or "unknown"),
                "category": str(event.get("category") or "unclassified"),
                "ticker": ticker,
                "known_at": str(event.get("known_at") or ""),
                "event_date": str(event.get("event_date") or ""),
                "entry_date": idx[k].date().isoformat(),
                "exit_date": idx[end].date().isoformat(),
                "horizon": int(horizon),
                "beta_spy": beta,
                "gross_spy_excess": gross_spy,
                "net_spy_excess_1x": _net_return(gross_spy, per_side_cost, 1.0),
                "net_spy_excess_2x": _net_return(gross_spy, per_side_cost, 2.0),
                "amount_usd": pd.to_numeric(event.get("amount_usd"), errors="coerce"),
                "timestamp_quality": str(event.get("timestamp_quality") or "unknown"),
                "sector_etf": sector_etf if sector_ok else "",
                "gross_sector_excess": np.nan,
                "net_sector_excess_2x": np.nan,
            }
            if sector_ok and sector_beta is not None:
                sector_lr = _path_log_returns(panel.o[sector_etf], panel.c[sector_etf], k, end)
                if sector_lr is not None and len(sector_lr) == horizon and np.isfinite(sector_lr).all():
                    gross_sector = float(np.expm1(np.sum(asset_lr - sector_beta * sector_lr)))
                    row["gross_sector_excess"] = gross_sector
                    row["net_sector_excess_2x"] = _net_return(gross_sector, per_side_cost, 2.0)
            rows.append(row)
    return pd.DataFrame(rows)


def _bh(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    q = np.empty(len(p), dtype=float)
    running = 1.0
    for rank in range(len(p), 0, -1):
        pos = order[rank - 1]
        running = min(running, p[pos] * len(p) / rank)
        q[pos] = min(1.0, running)
    return q.tolist()


def summarize(returns: pd.DataFrame, min_events: int = 50, min_split: int = 10,
              min_holdout_hit: float = 0.52, q_limit: float = 0.10,
              bootstrap_n: int = 2000, seed: int = 17) -> pd.DataFrame:
    """Chronological 60/20/20 discovery/validation/locked-holdout evaluation."""
    if returns is None or returns.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    rows = []
    keys = ["event_family", "category", "horizon"]
    for key, group in returns.groupby(keys, dropna=False):
        g = group.sort_values(["known_at", "event_date", "event_id", "ticker"]).drop_duplicates(["event_id", "ticker"])
        x = pd.to_numeric(g["net_spy_excess_2x"], errors="coerce").dropna().to_numpy()
        n = len(x)
        n_train, n_val = int(n * 0.6), int(n * 0.2)
        train, val, hold = x[:n_train], x[n_train:n_train + n_val], x[n_train + n_val:]
        pval = float(stats.ttest_1samp(x, 0.0).pvalue) if n >= 3 and np.std(x, ddof=1) > 0 else 1.0
        if n:
            boot = rng.choice(x, size=(bootstrap_n, n), replace=True).mean(axis=1)
            ci_low, ci_high = np.quantile(boot, [0.025, 0.975])
        else:
            ci_low = ci_high = np.nan
        rows.append({
            "event_family": key[0], "category": key[1], "horizon": int(key[2]),
            "n": n, "mean_net_2x": float(np.mean(x)) if n else np.nan,
            "hit_rate": float(np.mean(x > 0)) if n else np.nan,
            "p_value": pval, "q_value": np.nan,
            "ci95_low": float(ci_low), "ci95_high": float(ci_high),
            "discovery_n": len(train), "discovery_mean": float(np.mean(train)) if len(train) else np.nan,
            "validation_n": len(val), "validation_mean": float(np.mean(val)) if len(val) else np.nan,
            "holdout_n": len(hold), "holdout_mean": float(np.mean(hold)) if len(hold) else np.nan,
            "holdout_hit": float(np.mean(hold > 0)) if len(hold) else np.nan,
            "status": "INSUFFICIENT",
        })
    out = pd.DataFrame(rows)
    for horizon, group in out.groupby("horizon"):
        out.loc[group.index, "q_value"] = _bh(group["p_value"].astype(float).tolist())
    for i, r in out.iterrows():
        enough = (r["n"] >= min_events and r["discovery_n"] >= min_split
                  and r["validation_n"] >= min_split and r["holdout_n"] >= min_split)
        if not enough:
            out.at[i, "status"] = "INSUFFICIENT"
        elif (r["discovery_mean"] > 0 and r["validation_mean"] > 0 and r["holdout_mean"] > 0
              and r["holdout_hit"] >= min_holdout_hit and r["q_value"] <= q_limit):
            out.at[i, "status"] = "CANDIDATE"
        elif r["holdout_mean"] <= 0:
            out.at[i, "status"] = "REJECT"
        else:
            out.at[i, "status"] = "WATCH"
    return out.sort_values(["status", "event_family", "category", "horizon"]).reset_index(drop=True)


def markdown_report(summary: pd.DataFrame, returns: pd.DataFrame, feed_rows: int,
                    loaded_tickers: int, excluded_tickers: int, start: str) -> str:
    lines = [
        "# H078 — Federal event study",
        "",
        "**Status: research only. No live signal or bot integration.**",
        "",
        f"- Feed rows: {feed_rows}; price tickers loaded: {loaded_tickers}; tickers excluded by data cap: {excluded_tickers}.",
        f"- Price history start: {start}; event observations: {len(returns['event_id'].unique()) if not returns.empty else 0}.",
        "- Execution: exact pre-market timestamps may enter at same-session open; intraday/after-close and date-only events enter at the next session open.",
        "- Returns: market-model abnormal return versus SPY, net of round-trip stock costs at 1x and 2x; sector ETF excess is diagnostic where available.",
        "- Chronological split: 60% discovery / 20% validation / 20% locked holdout. Cooldown: one event per ticker per 60 calendar days.",
        "- DSR/PBO are not reported: this is one fixed, pre-registered event design with no parameter search. BH q-values adjust the event-family/category/horizon tests.",
        "- Limitations: daily bars cannot model intraday execution; date-only federal events use a conservative next-session entry; delisted/unmatched tickers may be absent (survivorship / entity-match bias).",
        "",
        "## Results",
        "",
    ]
    if summary is None or summary.empty:
        lines.append("No measurable events. Check feed availability, ticker matching and OHLCV coverage.")
    else:
        cols = ["event_family", "category", "horizon", "n", "mean_net_2x", "hit_rate", "q_value",
                "discovery_mean", "validation_mean", "holdout_mean", "holdout_hit", "status"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for row in summary[cols].to_dict("records"):
            vals = []
            for c in cols:
                v = row[c]
                vals.append(f"{v:.4f}" if isinstance(v, (float, np.floating)) and np.isfinite(v) else str(v))
            lines.append("| " + " | ".join(vals) + " |")
    lines += [
        "",
        "## Decision rule",
        "",
        f"A category is a candidate only with at least 50 independent events, at least 10 events in each chronological split, positive 2x-cost net excess return in discovery, validation and holdout, holdout hit rate >= 52%, and BH q <= 0.10.",
        "A candidate is not approved for live trading. It must pass a separate execution, robustness, and forward paper-trading review.",
    ]
    return "\n".join(lines) + "\n"
