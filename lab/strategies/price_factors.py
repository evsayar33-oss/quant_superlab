"""More price/volume-based cross-sectional and time-series anomalies."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import indicators as I
from lab.engine import rank_top_n, rebalance
from lab.strategies import strategy


def _rets(c):
    return c.pct_change(fill_method=None)


@strategy("residual_momentum",
          grid={"lookback": [126, 252], "top_n": [5, 10]},
          defaults={"lookback": 252, "top_n": 5, "skip": 21, "freq": "ME"},
          source="Blitz, Huij & Martens (2011) Residual Momentum")
def residual_momentum(c, lookback, top_n, skip, freq):
    r = _rets(c)
    mkt = r.mean(axis=1)
    cov = r.rolling(lookback, min_periods=lookback // 2).cov(mkt)
    beta = cov.div(mkt.rolling(lookback, min_periods=lookback // 2).var(), axis=0)
    resid = r - beta.mul(mkt, axis=0)
    score = resid.shift(skip).rolling(lookback - skip).sum() / resid.shift(skip).rolling(lookback - skip).std()
    return rebalance(rank_top_n(score, top_n), freq)


@strategy("frog_in_pan",
          grid={"lookback": [126, 252], "top_n": [5, 10]},
          defaults={"lookback": 252, "top_n": 5, "freq": "ME"},
          source="Da, Gurun & Warachka (2014) Frog in the Pan: information discreteness")
def frog_in_pan(c, lookback, top_n, freq):
    r = _rets(c)
    pret = c / c.shift(lookback) - 1
    pos = (r > 0).rolling(lookback).mean(); neg = (r < 0).rolling(lookback).mean()
    id_ = np.sign(pret) * (neg - pos)  # low ID = continuous information = stronger momentum
    score = pret.rank(axis=1, pct=True) - id_.rank(axis=1, pct=True)
    return rebalance(rank_top_n(score, top_n), freq)


@strategy("max_effect",
          grid={"lookback": [21, 63], "top_n": [5, 10]},
          defaults={"lookback": 21, "top_n": 5, "freq": "ME"},
          source="Bali, Cakici & Whitelaw (2011) Maxing Out: lottery stocks underperform")
def max_effect(c, lookback, top_n, freq):
    mx = _rets(c).rolling(lookback, min_periods=lookback // 2).max()
    return rebalance(rank_top_n(-mx, top_n), freq)


@strategy("idio_vol",
          grid={"lookback": [63, 126], "top_n": [5, 10]},
          defaults={"lookback": 63, "top_n": 5, "freq": "ME"},
          source="Ang, Hodrick, Xing & Zhang (2006) idiosyncratic volatility puzzle")
def idio_vol(c, lookback, top_n, freq):
    r = _rets(c)
    resid = r.sub(r.mean(axis=1), axis=0)
    iv = resid.rolling(lookback, min_periods=lookback // 2).std()
    return rebalance(rank_top_n(-iv, top_n), freq)


@strategy("betting_against_beta",
          grid={"lookback": [126, 252], "top_n": [5, 10]},
          defaults={"lookback": 252, "top_n": 5, "freq": "ME"},
          source="Frazzini & Pedersen (2014) Betting Against Beta (long low-beta leg)")
def betting_against_beta(c, lookback, top_n, freq):
    r = _rets(c)
    m = r.mean(axis=1)
    beta = r.rolling(lookback, min_periods=lookback // 2).cov(m).div(
        m.rolling(lookback, min_periods=lookback // 2).var(), axis=0)
    return rebalance(rank_top_n(-beta, top_n), freq)


@strategy("seasonality_same_month",
          grid={"years": [5, 10], "top_n": [5, 10]},
          defaults={"years": 5, "top_n": 5},
          source="Heston & Sadka (2008) Seasonality in the cross-section of returns")
def seasonality_same_month(c, years, top_n):
    m = c.resample("ME").last().pct_change(fill_method=None)
    # average return of the SAME calendar month in previous years (lags 12, 24, ...)
    score_m = sum(m.shift(12 * k) for k in range(1, years + 1)) / years
    # Decide at the end of month t-1 for month t: score for month t uses lags >= 11 months.
    score_next = score_m.shift(-1).iloc[:-1]
    sp = score_next.copy()
    sp.index = sp.index.to_period("M")
    daily = pd.DataFrame(sp.reindex(c.index.to_period("M")).values, index=c.index, columns=c.columns)
    return rebalance(rank_top_n(daily, top_n), "ME")


@strategy("mom_acceleration",
          grid={"short": [63], "long": [252], "top_n": [5, 10]},
          defaults={"short": 63, "long": 252, "top_n": 5, "freq": "ME"},
          source="Momentum acceleration: recent vs longer momentum")
def mom_acceleration(c, short, long, top_n, freq):
    acc = (c / c.shift(short) - 1) - (c.shift(short) / c.shift(long) - 1) * short / (long - short)
    return rebalance(rank_top_n(acc, top_n), freq)


@strategy("vol_managed_momentum",
          grid={"lookback": [252], "top_n": [5, 10], "target": [0.12, 0.18]},
          defaults={"lookback": 252, "top_n": 5, "target": 0.15, "freq": "ME"},
          source="Barroso & Santa-Clara (2015) Momentum has its moments")
def vol_managed_momentum(c, lookback, top_n, target, freq):
    from lab.engine import vol_target
    w = rebalance(rank_top_n(c.shift(21) / c.shift(lookback) - 1, top_n), freq)
    return vol_target(w, c, target, 126, cap=1.0)


@strategy("trend_quality",
          grid={"n": [63, 126], "top_n": [5, 10]},
          defaults={"n": 126, "top_n": 5, "freq": "ME"},
          source="Momentum ranked by trend R^2 (smooth trends persist)")
def trend_quality(c, n, top_n, freq):
    logp = np.log(c)
    x = np.arange(n) - (n - 1) / 2
    def r2(a):
        if np.isnan(a).any():
            return np.nan
        b = np.dot(x, a - a.mean()) / np.dot(x, x)
        fit = b * x
        ss = ((a - a.mean()) ** 2).sum()
        return np.sign(b) * (1 - ((a - a.mean() - fit) ** 2).sum() / ss) * abs(b) if ss > 0 else np.nan
    score = logp.rolling(n, min_periods=n).apply(r2, raw=True)
    return rebalance(rank_top_n(score, top_n), freq)


@strategy("rsi_rotation",
          grid={"n": [7, 14, 21, 28], "top_n": [3, 5, 10], "mode": ["strong", "weak"]},
          defaults={"n": 14, "top_n": 5, "mode": "strong", "freq": "W"},
          source="Cross-sectional RSI rotation (strength vs reversal)")
def rsi_rotation(c, n, top_n, mode, freq):
    r = I.rsi(c, n)
    return rebalance(rank_top_n(r if mode == "strong" else -r, top_n), freq)


@strategy("volume_shock",
          grid={"n": [20, 63], "top_n": [5, 10]},
          defaults={"n": 20, "top_n": 5, "freq": "W"},
          source="Gervais, Kaniel & Mingelgrin (2001) High-volume return premium",
          needs="panel")
def volume_shock(p, n, top_n, freq):
    rv = p.v.rolling(5).mean() / p.v.rolling(n * 5, min_periods=n).mean().shift(5)
    return rebalance(rank_top_n(rv, top_n), freq)
