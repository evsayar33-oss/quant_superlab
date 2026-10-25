"""Validation pipeline: the gate a hypothesis must pass before any bot may use it.

  1. Sweep every variant on the full history (causal -> reusable slices). Counts trials.
     Rule candidates: stage 2 tries every exit config on the best stage-1 variants,
     stage 3 tries every position-sizing mode on the best stage-2 variants.
  2. Walk-forward: in each rolling train window pick the best Sharpe variant, trade it on the
     next test window. Stitched test windows = out-of-sample (OOS) record. Windows in bars.
  3. Significance: Deflated Sharpe (all trials), PBO via CSCV, White Reality Check.
  4. Realism: 2x cost stress, risk-free excess Sharpe, USD-converted result for local markets.
  5. Robustness: block bootstrap, yearly stability, regimes (trend/vol/VIX/curve), 1-bar delay,
     random-entry benchmark, parameter neighbourhood, price-noise, Monte Carlo trade shuffle,
     walk-forward efficiency.
  6. Timing & profit studies: event study (best holding time), stop/target/hold grid, overlays.
  7. Verdict ACCEPT / WATCH / REJECT with every failed check written out.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lab import candidates as CD
from lab import metrics, robustness as RB
from lab.engine import Costs
from lab.panel import Panel
from lab.trade_engine import trade_stats

GATE = {
    "min_oos_years": 3.0,
    "min_dsr": 0.90,
    "min_oos_sharpe": 0.5,          # on excess-of-risk-free (USD for local-currency markets)
    "min_p_sharpe_pos": 0.85,
    "max_dd_floor": -0.45,
    "min_pos_year_frac": 0.55,
    "max_pbo": 0.50,
    "max_reality_check_p": 0.10,
    "min_trades": 30,               # rule candidates only
    "min_delay_retained": 0.40,     # Sharpe kept when executed one bar later
    "max_random_entry_p": 0.10,     # rule candidates: entry must beat random entries
    "min_neighbour_share_pos": 0.50,
}


def _matrix(runs: dict, index) -> tuple[pd.DataFrame, pd.DataFrame]:
    R = pd.DataFrame({k: v[0] for k, v in runs.items()}).reindex(index).fillna(0.0)
    TO = pd.DataFrame({k: v[1] for k, v in runs.items()}).reindex(index).fillna(0.0)
    return R, TO


def walk_forward(R: pd.DataFrame, TO: pd.DataFrame, train_years=3.0, test_months=6, warm=None, ppy=None):
    ppy = ppy or metrics.ann()
    idx = R.index
    train, step = int(train_years * ppy), max(int(test_months * ppy / 12), 1)
    warm = int(ppy * 260 / 252) if warm is None else warm
    parts, tparts, log = [], [], []
    t0 = warm + train
    while t0 < len(idx) - 5:
        te = min(t0 + step, len(idx))
        tr = R.iloc[t0 - train:t0]
        sd = tr.std()
        sr = (tr.mean() / sd.where(sd > 0)).fillna(-np.inf)
        best = sr.idxmax()
        parts.append(R[best].iloc[t0:te])
        tparts.append(TO[best].iloc[t0:te])
        oos_sr = metrics.sharpe(R[best].iloc[t0:te])
        log.append({"test_start": str(idx[t0]), "test_end": str(idx[te - 1]), "variant": best,
                    "is_sharpe": round(float(sr[best] * math.sqrt(ppy)), 3) if np.isfinite(sr[best]) else None,
                    "oos_sharpe": round(oos_sr, 3)})
        t0 += step
    if not parts:
        return pd.Series(dtype=float), pd.Series(dtype=float), log
    return pd.concat(parts), pd.concat(tparts), log


def block_bootstrap(r: pd.Series, n: int = 1000, block: int | None = None, seed: int = 7) -> dict:
    x = r.dropna().values
    block = block or max(int(metrics.ann() / 12), 5)
    if len(x) < block * 3:
        return {"p_sharpe_pos": None, "cagr_p05": None, "maxdd_p05": None}
    rng = np.random.default_rng(seed)
    T = len(x)
    srs, cg, dd = [], [], []
    for _ in range(n):
        out = np.empty(T); i = 0
        while i < T:
            s = rng.integers(0, T - block)
            L = min(rng.geometric(1 / block), T - i)
            seg = x[s:s + L]
            out[i:i + len(seg)] = seg
            i += max(len(seg), 1)
        srs.append(out.mean() / out.std() * math.sqrt(metrics.ann()) if out.std() > 0 else 0)
        eq = np.cumprod(1 + out)
        cg.append(eq[-1] ** (metrics.ann() / T) - 1 if eq[-1] > 0 else -1)
        dd.append((eq / np.maximum.accumulate(eq) - 1).min())
    return {"p_sharpe_pos": round(float(np.mean(np.array(srs) > 0)), 3),
            "cagr_p05": round(float(np.percentile(cg, 5)), 4),
            "maxdd_p05": round(float(np.percentile(dd, 5)), 4)}


def yearly_sharpe(r: pd.Series) -> dict:
    return {str(y): round(metrics.sharpe(g), 2) for y, g in r.groupby(r.index.year) if len(g) > metrics.ann() / 6}


def to_usd(r: pd.Series, fx: pd.Series | None) -> pd.Series:
    """Local-currency returns -> USD returns (fx = local price of 1 USD)."""
    if fx is None:
        return r
    f = fx.reindex(r.index).ffill()
    return ((1 + r) * (f.shift(1) / f) - 1).fillna(r)


def verdict(rep: dict) -> tuple[str, list[str]]:
    o, why = rep["oos"], []
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            ok = False
            why.append(msg)
    g = GATE
    main_sr = rep["gate_sharpe"]
    check(o["years"] >= g["min_oos_years"], f"OOS too short ({o['years']}y < {g['min_oos_years']}y)")
    check(rep["dsr"] >= g["min_dsr"], f"DSR {rep['dsr']} < {g['min_dsr']} (luck not excluded after {rep['n_trials']} trials)")
    check(main_sr >= g["min_oos_sharpe"], f"OOS Sharpe ({rep['gate_sharpe_basis']}) {main_sr} < {g['min_oos_sharpe']}")
    dd = min(o["max_dd"], (rep.get("oos_usd") or {}).get("max_dd", 0))   # worst of local and USD
    check(dd >= g["max_dd_floor"], f"OOS MaxDD {dd} worse than {g['max_dd_floor']} (local or USD)")
    bs = rep["bootstrap"]["p_sharpe_pos"]
    check(bs is not None and bs >= g["min_p_sharpe_pos"], f"bootstrap P(SR>0) {bs} < {g['min_p_sharpe_pos']}")
    ys = list(rep["yearly_sharpe"].values())
    frac = (sum(v > 0 for v in ys) / len(ys)) if ys else 0
    check(frac >= g["min_pos_year_frac"], f"only {frac:.0%} of OOS years positive")
    check(rep["stress_2x_cost"]["sharpe"] > rep["benchmark"].get("sharpe", 0),
          "with 2x costs it does not beat the equal-weight benchmark")
    if rep["pbo"] is not None:
        check(rep["pbo"] <= g["max_pbo"], f"PBO {rep['pbo']} > {g['max_pbo']} (variant selection is overfit)")
    if rep.get("reality_check_p") is not None:
        check(rep["reality_check_p"] <= g["max_reality_check_p"],
              f"Reality Check p {rep['reality_check_p']} > {g['max_reality_check_p']} (best variant may be data-mined)")
    ts = rep.get("trade_stats") or {}
    if "n_trades" in ts:
        check(ts["n_trades"] >= g["min_trades"], f"only {ts['n_trades']} OOS trades (< {g['min_trades']})")
    rob = rep.get("robustness", {})
    d = rob.get("delay") or {}
    if d.get("retained") is not None:
        check(d["retained"] >= g["min_delay_retained"], f"1-bar delay keeps only {d['retained']:.0%} of Sharpe (latency-fragile)")
    re_ = rob.get("random_entry") or {}
    if re_.get("p_value") is not None:
        check(re_["p_value"] <= g["max_random_entry_p"], f"random entries match it (p={re_['p_value']}): the edge is in the exits, not the signal")
    nb = rob.get("neighbourhood") or {}
    if nb.get("neighbours", 0) >= 2 and nb.get("share_positive") is not None:
        check(nb["share_positive"] >= g["min_neighbour_share_pos"],
              f"parameter spike: only {nb['share_positive']:.0%} of neighbouring settings are profitable")
    if ok:
        return "ACCEPT", ["all gate checks passed"]
    soft = main_sr > 0 and rep["dsr"] >= 0.5 and o["years"] >= 1
    return ("WATCH" if soft else "REJECT"), why


def validate(spec: dict, p: Panel, costs: Costs, train_years: float = 3.0, test_months: int = 6,
             studies: bool = True) -> dict:
    metrics.set_periods(p.ppy)
    years = len(p.index) / p.ppy
    if years < train_years + 1 + 2:  # short history (e.g. 2y of free 1h stock data): shrink the train window
        train_years = max(0.5, round((years - 1) / 3, 2))
        test_months = max(1, int(train_years * 12 / 4))
    cand = CD.from_spec(spec)
    vs = cand.variants()
    runs, errors = CD.run_all(cand, p, vs, costs)
    if not runs:
        raise RuntimeError(f"all variants failed: {list(errors.values())[:3]}")

    def top_keys(n):
        Rx, _ = _matrix(runs, p.index)
        return list(Rx.mean().div(Rx.std().replace(0, np.nan)).sort_values(ascending=False).index[:n])
    if isinstance(cand, CD.RuleCandidate) and cand.staged:
        seeds = [v for v in vs if v.key in set(top_keys(cand.stage2_top))]
        vs2 = cand.variants(stage=2, seeds=seeds)
        r2, e2 = CD.run_all(cand, p, vs2, costs); runs.update(r2); errors.update(e2); vs += vs2
        seeds = [v for v in vs if v.key in set(top_keys(2))]
        vs3 = cand.variants(stage=3, seeds=seeds)
        r3, e3 = CD.run_all(cand, p, vs3, costs); runs.update(r3); errors.update(e3); vs += vs3
    # stage 4: portfolio overlays (vol target, drawdown brake, equity-curve filter) on the best 2
    seeds = [v for v in vs if v.key in set(top_keys(2))]
    vs4 = cand.overlay_variants(seeds)
    r4, e4 = CD.run_all(cand, p, vs4, costs); runs.update(r4); errors.update(e4); vs += vs4
    R, TO = _matrix(runs, p.index)
    n_trials = R.shape[1]
    trial_srs = list((R.mean() / R.std().replace(0, np.nan)).dropna())
    ppy = p.ppy

    oos, oos_to, wf_log = walk_forward(R, TO, train_years, test_months, ppy=ppy)
    ew = CD.StrategyCandidate("equal_weight")
    bench = list(CD.run_all(ew, p, ew.variants(), costs, workers=1)[0].values())[0][0]
    b_oos = bench.reindex(oos.index).fillna(0) if len(oos) else bench
    stress = oos - oos_to * costs.per_turnover if len(oos) else oos
    has_oos = len(oos) > max(30, ppy / 8)

    final_key = wf_log[-1]["variant"] if wf_log else R.columns[0]
    final_v = next(v for v in vs if v.key == final_key)
    trades = runs[final_key][2]
    tstats = None
    if isinstance(trades, pd.DataFrame) and has_oos:
        tstats = trade_stats(trades[trades["exit"] >= oos.index[0]], len(oos) / ppy)

    # ---- risk-free and currency
    rf = p.rf_per_bar() if p.rf_annual is not None else None
    local_ccy = p.fx is not None
    oos_usd = to_usd(oos, p.fx) if local_ccy and has_oos else oos
    gate_sr = metrics.sharpe(oos_usd, rf) if has_oos else 0.0
    basis = ("USD, excess of US T-bill" if local_ccy else "excess of T-bill") if rf is not None else \
        ("USD" if local_ccy else "raw")

    pbo_v = metrics.pbo(R.iloc[int(ppy):]) if n_trials > 1 else None
    rc = metrics.reality_check(R.iloc[int(ppy):], bench) if n_trials > 1 else None
    full_sweep = (pd.DataFrame({"variant": R.columns, "sharpe": (R.mean() / R.std().replace(0, np.nan) * math.sqrt(ppy)).values})
                  .sort_values("sharpe", ascending=False).head(15).round(3).to_dict("records"))
    rep = {
        "name": cand.name,
        "kind": "rule" if isinstance(cand, CD.RuleCandidate) else "strategy",
        "source": cand.source,
        "timeframe": p.freq,
        "bars_per_year": round(ppy, 1),
        "n_assets": int(p.c.shape[1]),
        "data_start": str(p.index[0]),
        "data_end": str(p.index[-1]),
        "costs": {"commission": costs.commission, "slippage": costs.slippage,
                  "funding_annual": costs.funding_annual, "borrow_annual": costs.borrow_annual},
        "survivorship_mask": p.member is not None,
        "n_trials": n_trials,
        "train_years": train_years, "test_months": test_months,
        "failed_variants": len(errors),
        "full_sample_top": full_sweep,
        "oos": metrics.summary(oos, oos_to, b_oos, rf) if has_oos else {"years": 0, "sharpe": 0, "max_dd": 0},
        "oos_usd": metrics.summary(oos_usd, rf=rf) if local_ccy and has_oos else None,
        "gate_sharpe": round(gate_sr, 3),
        "gate_sharpe_basis": basis,
        "dsr": round(metrics.dsr(oos, n_trials, trial_srs), 3) if has_oos else 0.0,
        "pbo": round(pbo_v, 3) if pbo_v is not None else None,
        "reality_check_p": round(rc, 3) if rc is not None else None,
        "benchmark": metrics.summary(b_oos) if len(b_oos) > 30 else {"sharpe": 0},
        "stress_2x_cost": {"sharpe": round(metrics.sharpe(stress), 3) if has_oos else 0.0},
        "bootstrap": block_bootstrap(oos),
        "yearly_sharpe": yearly_sharpe(oos) if has_oos else {},
        "regimes": metrics.regime_breakdown(oos, p.bench, p.macro) if has_oos else {},
        "calendar": metrics.calendar_profile(oos) if has_oos else {},
        "trade_stats": tstats,
        "walk_forward": wf_log,
        "wf_efficiency": RB.wf_efficiency(wf_log, oos) if has_oos else None,
        "final_variant": final_key,
        "final_params": final_v.params,
        "robustness": {},
        "studies": {},
    }
    if studies and has_oos:
        rob = rep["robustness"]
        rob["delay"] = RB.delay_test(cand, p, final_v, costs)
        rob["neighbourhood"] = RB.param_neighborhood(R, final_key)
        rob["noise"] = RB.noise_test(cand, p, final_v, costs)
        if isinstance(cand, CD.RuleCandidate):
            rob["random_entry"] = RB.random_entry_test(cand, p, final_v, costs)
            rob["mc_trade_shuffle"] = RB.mc_trade_shuffle(trades)
            sig = cand._signals(p, final_v)
            es = RB.event_study(p, sig.entry_long, 1)
            eg = RB.exit_grid_study(p, sig.entry_long, 1, cost=2 * costs.per_turnover)
            rep["studies"]["event_study_long"] = es
            rep["studies"]["exit_grid_long"] = {k: v for k, v in eg.items() if k != "table"}
            rep["_exit_table"] = eg.get("table")
            if sig.entry_short is not None and cand.side != "long":
                rep["studies"]["event_study_short"] = RB.event_study(p, sig.entry_short, -1)
        rep["studies"]["overlays"] = RB.overlays(oos, ppy)
    if studies and spec.get("protection_study", True):
        try:   # capital-protection diagnostic on the final variant's FULL history (covers more crises)
            from lab import protect
            rep["protection"] = protect.study_series(runs[final_key][0], p.bench, ppy, costs.per_turnover,
                                                     getattr(p, "market", "") or "multi")
        except Exception as e:  # noqa: BLE001 - a diagnostic must never break a validation
            rep["protection"] = {"error": str(e)}
    rep["verdict"], rep["reasons"] = verdict(rep)
    rep["targets"] = cand.targets(p, final_v)
    rep["_oos_returns"] = oos
    rep["_bench_oos"] = b_oos
    return rep
