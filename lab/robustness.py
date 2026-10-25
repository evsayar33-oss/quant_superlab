"""Robustness, timing and profit-maximisation studies run on the FINAL selected variant.

  mc_trade_shuffle     Monte Carlo of the trade sequence (order risk): drawdown/return spread
  random_entry_test    same exits and trade frequency, random entries -> does the ENTRY add value?
  delay_test           execute one bar later -> how fast does the edge decay (latency risk)
  noise_test           jitter OHLC prices -> is the result fragile to tiny data changes?
  param_neighborhood   are neighbouring parameter values also good (plateau) or is it a spike?
  wf_efficiency        OOS Sharpe / IS Sharpe across walk-forward windows
  overlays             portfolio overlays: vol targeting, drawdown circuit-breaker, equity-curve filter
  event_study          forward return after the entry signal for 1..N bars -> best holding time
  exit_grid_study      stop% x target% x max-hold grid from real bar paths -> best SL/TP/timing
The studies inform the report; the decision gate uses delay/random-entry/neighbourhood checks.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from lab import metrics
from lab.engine import Costs
from lab.panel import Panel
from lab.rules import Signals


def mc_trade_shuffle(tlog: pd.DataFrame, n: int = 1000, seed: int = 1) -> dict:
    if tlog is None or len(tlog) < 10:
        return {}
    r = (tlog["ret"] * tlog["weight"]).values
    rng = np.random.default_rng(seed)
    dds, fin = [], []
    for _ in range(n):
        x = rng.permutation(r)
        eq = np.cumprod(1 + x)
        dds.append((eq / np.maximum.accumulate(eq) - 1).min())
        fin.append(eq[-1] - 1)
    return {"maxdd_median": round(float(np.median(dds)), 4), "maxdd_p95": round(float(np.percentile(dds, 5)), 4),
            "final_p05": round(float(np.percentile(fin, 5)), 4), "final_median": round(float(np.median(fin)), 4)}


def random_entry_test(cand, p: Panel, v, costs: Costs, n: int = 25, seed: int = 2) -> dict:
    """Random entries with the SAME exits, sizing and (calibrated) number of trades.
    Compares return per unit of market exposure, so a strategy is not rewarded for simply
    being invested more often in a rising market. p = share of random runs that do as well."""
    from lab.candidates import RuleCandidate
    from lab.trade_engine import EXIT_GRID, SIZE_GRID, run_trades
    if not isinstance(cand, RuleCandidate):
        return {}
    sig = cand._signals(p, v)
    ex, sz = EXIT_GRID[v.params["_exit"]], SIZE_GRID[v.params.get("_size", 0)]

    def score(res):
        expo = res.weights.abs().sum(axis=1).mean()
        return float(res.returns.mean() / expo) if expo > 0 else 0.0, len(res.meta["trades"])
    act, n_act = score(cand.run(p, v, costs))
    rng = np.random.default_rng(seed)
    rate_l = sig.entry_long.mean().values
    rate_s = sig.entry_short.mean().values if (sig.entry_short is not None and cand.side != "long") else None

    def one(scale):
        rl = pd.DataFrame(rng.random(sig.entry_long.shape) < rate_l * scale, index=p.index, columns=p.columns)
        rs = None if rate_s is None else pd.DataFrame(rng.random(sig.entry_long.shape) < rate_s * scale,
                                                      index=p.index, columns=p.columns)
        return score(run_trades(p, Signals(rl, sig.exit_long, rs, sig.exit_short), ex, costs, cand.side,
                                cand.max_positions, sz))
    _, n0 = one(1.0)
    scale = float(np.clip(n_act / n0, 0.2, 5.0)) if n0 else 1.0
    vals = np.array([one(scale)[0] for _ in range(n)])
    k = metrics.ann()
    return {"actual_ret_per_exposure_ann": round(act * k, 4), "random_median_ann": round(float(np.median(vals)) * k, 4),
            "random_p95_ann": round(float(np.percentile(vals, 95)) * k, 4), "trades_actual": n_act,
            "p_value": round(float((vals >= act).mean()), 3)}


def delay_test(cand, p: Panel, v, costs: Costs) -> dict:
    """One extra bar of latency. A real edge should degrade gracefully, not vanish."""
    from lab.candidates import RuleCandidate
    from lab import engine
    from lab.trade_engine import EXIT_GRID, SIZE_GRID, run_trades
    base = cand.run(p, v, costs).returns
    if isinstance(cand, RuleCandidate):
        s = cand._signals(p, v)
        sh = lambda x: None if x is None else x.shift(1, fill_value=False)  # noqa: E731
        late = run_trades(p, Signals(sh(s.entry_long), sh(s.exit_long), sh(s.entry_short), sh(s.exit_short)),
                          EXIT_GRID[v.params["_exit"]], costs, cand.side, cand.max_positions,
                          SIZE_GRID[v.params.get("_size", 0)]).returns
    else:
        prm = {k: x for k, x in v.params.items() if not k.startswith("_")}
        res = engine.run(p.c, cand.strat(p, **prm), costs, lag=2, ppy=p.ppy, member=p.member)
        if v.params.get("_overlay"):
            from lab import overlays
            res = overlays.apply(res, v.params["_overlay"], p.ppy, costs)
        late = res.returns
    b, l_ = metrics.sharpe(base), metrics.sharpe(late)
    return {"sharpe": round(b, 3), "sharpe_delayed_1bar": round(l_, 3),
            "retained": round(l_ / b, 3) if b > 0 else None}


def noise_test(cand, p: Panel, v, costs: Costs, n: int = 10, bp: float = 0.002, seed: int = 4) -> dict:
    rng = np.random.default_rng(seed)
    srs = []
    for _ in range(n):
        f = pd.DataFrame(1 + rng.normal(0, bp, p.c.shape), index=p.index, columns=p.columns)
        import dataclasses
        q = dataclasses.replace(p, o=p.o * f, h=p.h * f, l=p.l * f, c=p.c * f)
        try:
            srs.append(metrics.sharpe(cand.run(q, v, costs).returns))
        except Exception:  # noqa: BLE001
            pass
    if not srs:
        return {}
    return {"noise_bp": bp, "sharpe_min": round(float(np.min(srs)), 3), "sharpe_median": round(float(np.median(srs)), 3)}


def _parse(key: str) -> dict:
    out = {}
    head = key.split("|")
    for part in head[1].split(",") if len(head) > 1 else []:
        if "=" in part:
            k, val = part.split("=", 1)
            out[k] = val
    out["_rest"] = "|".join(head[2:])
    return out


def param_neighborhood(R: pd.DataFrame, best: str) -> dict:
    """Neighbours = variants equal to `best` except one parameter. Plateau => robust."""
    sr = R.mean() / R.std().replace(0, np.nan) * math.sqrt(metrics.ann())
    b = _parse(best)
    nb = []
    for k in R.columns:
        if k == best:
            continue
        q = _parse(k)
        if q["_rest"] != b["_rest"] or set(q) != set(b):
            continue
        diff = [x for x in b if x != "_rest" and b[x] != q[x]]
        if len(diff) == 1:
            nb.append(sr[k])
    if not nb:
        return {"neighbours": 0}
    nb = np.array([x for x in nb if np.isfinite(x)])
    best_sr = float(sr[best])
    return {"neighbours": int(len(nb)), "best_sharpe": round(best_sr, 3),
            "neighbour_median": round(float(np.median(nb)), 3) if len(nb) else None,
            "share_positive": round(float((nb > 0).mean()), 3) if len(nb) else None,
            "stability": round(float(np.median(nb) / best_sr), 3) if len(nb) and best_sr > 0 else None}


def wf_efficiency(wf_log: list[dict], oos: pd.Series) -> float | None:
    is_ = [w["is_sharpe"] for w in wf_log if w.get("is_sharpe") is not None and np.isfinite(w["is_sharpe"])]
    if not is_ or np.mean(is_) <= 0:
        return None
    return round(metrics.sharpe(oos) / float(np.mean(is_)), 3)


def overlays(r: pd.Series, ppy: float) -> dict:
    """Causal portfolio overlays on the OOS return stream (exposure decided from past bars only)."""
    out = {}
    def rep(x):
        return {"sharpe": round(metrics.sharpe(x), 3), "cagr": round(metrics.cagr(x), 4),
                "max_dd": round(metrics.max_drawdown(x), 4)}
    out["none"] = rep(r)
    look = max(int(ppy / 4), 10)
    vol = r.rolling(look, min_periods=look // 2).std().shift(1) * math.sqrt(ppy)
    for tv in (0.10, 0.15, 0.20):
        out[f"vol_target_{tv}"] = rep(r * (tv / vol).clip(upper=2.0).fillna(1.0))
    for thr in (0.10, 0.20):
        eq = (1 + r).cumprod()
        dd = (eq / eq.cummax() - 1).shift(1).fillna(0)
        out[f"dd_brake_{thr}"] = rep(r * np.where(dd < -thr, 0.5, 1.0))
    for n in (int(ppy / 6), int(ppy / 2)):
        eq = (1 + r).cumprod()
        on = (eq > eq.rolling(n, min_periods=n // 2).mean()).shift(1).fillna(True)
        out[f"equity_ma_{n}"] = rep(r.where(on, 0.0))
    best = max(out, key=lambda k: (out[k]["cagr"] / abs(out[k]["max_dd"])) if out[k]["max_dd"] < 0 else -1)
    out["best_by_calmar"] = best
    return out


def event_study(p: Panel, entries: pd.DataFrame, side: int = 1, horizons=(1, 2, 3, 5, 10, 15, 20, 40, 60)) -> dict:
    """Return from next-bar open to the close h bars later after each signal (in-sample diagnostic)."""
    o_next = p.o.shift(-1)
    out = {}
    for h in horizons:
        fwd = side * (p.c.shift(-h) / o_next - 1)
        x = fwd[entries.reindex_like(fwd).fillna(False).astype(bool)].stack().dropna()
        if len(x) < 10:
            continue
        out[h] = {"n": int(len(x)), "mean": round(float(x.mean()), 4), "hit": round(float((x > 0).mean()), 3),
                  "t": round(float(x.mean() / x.std() * math.sqrt(len(x))), 2) if x.std() > 0 else None,
                  "per_bar": round(float(x.mean() / h), 5)}
    if out:
        out["best_holding_bars"] = max((k for k in out if isinstance(k, int)), key=lambda k: out[k]["t"] or -9)
    return out


def exit_grid_study(p: Panel, entries: pd.DataFrame, side: int = 1, H: int = 40,
                    stops=(0.02, 0.03, 0.05, 0.08, 0.12, None), tps=(0.03, 0.05, 0.10, 0.15, 0.25, None),
                    holds=(3, 5, 10, 20, 40), cost: float = 0.003, max_events: int = 20000) -> dict:
    """Simulate every (stop %, target %, max hold) on real high/low paths after each entry
    (entry = next bar open; stop checked before target inside a bar). Vectorized.
    In-sample diagnostic: register the best combination as an exit config and let the gate judge it."""
    ev = entries.reindex_like(p.c).fillna(False).astype(bool).to_numpy(copy=True)
    ev[-1] = False
    ii, jj = np.nonzero(ev)
    if len(ii) < 20:
        return {}
    if len(ii) > max_events:
        sel = np.random.default_rng(0).choice(len(ii), max_events, replace=False)
        ii, jj = ii[sel], jj[sel]
    O, Hh, L, C = (x.to_numpy() for x in (p.o, p.h, p.l, p.c))
    T = len(O)
    e = ii + 1
    px = O[e, jj]
    ok = np.isfinite(px) & (px > 0)
    e, jj, px = e[ok], jj[ok], px[ok]
    steps = np.arange(H)
    rows_idx = np.minimum(e[:, None] + steps[None, :], T - 1)
    valid = (e[:, None] + steps[None, :]) <= T - 1
    hi = Hh[rows_idx, jj[:, None]] / px[:, None] - 1
    lo = L[rows_idx, jj[:, None]] / px[:, None] - 1
    cl = C[rows_idx, jj[:, None]] / px[:, None] - 1
    if side < 0:
        hi, lo, cl = -lo, -hi, -cl
    big = H + 10
    out = []
    for hold in holds:
        if hold > H:
            continue
        win = valid & (steps[None, :] < hold)
        last = np.minimum(hold, valid.sum(axis=1)) - 1
        base = cl[np.arange(len(e)), np.maximum(last, 0)]
        for sl in stops:
            s_hit = (lo <= -sl) & win if sl is not None else np.zeros_like(win)
            s_first = np.where(s_hit.any(1), s_hit.argmax(1), big)
            for tp in tps:
                t_hit = (hi >= tp) & win if tp is not None else np.zeros_like(win)
                t_first = np.where(t_hit.any(1), t_hit.argmax(1), big)
                r = np.where((s_first <= t_first) & (s_first < big), -(sl or 0),
                             np.where(t_first < big, tp or 0, base)) - cost
                bars = np.minimum(np.minimum(s_first, t_first), last) + 1
                out.append({"stop": sl, "target": tp, "max_hold": hold, "n": int(len(r)),
                            "mean": float(r.mean()), "hit": float((r > 0).mean()),
                            "per_bar": float(r.mean() / max(bars.mean(), 1)),
                            "t": float(r.mean() / r.std() * math.sqrt(len(r))) if r.std() > 0 else 0.0})
    df = pd.DataFrame(out).sort_values("t", ascending=False)
    return {"top": df.head(10).round(4).to_dict("records"), "n_events": int(len(e)), "table": df}
