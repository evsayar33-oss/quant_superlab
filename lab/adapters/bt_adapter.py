"""Optional backtesting.py adapter: bar-by-bar single-asset tests with stops/targets.

Use it when a rule needs intrabar logic (stop-loss, take-profit, trailing stop)
that the vectorized engine does not model. Example:

    python -m lab.adapters.bt_adapter THYAO.IS --sl 0.05 --tp 0.15
"""
from __future__ import annotations

import argparse
from pathlib import Path


def run_sma_with_stops(ticker: str, start: str, fast: int, slow: int, sl: float, tp: float,
                       commission: float = 0.002):
    from backtesting import Backtest, Strategy
    from backtesting.lib import crossover

    from lab.data import load_ohlcv

    df = load_ohlcv([ticker], start)[ticker].dropna()

    def sma(x, n):
        import pandas as pd
        return pd.Series(x).rolling(n).mean().values

    class SmaStops(Strategy):
        def init(self):
            self.f = self.I(sma, self.data.Close, fast)
            self.s = self.I(sma, self.data.Close, slow)

        def next(self):
            px = self.data.Close[-1]
            if not self.position and crossover(self.f, self.s):
                self.buy(sl=px * (1 - sl), tp=px * (1 + tp))
            elif self.position and crossover(self.s, self.f):
                self.position.close()

    bt = Backtest(df, SmaStops, cash=100_000, commission=commission, exclusive_orders=True)
    return bt.run(), bt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--start", default="2012-01-01")
    ap.add_argument("--fast", type=int, default=20)
    ap.add_argument("--slow", type=int, default=100)
    ap.add_argument("--sl", type=float, default=0.05)
    ap.add_argument("--tp", type=float, default=0.15)
    a = ap.parse_args()
    stats, bt = run_sma_with_stops(a.ticker, a.start, a.fast, a.slow, a.sl, a.tp)
    print(stats)
    out = Path("results") / f"bt_{a.ticker.replace('/', '_')}.html"
    out.parent.mkdir(exist_ok=True)
    bt.plot(filename=str(out), open_browser=False)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
