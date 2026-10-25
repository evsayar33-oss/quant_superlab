"""Advanced families: statistical arbitrage, machine-learning ranking, event drift, macro timing.

All causal: every decision at bar t uses data up to t only (models are refit on past windows).
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from lab import indicators as I
from lab.engine import rank_top_n, rebalance
from lab.strategies import strategy


# ============================================================ pairs trading (stat-arb)
@strategy("pairs_zscore",
          grid={"form": [126, 252], "entry_z": [1.5, 2.0, 2.5], "min_corr": [0.6, 0.8], "hedge": ["ratio", "ols"]},
          defaults={"form": 252, "entry_z": 2.0, "exit_z": 0.5, "min_corr": 0.7, "z_n": 63, "hedge": "ratio",
                    "max_pairs": 10, "max_half_life": 40},
          source="Gatev, Goetzmann & Rouwenhorst (2006) Pairs Trading; Vidyamurthy (2004)")
def pairs_zscore(c, form, entry_z, exit_z, min_corr, z_n, hedge, max_pairs, max_half_life):
    """hedge='ratio': log price ratio (GGR distance approach, beta = 1); 'ols': rolling OLS hedge ratio."""
    lc = np.log(c)
    r = lc.diff()
    cols = list(c.columns)
    if len(cols) > 40:  # keep the pair count tractable: most liquid-looking (longest history) names
        cols = list(c.notna().sum().sort_values(ascending=False).index[:40])
    pairs = list(itertools.combinations(range(len(cols)), 2))
    T, P = len(c), len(pairs)
    Z = np.full((T, P), np.nan); B = np.full((T, P), np.nan); OK = np.zeros((T, P), bool)
    for k, (a, b) in enumerate(pairs):
        la, lb = lc[cols[a]], lc[cols[b]]
        corr = r[cols[a]].rolling(form, min_periods=form // 2).corr(r[cols[b]])
        if hedge == "ols":
            beta = la.rolling(form, min_periods=form // 2).cov(lb) / lb.rolling(form, min_periods=form // 2).var()
        else:
            beta = pd.Series(1.0, index=la.index)
        spread = la - beta * lb
        mu, sd = spread.rolling(z_n).mean(), spread.rolling(z_n).std()
        dev = spread - spread.rolling(form, min_periods=form // 2).mean()
        ac = dev.rolling(form, min_periods=form // 2).corr(dev.shift(1))   # AR(1) of the demeaned spread
        hl = -np.log(2) / np.log(ac.where((ac > 0) & (ac < 1)))
        Z[:, k] = ((spread - mu) / sd).to_numpy()
        B[:, k] = beta.to_numpy()
        OK[:, k] = ((corr > min_corr) & (hl < max_half_life)).to_numpy()
    pos = np.zeros(P)
    W = np.zeros((T, len(cols)))
    ia = np.array([a for a, _ in pairs]); ib = np.array([b for _, b in pairs])
    for t in range(T):
        z = Z[t]
        close = (pos != 0) & (~np.isfinite(z) | (np.abs(z) < exit_z) | ~OK[t])
        pos[close] = 0
        free = max_pairs - int((pos != 0).sum())
        if free > 0:
            cand = (pos == 0) & OK[t] & np.isfinite(z) & (np.abs(z) > entry_z)
            if cand.any():
                order = np.argsort(-np.where(cand, np.abs(z), -1))[:free]
                order = order[cand[order]]
                pos[order] = -np.sign(z[order])
        live = np.nonzero(pos)[0]
        if len(live):
            bt = np.where(np.isfinite(B[t, live]), B[t, live], 1.0)
            g = 1 + np.abs(bt)
            np.add.at(W[t], ia[live], pos[live] / g / max_pairs)
            np.add.at(W[t], ib[live], -pos[live] * bt / g / max_pairs)
    return pd.DataFrame(W, index=c.index, columns=cols).reindex(columns=c.columns, fill_value=0.0)


# ============================================================ machine-learning ranking (walk-forward ridge)
def _features(c: pd.DataFrame) -> dict:
    r = c.pct_change(fill_method=None)
    return {
        "mom_1m": c / c.shift(21) - 1, "mom_3m": c / c.shift(63) - 1, "mom_6m": c / c.shift(126) - 1,
        "mom_12_1": c.shift(21) / c.shift(252) - 1, "vol_3m": r.rolling(63).std(),
        "rsi14": I.rsi(c, 14) / 100, "dist_52w_high": c / c.rolling(252).max() - 1,
        "max_1m": r.rolling(21).max(), "rev_1w": c / c.shift(5) - 1,
    }


@strategy("ml_ridge_rank",
          grid={"train_months": [36, 60], "alpha": [1.0, 10.0], "top_n": [5, 10]},
          defaults={"train_months": 36, "alpha": 10.0, "top_n": 5, "horizon": 21},
          source="Gu, Kelly & Xiu (2020) Empirical Asset Pricing via Machine Learning (linear baseline)")
def ml_ridge_rank(c, train_months, alpha, top_n, horizon):
    feats = _features(c)
    names = list(feats)
    # cross-sectional ranks (robust to scale), target = next-horizon return rank
    X = {k: v.rank(axis=1, pct=True) - 0.5 for k, v in feats.items()}
    y = (c.shift(-horizon) / c - 1).rank(axis=1, pct=True) - 0.5
    idx = c.index
    month_end = pd.Series(idx, index=idx).groupby(idx.to_period("M")).transform("max")
    reb = np.nonzero(idx == month_end.values)[0]
    score = pd.DataFrame(np.nan, index=idx, columns=c.columns)
    train = int(train_months * 21)
    for t in reb:
        lo, hi = t - train, t - horizon  # target of row hi is known at t (no look-ahead)
        if lo < 260:
            continue
        rows = slice(lo, hi + 1)
        Xs = np.stack([X[k].iloc[rows].to_numpy().ravel() for k in names], 1)
        ys = y.iloc[rows].to_numpy().ravel()
        m = np.isfinite(Xs).all(1) & np.isfinite(ys)
        if m.sum() < 200:
            continue
        A = Xs[m]; b = ys[m]
        w = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ b)
        xt = np.stack([X[k].iloc[t].to_numpy() for k in names], 1)
        score.iloc[t] = np.where(np.isfinite(xt).all(1), xt @ w, np.nan)
    return rebalance(rank_top_n(score.ffill(), top_n), "ME")


# ============================================================ post-report drift (PEAD proxy)
@strategy("post_report_drift",
          grid={"hold": [21, 42, 63], "min_react": [0.0, 0.02]},
          defaults={"hold": 42, "min_react": 0.0, "max_pos": 10},
          source="Ball & Brown (1968); Bernard & Thomas (1989) post-earnings-announcement drift (proxy)",
          kind="fundamental", needs="panel")
def post_report_drift(p, hold, min_react, max_pos):
    from lab.strategies.fundamental_factors import NoData
    ni = p.fund.get("net_income")
    if ni is None or ni.notna().mean().mean() < 0.15:
        raise NoData("net_income history unavailable")
    new = ni.ne(ni.shift(1)) & ni.notna() & ni.shift(1).notna()       # a new report became public
    growth = (ni - ni.shift(1)) / ni.shift(1).abs()
    mkt = p.c.pct_change(fill_method=None).mean(axis=1)
    react = p.c.pct_change(2, fill_method=None).sub(mkt.rolling(2).sum(), axis=0)  # 2-bar abnormal reaction
    good = new & (growth > 0) & (react > min_react)
    on = good.astype(float).replace(0, np.nan).ffill(limit=hold).fillna(0.0)
    n = on.sum(axis=1).clip(lower=max_pos)
    return on.div(n, axis=0)


# ============================================================ macro / breadth timing
@strategy("macro_risk_switch",
          grid={"vix_max": [20, 25, 30], "use_curve": [False, True], "trend_n": [100, 200]},
          defaults={"vix_max": 25, "use_curve": True, "trend_n": 200},
          source="Risk-on / risk-off timing with VIX, yield curve and trend",
          kind="time_series", needs="panel")
def macro_risk_switch(p, vix_max, use_curve, trend_n):
    on = pd.Series(True, index=p.index)
    if p.bench is not None:
        on &= p.bench > p.bench.rolling(trend_n, min_periods=trend_n // 2).mean()
    v = p.macro.get("^VIX") if p.macro else None
    if v is not None:
        on &= v.fillna(0) < vix_max
    if use_curve and p.macro and p.macro.get("^TNX") is not None and p.macro.get("^IRX") is not None:
        on &= (p.macro["^TNX"] - p.macro["^IRX"]).fillna(0) >= 0
    w = p.c.notna().astype(float)
    w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return w.mul(on.astype(float), axis=0)


@strategy("breadth_timing",
          grid={"ma": [50, 200], "thr": [0.4, 0.5, 0.6]},
          defaults={"ma": 200, "thr": 0.5},
          source="Market breadth (share of stocks above their moving average) timing",
          kind="time_series")
def breadth_timing(c, ma, thr):
    above = (c > c.rolling(ma, min_periods=ma // 2).mean()).where(c.notna())
    breadth = above.mean(axis=1)
    w = c.notna().astype(float)
    w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return w.mul((breadth > thr).astype(float), axis=0)


@strategy("usdtry_hedge_switch",
          grid={"n": [20, 50], "thr": [0.03, 0.05]},
          defaults={"n": 20, "thr": 0.05},
          source="BIST: step aside when the lira is in acute depreciation",
          kind="time_series", needs="panel")
def usdtry_hedge_switch(p, n, thr):
    fx = p.macro.get("USDTRY=X") if p.macro else None
    w = p.c.notna().astype(float)
    w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    if fx is None:
        return w
    calm = fx.pct_change(n, fill_method=None) < thr
    return w.mul(calm.astype(float).fillna(1.0), axis=0)
