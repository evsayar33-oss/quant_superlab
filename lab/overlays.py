"""Portfolio overlays as tradeable variants (not just report diagnostics).

An overlay scales the exposure of a finished strategy using ONLY past bars of that strategy:
  vt10 / vt15 / vt20   volatility target 10/15/20% (scale = target / trailing vol, capped at 1:
                       it can only de-risk, never lever up)
  dd10 / dd20          drawdown brake: half exposure while the strategy is >10% / >20% below its peak
  eqma_s / eqma_l      equity-curve filter: stay flat while equity is below its short / long average
Changing exposure costs money: |change in scale| x gross exposure x cost per turnover.
Overlay variants are counted as trials in the deflated statistics like any other variant.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lab.engine import Costs, Result

KINDS = ["vt10", "vt15", "vt20", "dd10", "dd20", "eqma_s", "eqma_l"]


def scale_series(r: pd.Series, kind: str, ppy: float) -> pd.Series:
    if kind.startswith("vt"):
        tv = int(kind[2:]) / 100
        look = max(int(ppy / 4), 10)
        vol = r.rolling(look, min_periods=look // 2).std().shift(1) * math.sqrt(ppy)
        return (tv / vol).clip(upper=1.0).fillna(1.0)
    if kind.startswith("dd"):
        thr = int(kind[2:]) / 100
        eq = (1 + r).cumprod()
        dd = (eq / eq.cummax() - 1).shift(1).fillna(0)
        return pd.Series(np.where(dd < -thr, 0.5, 1.0), index=r.index)
    if kind.startswith("eqma"):
        n = int(ppy / 6) if kind.endswith("_s") else int(ppy / 2)
        eq = (1 + r).cumprod()
        on = (eq > eq.rolling(n, min_periods=n // 2).mean()).shift(1)
        return on.fillna(True).astype(float)
    raise ValueError(kind)


def apply(res: Result, kind: str, ppy: float, costs: Costs) -> Result:
    r = res.returns
    sc = scale_series(r, kind, ppy)
    gross = res.weights.abs().sum(axis=1).reindex(r.index).fillna(0.0) if res.weights is not None else 1.0
    extra = sc.diff().abs().fillna(0.0) * gross
    out = r * sc - extra * costs.per_turnover
    to = res.turnover.reindex(r.index).fillna(0.0) * sc + extra
    w = res.weights.mul(sc.reindex(res.weights.index).fillna(1.0), axis=0) if res.weights is not None else None
    return Result(out, out, w, to, meta={**res.meta, "overlay": kind})
