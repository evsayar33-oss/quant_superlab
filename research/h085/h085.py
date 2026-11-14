"""H085: independent retrospective strategy-derivative search on frozen H083 data.

Research-only, REUSED_TEST; no brokerage orders, strategy approvals or production state.
Signals at the close of month t-1 determine exposure in month t.
Historical H083 strategy NAVs include their original commissions; add extra meta turnover
cost. The NAV blend is a research proxy, NOT a fully simulated tradable account.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

FREEZE_DATE = pd.Timestamp("2026-11-11")
CUT_1 = pd.Timestamp("2025-07-31")
CUT_2 = pd.Timestamp("2026-06-02")
COST_PER_TURN = (0.0025, 0.0050)
SEED = 85017

VARIANTS = [
    "EW10",
    *[f"winner_top{k}_{n}m" for n in (3, 6, 9) for k in (3, 5)],
    "winner_top3_6m_spy3risk", "winner_top5_6m_spy3risk",
    "risk_parity_6m", "risk_parity_9m",
    "blend50_6m", "blend50_9m",
    "breadth_3m_cash",
]
EVENT_VARIANTS = (
    "all", "sector_mean_180d", "category_mean_180d",
    "market_mean_90d", "sector_median_365d",
)


def read_monthly(h083: Path):
    nav_file = h083 / "rotation_daily_nav.csv"
    bench_file = h083 / "benchmark_spy_daily_nav.csv"
    raw = pd.read_csv(nav_file, parse_dates=["date"])
    bench = pd.read_csv(bench_file, parse_dates=["date"])
    req = {"date", "rule", "nav"}
    if req - set(raw) or {"date", "nav"} - set(bench):
        raise ValueError("Missing required daily NAV columns")
    if raw.duplicated(["date", "rule"]).any() or bench.date.duplicated().any():
        raise ValueError("Duplicate dated NAV observations")
    if not (raw.nav.gt(0).all() and bench.nav.gt(0).all()):
        raise ValueError("NAV values must be positive")
    if raw.date.max() > FREEZE_DATE or bench.date.max() > FREEZE_DATE:
        raise ValueError("Frozen source unexpectedly contains new dates")
    daily = raw.pivot(index="date", columns="rule", values="nav").sort_index()
    spy = bench.set_index("date").nav.sort_index()
    joined = daily.join(spy.rename("__SPY__"), how="inner").dropna(how="any")
    if len(joined) < 30:
        raise ValueError("Insufficient matching daily NAV rows")
    end = joined.resample("ME").last()
    ret = end.pct_change(fill_method=None).iloc[1:].dropna(how="any")
    if len(ret) < 12 or ret.shape[1] < 4:
        raise ValueError("Too little monthly strategy evidence")
    if not np.isfinite(ret.to_numpy()).all() or (ret.to_numpy() <= -1).any():
        raise ValueError("Invalid monthly returns")
    return ret.drop(columns="__SPY__"), ret["__SPY__"], {
        "rotation_strategies": daily.shape[1],
        "aligned_daily_rows": int(len(joined)),
        "month_rows": int(len(ret)),
        "data_start": str(joined.index.min().date()),
        "data_end": str(joined.index.max().date()),
        "nav_source_sha256": hashlib.sha256(nav_file.read_bytes()).hexdigest(),
        "spy_source_sha256": hashlib.sha256(bench_file.read_bytes()).hexdigest(),
    }


def weights_for_month(name: str, known: pd.DataFrame, spy_known: pd.Series) -> pd.Series:
    """History contains ONLY months completed before the portfolio's next month."""
    columns = known.columns
    z = pd.Series(0., index=columns, dtype=float)
    if name == "EW10":
        z[:] = 1. / len(z)
        return z
    if name == "breadth_3m_cash":
        if len(known) < 3:
            return z
        excess = known.tail(3).sub(spy_known.tail(3), axis=0)
        if float((excess.mean(axis=0) > 0).mean()) >= 0.6:
            z[:] = 1. / len(z)
        return z
    if name.startswith("risk_parity_"):
        n = int(name.split("_")[-1][:-1])
        if len(known) < n:
            return z
        std = known.tail(n).std(ddof=1)
        inv = (1 / std.where(std > 1e-6)).replace([np.inf, -np.inf], np.nan).dropna()
        if len(inv) < 3:
            return z
        return z.add(inv / inv.sum(), fill_value=0).fillna(0.)
    if name.startswith("blend50_"):
        n = int(name.split("_")[-1][:-1])
        if len(known) < n:
            return z
        rank = known.tail(n).sub(spy_known.tail(n), axis=0).mean(axis=0)
        top = rank.nlargest(3).index
        z[:] = .5 / len(z)
        z.loc[top] += .5 / len(top)
        return z
    if name.startswith("winner_top"):
        fields = name.split("_")
        k = int(fields[1][3:])
        n = int(fields[2][:-1])
        if len(known) < n:
            return z
        if name.endswith("_spy3risk"):
            if len(spy_known) < 3 or float((1 + spy_known.tail(3)).prod() - 1) <= 0:
                return z
        excess = known.tail(n).sub(spy_known.tail(n), axis=0).mean(axis=0)
        winners = excess.nlargest(k).index
        z.loc[winners] = 1. / len(winners)
        return z
    raise ValueError("Unregistered strategy name: " + name)


