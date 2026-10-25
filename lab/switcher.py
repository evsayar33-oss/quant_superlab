"""Regime switcher ("trading agent" without an LLM).

Every `rebalance_days` it gives capital to the strategies that worked best IN THE CURRENT REGIME of
their own coin, measured only on the past:

  * the return of bar t is credited to the regime that was known at the close of t-1
  * score(strategy, regime) = exponentially-decayed mean / decayed std of its past returns in that
    regime, shrunk towards 0 by n / (n + prior)  (little evidence -> small score)
  * a strategy needs `min_regime_days` of past history in a regime before it can be chosen in it
  * the top_k strategies with a POSITIVE score get equal weight; coin weight is capped at
    max_asset_weight; the rest stays in cash. No positive score -> 100% cash.
  * moving capital costs (commission + slippage) x |weight change| x the strategy's open exposure

It learns by itself: every new bar updates the scores, so the selection adapts when a strategy stops
working in a regime. Nothing is fit in the future: weights for bar t+1 use data up to the close of t.

Honest limit: roster members were chosen by the screening funnel on the same history, so the
switcher BACKTEST is optimistic for every member equally. Its real test is the forward (paper) record
in the arena; bots may use it only after the gate in config/arena.yaml passes on both.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from lab import metrics
from lab.regime import CODES, UNKNOWN, bars


def run(R: pd.DataFrame, reg: pd.DataFrame, expo: pd.DataFrame, asset_of: dict, ppy: float,
        cost_per_side: float, halflife_days: float = 30, top_k: int = 5, rebalance_days: float = 1,
        prior_days: float = 10, min_regime_days: float = 20, max_asset_weight: float = 0.4,
        eligible: pd.DataFrame | None = None) -> dict:
    """R: stand-alone bar returns per member; reg: regime code of each member's coin;
    expo: exposure each member holds at the close of each bar (sign ignored);
    eligible: optional bool frame, a member can be CHOSEN only where True (forward record: from the
    date it joined the arena until it retired; its earlier history still trains the scores)."""
    cols = list(R.columns)
    T, N = R.shape
    Rv = np.nan_to_num(R.to_numpy())
    G = reg.reindex(index=R.index, columns=cols).fillna(UNKNOWN).to_numpy().astype(int)
    X = np.abs(np.nan_to_num(expo.reindex(index=R.index, columns=cols).to_numpy()))
    E = None if eligible is None else eligible.reindex(index=R.index, columns=cols).fillna(False).to_numpy()
    hl = max(1.0, halflife_days * ppy / 365.0)
    a = 1.0 - 0.5 ** (1.0 / hl)
    prior = bars(prior_days, ppy)
    need = bars(min_regime_days, ppy)
    reb = bars(rebalance_days, ppy) if rebalance_days else 1
    K = len(CODES)
    m1 = np.zeros((K, N)); m2 = np.zeros((K, N)); cnt = np.zeros((K, N))
    assets = np.array([asset_of[c] for c in cols])
    uniq = {x: np.nonzero(assets == x)[0] for x in set(assets)}
    w = np.zeros(N)
    W = np.zeros((T, N)); ret = np.zeros(T); turn = np.zeros(T)
    rows = np.arange(N)
    for t in range(1, T):
        # 1) earn bar t with the weights decided at close t-1
        ret[t] = float(w @ Rv[t])
        # 2) credit bar t's returns to the regime known at close t-1
        g = G[t - 1]
        ok = g >= 0
        if ok.any():
            k = g[ok]; j = rows[ok]; x = Rv[t, ok]
            first = cnt[k, j] == 0
            m1[k, j] = np.where(first, x, (1 - a) * m1[k, j] + a * x)
            m2[k, j] = np.where(first, x * x, (1 - a) * m2[k, j] + a * x * x)
            cnt[k, j] += 1
        # 3) decide the weights for bar t+1 at the close of t
        if t % reb == 0:
            g = G[t]
            sc = np.full(N, -np.inf)
            okg = g >= 0
            if okg.any():
                kk = g[okg]; jj = rows[okg]
                mu, s2, n = m1[kk, jj], m2[kk, jj] - m1[kk, jj] ** 2, cnt[kk, jj]
                sd = np.sqrt(np.maximum(s2, 1e-18))
                s = mu / sd * (n / (n + prior))
                s = np.where((n >= need) & (sd > 1e-12), s, -np.inf)
                sc[okg] = s
            if E is not None:
                sc = np.where(E[t], sc, -np.inf)
            new = np.zeros(N)
            order = np.argsort(-sc)
            chosen = [j for j in order[:top_k] if sc[j] > 0]
            if chosen:
                new[chosen] = 1.0 / top_k            # unfilled slots stay in cash
                for _, idx in uniq.items():         # cap the weight of any single coin
                    s_ = new[idx].sum()
                    if s_ > max_asset_weight:
                        new[idx] *= max_asset_weight / s_
            dw = np.abs(new - w)
            cost = float((dw * X[t]).sum()) * cost_per_side
            turn[t] = float(dw.sum())
            ret[t] -= cost
            w = new
        W[t] = w
    out = pd.Series(ret, R.index)
    Wd = pd.DataFrame(W, R.index, cols)
    return {"returns": out, "weights": Wd, "turnover": pd.Series(turn, R.index),
            "current": {c: round(float(x), 4) for c, x in zip(cols, w) if x > 1e-9}}


def equal_weight(R: pd.DataFrame, alive: pd.DataFrame) -> pd.Series:
    """Benchmark: equal weight across members whose coin has data (rebalanced every bar, no extra cost)."""
    a = alive.reindex(index=R.index, columns=R.columns).fillna(False)
    n = a.sum(axis=1).replace(0, np.nan)
    return (R.where(a, 0.0).sum(axis=1) / n).fillna(0.0)


def grid(cfg: dict) -> list[dict]:
    return [{"halflife_days": h, "top_k": k}
            for h, k in itertools.product(cfg.get("halflife_days", [30]), cfg.get("top_k", [5]))]


def params_of(cfg: dict) -> dict:
    return dict(rebalance_days=cfg.get("rebalance_days", 1), prior_days=cfg.get("prior_days", 10),
                min_regime_days=cfg.get("min_regime_days", 20), max_asset_weight=cfg.get("max_asset_weight", 0.4))


def evaluate(R, reg, expo, asset_of, alive, ppy, cost, cfg: dict, windows: list, R_stress=None) -> dict:
    """Backtest the switcher grid against the equal-weight pool and check the backtest part of the gate."""
    metrics.set_periods(ppy)
    base = params_of(cfg)
    ew = equal_weight(R, alive)
    from lab.perp import window_start
    rows = []
    for g in grid(cfg):
        res = run(R, reg, expo, asset_of, ppy, cost, **g, **base)
        r = res["returns"]
        win = {}
        for y in windows:
            st = window_start(r.index, y)
            if st is None:
                continue
            rr, ee = r[r.index >= st], ew[ew.index >= st]
            win["full" if not y else f"{y}y"] = {"sharpe": round(metrics.sharpe(rr), 3),
                                                 "ew_sharpe": round(metrics.sharpe(ee), 3),
                                                 "ret": round(float((1 + rr).prod() - 1), 4),
                                                 "ew_ret": round(float((1 + ee).prod() - 1), 4),
                                                 "max_dd": round(metrics.max_drawdown(rr), 4)}
        rows.append({**g, "windows": win, "sharpe": round(metrics.sharpe(r), 3),
                     "max_dd": round(metrics.max_drawdown(r), 4)})
    d = cfg.get("default", {"halflife_days": 30, "top_k": 5})
    main = run(R, reg, expo, asset_of, ppy, cost, **d, **base)
    gate = cfg.get("gate", {})
    r = main["returns"]
    checks = {}
    win = {}
    for y in windows:
        st = window_start(r.index, y)
        if st is None:
            continue
        lab = "full" if not y else f"{y}y"
        win[lab] = (metrics.sharpe(r[r.index >= st]), metrics.sharpe(ew[ew.index >= st]))
    if gate.get("beat_equal_weight_all_windows", True):
        checks["beats_equal_weight_all_windows"] = bool(win) and all(s > e for s, e in win.values())
    if gate.get("positive_at_cost_stress", True) and R_stress is not None:
        rs = run(R_stress, reg, expo, asset_of, ppy, cost * cfg.get("cost_stress", 2.0), **d, **base)["returns"]
        checks["positive_at_cost_stress"] = bool((1 + rs).prod() > 1)
    checks["max_dd_ok"] = metrics.max_drawdown(r) >= gate.get("max_dd_floor", -0.45)
    share_pos = float(np.mean([x["sharpe"] > 0 for x in rows])) if rows else 0.0
    return {"default": d, "grid": rows, "grid_share_positive": round(share_pos, 3),
            "checks": checks, "backtest_pass": bool(checks) and all(checks.values()),
            "windows": {k: {"sharpe": round(s, 3), "ew_sharpe": round(e, 3)} for k, (s, e) in win.items()},
            "returns": r, "equal_weight": ew}
