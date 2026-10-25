"""Performance, risk and statistical-significance metrics (timeframe-aware).

Call set_periods(panel.ppy) before measuring a non-daily series; every annualised
number then uses the right bars-per-year. Sharpe/Sortino accept an optional
per-bar risk-free series (excess returns): in a high-rate market such as Turkey a
zero risk-free rate inflates Sharpe badly.

Significance: PSR, Deflated Sharpe (Bailey & Lopez de Prado 2014), PBO via CSCV
(Bailey et al. 2017), White (2000) Reality Check with stationary bootstrap.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
from scipy import stats

_P = {"ann": 252.0}
EULER = 0.5772156649


def set_periods(ppy: float) -> None:
    _P["ann"] = float(ppy)


def ann() -> float:
    return _P["ann"]


def _ex(r: pd.Series, rf: pd.Series | None) -> pd.Series:
    r = r.dropna()
    return r if rf is None else r - rf.reindex(r.index).fillna(0.0)


def sharpe(r: pd.Series, rf: pd.Series | None = None) -> float:
    x = _ex(r, rf)
    sd = x.std()
    return float(x.mean() / sd * math.sqrt(ann())) if sd and sd > 0 else 0.0


def sortino(r: pd.Series, rf: pd.Series | None = None) -> float:
    x = _ex(r, rf)
    dd = np.sqrt((np.minimum(x, 0) ** 2).mean())
    return float(x.mean() / dd * math.sqrt(ann())) if dd > 0 else 0.0


def drawdown(r: pd.Series) -> pd.Series:
    eq = (1 + r.fillna(0)).cumprod()
    return eq / eq.cummax() - 1


def max_drawdown(r: pd.Series) -> float:
    return float(drawdown(r).min()) if len(r) else 0.0


def dd_duration_max(r: pd.Series) -> int:
    """Longest stretch (bars) below a previous equity high."""
    under = (drawdown(r) < 0).astype(int).values
    best = cur = 0
    for u in under:
        cur = cur + 1 if u else 0
        best = max(best, cur)
    return int(best)


def ulcer_index(r: pd.Series) -> float:
    return float(np.sqrt((drawdown(r) ** 2).mean())) if len(r) else 0.0


def cagr(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 2:
        return 0.0
    total = float((1 + r).prod())
    yrs = len(r) / ann()
    return total ** (1 / yrs) - 1 if total > 0 else -1.0


def var_cvar(r: pd.Series, q: float = 0.05) -> tuple[float, float]:
    x = r.dropna()
    if len(x) < 30:
        return 0.0, 0.0
    v = float(np.quantile(x, q))
    return v, float(x[x <= v].mean())


def omega(r: pd.Series, thr: float = 0.0) -> float | None:
    x = r.dropna() - thr
    dn = -x[x < 0].sum()
    return float(x[x > 0].sum() / dn) if dn > 0 else None


def tail_ratio(r: pd.Series) -> float | None:
    x = r.dropna()
    if len(x) < 50:
        return None
    lo = abs(np.quantile(x, 0.05))
    return float(np.quantile(x, 0.95) / lo) if lo > 0 else None


def psr(r: pd.Series, sr_benchmark: float = 0.0) -> float:
    """P(true Sharpe > benchmark). Inputs and benchmark are per-period (not annual)."""
    r = r.dropna()
    n = len(r)
    if n < 30 or r.std() == 0:
        return 0.0
    sr = r.mean() / r.std()
    g3 = stats.skew(r)
    g4 = stats.kurtosis(r, fisher=False)
    denom = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return float(stats.norm.cdf((sr - sr_benchmark) * math.sqrt(n - 1) / denom))


def expected_max_sharpe(n_trials: int, sr_var: float) -> float:
    if n_trials <= 1:
        return 0.0
    z1 = stats.norm.ppf(1 - 1 / n_trials)
    z2 = stats.norm.ppf(1 - 1 / (n_trials * math.e))
    return math.sqrt(max(sr_var, 0)) * ((1 - EULER) * z1 + EULER * z2)


def dsr(r: pd.Series, n_trials: int, trial_sharpes: list[float] | None = None) -> float:
    r = r.dropna()
    if trial_sharpes and len(trial_sharpes) > 1:
        var = float(np.var(trial_sharpes, ddof=1))
    else:
        var = 1.0 / max(len(r), 1)
    return psr(r, expected_max_sharpe(n_trials, var))


def summary(r: pd.Series, turnover: pd.Series | None = None, bench: pd.Series | None = None,
            rf: pd.Series | None = None) -> dict:
    r = r.dropna()
    v, cv = var_cvar(r)
    mdd = max_drawdown(r)
    out = {
        "start": str(r.index[0]) if len(r) else None,
        "end": str(r.index[-1]) if len(r) else None,
        "years": round(len(r) / ann(), 2),
        "cagr": round(cagr(r), 4),
        "vol": round(float(r.std() * math.sqrt(ann())), 4),
        "sharpe": round(sharpe(r), 3),
        "sharpe_excess_rf": round(sharpe(r, rf), 3) if rf is not None else None,
        "sortino": round(sortino(r, rf), 3),
        "max_dd": round(mdd, 4),
        "max_dd_bars": dd_duration_max(r),
        "calmar": round(cagr(r) / abs(mdd), 3) if mdd < 0 else None,
        "ulcer": round(ulcer_index(r), 4),
        "var95": round(v, 4), "cvar95": round(cv, 4),
        "omega": round(o, 3) if (o := omega(r)) is not None else None,
        "tail_ratio": round(t, 3) if (t := tail_ratio(r)) is not None else None,
        "skew": round(float(stats.skew(r)), 3) if len(r) > 30 else None,
        "kurtosis": round(float(stats.kurtosis(r)), 3) if len(r) > 30 else None,
        "hit_rate": round(float((r > 0).mean()), 3) if len(r) else None,
        "psr": round(psr(r), 3),
        "time_in_market": None,
    }
    if turnover is not None and len(turnover):
        out["turnover_ann"] = round(float(turnover.mean() * ann()), 2)
    if bench is not None:
        b = bench.reindex(r.index).fillna(0)
        out["bench_cagr"] = round(cagr(b), 4)
        out["bench_sharpe"] = round(sharpe(b), 3)
        ex = r - b
        te = ex.std() * math.sqrt(ann())
        out["info_ratio"] = round(float(ex.mean() * ann() / te), 3) if te > 0 else None
        cov = np.cov(r, b)
        out["beta"] = round(float(cov[0, 1] / cov[1, 1]), 3) if cov[1, 1] > 0 else None
        up, dn = b > 0, b < 0
        out["up_capture"] = round(float(r[up].mean() / b[up].mean()), 3) if up.any() and b[up].mean() else None
        out["down_capture"] = round(float(r[dn].mean() / b[dn].mean()), 3) if dn.any() and b[dn].mean() else None
    return out


def monthly_table(r: pd.Series) -> pd.DataFrame:
    m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
    t = m.unstack()
    t["Year"] = (1 + r).groupby(r.index.year).prod() - 1
    return t.round(4)


def calendar_profile(r: pd.Series) -> dict:
    """Average return by weekday, month and (intraday) hour: timing of the edge."""
    out = {"weekday": {int(k): round(float(v), 5) for k, v in r.groupby(r.index.dayofweek).mean().items()},
           "month": {int(k): round(float(v), 5) for k, v in r.groupby(r.index.month).mean().items()}}
    if (r.index.hour != 0).any():
        out["hour"] = {int(k): round(float(v), 5) for k, v in r.groupby(r.index.hour).mean().items()}
    return out


def rolling_sharpe(r: pd.Series, window: int | None = None) -> pd.Series:
    w = window or int(ann())
    return r.rolling(w).mean() / r.rolling(w).std() * math.sqrt(ann())


def pbo(R: pd.DataFrame, S: int = 16) -> float | None:
    """Probability of Backtest Overfitting via CSCV. 0 = robust, > 0.5 = selection is noise."""
    R = R.dropna(how="all").fillna(0.0)
    R = R.loc[:, R.std() > 0]          # flat variants (no trades) carry no information
    T, K = R.shape
    if K < 2 or T < S * 20:
        return None
    blocks = np.array_split(np.arange(T), S)
    vals = R.values
    combos = list(itertools.combinations(range(S), S // 2))
    if len(combos) > 2000:
        combos = combos[:: len(combos) // 2000 + 1]

    def sr(ix):
        x = vals[ix]
        sd = x.std(axis=0)
        return np.where(sd > 0, x.mean(axis=0) / np.where(sd > 0, sd, 1), -np.inf)
    logits = []
    for is_b in combos:
        is_idx = np.concatenate([blocks[b] for b in is_b])
        oos_idx = np.concatenate([blocks[b] for b in range(S) if b not in is_b])
        best = int(np.argmax(sr(is_idx)))
        oos = sr(oos_idx)
        rank = (oos < oos[best]).sum() + 0.5 * ((oos == oos[best]).sum() - 1)
        w = (rank + 1) / (K + 1)
        logits.append(np.log(w / (1 - w)))
    return float(np.mean(np.array(logits) <= 0))


def reality_check(R: pd.DataFrame, bench: pd.Series | None = None, n: int = 500, block: int = 20,
                  seed: int = 3) -> float | None:
    """White (2000) Reality Check p-value: is the BEST variant better than the benchmark
    after accounting for searching over all K variants? Stationary bootstrap of the
    centred performance differentials. p < 0.05 -> the best result is not just data mining."""
    R = R.dropna(how="all").fillna(0.0)
    T, K = R.shape
    if T < block * 5 or K < 1:
        return None
    b = np.zeros(T) if bench is None else bench.reindex(R.index).fillna(0.0).values
    d = R.values - b[:, None]
    dbar = d.mean(axis=0)
    stat = math.sqrt(T) * dbar.max()
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n):
        idx = np.empty(T, dtype=int)
        i = 0
        while i < T:
            s = rng.integers(0, T)
            L = min(rng.geometric(1 / block), T - i)
            idx[i:i + L] = (s + np.arange(L)) % T
            i += L
        boot = math.sqrt(T) * (d[idx].mean(axis=0) - dbar).max()
        cnt += boot >= stat
    return float(cnt / n)


def regime_breakdown(r: pd.Series, bench: pd.Series | None, macro: dict | None = None) -> dict:
    """Sharpe of the strategy inside market regimes (trend, volatility, VIX, rates)."""
    if bench is None or len(r) < 100:
        return {}
    full_b = bench.ffill()
    n = int(ann())
    trend = (full_b > full_b.rolling(n * 200 // 252 or 2, min_periods=10).mean()).reindex(r.index)
    vol = full_b.pct_change(fill_method=None).rolling(max(n // 12, 5)).std()
    hi_vol = (vol > vol.rolling(n, min_periods=n // 2).median()).reindex(r.index)
    masks = [("bull", trend == True), ("bear", trend == False),  # noqa: E712
             ("calm", hi_vol == False), ("stressed", hi_vol == True)]  # noqa: E712
    if macro and "^VIX" in macro and macro["^VIX"] is not None:
        vix = macro["^VIX"].reindex(r.index)
        masks += [("vix_lt_20", vix < 20), ("vix_20_30", (vix >= 20) & (vix < 30)), ("vix_ge_30", vix >= 30)]
    if macro and "^TNX" in macro and "^IRX" in macro and macro["^TNX"] is not None and macro["^IRX"] is not None:
        curve = (macro["^TNX"] - macro["^IRX"]).reindex(r.index)
        masks += [("curve_inverted", curve < 0), ("curve_normal", curve >= 0)]
    out = {}
    for name, mask in masks:
        x = r[mask.fillna(False).astype(bool)]
        if len(x) > 30:
            out[name] = {"sharpe": round(sharpe(x), 2), "ann_ret": round(float(x.mean() * ann()), 4), "bars": int(len(x))}
    return out
