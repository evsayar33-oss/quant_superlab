"""H054 core rule (copy of quant_lab lab/core.py dual_trend_vt + apply_band). Do NOT change.
A test (tests/test_bot.py) compares this file with a fixture made by quant_lab."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

PARAMS = {"sma_days": 200, "horizons_days": [30, 90, 180], "target": 0.40, "lookback_days": 30}
BAND = 0.10


def bars(days: float, ppy: float) -> int:
    return max(2, int(round(days * ppy / 365.0)))


def exposure(close: pd.Series, ppy: float, prm: dict = PARAMS) -> pd.Series:
    """Target exposure in [0, 1] at each closed bar: long only above SMA200 and with >= 1 positive horizon,
    size = min(1, target / realised vol of the last 30 days)."""
    r = close.pct_change(fill_method=None)
    n = bars(prm["sma_days"], ppy)
    up = (close > close.rolling(n, min_periods=n).mean()).astype(float)
    ts = sum((close / close.shift(bars(h, ppy)) - 1 > 0).astype(float) for h in prm["horizons_days"]) / len(prm["horizons_days"])
    look = bars(prm["lookback_days"], ppy)
    vol = r.rolling(look, min_periods=look // 2).std() * math.sqrt(ppy)
    vt = (prm["target"] / vol).clip(upper=1.0).fillna(0.0)
    e = up * (ts > 0).astype(float) * vt
    return e.where(close.notna()).fillna(0.0).clip(0, 1)


def apply_band(e: pd.Series, band: float = BAND) -> pd.Series:
    v = e.to_numpy()
    out = np.empty_like(v)
    cur = 0.0
    for i, t in enumerate(v):
        if abs(t - cur) > band or (t == 0.0 and cur != 0.0):
            cur = t
        out[i] = cur
    return pd.Series(out, e.index)
