"""Entry / exit rule catalog for the trade engine.

A rule is fn(panel, **params) -> Signals with four boolean frames:
  entry_long, exit_long, entry_short, exit_short   (signal at close t -> trade at open t+1)
`entry_short`/`exit_short` may be None (long-only idea).

Every rule has a parameter GRID with indicator-setting variants (e.g. RSI 7/9/14/21/28).
The scanner sweeps the whole grid and the Deflated Sharpe Ratio pays for every variant.

FILTERS restrict entries (trend, ADX, market regime, volatility, volume, fundamentals).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from lab import indicators as I
from lab.panel import Panel


@dataclass
class Signals:
    entry_long: pd.DataFrame
    exit_long: pd.DataFrame
    entry_short: pd.DataFrame | None = None
    exit_short: pd.DataFrame | None = None


@dataclass
class Rule:
    name: str
    family: str
    fn: Callable[..., Signals]
    grid: dict = field(default_factory=dict)
    source: str = ""


RULES: dict[str, Rule] = {}


def rule(name: str, family: str, grid: dict, source: str = ""):
    def deco(fn):
        RULES[name] = Rule(name, family, fn, grid, source)
        return fn
    return deco


def _b(x: pd.DataFrame) -> pd.DataFrame:
    return x.fillna(False).astype(bool)


def _osc(osc: pd.DataFrame, lo: float, hi: float, exit_lo: float, exit_hi: float) -> Signals:
    """Mean-reversion oscillator: long when it crosses back up through `lo`."""
    return Signals(_b(I.cross_up(osc, lo)), _b(osc > exit_lo),
                   _b(I.cross_down(osc, hi)), _b(osc < exit_hi))


def _cross(fast: pd.DataFrame, slow: pd.DataFrame) -> Signals:
    up, dn = _b(I.cross_up(fast, slow)), _b(I.cross_down(fast, slow))
    return Signals(up, dn, dn, up)


def _state(direction: pd.DataFrame) -> Signals:
    """Trend-state indicator (+1/-1): enter on flip, exit on opposite flip."""
    d = direction
    up = _b((d > 0) & (d.shift(1) <= 0))
    dn = _b((d < 0) & (d.shift(1) >= 0))
    return Signals(up, dn, dn, up)


# =================================================================== MOMENTUM OSCILLATORS (mean reversion)
@rule("rsi_reversal", "oscillator",
      {"n": [2, 3, 5, 7, 9, 14, 21, 28], "lo": [10, 20, 25, 30, 35], "exit": [50, 60, 70]},
      "Wilder (1978) RSI; Connors (2009)")
def rsi_reversal(p: Panel, n, lo, exit):
    r = I.rsi(p.c, n)
    return _osc(r, lo, 100 - lo, exit, 100 - exit)


@rule("rsi_midline", "momentum", {"n": [9, 14, 21, 28], "level": [50, 55, 60]}, "RSI regime shift")
def rsi_midline(p: Panel, n, level):
    r = I.rsi(p.c, n)
    return Signals(_b(I.cross_up(r, level)), _b(I.cross_down(r, 50)),
                   _b(I.cross_down(r, 100 - level)), _b(I.cross_up(r, 50)))


@rule("stoch_reversal", "oscillator",
      {"k": [5, 9, 14, 21], "d": [3, 5], "smooth": [1, 3], "lo": [10, 20, 25]}, "Lane stochastic")
def stoch_reversal(p: Panel, k, d, smooth, lo):
    kk, dd = I.stoch(p.h, p.l, p.c, k, d, smooth)
    el = _b(I.cross_up(kk, dd) & (dd < lo + 10))
    es = _b(I.cross_down(kk, dd) & (dd > 90 - lo))
    return Signals(el, _b(kk > 80), es, _b(kk < 20))


@rule("stochrsi_reversal", "oscillator", {"n": [9, 14, 21], "lo": [5, 10, 20]}, "Chande & Kroll StochRSI")
def stochrsi_reversal(p: Panel, n, lo):
    k, _ = I.stoch_rsi(p.c, n)
    return _osc(k, lo, 100 - lo, 80, 20)


@rule("williams_reversal", "oscillator", {"n": [7, 10, 14, 21], "lo": [-95, -90, -80]}, "Williams %R")
def williams_reversal(p: Panel, n, lo):
    w = I.williams_r(p.h, p.l, p.c, n)
    return _osc(w, lo, -100 - lo, -30, -70)


@rule("cci_reversal", "oscillator", {"n": [14, 20, 40], "lo": [-200, -150, -100]}, "Lambert (1980) CCI")
def cci_reversal(p: Panel, n, lo):
    x = I.cci(p.h, p.l, p.c, n)
    return _osc(x, lo, -lo, 0, 0)


@rule("cci_breakout", "momentum", {"n": [14, 20, 40], "level": [100, 150]}, "CCI trend entry")
def cci_breakout(p: Panel, n, level):
    x = I.cci(p.h, p.l, p.c, n)
    return Signals(_b(I.cross_up(x, level)), _b(x < 0), _b(I.cross_down(x, -level)), _b(x > 0))


@rule("mfi_reversal", "oscillator", {"n": [10, 14, 21], "lo": [10, 20, 30]}, "Quong & Soudack MFI")
def mfi_reversal(p: Panel, n, lo):
    return _osc(I.mfi(p.h, p.l, p.c, p.v, n), lo, 100 - lo, 60, 40)


@rule("ultimate_reversal", "oscillator", {"a": [5, 7], "lo": [25, 30, 35]}, "Williams Ultimate Oscillator")
def ultimate_reversal(p: Panel, a, lo):
    return _osc(I.ultimate(p.h, p.l, p.c, a, 2 * a, 4 * a), lo, 100 - lo, 60, 40)


@rule("wavetrend_reversal", "oscillator",
      {"n1": [9, 10, 12], "n2": [18, 21, 26], "lo": [-60, -53, -40]}, "LazyBear WaveTrend (ATVS)")
def wavetrend_reversal(p: Panel, n1, n2, lo):
    w1, w2 = I.wavetrend(p.h, p.l, p.c, n1, n2)
    el = _b(I.cross_up(w1, w2) & (w1 < lo))
    es = _b(I.cross_down(w1, w2) & (w1 > -lo))
    return Signals(el, _b(I.cross_down(w1, w2) & (w1 > 0)), es, _b(I.cross_up(w1, w2) & (w1 < 0)))


@rule("zscore_reversion", "mean_reversion", {"n": [10, 20, 50], "z": [1.5, 2.0, 2.5]}, "Statistical mean reversion")
def zscore_reversion(p: Panel, n, z):
    x = I.zscore(p.c, n)
    return Signals(_b(I.cross_up(x, -z)), _b(x > 0), _b(I.cross_down(x, z)), _b(x < 0))


@rule("bollinger_reversion", "mean_reversion", {"n": [10, 20, 30], "k": [1.5, 2.0, 2.5, 3.0]}, "Bollinger (2001)")
def bollinger_reversion(p: Panel, n, k):
    lo, mid, up = I.bollinger(p.c, n, k)
    return Signals(_b(I.cross_up(p.c, lo)), _b(p.c > mid), _b(I.cross_down(p.c, up)), _b(p.c < mid))


@rule("ibs_reversion", "mean_reversion", {"lo": [0.1, 0.2, 0.3], "hi": [0.7, 0.8]}, "Internal Bar Strength")
def ibs_reversion(p: Panel, lo, hi):
    x = I.ibs(p.h, p.l, p.c)
    return Signals(_b(x < lo), _b(x > hi), _b(x > 1 - lo), _b(x < 1 - hi))


@rule("down_days", "mean_reversion", {"n": [3, 4, 5], "hold_exit": [1, 3]}, "Consecutive down closes")
def down_days(p: Panel, n, hold_exit):
    e = _b(I.consecutive(p.c, n, up=False))
    x = _b(I.consecutive(p.c, hold_exit, up=True))
    return Signals(e, x, _b(I.consecutive(p.c, n, up=True)), _b(I.consecutive(p.c, hold_exit, up=False)))


# =================================================================== TREND / MOMENTUM
@rule("ma_cross", "trend",
      {"kind": ["sma", "ema", "hma", "dema", "tema", "kama"],
       "pair": [(5, 20), (10, 30), (10, 50), (20, 50), (20, 100), (50, 150), (50, 200)]},
      "Moving-average crossover")
def ma_cross(p: Panel, kind, pair):
    f, s = pair
    return _cross(I.ma(p.c, f, kind), I.ma(p.c, s, kind))


@rule("price_ma", "trend", {"kind": ["sma", "ema", "hma", "kama"], "n": [20, 50, 100, 150, 200]},
      "Faber (2007) price vs moving average")
def price_ma(p: Panel, kind, n):
    return _cross(p.c, I.ma(p.c, n, kind))


@rule("triple_ma", "trend", {"set": [(5, 20, 50), (10, 50, 200), (20, 50, 100)], "kind": ["sma", "ema"]},
      "Triple MA alignment")
def triple_ma(p: Panel, set, kind):
    a, b, c = (I.ma(p.c, n, kind) for n in set)
    bull = (a > b) & (b > c); bear = (a < b) & (b < c)
    return Signals(_b(bull & ~bull.shift(1, fill_value=False)), _b(a < b),
                   _b(bear & ~bear.shift(1, fill_value=False)), _b(a > b))


@rule("macd_cross", "trend",
      {"cfg": [(12, 26, 9), (8, 21, 5), (5, 35, 5), (19, 39, 9), (6, 13, 4)], "zero_filter": [False, True]},
      "Appel MACD")
def macd_cross(p: Panel, cfg, zero_filter):
    line, sig, _ = I.macd(p.c, *cfg)
    s = _cross(line, sig)
    if zero_filter:
        s.entry_long = s.entry_long & (line < 0)
        s.entry_short = s.entry_short & (line > 0)
    return s


@rule("macd_zero", "trend", {"cfg": [(12, 26, 9), (8, 21, 5), (5, 35, 5)]}, "MACD zero-line cross")
def macd_zero(p: Panel, cfg):
    line, _, _ = I.macd(p.c, *cfg)
    return _cross(line, I.level(line, 0))


@rule("ppo_cross", "trend", {"cfg": [(12, 26, 9), (10, 30, 9)]}, "Percentage Price Oscillator")
def ppo_cross(p: Panel, cfg):
    line, sig, _ = I.ppo(p.c, *cfg)
    return _cross(line, sig)


@rule("trix_cross", "trend", {"n": [9, 12, 15, 21], "signal": [7, 9]}, "Hutson TRIX")
def trix_cross(p: Panel, n, signal):
    line, sig = I.trix(p.c, n, signal)
    return _cross(line, sig)


@rule("tsi_cross", "trend", {"cfg": [(25, 13, 7), (13, 7, 7), (40, 20, 10)]}, "Blau True Strength Index")
def tsi_cross(p: Panel, cfg):
    line, sig = I.tsi(p.c, *cfg)
    return _cross(line, sig)


@rule("roc_breakout", "momentum", {"n": [10, 21, 63, 126, 252], "th": [0, 5, 10]}, "Rate-of-change momentum")
def roc_breakout(p: Panel, n, th):
    r = I.roc(p.c, n)
    return Signals(_b(I.cross_up(r, th)), _b(r < 0), _b(I.cross_down(r, -th)), _b(r > 0))


@rule("awesome_zero", "momentum", {"fast": [5], "slow": [34, 50]}, "Bill Williams Awesome Oscillator")
def awesome_zero(p: Panel, fast, slow):
    a = I.awesome(p.h, p.l, fast, slow)
    return _cross(a, I.level(a, 0))


@rule("coppock_turn", "momentum", {"scale": [5, 21]}, "Coppock curve 14/11/10 (weekly or monthly bars)")
def coppock_turn(p: Panel, scale):
    x = I.coppock(p.c, 14 * scale, 11 * scale, 10 * scale)
    up = _b((x.diff() > 0) & (x.diff().shift(1) <= 0) & (x < 0))
    return Signals(up, _b((x.diff() < 0) & (x > 0)), None, None)


@rule("adx_trend", "trend", {"n": [10, 14, 20], "th": [20, 25, 30]}, "Wilder DMI/ADX")
def adx_trend(p: Panel, n, th):
    pdi, mdi, adx = I.dmi(p.h, p.l, p.c, n)
    strong = adx > th
    return Signals(_b(I.cross_up(pdi, mdi) & strong), _b(I.cross_down(pdi, mdi)),
                   _b(I.cross_down(pdi, mdi) & strong), _b(I.cross_up(pdi, mdi)))


@rule("aroon_cross", "trend", {"n": [14, 25, 50]}, "Chande Aroon")
def aroon_cross(p: Panel, n):
    up, dn = I.aroon(p.h, p.l, n)
    return _cross(up, dn)


@rule("vortex_cross", "trend", {"n": [14, 21, 28]}, "Botes & Siepman Vortex")
def vortex_cross(p: Panel, n):
    vp, vm = I.vortex(p.h, p.l, p.c, n)
    return _cross(vp, vm)


@rule("supertrend_flip", "trend",
      {"cfg": [(7, 2.0), (10, 2.0), (10, 3.0), (14, 3.0), (20, 4.0)]}, "Supertrend (ATR bands)")
def supertrend_flip(p: Panel, cfg):
    return _state(I.supertrend(p.h, p.l, p.c, *cfg))


@rule("psar_flip", "trend", {"cfg": [(0.01, 0.1), (0.02, 0.2), (0.03, 0.3)]}, "Wilder Parabolic SAR")
def psar_flip(p: Panel, cfg):
    return _state(I.psar(p.h, p.l, *cfg))


@rule("ichimoku_cloud", "trend", {"cfg": [(9, 26, 52), (7, 22, 44), (20, 60, 120)]}, "Ichimoku Kinko Hyo")
def ichimoku_cloud(p: Panel, cfg):
    t, k, a, b = I.ichimoku(p.h, p.l, p.c, *cfg)
    top, bot = np.maximum(a, b), np.minimum(a, b)
    bull = (p.c > top) & (t > k); bear = (p.c < bot) & (t < k)
    return Signals(_b(bull & ~bull.shift(1, fill_value=False)), _b(p.c < k),
                   _b(bear & ~bear.shift(1, fill_value=False)), _b(p.c > k))


@rule("heikin_ashi", "trend", {"confirm": [1, 2, 3]}, "Heikin-Ashi colour change")
def heikin_ashi(p: Panel, confirm):
    d = I.heikin_ashi_dir(p.o, p.h, p.l, p.c)
    up = (d > 0).astype(int).rolling(confirm).sum() == confirm
    dn = (d < 0).astype(int).rolling(confirm).sum() == confirm
    return Signals(_b(up & ~up.shift(1, fill_value=False)), _b(d < 0),
                   _b(dn & ~dn.shift(1, fill_value=False)), _b(d > 0))


@rule("linreg_slope", "trend", {"n": [20, 50, 100], "th": [0.0005, 0.001]}, "Regression slope")
def linreg_slope(p: Panel, n, th):
    s = I.linreg_slope(p.c, n)
    return Signals(_b(I.cross_up(s, th)), _b(s < 0), _b(I.cross_down(s, -th)), _b(s > 0))


@rule("elder_impulse", "trend", {"ema_n": [13, 21], "macd_cfg": [(12, 26, 9)]}, "Elder Impulse System")
def elder_impulse(p: Panel, ema_n, macd_cfg):
    e = I.ema(p.c, ema_n); _, _, hist = I.macd(p.c, *macd_cfg)
    green = (e.diff() > 0) & (hist.diff() > 0); red = (e.diff() < 0) & (hist.diff() < 0)
    return Signals(_b(green & ~green.shift(1, fill_value=False)), _b(red),
                   _b(red & ~red.shift(1, fill_value=False)), _b(green))


# =================================================================== BREAKOUT / VOLATILITY
@rule("donchian_breakout", "breakout", {"entry": [20, 40, 55, 100], "exit": [10, 20]}, "Turtle / Donchian")
def donchian_breakout(p: Panel, entry, exit):
    lo_e, hi_e = I.donchian(p.h, p.l, entry)
    lo_x, hi_x = I.donchian(p.h, p.l, exit)
    return Signals(_b(p.c > hi_e.shift(1)), _b(p.c < lo_x.shift(1)),
                   _b(p.c < lo_e.shift(1)), _b(p.c > hi_x.shift(1)))


@rule("bollinger_breakout", "breakout", {"n": [20, 50], "k": [1.5, 2.0, 2.5]}, "Bollinger band breakout")
def bollinger_breakout(p: Panel, n, k):
    lo, mid, up = I.bollinger(p.c, n, k)
    return Signals(_b(I.cross_up(p.c, up)), _b(p.c < mid), _b(I.cross_down(p.c, lo)), _b(p.c > mid))


@rule("bb_squeeze", "breakout", {"n": [20], "q": [0.1, 0.2], "look": [126, 252]}, "Bollinger squeeze release")
def bb_squeeze(p: Panel, n, q, look):
    w = I.bb_width(p.c, n)
    squeezed = w <= w.rolling(look, min_periods=look // 2).quantile(q)
    lo, mid, up = I.bollinger(p.c, n)
    was = squeezed.shift(1, fill_value=False)
    return Signals(_b(was & (p.c > up)), _b(p.c < mid), _b(was & (p.c < lo)), _b(p.c > mid))


@rule("keltner_breakout", "breakout", {"n": [20, 50], "k": [1.5, 2.0, 2.5]}, "Keltner channel")
def keltner_breakout(p: Panel, n, k):
    lo, mid, up = I.keltner(p.h, p.l, p.c, n, k)
    return Signals(_b(I.cross_up(p.c, up)), _b(p.c < mid), _b(I.cross_down(p.c, lo)), _b(p.c > mid))


@rule("atr_breakout", "breakout", {"n": [10, 20], "k": [1.0, 1.5, 2.0]}, "Volatility (ATR) breakout")
def atr_breakout(p: Panel, n, k):
    a = I.atr(p.h, p.l, p.c, n)
    up = p.c > p.c.shift(1) + k * a.shift(1)
    dn = p.c < p.c.shift(1) - k * a.shift(1)
    m = I.sma(p.c, n)
    return Signals(_b(up), _b(p.c < m), _b(dn), _b(p.c > m))


@rule("nr7_breakout", "breakout", {"n": [4, 7]}, "Crabel narrow-range breakout")
def nr7_breakout(p: Panel, n):
    setup = I.nr(p.h, p.l, n).shift(1, fill_value=False)
    return Signals(_b(setup & (p.c > p.h.shift(1))), _b(p.c < p.l.shift(1)),
                   _b(setup & (p.c < p.l.shift(1))), _b(p.c > p.h.shift(1)))


@rule("high_52w_break", "breakout", {"n": [126, 252], "exit_ma": [50, 100]}, "George & Hwang 52-week high")
def high_52w_break(p: Panel, n, exit_ma):
    hi = p.h.rolling(n, min_periods=n).max().shift(1)
    m = I.sma(p.c, exit_ma)
    return Signals(_b(p.c > hi), _b(p.c < m), None, None)


@rule("volume_breakout", "breakout", {"n": [20, 50], "rv": [1.5, 2.0, 3.0]}, "Price breakout on volume surge")
def volume_breakout(p: Panel, n, rv):
    hi = p.h.rolling(n, min_periods=n).max().shift(1)
    lo = p.l.rolling(n, min_periods=n).min().shift(1)
    surge = I.rel_volume(p.v, n) > rv
    m = I.sma(p.c, n)
    return Signals(_b((p.c > hi) & surge), _b(p.c < m), _b((p.c < lo) & surge), _b(p.c > m))


@rule("gap_fade", "mean_reversion", {"g": [0.02, 0.03, 0.05]}, "Opening gap fade (close-based)")
def gap_fade(p: Panel, g):
    gp = I.gap(p.o, p.c)
    return Signals(_b(gp < -g), _b(p.c > p.c.shift(1)), _b(gp > g), _b(p.c < p.c.shift(1)))


# =================================================================== VOLUME
@rule("obv_trend", "volume", {"n": [20, 50], "price_n": [20, 50]}, "Granville OBV")
def obv_trend(p: Panel, n, price_n):
    o = I.obv(p.c, p.v)
    up = (o > I.ema(o, n)) & (p.c > I.ema(p.c, price_n))
    dn = (o < I.ema(o, n)) & (p.c < I.ema(p.c, price_n))
    return Signals(_b(up & ~up.shift(1, fill_value=False)), _b(o < I.ema(o, n)),
                   _b(dn & ~dn.shift(1, fill_value=False)), _b(o > I.ema(o, n)))


@rule("cmf_flow", "volume", {"n": [10, 20, 40], "th": [0.05, 0.1, 0.2]}, "Chaikin Money Flow")
def cmf_flow(p: Panel, n, th):
    x = I.cmf(p.h, p.l, p.c, p.v, n)
    return Signals(_b(I.cross_up(x, th)), _b(x < 0), _b(I.cross_down(x, -th)), _b(x > 0))


@rule("chaikin_osc", "volume", {"cfg": [(3, 10), (5, 20)]}, "Chaikin oscillator")
def chaikin_osc(p: Panel, cfg):
    x = I.chaikin_osc(p.h, p.l, p.c, p.v, *cfg)
    return _cross(x, I.level(x, 0))


@rule("vwap_cross", "volume", {"n": [10, 20, 50]}, "Rolling VWAP cross")
def vwap_cross(p: Panel, n):
    return _cross(p.c, I.rolling_vwap(p.h, p.l, p.c, p.v, n))


@rule("force_index", "volume", {"n": [2, 13]}, "Elder Force Index")
def force_index(p: Panel, n):
    f = I.force_index(p.c, p.v, n)
    trend = p.c > I.ema(p.c, 50)
    return Signals(_b((f < 0) & trend & (f.shift(1) >= 0)), _b(f > 0), None, None)


# =================================================================== CANDLESTICK
@rule("engulfing", "candle", {"trend_n": [0, 50, 200]}, "Nison candlestick engulfing")
def engulfing(p: Panel, trend_n):
    bull, bear = I.bullish_engulfing(p.o, p.c), I.bearish_engulfing(p.o, p.c)
    if trend_n:
        m = I.sma(p.c, trend_n)
        bull, bear = bull & (p.c > m), bear & (p.c < m)
    return Signals(_b(bull), _b(I.bearish_engulfing(p.o, p.c)), _b(bear), _b(I.bullish_engulfing(p.o, p.c)))


@rule("hammer_star", "candle", {"lookback_low": [10, 20]}, "Hammer at a local low / shooting star at a high")
def hammer_star(p: Panel, lookback_low):
    at_low = p.l <= p.l.rolling(lookback_low).min()
    at_high = p.h >= p.h.rolling(lookback_low).max()
    m = I.sma(p.c, lookback_low)
    return Signals(_b(I.hammer(p.o, p.h, p.l, p.c) & at_low), _b(p.c > m),
                   _b(I.shooting_star(p.o, p.h, p.l, p.c) & at_high), _b(p.c < m))


@rule("inside_bar", "candle", {"trend_n": [50, 200]}, "Inside-bar breakout with trend")
def inside_bar(p: Panel, trend_n):
    ib = I.inside_bar(p.h, p.l).shift(1, fill_value=False)
    m = I.sma(p.c, trend_n)
    return Signals(_b(ib & (p.c > p.h.shift(1)) & (p.c > m)), _b(p.c < m),
                   _b(ib & (p.c < p.l.shift(1)) & (p.c < m)), _b(p.c > m))


# =================================================================== REGIME-ADAPTIVE
@rule("hurst_switch", "adaptive", {"n": [100, 200], "fast": [20], "rsi_n": [2, 5]},
      "Trend-follow when persistent, mean-revert when anti-persistent")
def hurst_switch(p: Panel, n, fast, rsi_n):
    hp = I.hurst_proxy(p.c, n)
    m = I.sma(p.c, fast); r = I.rsi(p.c, rsi_n)
    trend_e = (hp > 0.55) & I.cross_up(p.c, m)
    mr_e = (hp < 0.45) & (r < 10)
    return Signals(_b(trend_e | mr_e), _b(((hp > 0.55) & (p.c < m)) | ((hp <= 0.55) & (r > 70))), None, None)


@rule("chop_switch", "adaptive", {"n": [14], "lo": [38.2], "hi": [61.8]}, "Choppiness-index regime switch")
def chop_switch(p: Panel, n, lo, hi):
    ch = I.choppiness(p.h, p.l, p.c, n)
    lo_, mid, up = I.bollinger(p.c, 20, 2)
    _, hi_d = I.donchian(p.h, p.l, 20)
    trend_e = (ch < lo) & (p.c > hi_d.shift(1))
    range_e = (ch > hi) & I.cross_up(p.c, lo_)
    return Signals(_b(trend_e | range_e), _b(p.c < mid), None, None)


# =================================================================== FILTERS
FILTERS: dict[str, Callable[[Panel], tuple[pd.DataFrame, pd.DataFrame]]] = {}


# ------------------------------------------------------------------ COT positioning (futures "fundamentals")
def _cot_z(p: Panel, key: str, n: int) -> pd.DataFrame | None:
    """Rolling z-score of a CFTC COT series (lab/cot.py makes it public-dated: report + 6 days)."""
    x = (p.extra or {}).get(key)
    if x is None or not isinstance(x, pd.DataFrame):
        return None
    x = x.reindex(index=p.index, columns=p.columns)
    if x.notna().sum().sum() == 0:
        return None
    m, sd = x.rolling(n, min_periods=n // 2).mean(), x.rolling(n, min_periods=n // 2).std()
    return (x - m) / sd.where(sd > 0)


def _none(p: Panel) -> Signals:
    f = pd.DataFrame(False, index=p.index, columns=p.columns)
    return Signals(f, f, f, f)


@rule("cot_extreme", "positioning", {"n": [260, 520, 780], "th": [1.5, 2.0]},
      "Briese (2008) The Commitments of Traders Bible: speculator extremes are contrarian; CFTC COT")
def cot_extreme(p: Panel, n, th):
    z = _cot_z(p, "cot_spec_net", n)
    if z is None:
        return _none(p)
    return Signals(_b(I.cross_up(-z, th)), _b(z > 0), _b(I.cross_up(z, th)), _b(z < 0))


@rule("cot_commercial", "positioning", {"n": [260, 780], "th": [1.0, 1.5]},
      "Briese (2008): commercials (hedgers) net long extreme = bullish; CFTC COT")
def cot_commercial(p: Panel, n, th):
    z = _cot_z(p, "cot_comm_net", n)
    if z is None:
        return _none(p)
    return Signals(_b(I.cross_up(z, th)), _b(z < 0), _b(I.cross_up(-z, th)), _b(z > 0))


# ------------------------------------------------------------------ seasonality / calendar rules (free, no extra data)
# The trading calendar is known in advance, so "is the NEXT bar inside the window?" is not look-ahead:
# the signal at close t asks about bar t+1, the trade fills at open t+1 (same timing as every other rule).
def _cal(p: Panel):
    """(month, weekday, bars_from_month_start, bars_to_month_end) of the NEXT bar, per bar. Daily data only."""
    idx = pd.DatetimeIndex(p.index)
    if len(idx) < 30 or (idx[1:] - idx[:-1]).median() > pd.Timedelta(days=4) or (idx[1:] - idx[:-1]).median() < pd.Timedelta(hours=20):
        return None
    ser = pd.Series(idx, index=idx)
    ym = ser.dt.to_period("M")
    start_rank = ym.groupby(ym).cumcount() + 1                     # 1 = first bar of the month
    end_rank = ym.groupby(ym).cumcount(ascending=False) + 1       # 1 = last bar of the month
    nxt = lambda x: pd.Series(x.shift(-1).values, index=idx)        # value of bar t+1 seen at t
    month = nxt(ser.dt.month.astype(float))
    wd = nxt(ser.dt.weekday.astype(float))
    return month, wd, nxt(start_rank.astype(float)), nxt(end_rank.astype(float))


def _win_signals(p: Panel, inside_next: pd.Series) -> Signals:
    """Long while the next bar is inside the window. entry = window starts, exit = window ends."""
    ins = inside_next.fillna(False).astype(bool)
    prev = ins.shift(1, fill_value=False)
    el = ins & ~prev
    xl = ~ins & prev
    cols = p.columns
    f = lambda sr: pd.DataFrame(np.repeat(sr.values[:, None], len(cols), 1), index=p.index, columns=cols)
    return Signals(_b(f(el)), _b(f(xl)))


@rule("turn_of_month", "seasonality", {"pre": [1, 2, 3], "post": [1, 2, 3, 4]},
      "Ariel (1987) 'A monthly effect in stock returns'; Lakonishok & Smidt (1988): gains cluster around the turn of the month")
def turn_of_month(p: Panel, pre, post):
    c = _cal(p)
    if c is None:
        return _none(p)
    _, _, srank, erank = c
    return _win_signals(p, (erank <= pre) | (srank <= post))


@rule("weekday_long", "seasonality", {"day": [0, 1, 2, 3, 4]},
      "French (1980) 'Stock returns and the weekend effect'; Gibbons & Hess (1981): returns differ by weekday")
def weekday_long(p: Panel, day):
    c = _cal(p)
    if c is None:
        return _none(p)
    return _win_signals(p, c[1] == day)


@rule("halloween", "seasonality", {"start": [10, 11], "end": [3, 4, 5]},
      "Bouman & Jacobsen (2002) 'The Halloween indicator, Sell in May and go away': winter months beat summer")
def halloween(p: Panel, start, end):
    c = _cal(p)
    if c is None:
        return _none(p)
    m = c[0]
    inside = (m >= start) | (m <= end)
    return _win_signals(p, inside)


@rule("funding_extreme", "positioning", {"n": [90, 180, 365], "th": [1.5, 2.0]},
      "Contrarian crowding logic (Briese 2008) applied to perp funding: extreme positive funding = crowded longs. "
      "Funding history: Binance public files (free)")
def funding_extreme(p: Panel, n, th):
    fr = p.extra.get("funding_daily") if p.extra else None
    if fr is None:
        return _none(p)
    m7 = fr.rolling(7, min_periods=4).mean()
    z = (m7 - m7.rolling(n, min_periods=n // 2).mean()) / m7.rolling(n, min_periods=n // 2).std()
    z = z.reindex(index=p.index, columns=p.columns)
    return Signals(_b(I.cross_up(-z, th)), _b(z > 0), _b(I.cross_up(z, th)), _b(z < 0))


def filt(name):
    def deco(fn):
        FILTERS[name] = fn
        return fn
    return deco


def _all(p: Panel, val: bool = True):
    return pd.DataFrame(val, index=p.index, columns=p.columns)


@filt("none")
def f_none(p):
    return _all(p), _all(p)


for _n in (50, 100, 200):
    def _mk(n):
        def f(p):
            m = I.sma(p.c, n)
            return _b(p.c > m), _b(p.c < m)
        return f
    FILTERS[f"trend_sma{_n}"] = _mk(_n)


for _t in (20, 25):
    def _mk_adx(t):
        def f(p):
            _, _, adx = I.dmi(p.h, p.l, p.c, 14)
            s = _b(adx > t)
            return s, s
        return f
    FILTERS[f"adx{_t}"] = _mk_adx(_t)


@filt("regime_bench200")
def f_regime(p):
    """Longs only when the market (benchmark) is above its 200-day SMA; shorts only below."""
    if p.bench is None:
        return _all(p), _all(p)
    up = p.bench > p.bench.rolling(200, min_periods=200).mean()
    L = pd.DataFrame(np.repeat(up.values[:, None], p.c.shape[1], 1), index=p.index, columns=p.columns)
    return _b(L), _b(~L)


@filt("low_vol")
def f_low_vol(p):
    n = I.natr(p.h, p.l, p.c, 20)
    calm = n < n.rolling(252, min_periods=126).median()
    return _b(calm), _b(calm)


@filt("volume_confirm")
def f_vol(p):
    s = _b(I.rel_volume(p.v, 20) > 1.0)
    return s, s


@filt("fund_quality")
def f_quality(p):
    """ROE above the cross-sectional median (needs fundamentals; otherwise no filter)."""
    roe = p.fund.get("roe")
    if roe is None or roe.notna().sum().sum() == 0:
        return _all(p), _all(p)
    med = roe.median(axis=1)
    good = roe.gt(med, axis=0)
    return _b(good), _b(~good)


@filt("fund_value")
def f_value(p):
    ep = p.fund.get("ep")
    if ep is None or ep.notna().sum().sum() == 0:
        return _all(p), _all(p)
    cheap = ep.gt(ep.median(axis=1), axis=0)
    return _b(cheap), _b(~cheap)


def grid_points(grid: dict) -> list[dict]:
    import itertools
    if not grid:
        return [{}]
    keys = list(grid)
    return [dict(zip(keys, v)) for v in itertools.product(*(grid[k] for k in keys))]


def apply_filter(sig: Signals, p: Panel, name: str) -> Signals:
    if name == "none":
        return sig
    fl, fs = FILTERS[name](p)
    return Signals(sig.entry_long & fl, sig.exit_long,
                   None if sig.entry_short is None else sig.entry_short & fs, sig.exit_short)


def n_variants() -> int:
    return sum(len(grid_points(r.grid)) for r in RULES.values())


# ------------------------------------------------------------------ higher-timeframe (multi-timeframe) filters
def _htf_trend(p: Panel, rule: str, n: int):
    """Trend of a HIGHER timeframe built only from completed higher-timeframe bars."""
    hc = p.c.resample(rule).last()
    up = hc > hc.rolling(n, min_periods=n).mean()
    intraday = len(p.index) > 1 and (p.index[1:] - p.index[:-1]).min() < pd.Timedelta(hours=20)
    if intraday:  # a weekly/monthly close is only known after that day ends
        up.index = up.index.normalize() + pd.Timedelta(days=1)
    al = up.astype(float).reindex(up.index.union(p.index)).sort_index().ffill().reindex(p.index)
    return al


for _nm, (_rule, _n) in {"htf_week_sma30": ("W-FRI", 30), "htf_week_sma10": ("W-FRI", 10),
                         "htf_month_sma10": ("ME", 10)}.items():
    def _mk_htf(rule, n):
        def f(p):
            al = _htf_trend(p, rule, n)
            return _b(al == 1), _b(al == 0)
        return f
    FILTERS[_nm] = _mk_htf(_rule, _n)


# ------------------------------------------------------------------ macro regime filters
def _macro_bool(p: Panel, key: str, fn):
    s = p.macro.get(key) if p.macro else None
    if s is None:
        return None
    ok = fn(s)
    return pd.DataFrame(np.repeat(ok.values[:, None], p.c.shape[1], 1), index=p.index, columns=p.columns)


@filt("vix_below_25")
def f_vix(p):
    m = _macro_bool(p, "^VIX", lambda s: s < 25)
    return (_all(p), _all(p)) if m is None else (_b(m), _b(~m))


@filt("vix_spike_buy")
def f_vix_spike(p):
    """Contrarian: allow longs only after fear spikes (VIX > 30)."""
    m = _macro_bool(p, "^VIX", lambda s: s > 30)
    return (_all(p), _all(p)) if m is None else (_b(m), _b(m))


@filt("usdtry_calm")
def f_usdtry(p):
    """BIST: avoid longs while the lira is under acute stress (USDTRY 20-day move > 5%)."""
    m = _macro_bool(p, "USDTRY=X", lambda s: s.pct_change(20, fill_method=None) < 0.05)
    return (_all(p), _all(p)) if m is None else (_b(m), _b(~m))


@filt("curve_normal")
def f_curve(p):
    """Longs only when the US yield curve (10y - 3m) is not inverted."""
    if not p.macro or p.macro.get("^TNX") is None or p.macro.get("^IRX") is None:
        return _all(p), _all(p)
    ok = (p.macro["^TNX"] - p.macro["^IRX"]) >= 0
    m = pd.DataFrame(np.repeat(ok.values[:, None], p.c.shape[1], 1), index=p.index, columns=p.columns)
    return _b(m), _b(~m)


@filt("member_only")
def f_member(p):
    """Survivorship control: entries only while the asset was an index member."""
    if p.member is None:
        return _all(p), _all(p)
    return _b(p.member), _b(p.member)


@filt("vix_term_contango")
def f_vix_term(p):
    """Longs only while the VIX curve is in contango (VIX < 3-month VIX): calm market, no stress inversion."""
    a, b = (p.macro or {}).get("^VIX"), (p.macro or {}).get("^VIX3M")
    if a is None or b is None:
        return _all(p), _all(p)
    ok = (a / b) < 1.0
    m = pd.DataFrame(np.repeat(ok.values[:, None], p.c.shape[1], 1), index=p.index, columns=p.columns)
    return _b(m), _b(~m)


@filt("credit_calm")
def f_credit(p):
    """Longs only while high-yield credit outperforms Treasuries (HYG/IEF above its 100-bar average)."""
    a, b = (p.macro or {}).get("HYG"), (p.macro or {}).get("IEF")
    if a is None or b is None:
        return _all(p), _all(p)
    r = a / b
    ok = r > r.rolling(100, min_periods=50).mean()
    m = pd.DataFrame(np.repeat(ok.values[:, None], p.c.shape[1], 1), index=p.index, columns=p.columns)
    return _b(m), _b(~m)


# ------------------------------------------------------------------ two-signal confirmation (combinations)
def confirm(primary: Signals, secondary: Signals, within: int = 0) -> Signals:
    """Entry only when the primary rule fires AND the secondary rule fired on the same bar
    or within the previous `within` bars. Exits follow the primary rule.
    Example: RSI oversold cross confirmed by a MACD bullish cross in the last 3 bars."""
    def win(x):
        if x is None:
            return None
        return x if within <= 0 else x.astype(int).rolling(within + 1, min_periods=1).max().astype(bool)
    el = primary.entry_long & win(secondary.entry_long)
    es = None
    if primary.entry_short is not None and secondary.entry_short is not None:
        es = primary.entry_short & win(secondary.entry_short)
    return Signals(_b(el), primary.exit_long, None if es is None else _b(es), primary.exit_short)


@filt("dxy_weak")
def f_dxy(p):
    """Longs only while the US dollar index is below its 100-bar average."""
    m = _macro_bool(p, "DX-Y.NYB", lambda s: s < s.rolling(100, min_periods=50).mean())
    return (_all(p), _all(p)) if m is None else (_b(m), _b(~m))


@filt("real_yield_falling")
def f_real(p):
    """Longs only while TIPS outperform nominal Treasuries (real yields falling)."""
    if not p.macro or p.macro.get("TIP") is None or p.macro.get("IEF") is None:
        return _all(p), _all(p)
    r = p.macro["TIP"] / p.macro["IEF"]
    ok = r > r.rolling(100, min_periods=50).mean()
    m = pd.DataFrame(np.repeat(ok.values[:, None], p.c.shape[1], 1), index=p.index, columns=p.columns)
    return _b(m), _b(~m)


# ================================================================ SMC / ICT family (added 2026-10-18)
# Smart Money Concepts as defined by ICT (M. Huddleston) and coded in the open-source reference package
# `smartmoneyconcepts` (github.com/joshyattridge/smart-money-concepts): swing structure, break of structure
# (BOS), change of character (CHoCH), fair value gap (FVG), order block (OB), liquidity sweep and the
# optimal trade entry (OTE) retracement. Academic evidence is close to none; these rules exist so the claim
# can be tested. NO LOOK-AHEAD: a swing point at bar t-k is only known at bar t (k bars later), so every
# level below is the last swing CONFIRMED up to close t.

def _swings(p: Panel, k: int):
    """Last confirmed swing high / low levels (known at t) and the previous distinct level."""
    w = 2 * k + 1
    hi_ok = p.h.shift(k) == p.h.rolling(w, min_periods=w).max()
    lo_ok = p.l.shift(k) == p.l.rolling(w, min_periods=w).min()
    sh = p.h.shift(k).where(hi_ok).ffill()
    sl = p.l.shift(k).where(lo_ok).ffill()
    sh_prev = sh.shift(1).where(sh != sh.shift(1)).ffill()
    sl_prev = sl.shift(1).where(sl != sl.shift(1)).ffill()
    return sh, sl, sh_prev, sl_prev


def _since(ev: pd.DataFrame) -> pd.DataFrame:
    """Bars since the last True (0 on the event bar, NaN before the first)."""
    n = pd.DataFrame(np.arange(len(ev))[:, None].repeat(ev.shape[1], 1), ev.index, ev.columns)
    return n - n.where(ev).ffill()


@rule("smc_bos", "smc", {"k": [2, 3, 5, 8]}, "ICT break of structure; smartmoneyconcepts bos_choch")
def smc_bos(p: Panel, k):
    sh, sl, _, _ = _swings(p, k)
    return Signals(_b(I.cross_up(p.c, sh)), _b(p.c < sl), _b(I.cross_down(p.c, sl)), _b(p.c > sh))


@rule("smc_choch", "smc", {"k": [3, 5, 8]}, "ICT change of character (first break against the swing structure)")
def smc_choch(p: Panel, k):
    sh, sl, sh_prev, sl_prev = _swings(p, k)
    down_struct, up_struct = sh < sh_prev, sl > sl_prev          # lower highs / higher lows
    return Signals(_b(down_struct & I.cross_up(p.c, sh)), _b(p.c < sl),
                   _b(up_struct & I.cross_down(p.c, sl)), _b(p.c > sh))


@rule("smc_fvg", "smc", {"max_age": [10, 20, 40], "min_gap_atr": [0.0, 0.5]}, "ICT fair value gap retracement entry")
def smc_fvg(p: Panel, max_age, min_gap_atr):
    a = I.atr(p.h, p.l, p.c, 14)
    bull = (p.l > p.h.shift(2)) & ((p.l - p.h.shift(2)) >= min_gap_atr * a)
    bear = (p.h < p.l.shift(2)) & ((p.l.shift(2) - p.h) >= min_gap_atr * a)
    b_top, b_bot = p.l.where(bull).ffill(), p.h.shift(2).where(bull).ffill()
    s_bot, s_top = p.h.where(bear).ffill(), p.l.shift(2).where(bear).ffill()
    ab, as_ = _since(_b(bull)), _since(_b(bear))
    el = (ab >= 1) & (ab <= max_age) & (p.l <= b_top) & (p.c > b_bot)
    es = (as_ >= 1) & (as_ <= max_age) & (p.h >= s_bot) & (p.c < s_top)
    return Signals(_b(el), _b((p.c < b_bot) | bear), _b(es), _b((p.c > s_top) | bull))


@rule("smc_order_block", "smc", {"k": [3, 5], "max_age": [20, 50]}, "ICT order block retest after a BOS")
def smc_order_block(p: Panel, k, max_age):
    sh, sl, _, _ = _swings(p, k)
    bos_up, bos_dn = _b(I.cross_up(p.c, sh)), _b(I.cross_down(p.c, sl))
    down_c, up_c = p.c < p.o, p.c > p.o
    ob_hi = p.h.where(down_c).ffill().shift(1).where(bos_up).ffill()      # last bearish candle before the BOS
    ob_lo = p.l.where(down_c).ffill().shift(1).where(bos_up).ffill()
    os_hi = p.h.where(up_c).ffill().shift(1).where(bos_dn).ffill()
    os_lo = p.l.where(up_c).ffill().shift(1).where(bos_dn).ffill()
    au, ad = _since(bos_up), _since(bos_dn)
    el = (au >= 1) & (au <= max_age) & (p.l <= ob_hi) & (p.c > ob_lo)
    es = (ad >= 1) & (ad <= max_age) & (p.h >= os_lo) & (p.c < os_hi)
    return Signals(_b(el), _b((p.c < ob_lo) | (p.c < sl)), _b(es), _b((p.c > os_hi) | (p.c > sh)))


@rule("smc_liquidity_sweep", "smc", {"k": [3, 5, 10]}, "ICT liquidity sweep / stop hunt (Wyckoff spring/upthrust)")
def smc_liquidity_sweep(p: Panel, k):
    sh, sl, _, _ = _swings(p, k)
    sw_lo = (p.l < sl.shift(1)) & (p.c > sl.shift(1))
    sw_hi = (p.h > sh.shift(1)) & (p.c < sh.shift(1))
    lo_ref = p.l.where(sw_lo).ffill()
    hi_ref = p.h.where(sw_hi).ffill()
    return Signals(_b(sw_lo), _b((p.c < lo_ref) | (p.c > sh)), _b(sw_hi), _b((p.c > hi_ref) | (p.c < sl)))


@rule("smc_ote", "smc", {"k": [3, 5, 8], "fib_lo": [0.5, 0.618]}, "ICT optimal trade entry: retracement into the 50/61.8-79% zone of the last leg")
def smc_ote(p: Panel, k, fib_lo):
    sh, sl, sh_prev, sl_prev = _swings(p, k)
    w = 2 * k + 1
    t_hi = _since(_b(p.h.shift(k) == p.h.rolling(w, min_periods=w).max()))
    t_lo = _since(_b(p.l.shift(k) == p.l.rolling(w, min_periods=w).min()))
    up_leg, dn_leg = t_hi < t_lo, t_lo < t_hi              # last confirmed swing was the high -> bullish leg
    rng = sh - sl
    z_hi, z_lo = sh - fib_lo * rng, sh - 0.79 * rng          # discount zone of a bullish leg
    s_lo, s_hi = sl + fib_lo * rng, sl + 0.79 * rng          # premium zone of a bearish leg
    el = up_leg & (sl > sl_prev) & (p.l <= z_hi) & (p.c >= z_lo) & (p.c > p.o)
    es = dn_leg & (sh < sh_prev) & (p.h >= s_lo) & (p.c <= s_hi) & (p.c < p.o)
    return Signals(_b(el), _b((p.c > sh) | (p.c < z_lo)), _b(es), _b((p.c < sl) | (p.c > s_hi)))


@filt("fib_pd")
def f_fib_pd(p):
    """Fibonacci premium / discount (ICT) of the dealing range between the last CONFIRMED swing high and low
    (k = 5): longs only in discount (close below the 50% level), shorts only in premium (above it). H073."""
    sh, sl, _, _ = _swings(p, 5)
    eq = (sh + sl) / 2
    return _b(p.c < eq), _b(p.c > eq)


# ================================================================ divergence + pivot levels (added 2026-10-18)
def _divergence(p: Panel, osc: pd.DataFrame, k: int):
    """Regular divergence at a confirmed swing: price lower low + oscillator higher low (bull), and mirror."""
    w = 2 * k + 1
    lo_ok = p.l.shift(k) == p.l.rolling(w, min_periods=w).min()
    hi_ok = p.h.shift(k) == p.h.rolling(w, min_periods=w).max()
    pl, ol = p.l.shift(k).where(lo_ok), osc.shift(k).where(lo_ok)
    ph, oh = p.h.shift(k).where(hi_ok), osc.shift(k).where(hi_ok)
    pl_prev, ol_prev = pl.ffill().shift(1), ol.ffill().shift(1)
    ph_prev, oh_prev = ph.ffill().shift(1), oh.ffill().shift(1)
    bull = lo_ok & (pl < pl_prev) & (ol > ol_prev)
    bear = hi_ok & (ph > ph_prev) & (oh < oh_prev)
    return _b(bull), _b(bear)


@rule("rsi_divergence", "divergence", {"n": [14], "k": [3, 5], "exit_level": [50, 70]}, "Wilder / Cardwell RSI regular divergence")
def rsi_divergence(p: Panel, n, k, exit_level):
    r = I.rsi(p.c, n)
    bull, bear = _divergence(p, r, k)
    return Signals(bull, _b(r > exit_level), bear, _b(r < 100 - exit_level))


@rule("macd_divergence", "divergence", {"k": [3, 5], "fast": [12], "slow": [26]}, "Appel MACD histogram divergence")
def macd_divergence(p: Panel, k, fast, slow):
    m = I.macd(p.c, fast, slow, 9)
    hist = m[2] if isinstance(m, tuple) else m
    bull, bear = _divergence(p, hist, k)
    return Signals(bull, _b(I.cross_down(hist, 0)), bear, _b(I.cross_up(hist, 0)))


@rule("pivot_bounce", "levels", {"window": [1, 5, 20]}, "Floor-trader pivot points: bounce at S1/R1, target P")
def pivot_bounce(p: Panel, window):
    H, L, C = p.h.rolling(window).max().shift(1), p.l.rolling(window).min().shift(1), p.c.shift(1)
    P = (H + L + C) / 3
    S1, R1 = 2 * P - H, 2 * P - L
    S2, R2 = P - (H - L), P + (H - L)
    return Signals(_b((p.l <= S1) & (p.c > S1)), _b((p.c >= P) | (p.c < S2)),
                   _b((p.h >= R1) & (p.c < R1)), _b((p.c <= P) | (p.c > R2)))
