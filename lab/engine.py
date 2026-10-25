"""Vectorized portfolio engine (pure pandas/numpy, no look-ahead).

Contract:
  - A strategy returns TARGET WEIGHTS computed with information up to the close of day t.
  - The engine applies them from day t+1 (weights.shift(1)). This removes look-ahead bias.
  - Costs = turnover * (commission + slippage), charged on the day the trade happens.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Costs:
    commission: float = 0.001   # per side, fraction of traded notional
    slippage: float = 0.0005    # per side
    borrow_annual: float = 0.0  # short borrow cost (annual), applied to |short| weight
    funding_annual: float = 0.0  # perp funding / financing (annual), applied to gross exposure

    @property
    def per_turnover(self) -> float:
        return self.commission + self.slippage


@dataclass
class Result:
    returns: pd.Series                 # daily net portfolio returns
    gross: pd.Series                   # daily gross returns
    weights: pd.DataFrame              # held weights (after shift)
    turnover: pd.Series                # daily one-way turnover
    meta: dict = field(default_factory=dict)

    @property
    def equity(self) -> pd.Series:
        return (1 + self.returns).cumprod()


def run(prices: pd.DataFrame, target_weights: pd.DataFrame, costs: Costs | None = None,
        lag: int = 1, ppy: float = 252.0, member: pd.DataFrame | None = None) -> Result:
    costs = costs or Costs()
    prices = prices.sort_index()
    tw = target_weights.reindex(prices.index).reindex(columns=prices.columns).fillna(0.0)
    if member is not None:  # survivorship control: never hold a stock outside its membership window
        tw = tw.where(member.reindex(index=tw.index, columns=tw.columns).fillna(False), 0.0)
    held = tw.shift(lag).fillna(0.0)
    asset_ret = prices.pct_change(fill_method=None).fillna(0.0)
    # An asset with no price today cannot be held: zero its contribution.
    asset_ret = asset_ret.where(prices.notna(), 0.0)
    gross = (held * asset_ret).sum(axis=1)
    turnover = held.diff().abs().sum(axis=1).fillna(held.abs().sum(axis=1))
    cost = turnover * costs.per_turnover
    if costs.borrow_annual:
        cost = cost + held.clip(upper=0).abs().sum(axis=1) * costs.borrow_annual / ppy
    if costs.funding_annual:
        cost = cost + held.abs().sum(axis=1) * costs.funding_annual / ppy
    net = gross - cost
    first = held.abs().sum(axis=1).gt(0)
    if first.any():
        start = first.idxmax()
        net, gross, turnover = net.loc[start:], gross.loc[start:], turnover.loc[start:]
        held = held.loc[start:]
    return Result(net, gross, held, turnover)


# ---------- weight helpers used by strategies ----------

def rank_top_n(score: pd.DataFrame, n: int, long_short: bool = False) -> pd.DataFrame:
    """Equal-weight the top n by score (and short the bottom n if long_short)."""
    valid = score.notna()
    r = score.rank(axis=1, ascending=False, method="first")
    cnt = valid.sum(axis=1)
    k = np.minimum(n, cnt // (2 if long_short else 1)).replace(0, np.nan)
    long_ = (r.le(k, axis=0) & valid).astype(float).div(k, axis=0)
    if not long_short:
        return long_.fillna(0.0)
    rb = score.rank(axis=1, ascending=True, method="first")
    short = (rb.le(k, axis=0) & valid).astype(float).div(k, axis=0)
    return (0.5 * long_ - 0.5 * short).fillna(0.0)


def rebalance(weights: pd.DataFrame, freq: str = "ME") -> pd.DataFrame:
    """Hold weights constant between rebalance dates (last trading day of each period)."""
    if freq in (None, "D", "1D"):
        return weights
    idx = weights.index
    marks = pd.Series(idx, index=idx).groupby(idx.to_period(freq.rstrip("E") or "M")).transform("max")
    is_reb = pd.Series(idx == marks.values, index=idx)
    return weights.where(is_reb, np.nan).ffill().fillna(0.0)


def vol_target(weights: pd.DataFrame, prices: pd.DataFrame, target: float = 0.15,
               lookback: int = 63, cap: float = 2.0, ppy: float = 252.0) -> pd.DataFrame:
    """Scale the whole book to an annual volatility target (uses past data only)."""
    r = prices.pct_change(fill_method=None).fillna(0.0)
    port = (weights.shift(1).fillna(0) * r).sum(axis=1)
    realized = port.rolling(lookback, min_periods=20).std() * np.sqrt(ppy)
    scale = (target / realized).clip(upper=cap).fillna(0.0)
    return weights.mul(scale, axis=0)
