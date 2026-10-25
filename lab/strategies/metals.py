"""Metal-specific drivers (gold, silver, copper, PGMs).

Drivers (all free, all aligned point-in-time):
  US dollar (DX-Y.NYB)          weak dollar -> supportive for metals
  real yields (TIP / IEF ratio) TIPS outperforming nominal Treasuries = real yields falling -> gold up
  gold/silver ratio (GC=F/SI=F) extreme ratio tends to mean-revert (relative value)
  copper/gold ratio (HG=F/GC=F) rising = growth / risk-on -> industrial metals over gold
  CFTC COT positioning          crowded speculator positioning (contrarian) / commercial hedging
  calendar seasonality          each asset's own average return in that calendar month (past years only)
Strategies raise NoData when a driver is missing, so a result is never faked.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.engine import rebalance
from lab.strategies import strategy
from lab.strategies.fundamental_factors import NoData

GOLD = {"GC=F", "GLD", "IAU", "GDX", "GDXJ", "XAUUSD=X"}
SILVER = {"SI=F", "SLV", "SIL", "SILJ"}
INDUSTRIAL = {"HG=F", "CPER", "COPX", "PL=F", "PPLT", "PA=F", "PALL"}


def _ew(p, mask_cols=None) -> pd.DataFrame:
    w = p.c.notna().astype(float)
    if mask_cols is not None:
        w = w[[c for c in w.columns]] * pd.Series({c: float(c in mask_cols) for c in w.columns})
    s = w.sum(axis=1).replace(0, np.nan)
    return w.div(s, axis=0).fillna(0.0)


def _macro(p, key):
    s = p.macro.get(key) if p.macro else None
    if s is None or s.notna().mean() < 0.3:
        raise NoData(f"macro series {key} unavailable")
    return s.ffill()


def _gate(w: pd.DataFrame, on: pd.Series) -> pd.DataFrame:
    return w.mul(on.reindex(w.index).fillna(False).astype(float), axis=0)


@strategy("dxy_metal_switch", grid={"n": [50, 100, 200]}, defaults={"n": 100},
          source="Dollar-metals inverse relationship (Capie, Mills & Wood 2005)",
          kind="time_series", needs="panel")
def dxy_metal_switch(p, n):
    dxy = _macro(p, "DX-Y.NYB")
    return _gate(_ew(p), dxy < dxy.rolling(n, min_periods=n // 2).mean())


@strategy("real_yield_switch", grid={"n": [50, 100, 200]}, defaults={"n": 100},
          source="Gold vs real interest rates (Erb & Harvey 2013, The Golden Dilemma)",
          kind="time_series", needs="panel")
def real_yield_switch(p, n):
    ratio = _macro(p, "TIP") / _macro(p, "IEF")
    return _gate(_ew(p), ratio > ratio.rolling(n, min_periods=n // 2).mean())


@strategy("gold_silver_ratio", grid={"z_n": [126, 252, 504], "entry": [1.0, 1.5, 2.0], "neutral": ["both", "flat"]},
          defaults={"z_n": 252, "entry": 1.5, "neutral": "both"},
          source="Gold/silver ratio mean reversion (relative value)", kind="time_series", needs="panel")
def gold_silver_ratio(p, z_n, entry, neutral):
    r = np.log(_macro(p, "GC=F") / _macro(p, "SI=F"))
    z = (r - r.rolling(z_n, min_periods=z_n // 2).mean()) / r.rolling(z_n, min_periods=z_n // 2).std()
    g = [c for c in p.columns if c in GOLD]
    s = [c for c in p.columns if c in SILVER]
    if not g or not s:
        raise NoData("universe needs both gold and silver assets")
    wg, ws, wb = _ew(p, set(g)), _ew(p, set(s)), _ew(p, set(g) | set(s))
    hi, lo = (z > entry).astype(float), (z < -entry).astype(float)
    mid = 1 - hi - lo
    base = wb if neutral == "both" else wb * 0
    return ws.mul(hi, axis=0) + wg.mul(lo, axis=0) + base.mul(mid, axis=0)


@strategy("copper_gold_rotation", grid={"n": [50, 100, 200]}, defaults={"n": 100},
          source="Copper/gold ratio as growth signal (risk-on industrial vs safe-haven gold)",
          kind="time_series", needs="panel")
def copper_gold_rotation(p, n):
    r = _macro(p, "HG=F") / _macro(p, "GC=F")
    risk_on = r > r.rolling(n, min_periods=n // 2).mean()
    ind = [c for c in p.columns if c in INDUSTRIAL | SILVER]
    gld = [c for c in p.columns if c in GOLD]
    if not ind or not gld:
        raise NoData("universe needs industrial and gold assets")
    wi, wg = _ew(p, set(ind)), _ew(p, set(gld))
    on = risk_on.reindex(p.index).fillna(False).astype(float)
    return wi.mul(on, axis=0) + wg.mul(1 - on, axis=0)


def _cot(p, key="cot_spec_net"):
    x = p.extra.get(key) if p.extra else None
    if x is None or x.notna().mean().mean() < 0.3:
        raise NoData("COT positioning unavailable for this universe")
    return x.reindex(columns=p.columns)


@strategy("cot_contrarian", grid={"look": [156, 260, 520], "thr": [1.0, 1.5, 2.0]},
          defaults={"look": 260, "thr": 1.5},
          source="Speculator positioning extremes are contrarian (Wang 2003; Sanders, Boris & Manfredo 2004)",
          kind="time_series", needs="panel")
def cot_contrarian(p, look, thr):
    x = _cot(p)
    z = (x - x.rolling(look, min_periods=look // 2).mean()) / x.rolling(look, min_periods=look // 2).std()
    state = pd.DataFrame(np.nan, index=x.index, columns=x.columns)
    state[z < -thr] = 1.0
    state[z > 0] = 0.0
    on = state.ffill().fillna(0.0)
    return on.div(len(x.columns))


@strategy("cot_commercial_follow", grid={"look": [156, 260], "thr": [0.5, 1.0]},
          defaults={"look": 260, "thr": 1.0},
          source="Commercial hedgers' positioning leads prices (Bessembinder & Chan 1992)",
          kind="time_series", needs="panel")
def cot_commercial_follow(p, look, thr):
    x = _cot(p, "cot_comm_net")
    z = (x - x.rolling(look, min_periods=look // 2).mean()) / x.rolling(look, min_periods=look // 2).std()
    on = (z > thr).astype(float).where(z.notna(), 0.0)
    return on.div(len(x.columns))


@strategy("ts_seasonality", grid={"years": [5, 10, 15], "thr": [0.0, 0.005]},
          defaults={"years": 10, "thr": 0.0},
          source="Calendar seasonality of commodities (Sorensen 2002; Heston & Sadka 2008)",
          kind="time_series")
def ts_seasonality(c, years, thr):
    m = c.resample("ME").last().pct_change(fill_method=None)
    avg = sum(m.shift(12 * k) for k in range(1, years + 1)) / years       # same month, past years only
    nxt = avg.shift(-1).iloc[:-1]                                          # decided at end of the prior month
    nxt.index = nxt.index.to_period("M")
    d = pd.DataFrame(nxt.reindex(c.index.to_period("M")).values, index=c.index, columns=c.columns)
    on = (d > thr).astype(float).where(d.notna(), 0.0)
    return rebalance(on.div(len(c.columns)), "ME")