def simulate_months(rates: pd.DataFrame, spy: pd.Series, name: str,
                    cost_per_turn: float = .0025):
    """Cost of changes in allocation; no lookahead; cash carries zero return.

    Extra fee is per one-way turnover incl. changes to cash. Base strategy
    NAVs contain their commissions but scale fixed commissions imperfectly.
    """
    if not rates.index.equals(spy.index):
        raise ValueError("Calendar mismatch")
    weights = pd.Series(0., index=rates.columns)
    cash_weight = 1.
    nav = 1.
    ledger = []
    for i, when in enumerate(rates.index):
        new = weights_for_month(name, rates.iloc[:i], spy.iloc[:i])
        if new.isna().any() or (new < -1e-10).any() or float(new.sum()) > 1.0000001:
            raise ValueError("Bad/leveraged weights")
        new_cash = max(0., 1. - float(new.sum()))
        turnover = .5 * (float((new - weights).abs().sum()) + abs(new_cash - cash_weight))
        fee = turnover * cost_per_turn
        realized = float(new @ rates.iloc[i]) - fee
        nav *= 1. + realized
        ledger.append({"month": str(when.date()), "strategy": name, "return_net": realized,
                       "spy_return": float(spy.iloc[i]), "cost_rate": fee,
                       "turnover": turnover, "cash_weight": new_cash,
                       "nav": nav, "active": int(float(new.sum()) > 0)})
        weights, cash_weight = new, new_cash
    return pd.DataFrame(ledger)


def evaluate(ledger: pd.DataFrame):
    if ledger.empty:
        return {}
    r = ledger.return_net.to_numpy(float)
    b = ledger.spy_return.to_numpy(float)
    active = r - b
    eq = np.cumprod(1. + r)
    dd = float((eq / np.maximum.accumulate(np.r_[1., eq])[1:] - 1).min())
    x = len(r)
    sr = float(r.mean() / r.std(ddof=1) * np.sqrt(12)) if x >= 12 and r.std(ddof=1) > 0 else None
    return {"months": x, "net_total": float(eq[-1] - 1),
            "spy_total": float(np.prod(1 + b) - 1),
            "active_total_gap": float(eq[-1] - np.prod(1 + b)),
            "mean_active_month": float(active.mean()), "max_drawdown": dd,
            "sharpe": sr, "active_months": int(ledger.active.sum()),
            "avg_cash_weight": float(ledger.cash_weight.mean()),
            "extra_cost_sum": float(ledger.cost_rate.sum())}


