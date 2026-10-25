"""Technical indicator library.

All functions are vectorized over a WIDE frame (index = dates, columns = assets) and are
strictly causal: the value at row t uses rows <= t only.

Inputs follow the Panel convention: o, h, l, c, v = open, high, low, close, volume.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DF = pd.DataFrame


# ------------------------------------------------------------------ moving averages
def sma(x: DF, n: int) -> DF:
    return x.rolling(n, min_periods=n).mean()


def ema(x: DF, n: int) -> DF:
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def rma(x: DF, n: int) -> DF:  # Wilder smoothing
    return x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def wma(x: DF, n: int) -> DF:
    w = np.arange(1, n + 1, dtype=float)
    return x.rolling(n, min_periods=n).apply(lambda a: np.dot(a, w) / w.sum(), raw=True)


def hma(x: DF, n: int) -> DF:
    half, root = max(n // 2, 1), max(int(np.sqrt(n)), 1)
    return wma(2 * wma(x, half) - wma(x, n), root)


def dema(x: DF, n: int) -> DF:
    e = ema(x, n)
    return 2 * e - ema(e, n)


def tema(x: DF, n: int) -> DF:
    e1 = ema(x, n); e2 = ema(e1, n); e3 = ema(e2, n)
    return 3 * e1 - 3 * e2 + e3


def kama(x: DF, n: int = 10, fast: int = 2, slow: int = 30) -> DF:
    change = (x - x.shift(n)).abs()
    vol = x.diff().abs().rolling(n).sum()
    er = (change / vol.replace(0, np.nan)).fillna(0)
    sc = (er * (2 / (fast + 1) - 2 / (slow + 1)) + 2 / (slow + 1)) ** 2
    out = np.full(x.shape, np.nan)
    xv, scv = x.values, sc.values
    for j in range(x.shape[1]):
        prev = np.nan
        for i in range(x.shape[0]):
            if np.isnan(xv[i, j]):
                continue
            if np.isnan(prev):
                prev = xv[i, j] if i >= n else np.nan
            else:
                prev = prev + scv[i, j] * (xv[i, j] - prev)
            out[i, j] = prev
    return DF(out, index=x.index, columns=x.columns)


MA = {"sma": sma, "ema": ema, "wma": wma, "hma": hma, "dema": dema, "tema": tema,
      "kama": lambda x, n: kama(x, n)}


def ma(x: DF, n: int, kind: str = "sma") -> DF:
    return MA[kind](x, n)


# ------------------------------------------------------------------ volatility
def true_range(h: DF, l: DF, c: DF) -> DF:
    pc = c.shift(1)
    return np.maximum(h - l, np.maximum((h - pc).abs(), (l - pc).abs()))


def atr(h: DF, l: DF, c: DF, n: int = 14) -> DF:
    return rma(true_range(h, l, c), n)


def natr(h, l, c, n=14) -> DF:
    return atr(h, l, c, n) / c * 100


def bollinger(c: DF, n: int = 20, k: float = 2.0):
    m = sma(c, n); s = c.rolling(n, min_periods=n).std()
    return m - k * s, m, m + k * s


def bb_percent_b(c, n=20, k=2.0) -> DF:
    lo, _, up = bollinger(c, n, k)
    return (c - lo) / (up - lo)


def bb_width(c, n=20, k=2.0) -> DF:
    lo, m, up = bollinger(c, n, k)
    return (up - lo) / m


def keltner(h, l, c, n=20, k=2.0, atr_n=10):
    m = ema(c, n); a = atr(h, l, c, atr_n)
    return m - k * a, m, m + k * a


def donchian(h, l, n=20):
    return l.rolling(n, min_periods=n).min(), h.rolling(n, min_periods=n).max()


def zscore(c: DF, n: int = 20) -> DF:
    return (c - sma(c, n)) / c.rolling(n, min_periods=n).std()


def hist_vol(c: DF, n: int = 21) -> DF:
    return c.pct_change(fill_method=None).rolling(n, min_periods=n).std() * np.sqrt(252)


def choppiness(h, l, c, n=14) -> DF:
    s = true_range(h, l, c).rolling(n).sum()
    rng = h.rolling(n).max() - l.rolling(n).min()
    return 100 * np.log10(s / rng.replace(0, np.nan)) / np.log10(n)


# ------------------------------------------------------------------ momentum / oscillators
def rsi(c: DF, n: int = 14) -> DF:
    d = c.diff()
    up = rma(d.clip(lower=0), n); dn = rma(-d.clip(upper=0), n)
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).where(dn != 0, 100.0).where(up.notna())


def stoch(h, l, c, k: int = 14, d: int = 3, smooth: int = 3):
    ll = l.rolling(k, min_periods=k).min(); hh = h.rolling(k, min_periods=k).max()
    raw = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    kk = sma(raw, smooth) if smooth > 1 else raw
    return kk, sma(kk, d)


def stoch_rsi(c, n=14, k=3, d=3):
    r = rsi(c, n)
    lo = r.rolling(n, min_periods=n).min(); hi = r.rolling(n, min_periods=n).max()
    sr = 100 * (r - lo) / (hi - lo).replace(0, np.nan)
    kk = sma(sr, k)
    return kk, sma(kk, d)


def williams_r(h, l, c, n=14) -> DF:
    hh = h.rolling(n, min_periods=n).max(); ll = l.rolling(n, min_periods=n).min()
    return -100 * (hh - c) / (hh - ll).replace(0, np.nan)


def cci(h, l, c, n=20) -> DF:
    tp = (h + l + c) / 3
    m = sma(tp, n)
    md = tp.rolling(n, min_periods=n).apply(lambda a: np.mean(np.abs(a - a.mean())), raw=True)
    return (tp - m) / (0.015 * md.replace(0, np.nan))


def mfi(h, l, c, v, n=14) -> DF:
    tp = (h + l + c) / 3
    mf = tp * v
    pos = mf.where(tp > tp.shift(1), 0.0).rolling(n, min_periods=n).sum()
    neg = mf.where(tp < tp.shift(1), 0.0).rolling(n, min_periods=n).sum()
    return 100 - 100 / (1 + pos / neg.replace(0, np.nan))


def roc(c, n=10) -> DF:
    return (c / c.shift(n) - 1) * 100


def macd(c, fast=12, slow=26, signal=9):
    line = ema(c, fast) - ema(c, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def ppo(c, fast=12, slow=26, signal=9):
    line = (ema(c, fast) / ema(c, slow) - 1) * 100
    sig = ema(line, signal)
    return line, sig, line - sig


def trix(c, n=15, signal=9):
    t = ema(ema(ema(c, n), n), n)
    line = t.pct_change(fill_method=None) * 100
    return line, ema(line, signal)


def tsi(c, long=25, short=13, signal=7):
    d = c.diff()
    num = ema(ema(d, long), short); den = ema(ema(d.abs(), long), short)
    line = 100 * num / den.replace(0, np.nan)
    return line, ema(line, signal)


def awesome(h, l, fast=5, slow=34) -> DF:
    mid = (h + l) / 2
    return sma(mid, fast) - sma(mid, slow)


def ultimate(h, l, c, a=7, b=14, d=28) -> DF:
    pc = c.shift(1)
    bp = c - np.minimum(l, pc)
    tr = np.maximum(h, pc) - np.minimum(l, pc)
    avg = lambda n: bp.rolling(n).sum() / tr.rolling(n).sum().replace(0, np.nan)  # noqa: E731
    return 100 * (4 * avg(a) + 2 * avg(b) + avg(d)) / 7


def dmi(h, l, c, n=14):
    up = h.diff(); dn = -l.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    mdm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = rma(true_range(h, l, c), n)
    pdi = 100 * rma(pdm, n) / tr.replace(0, np.nan)
    mdi = 100 * rma(mdm, n) / tr.replace(0, np.nan)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return pdi, mdi, rma(dx, n)


def aroon(h, l, n=25):
    up = h.rolling(n + 1, min_periods=n + 1).apply(lambda a: 100 * np.argmax(a) / n, raw=True)
    dn = l.rolling(n + 1, min_periods=n + 1).apply(lambda a: 100 * np.argmin(a) / n, raw=True)
    return up, dn


def vortex(h, l, c, n=14):
    tr = true_range(h, l, c).rolling(n).sum()
    vp = (h - l.shift(1)).abs().rolling(n).sum() / tr
    vm = (l - h.shift(1)).abs().rolling(n).sum() / tr
    return vp, vm


def wavetrend(h, l, c, n1=10, n2=21):
    """LazyBear WaveTrend (used by the owner's ATVS indicator)."""
    ap = (h + l + c) / 3
    esa = ema(ap, n1)
    d = ema((ap - esa).abs(), n1)
    ci = (ap - esa) / (0.015 * d.replace(0, np.nan))
    wt1 = ema(ci, n2)
    return wt1, sma(wt1, 4)


def momentum(c, n=10) -> DF:
    return c - c.shift(n)


def coppock(c, r1=14, r2=11, n=10) -> DF:
    return wma(roc(c, r1) + roc(c, r2), n)


def dpo(c, n=20) -> DF:
    # causal variant: price minus a lagged SMA (no centring, so no look-ahead)
    return c - sma(c, n).shift(n // 2 + 1)


# ------------------------------------------------------------------ trend systems
def supertrend(h, l, c, n=10, mult=3.0) -> DF:
    """Returns direction: +1 uptrend, -1 downtrend."""
    a = atr(h, l, c, n).values
    hl2 = ((h + l) / 2).values
    cv = c.values
    ub, lb = hl2 + mult * a, hl2 - mult * a
    T, N = cv.shape
    fu, fl = ub.copy(), lb.copy()
    d = np.zeros((T, N))
    for i in range(1, T):
        pu, pl, pc = fu[i - 1], fl[i - 1], cv[i - 1]
        fu[i] = np.where((ub[i] < pu) | (pc > pu) | np.isnan(pu), ub[i], pu)
        fl[i] = np.where((lb[i] > pl) | (pc < pl) | np.isnan(pl), lb[i], pl)
        prev = d[i - 1]
        up = np.where(cv[i] > fu[i - 1], 1, np.where(cv[i] < fl[i - 1], -1, prev))
        d[i] = np.where(np.isnan(a[i]), 0, np.where(prev == 0, np.where(cv[i] > hl2[i], 1, -1), up))
    return DF(d, index=c.index, columns=c.columns)


def psar(h, l, step=0.02, max_step=0.2) -> DF:
    """Parabolic SAR direction (+1 long / -1 short)."""
    hv, lv = h.values, l.values
    T, N = hv.shape
    out = np.zeros((T, N))
    for j in range(N):
        up, af, ep, sar = True, step, np.nan, np.nan
        for i in range(T):
            if np.isnan(hv[i, j]) or np.isnan(lv[i, j]):
                continue
            if np.isnan(sar):
                sar, ep = lv[i, j], hv[i, j]
                out[i, j] = 1
                continue
            sar = sar + af * (ep - sar)
            if up:
                if lv[i, j] < sar:
                    up, sar, ep, af = False, ep, lv[i, j], step
                elif hv[i, j] > ep:
                    ep, af = hv[i, j], min(af + step, max_step)
            else:
                if hv[i, j] > sar:
                    up, sar, ep, af = True, ep, hv[i, j], step
                elif lv[i, j] < ep:
                    ep, af = lv[i, j], min(af + step, max_step)
            out[i, j] = 1 if up else -1
    return DF(out, index=h.index, columns=h.columns)


def ichimoku(h, l, c, conv=9, base=26, span_b=52):
    mid = lambda n: (h.rolling(n).max() + l.rolling(n).min()) / 2  # noqa: E731
    tenkan, kijun = mid(conv), mid(base)
    # The cloud plotted at t was computed `base` bars earlier -> shift forward = causal.
    span_a = ((tenkan + kijun) / 2).shift(base)
    span_b_ = mid(span_b).shift(base)
    return tenkan, kijun, span_a, span_b_


def heikin_ashi_dir(o, h, l, c) -> DF:
    hcv = ((o + h + l + c) / 4).to_numpy(copy=True)
    ov, cv = o.to_numpy(copy=True), c.to_numpy(copy=True)
    hov = np.full(hcv.shape, np.nan)
    hov[0] = (ov[0] + cv[0]) / 2
    for i in range(1, len(hov)):
        hov[i] = np.where(np.isnan(hov[i - 1]), (ov[i] + cv[i]) / 2, (hov[i - 1] + hcv[i - 1]) / 2)
    return DF(np.sign(hcv - hov), index=c.index, columns=c.columns)


def linreg_slope(c, n=20) -> DF:
    x = np.arange(n) - (n - 1) / 2
    return c.rolling(n, min_periods=n).apply(lambda a: np.dot(x, a) / np.dot(x, x), raw=True) / c


def hurst_proxy(c, n=100) -> DF:
    """Variance-ratio proxy: >0.5 trending, <0.5 mean-reverting."""
    r1 = np.log(c).diff()
    r10 = np.log(c).diff(10)
    vr = r10.rolling(n).var() / (10 * r1.rolling(n).var())
    return 0.5 + 0.5 * np.log(vr.clip(lower=1e-6)) / np.log(10)


# ------------------------------------------------------------------ volume
def obv(c, v) -> DF:
    return (np.sign(c.diff()).fillna(0) * v).cumsum()


def cmf(h, l, c, v, n=20) -> DF:
    mfm = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    return (mfm * v).rolling(n).sum() / v.rolling(n).sum().replace(0, np.nan)


def adl(h, l, c, v) -> DF:
    mfm = ((c - l) - (h - c)) / (h - l).replace(0, np.nan)
    return (mfm.fillna(0) * v).cumsum()


def chaikin_osc(h, l, c, v, fast=3, slow=10) -> DF:
    a = adl(h, l, c, v)
    return ema(a, fast) - ema(a, slow)


def force_index(c, v, n=13) -> DF:
    return ema(c.diff() * v, n)


def rolling_vwap(h, l, c, v, n=20) -> DF:
    tp = (h + l + c) / 3
    return (tp * v).rolling(n).sum() / v.rolling(n).sum().replace(0, np.nan)


def session_vwap(h, l, c, v, session) -> DF:
    """VWAP anchored at each session start; `session` labels the bars of one session (e.g. the date)."""
    tp = (h + l + c) / 3
    pv = (tp * v).groupby(session).cumsum()
    return pv / v.groupby(session).cumsum().replace(0, np.nan)


def rel_volume(v, n=20) -> DF:
    return v / sma(v, n).shift(1)


def eom(h, l, v, n=14) -> DF:
    mid = (h + l) / 2
    box = (v / 1e6) / (h - l).replace(0, np.nan)
    return sma(mid.diff() / box, n)


# ------------------------------------------------------------------ candles / price action
def ibs(h, l, c) -> DF:
    return (c - l) / (h - l).replace(0, np.nan)


def bullish_engulfing(o, c) -> DF:
    return (c.shift(1) < o.shift(1)) & (c > o) & (c >= o.shift(1)) & (o <= c.shift(1))


def bearish_engulfing(o, c) -> DF:
    return (c.shift(1) > o.shift(1)) & (c < o) & (c <= o.shift(1)) & (o >= c.shift(1))


def hammer(o, h, l, c) -> DF:
    body = (c - o).abs(); rng = (h - l).replace(0, np.nan)
    lower = np.minimum(o, c) - l; upper = h - np.maximum(o, c)
    return (lower >= 2 * body) & (upper <= 0.3 * body + 0.1 * rng) & (body / rng < 0.4)


def shooting_star(o, h, l, c) -> DF:
    body = (c - o).abs(); rng = (h - l).replace(0, np.nan)
    lower = np.minimum(o, c) - l; upper = h - np.maximum(o, c)
    return (upper >= 2 * body) & (lower <= 0.3 * body + 0.1 * rng) & (body / rng < 0.4)


def nr(h, l, n=7) -> DF:
    r = h - l
    return r <= r.rolling(n, min_periods=n).min()


def inside_bar(h, l) -> DF:
    return (h < h.shift(1)) & (l > l.shift(1))


def consecutive(c, n=3, up=False) -> DF:
    d = (c.diff() > 0) if up else (c.diff() < 0)
    return d.astype(int).rolling(n, min_periods=n).sum() == n


def gap(o, c) -> DF:
    return o / c.shift(1) - 1


# ------------------------------------------------------------------ helpers
def cross_up(a, b) -> DF:
    b = b if isinstance(b, pd.DataFrame) else pd.DataFrame(b, index=a.index, columns=a.columns)
    return (a > b) & (a.shift(1) <= b.shift(1))


def cross_down(a, b) -> DF:
    b = b if isinstance(b, pd.DataFrame) else pd.DataFrame(b, index=a.index, columns=a.columns)
    return (a < b) & (a.shift(1) >= b.shift(1))


def level(x: DF, value: float) -> DF:
    return pd.DataFrame(value, index=x.index, columns=x.columns)
