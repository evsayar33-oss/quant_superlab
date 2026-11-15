"""H117: predeclared transaction-cost reduction experiments for H116 rotations.

No production changes; no live orders. All candidate weights are strictly
functions of completed 4h bars at or before their timestamp.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import importlib.util

# The unittest discovery path contains another module called research.py;
# import the H116 reference by exact file path to avoid shadowing.
_spec = importlib.util.spec_from_file_location("h116_reference", ROOT / "research/h116/research.py")
if _spec is None or _spec.loader is None:
    raise ImportError("MISSING_H116_REFERENCE")
h116 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h116)

MODELS = (
    "mom2_baseline", "regime_raw",
    "regime_7d", "regime_14d", "regime_28d",
    "regime_band20", "regime_band30", "regime_band40",
    "regime_7d_band20", "regime_14d_band20",
    "rotation_7d", "drawdown_7d",
    "mom2_25_regime75", "mom2_50_regime50", "mom2_75_regime25",
)
COSTS = h116.COST_BPS
INTERVALS = (42, 84, 168)
SCHEMA = "h117.turnover_resilience.v1"


def spaced_rebalance(raw: pd.DataFrame, interval: int, zero_exit: bool = True) -> pd.DataFrame:
    """Only update scheduled entries; exit to cash immediately on complete risk-off."""
    if interval < 1:
        raise ValueError("INVALID_REBALANCE_INTERVAL")
    out = np.zeros_like(raw.to_numpy(dtype=float))
    current = np.zeros(len(raw.columns))
    for i, target in enumerate(raw.to_numpy(dtype=float)):
        if i % interval == 0:
            current = target.copy()
        elif zero_exit and target.sum() < 1e-10:
            current = np.zeros_like(current)
        out[i] = current
    return pd.DataFrame(out, index=raw.index, columns=raw.columns)


def wide_band(raw: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Take only meaningful allocation changes, but never block full risk-off."""
    if not 0 <= threshold <= 1:
        raise ValueError("INVALID_BAND")
    return h116.banded(raw, threshold)


def mix(a: pd.DataFrame, b: pd.DataFrame, a_share: float) -> pd.DataFrame:
    if not 0 <= a_share <= 1:
        raise ValueError("INVALID_BLEND")
    if not a.index.equals(b.index) or not a.columns.equals(b.columns):
        raise ValueError("BLEND_INDEX_MISMATCH")
    return a * a_share + b * (1 - a_share)


def build(closes: pd.DataFrame) -> dict[str, pd.DataFrame]:
    prior = h116.make_weights(closes)
    mom = prior["h054_mom2"]
    regime = prior["top2_btc_regime"]
    rotation = prior["top2_90d"]
    draw = prior["top2_drawdown_guard"]
    variants = {
        "mom2_baseline": mom,
        "regime_raw": regime,
        "regime_7d": spaced_rebalance(regime, 42),
        "regime_14d": spaced_rebalance(regime, 84),
        "regime_28d": spaced_rebalance(regime, 168),
        "regime_band20": wide_band(regime, 0.20),
        "regime_band30": wide_band(regime, 0.30),
        "regime_band40": wide_band(regime, 0.40),
        "regime_7d_band20": spaced_rebalance(wide_band(regime, 0.20), 42),
        "regime_14d_band20": spaced_rebalance(wide_band(regime, 0.20), 84),
        "rotation_7d": spaced_rebalance(rotation, 42),
        "drawdown_7d": spaced_rebalance(draw, 42),
        "mom2_25_regime75": mix(mom, regime, 0.25),
        "mom2_50_regime50": mix(mom, regime, 0.50),
        "mom2_75_regime25": mix(mom, regime, 0.75),
    }
    if tuple(variants) != MODELS:
        raise AssertionError("FROZEN_H117_CANDIDATES_CHANGED")
    for name, w in variants.items():
        if not np.isfinite(w.to_numpy()).all() or (w.to_numpy() < -1e-10).any() or (
            w.sum(axis=1) > 1.000001).any():
            raise ValueError(name + ":INVALID_EXPOSURE")
    return variants


