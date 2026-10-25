"""Market regime per coin: TREND_UP, TREND_DOWN, RANGE (yatay) or VOLATILE (volatil).

Rule-based, closed bars only (bar t uses data up to the close of t), with hysteresis.
Rules (config/arena.yaml `regime`, written before any result was seen):
  1. VOLATILE  if realized volatility is in the top (1 - vol_hi_pct) of its PAST year
  2. TREND     if ADX >= adx_trend AND Kaufman efficiency ratio >= er_trend
               direction: close above its SMA -> TREND_UP, below -> TREND_DOWN
  3. RANGE     otherwise
  A new regime is used only after it held for `confirm_bars` consecutive bars (fewer false flips).
Sources: Wilder (1978) ADX; Kaufman (1995) efficiency ratio; volatility regimes as in
Ang & Bekaert (2002) - here in a transparent rule form instead of a fitted HMM.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import indicators as I
from lab.panel import Panel

RANGE, TREND_UP, TREND_DOWN, VOLATILE = 0, 1, 2, 3
UNKNOWN = -1
NAMES = {RANGE: "range", TREND_UP: "trend_up", TREND_DOWN: "trend_down", VOLATILE: "volatile", UNKNOWN: "unknown"}
TR = {RANGE: "Yatay", TREND_UP: "Trend ↑", TREND_DOWN: "Trend ↓", VOLATILE: "Volatil", UNKNOWN: "Belirsiz"}
CODES = (RANGE, TREND_UP, TREND_DOWN, VOLATILE)


def bars(days: float, ppy: float) -> int:
    return max(2, int(round(days * ppy / 365.0)))


def efficiency_ratio(c: pd.DataFrame, n: int) -> pd.DataFrame:
    move = (c - c.shift(n)).abs()
    path = c.diff().abs().rolling(n, min_periods=n).sum()
    return move / path.replace(0, np.nan)


def raw_regime(p: Panel, cfg: dict) -> pd.DataFrame:
    ppy = p.ppy
    c = p.c
    _, _, adx = I.dmi(p.h, p.l, c, int(cfg.get("adx_n", 14)))
    er = efficiency_ratio(c, bars(cfg.get("er_days", 5), ppy))
    rv = c.pct_change(fill_method=None).rolling(bars(cfg.get("vol_days", 5), ppy)).std()
    w = bars(cfg.get("vol_rank_days", 365), ppy)
    vrank = rv.rolling(w, min_periods=w // 2).rank(pct=True)
    ma = I.sma(c, bars(cfg.get("trend_ma_days", 17), ppy))
    trend = (adx >= cfg.get("adx_trend", 25)) & (er >= cfg.get("er_trend", 0.30))
    out = np.where(vrank >= cfg.get("vol_hi_pct", 0.80), VOLATILE,
                   np.where(trend, np.where(c > ma, TREND_UP, TREND_DOWN), RANGE))
    known = vrank.notna() & adx.notna() & er.notna() & ma.notna()
    return pd.DataFrame(np.where(known, out, UNKNOWN), index=c.index, columns=c.columns).astype(int)


def hysteresis(raw: pd.DataFrame, confirm: int) -> pd.DataFrame:
    if confirm <= 1:
        return raw
    a = raw.to_numpy()
    out = a.copy()
    T, N = a.shape
    cur = a[0].copy()
    cand = a[0].copy()
    run = np.ones(N, int)
    for i in range(1, T):
        x = a[i]
        same = x == cand
        run = np.where(same, run + 1, 1)
        cand = np.where(same, cand, x)
        switch = (cand != cur) & ((run >= confirm) | (cur == UNKNOWN))
        cur = np.where(switch, cand, cur)
        out[i] = cur
    return pd.DataFrame(out, index=raw.index, columns=raw.columns)


def classify(p: Panel, cfg: dict) -> pd.DataFrame:
    """Regime code per bar and coin (int frame). Uses only data up to each bar's close."""
    return hysteresis(raw_regime(p, cfg), int(cfg.get("confirm_bars", 3)))


def summary(reg: pd.DataFrame) -> dict:
    """Share of time in each regime and the current regime, per coin."""
    out = {}
    for col in reg.columns:
        s = reg[col]
        s = s[s != UNKNOWN]
        if not len(s):
            continue
        out[col] = {"now": NAMES[int(s.iloc[-1])], "now_tr": TR[int(s.iloc[-1])],
                    "since": str(s.index[(s != s.iloc[-1]).to_numpy().nonzero()[0][-1] + 1]
                                 if (s != s.iloc[-1]).any() else s.index[0]),
                    "share": {NAMES[k]: round(float((s == k).mean()), 3) for k in CODES}}
    return out