def approximate_max_mean_bootstrap(active: pd.DataFrame, n_boot: int = 1200,
                                   block_mean: int = 3, seed: int = SEED):
    """Centered cross-sectional stationary block-bootstrap max-mean null.
    Exposed history; indicative multiplicity check only, not independent proof.
    """
    if len(active) < 24 or active.shape[1] < 2:
        return {"p": None, "months": int(len(active)), "reps": n_boot,
                "explanation": "At least 24 calendar months required"}
    a = active.to_numpy(float)
    means = a.mean(axis=0)
    observed = float(means.max())
    centered = a - means
    rng = np.random.default_rng(seed)
    sims = np.empty(n_boot)
    n = len(a)
    for j in range(n_boot):
        ix = np.empty(n, dtype=int)
        ix[0] = rng.integers(0, n)
        for t in range(1, n):
            ix[t] = rng.integers(0, n) if rng.random() < 1./block_mean else (ix[t-1]+1) % n
        sims[j] = centered[ix].mean(axis=0).max()
    return {"p": float((1 + (sims >= observed).sum()) / (1 + n_boot)),
            "observed_max_active_month": observed,
            "months": n, "reps": n_boot, "number_candidates": int(a.shape[1]),
            "explanation": "Approximate family-wise White Reality Check, reused history"}


def event_causal_audit(frame: pd.DataFrame):
    required = {"name","ticker","entry_date","exit_date","sector_etf",
                "category","midas_net","excess_vs_spy","split","event_id"}
    if required - set(frame):
        raise ValueError("Required event fields missing: " + str(required - set(frame)))
    d = frame.loc[(frame.name == "baseline/20/time") & (frame.split != "PURGED")].copy()
    d["entry_date"] = pd.to_datetime(d.entry_date, errors="raise")
    d["exit_date"] = pd.to_datetime(d.exit_date, errors="raise")
    if (d.exit_date < d.entry_date).any() or d.event_id.duplicated().any():
        raise ValueError("Duplicate event ID or invalid trade times")
    d["sector_etf"] = d.sector_etf.fillna("UNKNOWN").astype(str)
    d["category"] = d.category.fillna("UNKNOWN").astype(str)
    d = d.sort_values(["entry_date", "event_id"]).reset_index(drop=True)
    audit = []
    for r in d.itertuples(index=False):
        # Current trade, same-day settlements and future outcomes are all excluded.
        past = d[(d.exit_date < r.entry_date) & (d.ticker != r.ticker)]
        sector = past[(past.sector_etf == r.sector_etf) &
                      (past.exit_date >= r.entry_date - pd.Timedelta(days=180))]
        category = past[(past.category == r.category) &
                        (past.exit_date >= r.entry_date - pd.Timedelta(days=180))]
        mkt = past[past.exit_date >= r.entry_date - pd.Timedelta(days=90)]
        sector_year = past[(past.sector_etf == r.sector_etf) &
                           (past.exit_date >= r.entry_date - pd.Timedelta(days=365))]
        choices = {
            "all": True,
            "sector_mean_180d": len(sector) >= 8 and sector.excess_vs_spy.mean() > 0,
            "category_mean_180d": len(category) >= 8 and category.excess_vs_spy.mean() > 0,
            "market_mean_90d": len(mkt) >= 20 and mkt.excess_vs_spy.mean() > 0,
            "sector_median_365d": len(sector_year) >= 12 and sector_year.excess_vs_spy.median() > 0,
        }
        audit.append({"event_id": str(r.event_id), "entry_date": str(r.entry_date.date()),
                      "exit_date": str(r.exit_date.date()), "ticker": str(r.ticker),
                      "excess_vs_spy": float(r.excess_vs_spy), "midas_net": float(r.midas_net),
                      **choices})
    return pd.DataFrame(audit)


def event_summary(audit: pd.DataFrame):
    rows = []
    for name in EVENT_VARIANTS:
        z = audit[audit[name]]
        rows.append({"variant": name, "events": int(len(z)),
                     "mean_excess_vs_spy": float(z.excess_vs_spy.mean()) if len(z) else None,
                     "net_ticket_pnl": float(z.midas_net.sum()) if len(z) else 0.,
                     "win_frac": float((z.midas_net > 0).mean()) if len(z) else None,
                     "approval": False, "evidence": "REUSED_TEST_NO_PORTFOLIO"})
    return pd.DataFrame(rows)


