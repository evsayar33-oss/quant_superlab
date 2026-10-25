"""Strategy catalog (hypothesis library).

Every strategy is a pure function: (prices, **params) -> target weights DataFrame.
Weights use data up to the close of day t only; the engine trades them at t+1.

Register with @strategy(name, grid, source). `grid` is the parameter search space the
validator sweeps; its size feeds the Deflated Sharpe Ratio (more trials -> higher bar).
Sources are the papers listed in paperswithbacktest/awesome-systematic-trading and
the original academic literature.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from lab.engine import rank_top_n, rebalance, vol_target


@dataclass
class Strategy:
    name: str
    fn: Callable[..., pd.DataFrame]
    grid: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    source: str = ""
    kind: str = "cross_section"  # cross_section | time_series | fundamental
    needs: str = "close"         # close -> fn(close DataFrame); panel -> fn(Panel)

    def __call__(self, data, **params) -> pd.DataFrame:
        from lab.panel import Panel
        p = {**self.defaults, **params}
        if self.needs == "close" and isinstance(data, Panel):
            data = data.c
        return self.fn(data, **p)


REGISTRY: dict[str, Strategy] = {}


def strategy(name: str, grid: dict, defaults: dict, source: str, kind: str = "cross_section",
             needs: str = "close"):
    def deco(fn):
        REGISTRY[name] = Strategy(name, fn, grid, defaults, source, kind, needs)
        return fn
    return deco


def get(name: str) -> Strategy:
    if name not in REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Known: {sorted(REGISTRY)}")
    return REGISTRY[name]


# ----------------------------------------------------------------------------
# 1. Cross-sectional momentum (12-1)
# ----------------------------------------------------------------------------
@strategy("xs_momentum",
          grid={"lookback": [126, 189, 252], "skip": [0, 21], "top_n": [3, 5, 10]},
          defaults={"lookback": 252, "skip": 21, "top_n": 5, "freq": "ME"},
          source="Jegadeesh & Titman (1993) Returns to Buying Winners and Selling Losers")
def xs_momentum(prices, lookback, skip, top_n, freq):
    score = prices.shift(skip) / prices.shift(lookback) - 1
    return rebalance(rank_top_n(score, top_n), freq)


# ----------------------------------------------------------------------------
# 2. Time-series momentum (trend following), vol-targeted
# ----------------------------------------------------------------------------
@strategy("ts_momentum",
          grid={"lookback": [63, 126, 252], "vol_target": [0.10, 0.15]},
          defaults={"lookback": 252, "vol_target": 0.15, "long_only": True, "freq": "ME"},
          source="Moskowitz, Ooi & Pedersen (2012) Time Series Momentum",
          kind="time_series")
def ts_momentum(prices, lookback, vol_target, long_only, freq):
    sig = np.sign(prices / prices.shift(lookback) - 1)
    if long_only:
        sig = sig.clip(lower=0)
    vol = prices.pct_change(fill_method=None).rolling(63, min_periods=20).std() * np.sqrt(252)
    w = (sig * (vol_target / vol)).div(prices.notna().sum(axis=1), axis=0)
    w = w.clip(-1, 1).fillna(0.0)
    return rebalance(w, freq)


# ----------------------------------------------------------------------------
# 3. Moving-average crossover (per asset, equal weight across assets)
# ----------------------------------------------------------------------------
@strategy("ma_timing",
          grid={"fast": [20, 50], "slow": [100, 200]},
          defaults={"fast": 50, "slow": 200},
          source="Faber (2007) A Quantitative Approach to Tactical Asset Allocation",
          kind="time_series")
def ma_timing(prices, fast, slow):
    on = (prices.rolling(fast).mean() > prices.rolling(slow).mean()).astype(float)
    on = on.where(prices.rolling(slow).count() >= slow, 0.0)
    return on.div(prices.notna().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


# ----------------------------------------------------------------------------
# 4. Short-term reversal (weekly losers bounce)
# ----------------------------------------------------------------------------
@strategy("st_reversal",
          grid={"lookback": [5, 10, 21], "top_n": [3, 5]},
          defaults={"lookback": 5, "top_n": 5, "freq": "W"},
          source="Lehmann (1990) Fads, Martingales and Market Efficiency; Jegadeesh (1990)")
def st_reversal(prices, lookback, top_n, freq):
    score = -(prices / prices.shift(lookback) - 1)
    return rebalance(rank_top_n(score, top_n), freq)


# ----------------------------------------------------------------------------
# 5. Low-volatility anomaly
# ----------------------------------------------------------------------------
@strategy("low_vol",
          grid={"lookback": [63, 126, 252], "top_n": [5, 10]},
          defaults={"lookback": 252, "top_n": 5, "freq": "ME"},
          source="Ang, Hodrick, Xing & Zhang (2006); Baker, Bradley & Wurgler (2011)")
def low_vol(prices, lookback, top_n, freq):
    vol = prices.pct_change(fill_method=None).rolling(lookback, min_periods=lookback // 2).std()
    return rebalance(rank_top_n(-vol, top_n), freq)


# ----------------------------------------------------------------------------
# 6. 52-week-high proximity
# ----------------------------------------------------------------------------
@strategy("high_52w",
          grid={"top_n": [3, 5, 10]},
          defaults={"top_n": 5, "window": 252, "freq": "ME"},
          source="George & Hwang (2004) The 52-Week High and Momentum Investing")
def high_52w(prices, top_n, window, freq):
    score = prices / prices.rolling(window, min_periods=window // 2).max()
    return rebalance(rank_top_n(score, top_n), freq)


# ----------------------------------------------------------------------------
# 7. Dual momentum (relative + absolute filter, cash otherwise)
# ----------------------------------------------------------------------------
@strategy("dual_momentum",
          grid={"lookback": [126, 252], "top_n": [1, 3, 5]},
          defaults={"lookback": 252, "top_n": 3, "freq": "ME"},
          source="Antonacci (2014) Dual Momentum Investing")
def dual_momentum(prices, lookback, top_n, freq):
    mom = prices / prices.shift(lookback) - 1
    w = rank_top_n(mom, top_n)
    w = w.where(mom > 0, 0.0)  # absolute filter: only positive momentum, rest in cash
    return rebalance(w, freq)


# ----------------------------------------------------------------------------
# 8. Turn-of-the-month seasonality
# ----------------------------------------------------------------------------
@strategy("turn_of_month",
          grid={"days_before": [1, 2, 3], "days_after": [2, 3, 4]},
          defaults={"days_before": 1, "days_after": 3},
          source="Ariel (1987); Lakonishok & Smidt (1988) Turn-of-the-month effect",
          kind="time_series")
def turn_of_month(prices, days_before, days_after):
    idx = prices.index
    per = idx.to_period("M")
    s = pd.Series(1, index=idx)
    pos_from_start = s.groupby(per).cumsum()            # 1..n
    pos_from_end = s[::-1].groupby(per[::-1]).cumsum()[::-1]  # n..1
    target = (pos_from_start <= days_after) | (pos_from_end <= days_before)
    # Weight set at close t is held on t+1, so shift the (known in advance) calendar mask by -1.
    hold_next = target.shift(-1).fillna(False).astype(bool)
    on = pd.DataFrame(np.repeat(hold_next.values[:, None], prices.shape[1], axis=1),
                      index=idx, columns=prices.columns).astype(float)
    return on.div(prices.notna().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


# ----------------------------------------------------------------------------
# 9. RSI(2) mean reversion in an uptrend (Connors)
# ----------------------------------------------------------------------------
def _rsi(p: pd.DataFrame, n: int) -> pd.DataFrame:
    d = p.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


@strategy("rsi_reversion",
          grid={"n": [2, 3], "entry": [5, 10, 20], "exit": [50, 70]},
          defaults={"n": 2, "entry": 10, "exit": 70, "trend": 200},
          source="Connors & Alvarez (2009) Short Term Trading Strategies That Work",
          kind="time_series")
def rsi_reversion(prices, n, entry, exit, trend):
    rsi = _rsi(prices, n)
    up = prices > prices.rolling(trend).mean()
    state = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    state[(rsi < entry) & up] = 1.0
    state[(rsi > exit) | ~up] = 0.0
    on = state.ffill().fillna(0.0)
    return on.div(prices.notna().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


# ----------------------------------------------------------------------------
# Benchmark: equal-weight buy & hold of the universe (monthly rebalance)
# ----------------------------------------------------------------------------
@strategy("equal_weight", grid={}, defaults={"freq": "ME"},
          source="Benchmark: 1/N (DeMiguel, Garlappi & Uppal, 2009)")
def equal_weight(prices, freq):
    w = prices.notna().astype(float)
    return rebalance(w.div(w.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0), freq)


from lab.strategies import price_factors, fundamental_factors, advanced, metals, crypto_core  # noqa: E402,F401  (registers more)

__all__ = ["REGISTRY", "get", "strategy", "Strategy", "vol_target"]
