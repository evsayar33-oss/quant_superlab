"""Discovery scan: try EVERYTHING on a universe, then rank honestly.

  * every entry/exit rule x every parameter variant x chosen filters (signal exit)
  * every weight strategy (price factors, fundamental factors, calendar) x its grid
Each family (one rule or one strategy) gets its own walk-forward OOS record.
Full-sample Deflated Sharpe uses the TOTAL number of trials in the scan, so a lucky
variant among thousands cannot look significant. A global PBO measures how much the
"pick the best backtest" step itself is overfit.

The scan never writes decisions. It proposes hypotheses (YAML snippet) for the families
that look best out of sample; those must then pass the full gate in run.py.
"""
from __future__ import annotations

import itertools
import math
import time

import numpy as np
import pandas as pd

from lab import candidates as CD
from lab import metrics, rules
from lab.engine import Costs
from lab.panel import Panel
from lab.strategies import REGISTRY
from lab.strategies.fundamental_factors import NoData
from lab.validation import _matrix, walk_forward


def _families(R, TO, fam_of, sr_d, K, trial_srs, ppy, costs, errors):
    rows = []
    for fam in sorted(set(fam_of.values())):
        cols = [k for k, f in fam_of.items() if f == fam]
        if sr_d[cols].notna().sum() == 0:
            errors[fam] = "no trades / flat returns in every variant"
            continue
        oos, oos_to, log = walk_forward(R[cols], TO[cols])
        best = sr_d[cols].idxmax()
        ok = len(oos) > 60
        rows.append({
            "family": fam,
            "variants": len(cols),
            "best_variant": best,
            "best_full_sharpe": round(float(sr_d[best] * math.sqrt(ppy)), 3),
            "best_full_dsr": round(metrics.dsr(R[best].iloc[int(ppy):], K, trial_srs), 3),
            "wf_oos_sharpe": round(metrics.sharpe(oos), 3) if ok else None,
            "wf_oos_cagr": round(metrics.cagr(oos), 4) if ok else None,
            "wf_oos_maxdd": round(metrics.max_drawdown(oos), 4) if ok else None,
            "wf_oos_2x_cost_sharpe": round(metrics.sharpe(oos - oos_to * costs.per_turnover), 3) if ok else None,
            "family_pbo": round(v, 3) if (v := metrics.pbo(R[cols].iloc[int(ppy):])) is not None else None,
        })
    return pd.DataFrame(rows).sort_values("wf_oos_sharpe", ascending=False, na_position="last")


def scan(p: Panel, costs: Costs, families: str = "all", filters=("none",), side: str = "long",
         rule_names: list[str] | None = None, combo_top: int = 6, combo_within=(0, 3, 5)) -> dict:
    """Stage A: every rule x variant x filter and every strategy x grid (each idea ALONE).
    Stage B: the best `combo_top` rule families are paired (A confirmed by B within 0/3/5 bars),
    each with its best stage-A settings -> every ordered pair is tested (ideas COMBINED).
    All stages count as trials for the deflated statistics."""
    t0 = time.time()
    metrics.set_periods(p.ppy)
    all_runs, fam_of, par_of, errors = {}, {}, {}, {}
    todo = []
    if families in ("all", "rules"):
        for name in (rule_names or list(rules.RULES)):
            todo.append(CD.RuleCandidate(name, filters, None, side, staged=False))
    if families in ("all", "strategies", "factors"):
        for name, s in REGISTRY.items():
            if name == "equal_weight":
                continue
            if families == "factors" and s.kind != "fundamental":
                continue
            if s.kind == "fundamental" and not p.fund:
                continue
            todo.append(CD.StrategyCandidate(name))

    def run(cand, vs):
        runs, err = CD.run_all(cand, p, vs, costs)
        for v in vs:
            if v.key in runs:
                fam_of[v.key], par_of[v.key] = cand.name, v.params
        all_runs.update(runs)
        if err:
            errors[cand.name] = str(list(err.values())[0])[:200]
        print(f"[scan] {cand.name:32s} {len(runs):4d} variants ({len(err)} failed)  t={time.time() - t0:.0f}s")
    for cand in todo:
        run(cand, cand.variants())

    # ---- stage B: two-signal combinations of the strongest rule families
    R, TO = _matrix(all_runs, p.index)
    sr_d = R.mean() / R.std().replace(0, np.nan)
    stage_a = _families(R, TO, fam_of, sr_d, R.shape[1], list(sr_d.dropna()), p.ppy, costs, {})
    rule_rows = stage_a[stage_a["family"].isin(rules.RULES) & stage_a["wf_oos_sharpe"].notna()].head(combo_top)
    best = {r.family: par_of[r.best_variant] for r in rule_rows.itertuples()}
    for a_name, b_name in itertools.permutations(best, 2):
        pa, pb = best[a_name], best[b_name]
        cand = CD.RuleCandidate(a_name, [pa["_filter"]], None, side, staged=False, confirm=b_name,
                                confirm_within=list(combo_within),
                                confirm_params={k: v for k, v in pb.items() if not k.startswith("_")})
        gp = {k: v for k, v in pa.items() if not k.startswith("_")}
        vs = []
        for w in combo_within:
            prm = {**gp, "_filter": pa["_filter"], "_exit": 0, "_size": 0, "_cparams": cand.confirm_points[0], "_cwithin": w}
            vs.append(CD.Variant(cand._key(gp, pa["_filter"], 0, 0, prm), prm))
        run(cand, vs)

    R, TO = _matrix(all_runs, p.index)
    K = R.shape[1]
    sr_d = R.mean() / R.std().replace(0, np.nan)
    trial_srs = list(sr_d.dropna())
    board = _families(R, TO, fam_of, sr_d, K, trial_srs, p.ppy, costs, errors)
    ann = math.sqrt(p.ppy)
    variants = pd.DataFrame({
        "family": [fam_of[k] for k in R.columns], "variant": R.columns,
        "sharpe": (sr_d * ann).round(3).values,
        "cagr": [round(metrics.cagr(R[k]), 4) for k in R.columns],
        "max_dd": [round(metrics.max_drawdown(R[k]), 4) for k in R.columns],
        "turnover_ann": (TO.mean() * p.ppy).round(2).values,
    }).sort_values("sharpe", ascending=False)
    bench = CD.run_all(CD.StrategyCandidate("equal_weight"), p,
                       CD.StrategyCandidate("equal_weight").variants(), costs, workers=1)[0]
    b = list(bench.values())[0][0]
    return {
        "universe": p.name,
        "n_trials": K,
        "global_pbo": round(g, 3) if (g := metrics.pbo(R.iloc[int(p.ppy):])) is not None else None,
        "benchmark_sharpe": round(metrics.sharpe(b.iloc[int(p.ppy):]), 3),
        "reality_check_p": metrics.reality_check(R.iloc[int(p.ppy):], b, n=300),
        "timeframe": p.freq,
        "board": board,
        "variants": variants,
        "combos_tested": int(sum(1 for f in set(fam_of.values()) if "+" in f)),
        "errors": errors,
        "seconds": round(time.time() - t0),
    }


