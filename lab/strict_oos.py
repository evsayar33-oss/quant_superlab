"""Train-only, fold-local candidate provenance for the central lab gate.

Full-history pre-computation of *causal* returns is permissible as a
performance cache. Candidate STAGE SELECTION is NOT: each stage's
seeds must be determined from the fold's train slice only.

This module never changes PAPER/live positions. Test-fold trades are
attributed to the variant selected before that fold, not to the final
variant chosen after looking at all of history.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from lab import candidates as CD


def _rank(runs, keys, index, a, b, n=1):
    """Select candidates using *only* [a,b) historical train returns."""
    values = []
    for key in dict.fromkeys(keys):
        if key not in runs:
            continue
        series = runs[key][0].reindex(index[a:b])
        if series.isna().any():
            continue  # missing historical returns are not cash / successes
        arr = series.to_numpy(dtype=float)
        if not np.isfinite(arr).all() or len(arr) < 2:
            continue
        sd = float(np.std(arr, ddof=1))
        if sd <= 0:
            continue
        sr = float(np.mean(arr) / sd)
        if np.isfinite(sr):
            values.append((sr, key))
    values.sort(key=lambda x: (-x[0], x[1]))
    return [key for _, key in values[:n]]


def nested_walk_forward(cand, panel, costs, stage1, runs, train_years=3.0,
                        test_months=6, *, warm=None, ppy=None):
    """Return train-only selected OOS, real fold-specific closed trades and audit.

    Secondary exit, sizing and overlay hypotheses are *generated anew
    per fold* from the training window; never from full-sample winners.

    Selected variant returns are cached but must be causal in t. Actual
    stop/entry execution and cross-fold model transitions are separate
    questions, exposed as explicit limitations (not hidden as a fill).
    """
    ppy = ppy or panel.ppy
    index = panel.index
    train = int(train_years * ppy)
    step = max(int(test_months * ppy / 12), 1)
    warm = int(ppy * 260 / 252) if warm is None else int(warm)
    t0 = warm + train
    if not stage1:
        raise ValueError("STRICT_OOS_NO_INITIAL_HYPOTHESES")
    cache = dict(runs)
    by_key = {v.key: v for v in stage1}
    first = list(by_key)
    all_tested = set(first)
    failures = {}
    parts, turnover_parts, logs, trade_parts = [], [], [], []
    cross_boundary = 0
    data_gaps = 0
    transitions = 0
    previous_key = None

    def expand(variants):
        pending = []
        for v in variants:
            all_tested.add(v.key)
            if v.key not in by_key:
                by_key[v.key] = v
            if v.key not in cache and v.key not in failures:
                pending.append(v)
        if pending:
            output, errors = CD.run_all(cand, panel, pending, costs)
            cache.update(output)
            failures.update(errors)
        return [v.key for v in variants if v.key in cache]

    while t0 < len(index) - 5:
        te = min(t0 + step, len(index))
        a = t0 - train
        available = [key for key in first if key in cache]
        if isinstance(cand, CD.RuleCandidate) and cand.staged:
            seeds = _rank(cache, available, index, a, t0, cand.stage2_top)
            next_stage = [by_key[k] for k in seeds]
            available += expand(cand.variants(stage=2, seeds=next_stage))
            seeds2 = _rank(cache, available, index, a, t0, 2)
            available += expand(cand.variants(stage=3, seeds=[by_key[k] for k in seeds2]))
        # Portfolio overlays are also selected from train-only seeds.
        seeds3 = _rank(cache, available, index, a, t0, 2)
        available += expand(cand.overlay_variants([by_key[k] for k in seeds3]))
        chosen = _rank(cache, available, index, a, t0, 1)
        if not chosen:
            raise ValueError("STRICT_OOS_FOLD_HAS_NO_TRAIN_QUALIFIED_VARIANT")
        key = chosen[0]
        s, turnover, trades = cache[key]
        test_index = index[t0:te]
        sr = s.reindex(test_index)
        to = turnover.reindex(test_index)
        if sr.isna().any() or to.isna().any():
            data_gaps += int(sr.isna().sum() + to.isna().sum())
            # Do not pretend gaps were zero-profit positions.
            raise ValueError("STRICT_OOS_MISSING_TEST_RETURNS_OR_TURNOVER")
        if not np.isfinite(sr.values).all() or not np.isfinite(to.values).all():
            raise ValueError("STRICT_OOS_NONFINITE_TEST_VALUES")
        if previous_key is not None and key != previous_key:
            transitions += 1
        previous_key = key
        parts.append(sr)
        turnover_parts.append(to)
        trades_this_fold = 0
        if isinstance(cand, CD.RuleCandidate):
            if not isinstance(trades, pd.DataFrame):
                raise ValueError("STRICT_OOS_MISSING_RULE_TRADE_LEDGER")
            if not trades.empty:
                # There is no evidence of a strategy-switch fill for a
                # trade opened before the fold, so exclude it from OOS
                # trade statistics and flag the boundary-execution gap.
                entry = pd.to_datetime(trades["entry"])
                exit_ = pd.to_datetime(trades["exit"])
                opened = (entry >= test_index[0]) & (entry <= test_index[-1])
                closed = (exit_ >= test_index[0]) & (exit_ <= test_index[-1])
                cross_boundary += int((closed & ~opened).sum())
                completed = trades.loc[opened & closed].copy()
                if not completed.empty:
                    completed["_fold"] = len(logs)
                    trade_parts.append(completed)
                    trades_this_fold = len(completed)
        logs.append({
            "test_start": str(test_index[0]), "test_end": str(test_index[-1]),
            "train_start": str(index[a]), "train_end": str(index[t0-1]),
            "variant": key,
            "train_eligible_variants": len(set(available)),
            "train_only_seed_selection": True,
            "completed_fold_trades": int(trades_this_fold),
            "oos_sharpe": round(float(sr.mean() / sr.std() * math.sqrt(ppy)), 3)
                          if sr.std() > 0 else 0.0,
        })
        t0 = te

    oos = pd.concat(parts) if parts else pd.Series(dtype=float)
    turn = pd.concat(turnover_parts) if turnover_parts else pd.Series(dtype=float)
    fold_trades = pd.concat(trade_parts, ignore_index=True) if trade_parts else pd.DataFrame()
    return {
        "oos": oos, "turnover": turn,
        "trades": fold_trades,
        "folds": logs,
        "cache": cache,
        "variants": by_key,
        "errors": failures,
        "trials": len(all_tested),
        "cross_boundary_trades": cross_boundary,
        "variant_switches_without_execution_replay": transitions,
        "missing_test_bars": data_gaps,
        "complete": bool(logs) and data_gaps == 0,
        "fold_execution_verified": cross_boundary == 0 and transitions == 0,
        "interpretation": "TRAIN_ONLY_VARIANT_SELECTION_NOT_EXECUTABLE_FILL_PROOF",
    }
