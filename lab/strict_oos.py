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
    previous_weights = None
    realized_boundary_turnover = 0.0
    net_boundary_cost_adjustment = 0.0
    simulations = {}
    selected_bars = []
    column_names = panel.columns

    def held_at(key, at):
        # Only re-run the selected candidate, at most once per unique key.
        # Its ordinary simulated weights are the state available to the
        # original bar-return engine, NOT broker-executed position evidence.
        if key not in simulations:
            result = cand.run(panel, by_key[key], costs)
            if result.weights is None:
                raise ValueError("STRICT_OOS_CANNOT_ACCOUNT_TRANSITION_WEIGHTS")
            simulations[key] = result
        weights = simulations[key].weights
        if at in weights.index:
            pos = weights.loc[at].reindex(column_names)
            if pos.isna().any() or not np.isfinite(pos.to_numpy(dtype=float)).all():
                raise ValueError("STRICT_OOS_INVALID_POSITION_WEIGHTS")
            return pos.astype(float)
        if weights.empty or at < weights.index.min():
            # An inactive strategy is genuinely flat before its first entry.
            return pd.Series(0.0, index=column_names, dtype=float)
        raise ValueError("STRICT_OOS_UNOBSERVED_POSITION_BAR")

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
        switched = previous_key is None or key != previous_key
        if previous_key is not None and key != previous_key:
            transitions += 1
        # Model switching is ordinary portfolio rebalancing, NOT automatic
        # failure. Correct the first test bar's originally charged turnover
        # from the selected candidate's own historical holdings to the
        # portfolio holdings actually carried from the previous fold.
        if switched:
            new_held = held_at(key, test_index[0])
            prior = (previous_weights if previous_weights is not None
                     else pd.Series(0.0, index=column_names, dtype=float))
            handoff_turnover = float((new_held - prior).abs().sum())
            cached_turnover = float(to.iloc[0])
            cached_previous = held_at(key, index[t0 - 1])
            cached_net_change = float((new_held - cached_previous).abs().sum())
            # Same-bar entries/exits and partial fills can generate *real*
            # turnover without changing end-of-bar holdings. Preserve it:
            # replacing the entire cached turnover would make such trades free.
            internal_churn = max(0.0, cached_turnover - cached_net_change)
            actual_turnover = handoff_turnover + internal_churn
            if not (np.isfinite(actual_turnover) and np.isfinite(cached_turnover)):
                raise ValueError("STRICT_OOS_NONFINITE_HANDOFF_COST")
            adjustment = (actual_turnover - cached_turnover) * costs.per_turnover
            sr = sr.copy()
            to = to.copy()
            sr.iloc[0] -= adjustment
            to.iloc[0] = actual_turnover
            realized_boundary_turnover += handoff_turnover
            net_boundary_cost_adjustment += adjustment
        previous_weights = held_at(key, test_index[-1])
        previous_key = key
        parts.append(sr)
        turnover_parts.append(to)
        selected_bars.append(pd.Series(key, index=test_index))
        if isinstance(cand, CD.RuleCandidate) and not isinstance(trades, pd.DataFrame):
            raise ValueError("STRICT_OOS_MISSING_RULE_TRADE_LEDGER")
        logs.append({
            "test_start": str(test_index[0]), "test_end": str(test_index[-1]),
            "train_start": str(index[a]), "train_end": str(index[t0-1]),
            "variant": key,
            "train_eligible_variants": len(set(available)),
            "train_only_seed_selection": True,
            "switch_turnover_reconciled_to_prior_fold": bool(switched),
            "oos_sharpe": round(float(sr.mean() / sr.std() * math.sqrt(ppy)), 3)
                          if sr.std() > 0 else 0.0,
        })
        t0 = te

    oos = pd.concat(parts) if parts else pd.Series(dtype=float)
    turn = pd.concat(turnover_parts) if turnover_parts else pd.Series(dtype=float)
    # Trades that genuinely span two consecutive OOS folds are not
    # invalid just because the reporting windows changed. Count each
    # completed trade once if the SAME selected model remained active
    # throughout its entire life. Never count pre-OOS trades, nor pretend
    # a discarded model's historical entry happened in the OOS book.
    selected = pd.concat(selected_bars) if selected_bars else pd.Series(dtype=object)
    if isinstance(cand, CD.RuleCandidate):
        for key in dict.fromkeys(selected.tolist()):
            trades = cache[key][2]
            if not isinstance(trades, pd.DataFrame):
                raise ValueError("STRICT_OOS_MISSING_RULE_TRADE_LEDGER")
            if trades.empty:
                continue
            for _, trade in trades.iterrows():
                opened, closed = pd.Timestamp(trade["entry"]), pd.Timestamp(trade["exit"])
                if opened not in selected.index or closed not in selected.index:
                    if closed in selected.index and selected.loc[closed] == key:
                        cross_boundary += 1
                    continue
                if closed < opened:
                    raise ValueError("STRICT_OOS_INVALID_TRADE_LIFETIME")
                lifetime = selected.loc[opened:closed]
                if not lifetime.empty and lifetime.eq(key).all():
                    tr = trade.to_dict()
                    tr["_fold"] = next(i for i, entry in enumerate(logs)
                                       if entry["test_start"] <= str(closed) <= entry["test_end"])
                    trade_parts.append(tr)
                elif selected.loc[closed] == key:
                    cross_boundary += 1
    fold_trades = pd.DataFrame(trade_parts)
    if not fold_trades.empty:
        fold_trades = fold_trades.sort_values(["exit", "entry"]).reset_index(drop=True)
    for i, entry in enumerate(logs):
        entry["completed_fold_trades"] = (int((fold_trades["_fold"] == i).sum())
                                           if not fold_trades.empty else 0)
    return {
        "oos": oos, "turnover": turn,
        "trades": fold_trades,
        "folds": logs,
        "cache": cache,
        "variants": by_key,
        "errors": failures,
        "trials": len(all_tested),
        "cross_boundary_trades": cross_boundary,
        "variant_switches_cost_modelled": transitions,
        "first_bar_model_transition_turnover": round(realized_boundary_turnover, 9),
        "net_model_transition_cost_adjustment": round(net_boundary_cost_adjustment, 9),
        "missing_test_bars": data_gaps,
        "complete": bool(logs) and data_gaps == 0,
        "fold_execution_verified": bool(logs) and data_gaps == 0,
        "fold_execution_method": "SIMULATED_POSITION_HANDOFF_WITH_REPLACED_ONE_WAY_TURNOVER",
        "interpretation": "COST_ADJUSTED_HISTORICAL_WALK_FORWARD_NOT_BROKER_FILL_PROOF",
    }