def to_markdown(res: dict, top: int = 25) -> str:
    b = res["board"].head(top)
    lines = [f"# Scan — {res['universe']}",
             "",
             f"- Variants tried: **{res['n_trials']}** · global PBO: **{res['global_pbo']}** · "
             f"equal-weight benchmark Sharpe: {res['benchmark_sharpe']} · Reality Check p (best vs benchmark): "
             f"{res.get('reality_check_p')} · timeframe {res.get('timeframe')} · runtime {res['seconds']}s",
             f"- Single ideas and two-signal combinations (`A+B` = A confirmed by B): {res.get('combos_tested', 0)} combo families. "
             "Every variant's own result is in the matching `_variants.csv`.",
             "- Ranked by walk-forward OOS Sharpe per family. Full-sample DSR is deflated by ALL trials.",
             "- A scan result is a LEAD, not a decision. Register a hypothesis and run the gate.",
             "",
             "| # | family | variants | WF OOS Sharpe | OOS CAGR | OOS MaxDD | 2x-cost Sharpe | family PBO | best full Sharpe | DSR(all trials) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(b.itertuples(), 1):
        lines.append(f"| {i} | {r.family} | {r.variants} | {r.wf_oos_sharpe} | {r.wf_oos_cagr} | {r.wf_oos_maxdd} | "
                     f"{r.wf_oos_2x_cost_sharpe} | {r.family_pbo} | {r.best_full_sharpe} | {r.best_full_dsr} |")
    if res["errors"]:
        lines += ["", "## Skipped / failed families", *[f"- {k}: {v}" for k, v in res["errors"].items()]]
    return "\n".join(lines)


def suggest_yaml(res: dict, universe: str, n: int = 5, start_id: int = 900) -> str:
    out = ["# Suggested hypotheses from the scan (copy into hypotheses/registry.yaml, give real ids)"]
    good = res["board"][(res["board"]["wf_oos_sharpe"].fillna(-9) > res["benchmark_sharpe"])].head(n)
    for i, r in enumerate(good.itertuples()):
        if "+" in r.family:
            a, b = r.family.split("+", 1)
            head = [f"  rule: {a}", f"  confirm: {b}", "  confirm_within: [0, 3, 5]"]
            key = "rule"
        else:
            key = "rule" if r.family in rules.RULES else "strategy"
            head = [f"  {key}: {r.family}"]
        out += [f"- id: S{start_id + i}", *head, f"  universe: {universe}",
                "  for_system: TODO", "  status: active",
                *(['  filters: [none, trend_sma200, regime_bench200]', '  side: long'] if key == "rule" else []),
                f"  note: \"scan lead: WF OOS Sharpe {r.wf_oos_sharpe}, family PBO {r.family_pbo}\""]
    return "\n".join(out)
