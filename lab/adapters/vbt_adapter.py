"""Optional vectorbt adapter: fast parameter heat-maps for single-asset rules.

Use it to EXPLORE an idea quickly. The decision gate stays lab.validation
(walk-forward + DSR); a heat-map alone never approves a strategy.

    python -m lab.adapters.vbt_adapter THYAO.IS --fast 5 50 5 --slow 50 250 10
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


def ma_heatmap(ticker: str, fast: range, slow: range, start: str = "2012-01-01", fees: float = 0.002):
    import vectorbt as vbt

    from lab.data import load_prices

    close = load_prices([ticker], start)[ticker].dropna()
    fast_ma, slow_ma = vbt.MA.run_combs(close, window=list(fast) + list(slow), r=2,
                                        short_names=["fast", "slow"])
    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)
    pf = vbt.Portfolio.from_signals(close, entries, exits, fees=fees, freq="1D")
    sr = pf.sharpe_ratio()
    return sr, pf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--fast", nargs=3, type=int, default=[5, 50, 5])
    ap.add_argument("--slow", nargs=3, type=int, default=[50, 250, 10])
    ap.add_argument("--start", default="2012-01-01")
    a = ap.parse_args()
    sr, _ = ma_heatmap(a.ticker, range(*a.fast), range(*a.slow), a.start)
    sr = sr.replace([np.inf, -np.inf], np.nan).dropna()
    out = Path("results") / f"vbt_ma_{a.ticker.replace('/', '_')}.csv"
    out.parent.mkdir(exist_ok=True)
    sr.sort_values(ascending=False).to_csv(out)
    print(f"{len(sr)} combinations tested. Top 10 Sharpe:\n{sr.sort_values(ascending=False).head(10)}")
    print(f"WARNING: {len(sr)} trials -> the best Sharpe is inflated. Validate with run.py (DSR).")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
