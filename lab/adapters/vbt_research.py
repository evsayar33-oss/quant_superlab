"""Research-only SMA grid with independent equity accounting.

Signals are calculated on close t and executed at close t+1. The independent
reference ledger and vectorbt receive identical price/fee/slippage assumptions.
This is NOT a next-open fill model, and is not the production decision gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def clean_close(close: pd.Series) -> pd.Series:
    if not isinstance(close, pd.Series):
        raise TypeError("close must be a pandas Series")
    series = pd.to_numeric(close, errors="coerce").dropna().astype(float)
    if len(series) < 30 or not np.isfinite(series).all() or (series <= 0).any():
        raise ValueError("At least 30 finite, positive close prices are required")
    if series.index.has_duplicates or not series.index.is_monotonic_increasing:
        raise ValueError("Dates must be unique and increasing")
    return series


def parameter_pairs(fast_values, slow_values, max_trials: int = 500):
    fast = sorted(set(int(x) for x in fast_values))
    slow = sorted(set(int(x) for x in slow_values))
    if not fast or not slow or any(x < 2 for x in fast + slow):
        raise ValueError("Moving-average windows must be >= 2")
    pairs = [(f, s) for f in fast for s in slow if f < s]
    if not pairs:
        raise ValueError("No valid fast < slow combinations")
    if len(pairs) > max_trials:
        raise ValueError(f"{len(pairs)} trials exceed max_trials={max_trials}")
    return pairs


def execution_signals(close: pd.Series, fast: int, slow: int):
    # The crossover at close t is known only after close t, so trade at t+1 close.
    short = close.rolling(fast, min_periods=fast).mean()
    long = close.rolling(slow, min_periods=slow).mean()
    entry = ((short > long) & (short.shift(1) <= long.shift(1))).fillna(False)
    exit_ = ((short < long) & (short.shift(1) >= long.shift(1))).fillna(False)
    return entry.shift(1, fill_value=False).astype(bool), exit_.shift(1, fill_value=False).astype(bool)


def independent_equity(close: pd.Series, entries: pd.Series, exits: pd.Series,
                       fee: float = 0.001, slippage: float = 0.0005,
                       initial_cash: float = 10000) -> pd.Series:
    """All-in long-only execution at next close, with costs on both sides."""
    if not (0 <= fee < 1 and 0 <= slippage < 1 and initial_cash > 0):
        raise ValueError("Invalid fee, slippage or initial cash")
    cash, units = float(initial_cash), 0.0
    values = []
    for px, buy, sell in zip(close.to_numpy(), entries.to_numpy(), exits.to_numpy()):
        if units > 0 and bool(sell):
            cash = units * px * (1 - slippage) * (1 - fee)
            units = 0.0
        elif units == 0 and bool(buy):
            units = cash / (px * (1 + slippage) * (1 + fee))
            cash = 0.0
        values.append(cash + units * px)
    return pd.Series(values, index=close.index, name="independent_equity")


def run_research(close: pd.Series, fast_values, slow_values,
                 fee: float = 0.001, slippage: float = 0.0005,
                 initial_cash: float = 10000, max_trials: int = 500,
                 tolerance: float = 1e-4) -> tuple[pd.DataFrame, dict]:
    """Compare identical assumptions, never approve or register a strategy."""
    import vectorbt as vbt  # optional: pip install -r requirements-optional.txt

    close = clean_close(close)
    if not (0 <= fee < 1 and 0 <= slippage < 1 and initial_cash > 0):
        raise ValueError("Invalid execution assumptions")
    pairs = parameter_pairs(fast_values, slow_values, max_trials=max_trials)
    records = []
    for fast, slow in pairs:
        entries, exits = execution_signals(close, fast, slow)
        independent = independent_equity(close, entries, exits, fee, slippage, initial_cash)
        portfolio = vbt.Portfolio.from_signals(
            close, entries, exits, init_cash=initial_cash, fees=fee,
            slippage=slippage, freq="1D", direction="longonly")
        vbt_value = portfolio.value().reindex(close.index)
        # Compare the full equity path, not only the final return / Sharpe.
        relative_gap = float(((vbt_value - independent).abs() / initial_cash).max())
        independently_valid = bool(np.isfinite(relative_gap) and relative_gap <= tolerance)
        ret = independent.pct_change().fillna(0.0)
        dd = independent / independent.cummax() - 1
        annual_sharpe = (float(ret.mean() / ret.std() * np.sqrt(252))
                         if ret.std() > 0 else 0.0)
        records.append({
            "fast": fast, "slow": slow, "trial_id": f"MA_{fast}_{slow}",
            "return_net": float(independent.iloc[-1] / initial_cash - 1),
            "max_drawdown": float(dd.min()), "sharpe": annual_sharpe,
            "orders": int(portfolio.orders.count()),
            "max_equity_gap_pct_of_initial": relative_gap * 100,
            "engine_agreement": independently_valid,
        })
    frame = pd.DataFrame(records).sort_values(
        ["engine_agreement", "sharpe"], ascending=[False, False]
    ).reset_index(drop=True)
    summary = {
        "purpose": "EXPLORATION_ONLY", "gate_eligible": False,
        "execution": "signal at close t, fill at close t+1",
        "trial_count": len(pairs), "fee_per_side": fee,
        "slippage_per_side": slippage, "initial_cash": initial_cash,
        "date_start": str(close.index[0]), "date_end": str(close.index[-1]),
        "max_equity_gap_pct_of_initial": float(frame["max_equity_gap_pct_of_initial"].max()),
        "all_engines_agree": bool(frame["engine_agreement"].all()),
        "limitations": [
            "same close-price feed shared by both engines: NOT independent market data",
            "no next-open execution, partial fills, liquidity model or dividends",
            "in-sample exploratory rankings; not OOS evidence or investment approval",
            "all tested variants must count toward downstream multiple-testing correction",
        ],
    }
    return frame, summary


def read_csv_prices(path: str, date_col="Date", close_col="Close") -> pd.Series:
    data = pd.read_csv(path)
    if date_col not in data or close_col not in data:
        raise ValueError(f"CSV requires {date_col!r} and {close_col!r} columns")
    dt = pd.to_datetime(data[date_col], errors="raise", utc=True)
    price = pd.Series(pd.to_numeric(data[close_col], errors="coerce").to_numpy(),
                      index=dt.dt.tz_localize(None), name="Close")
    return clean_close(price)


def main():
    parser = argparse.ArgumentParser(description="Research only: CSV vectorbt parity / SMA grid")
    parser.add_argument("csv", help="CSV with Date and Close columns")
    parser.add_argument("--fast", nargs=3, type=int, default=[5, 51, 5],
                        metavar=("START", "STOP", "STEP"))
    parser.add_argument("--slow", nargs=3, type=int, default=[50, 251, 10],
                        metavar=("START", "STOP", "STEP"))
    parser.add_argument("--fee", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--out", default="results/vbt_research")
    args = parser.parse_args()
    if args.fast[2] <= 0 or args.slow[2] <= 0:
        parser.error("Steps must be positive")
    result, summary = run_research(read_csv_prices(args.csv),
        range(*args.fast), range(*args.slow), fee=args.fee, slippage=args.slippage)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(path.with_suffix(".csv"), index=False)
    path.with_suffix(".json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not summary["all_engines_agree"]:
        raise SystemExit("ENGINE PARITY FAILED: inspect individual rows; NO APPROVAL")


if __name__ == "__main__":
    main()