def run(opens: pd.DataFrame, closes: pd.DataFrame, sources: dict) -> tuple[dict, list[dict]]:
    variants = build(closes)
    rows = []
    for name in MODELS:
        for fee in COSTS:
            ledger = h116.simulate(opens, variants[name], fee)
            rows.append({
                "candidate": name, "cost_bps_per_side": fee,
                "full": h116.stats(ledger),
                "splits": {period: h116.stats(ledger.loc[start:pd.Timestamp(end)-h116.STEP])
                           for period, (start, end) in h116.SPLITS.items()},
            })
    idx = {(r["candidate"], r["cost_bps_per_side"]): r for r in rows}
    base = idx[("mom2_baseline", 15)]
    raw = idx[("regime_raw", 15)]
    winners = []
    for name in MODELS[2:]:
        x15, x30, x45 = (idx[(name, c)] for c in COSTS)
        base30, base45 = idx[("mom2_baseline", 30)], idx[("mom2_baseline", 45)]
        # Stronger gate than H116: robustness persists at 3x per-side trading cost.
        if (x15["full"]["return_pct"] > base["full"]["return_pct"]
            and x30["full"]["return_pct"] > base30["full"]["return_pct"]
            and x45["full"]["return_pct"] > base45["full"]["return_pct"]
            and x15["splits"]["validation_2023_24"]["return_pct"] >
                base["splits"]["validation_2023_24"]["return_pct"]
            and x15["splits"]["reused_tail_2025_26"]["return_pct"] >
                base["splits"]["reused_tail_2025_26"]["return_pct"]
            and x15["full"]["max_dd_pct"] >= base["full"]["max_dd_pct"] - 5
            and x15["full"]["turnover"] < raw["full"]["turnover"] * 0.90):
            winners.append(name)
    winners.sort(key=lambda n: idx[(n, 15)]["full"]["return_pct"], reverse=True)
    summary = {
        "schema": SCHEMA,
        "research_only": True,
        "alpha_accepted": False,
        "future_profit_verified": False,
        "source_data": sources,
        "models": list(MODELS),
        "model_count": len(MODELS),
        "scenarios": len(rows),
        "comparison": "MOM2 vs H116 raw BTC regime vs fixed turnover reductions",
        "costs_per_traded_side_bps": list(COSTS),
        "windows": h116.SPLITS,
        "qualified_45bps_cost_robust": winners,
        "reach_200pct_at_15bps": [
            name for name in MODELS if idx[(name, 15)]["full"]["return_pct"] >= 200
        ],
        "reliability_notes": [
            "History is already viewed; not untouched out-of-sample",
            "Scheduled weights implicitly assume intra-period rebalancing only at new target changes; price-drift transaction costs may be understated",
            "Funding, multi-venue execution and spread history unverified",
            "All cross-asset symbols selected from surviving market listings",
            "No portfolio/live trading authorization",
        ],
    }
    return summary, rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="results/h117")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    opens, closes, sources = h116.load_prices()
    summary, rows = run(opens, closes, sources)
    (out/"summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    (out/"matrix.json").write_text(json.dumps(rows, indent=2, allow_nan=False))
    pd.DataFrame([
        {"candidate": r["candidate"], "cost_bps_per_side": r["cost_bps_per_side"],
         "period": p, **v}
        for r in rows for p, v in [("full", r["full"]), *list(r["splits"].items())]
    ]).to_csv(out/"matrix.csv", index=False)
    (out/"committee.md").write_text(
        "# H117 — turnover resilient crypto strategy research\n\n"
        "45bp cost-robust historical candidates: " +
        (", ".join(summary["qualified_45bps_cost_robust"]) or "NONE") + "\n\n"
        "200% historical net-return candidates (15bp): " +
        (", ".join(summary["reach_200pct_at_15bps"]) or "NONE") +
        "\n\nNOT validated prospective alpha; no production/live authorization.\n")
    print(json.dumps({"45bps_cost_robust": summary["qualified_45bps_cost_robust"],
                      "hit200_15bps": summary["reach_200pct_at_15bps"]}, indent=2))


if __name__ == "__main__":
    main()
