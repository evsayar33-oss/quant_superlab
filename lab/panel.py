"""Panel: the container every strategy receives.

  panel.o / .h / .l / .c / .v   wide OHLCV frames (bars x assets)
  panel.bench                   benchmark close (Series) or None
  panel.fund                    dict[field] -> wide point-in-time fundamental frame
  panel.macro                   dict[ticker] -> macro series aligned to bars (^VIX, USDTRY=X, ...)
  panel.rf_annual               risk-free rate (annual, decimal) aligned to bars, or None
  panel.fx                      local-currency price of 1 USD (to report results in USD), or None
  panel.member                  bool frame: was the asset an index member at that time (survivorship)
  panel.freq / panel.ppy        timeframe label and bars per year (measured from the data)
  panel.extra                   other point-in-time frames (CFTC COT positioning, ...)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Panel:
    o: pd.DataFrame
    h: pd.DataFrame
    l: pd.DataFrame
    c: pd.DataFrame
    v: pd.DataFrame
    bench: pd.Series | None = None
    fund: dict = field(default_factory=dict)
    name: str = ""
    freq: str = "1d"
    market: str = ""
    macro: dict = field(default_factory=dict)
    rf_annual: pd.Series | None = None
    fx: pd.Series | None = None
    member: pd.DataFrame | None = None
    costs_meta: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)   # e.g. COT positioning frames (cot_spec_net, cot_comm_net)

    @property
    def index(self):
        return self.c.index

    @property
    def columns(self):
        return self.c.columns

    @property
    def ppy(self) -> float:
        """Bars per year, measured (works for any timeframe and market calendar)."""
        idx = self.c.index
        if len(idx) < 3:
            return 252.0
        years = (idx[-1] - idx[0]).total_seconds() / (365.25 * 86400)
        return float(len(idx) / years) if years > 0 else 252.0

    def rf_per_bar(self) -> pd.Series:
        if self.rf_annual is None:
            return pd.Series(0.0, index=self.index)
        return (1 + self.rf_annual.fillna(0.0)) ** (1 / self.ppy) - 1

    @staticmethod
    def from_ohlcv(data: dict[str, pd.DataFrame], bench: pd.Series | None = None, name: str = "") -> "Panel":
        def wide(col):
            return pd.DataFrame({t: d[col] for t, d in data.items()}).sort_index()
        c = wide("Close")
        c = c.where(c > 0).ffill(limit=5)
        o, h, l = (wide(k).reindex(c.index) for k in ("Open", "High", "Low"))
        o = o.where(o > 0, c); h = h.where(h > 0, c); l = l.where(l > 0, c)
        h = np.maximum(h, np.maximum(o, c)); l = np.minimum(l, np.minimum(o, c))
        v = wide("Volume").reindex(c.index).fillna(0)
        if bench is not None:
            bench = bench.reindex(bench.index.union(c.index)).sort_index().ffill().reindex(c.index)
        return Panel(o.where(c.notna()), h.where(c.notna()), l.where(c.notna()), c, v, bench, {}, name)

    @staticmethod
    def from_close(c: pd.DataFrame, seed: int = 0, name: str = "synthetic") -> "Panel":
        """Build a plausible OHLCV panel from closes (for offline tests)."""
        rng = np.random.default_rng(seed)
        prev = c.shift(1).fillna(c)
        o = prev * (1 + rng.normal(0, 0.003, c.shape))
        spread = np.abs(rng.normal(0, 0.008, c.shape))
        h = np.maximum(o, c) * (1 + spread)
        l = np.minimum(o, c) * (1 - spread)
        v = pd.DataFrame(rng.lognormal(13, 0.4, c.shape), index=c.index, columns=c.columns)
        return Panel(o, h, l, c, v, c.mean(axis=1), {}, name)