def run(source: Path, output: Path):
    rates, spy, meta = read_monthly(source)
    output.mkdir(parents=True, exist_ok=True)
    scores = []
    frame = {}
    for c in COST_PER_TURN:
        for name in VARIANTS:
            row = simulate_months(rates, spy, name, cost_per_turn=c)
            tag = f"{name}|{int(c*10000)}bp"
            frame[tag] = row.return_net.to_numpy() - spy.to_numpy()
            scores.append({"name": name, "extra_cost_bps_per_turn": int(c * 10000),
                           **evaluate(row), "data_split": "REUSED_TEST", "approved": False})
            row.to_csv(output / f"monthly_{tag.replace('|','_')}.csv", index=False)
    score = pd.DataFrame(scores)
    score.to_csv(output / "meta_strategy_scores.csv", index=False)
    active = pd.DataFrame(frame, index=rates.index)
    boot = approximate_max_mean_bootstrap(active)
    event_file = source / "all_style_trades.csv"
    if not event_file.exists():
        raise FileNotFoundError(event_file)
    a = event_causal_audit(pd.read_csv(event_file))
    e = event_summary(a)
    e.to_csv(output / "causal_event_conditioning.csv", index=False)
    a.to_csv(output / "event_causal_audit.csv", index=False)
    observations = {
        "study": "H085", "run_type": "EXPLORATORY_REUSED_TEST",
        "new_approved_strategies": 0, "simulated_trade_orders": 0,
        "variants": len(VARIANTS), "event_variants": len(EVENT_VARIANTS),
        "cost_scenarios": [int(x * 10000) for x in COST_PER_TURN],
        "meta": meta, "benchmark": "SPY monthly strategy NAV",
        "source_frozen": True, "boot_max_mean": boot,
        "event_rows": len(a), "event_file_sha256": hashlib.sha256(event_file.read_bytes()).hexdigest(),
        "splits": {
            "discovery_months": int((rates.index < CUT_1).sum()),
            "validation_months": int(((rates.index >= CUT_1) & (rates.index < CUT_2)).sum()),
            "reused_2026_months": int((rates.index >= CUT_2).sum()),
        },
        "known_limits": [
            "Already exposed H083 history; no sealed/untouched out-of-sample proof",
            "Meta NAV blending is a portfolio proxy; H083 tickets have fixed fees that do not scale linearly",
            "Monthly strategy-switch execution and taxes are approximated, not order-level replayed",
            "Event scores sum overlapping tickets; not a funded portfolio backtest",
            "Liquidity, delisting, historic price availability and broker access still need independent verification",
        ],
    }
    (output / "H085_REPORT.json").write_text(json.dumps(observations, indent=2), encoding="utf-8")
    lines = ["# H085 — New strategy derivatives (frozen H083 data)", "",
             "**REUSED_TEST research only. Not independent proof of alpha or trade authorization.**", "",
             f"- Exposed months: {len(rates)}, events: {len(a)}, rotation rules: {rates.shape[1]}.",
             f"- Monthly variants: {len(VARIANTS)} at {len(COST_PER_TURN)} incremental cost scenarios.",
             f"- Exploratory stationary-bootstrap max-stat p: {boot.get('p')}.",
             "", "## Top proxy variants (25bp extra turnover)", ""]
    for _, r in score[score.extra_cost_bps_per_turn == 25].sort_values("active_total_gap", ascending=False).head(8).iterrows():
        lines.append(f"- {r['name']}: net {r['net_total']:+.1%}; SPY {r['spy_total']:+.1%}; max DD {r['max_drawdown']:.1%}; active months {r['active_months']}; approval NO")
    lines += ["", "## Event conditioning (20-day baseline)", ""]
    for _, r in e.iterrows():
        v = r["mean_excess_vs_spy"]
        lines.append(f"- {r['variant']}: {r['events']} events, mean trade excess {v if pd.notna(v) else 'n/a'}; approval NO")
    lines += ["", "No retroactive production signals. Exact inputs and all losing variants are available in CSV/JSON artifacts."]
    (output / "H085_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(observations, indent=2))
    return observations


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--h083-results", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    run(args.h083_results, args.output)
