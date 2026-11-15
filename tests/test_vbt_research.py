"""Offline unit checks plus optional true vectorbt parity checks.

Run: python -m pytest -q tests/test_vbt_research.py
The parity test is skipped if optional vectorbt is not installed.
"""
import numpy as np
import pandas as pd
import pytest

from lab.adapters.vbt_research import (clean_close, execution_signals,
    independent_equity, parameter_pairs, run_research)


def test_cartesian_pairs_and_invalid_lookback():
    assert parameter_pairs([5, 10], [9, 20]) == [(5, 9), (5, 20), (10, 20)]
    with pytest.raises(ValueError):
        parameter_pairs([10], [8])
    with pytest.raises(ValueError):
        parameter_pairs(range(2, 50), range(50, 100), max_trials=100)


def test_clean_input_rejects_duplicates_and_bad_prices():
    price = pd.Series(np.full(40, 100.), index=pd.date_range("2020-01-01", periods=40))
    assert len(clean_close(price)) == 40
    with pytest.raises(ValueError):
        clean_close(pd.Series([100.] * 40, index=[1] * 40))
    price.iloc[10] = -10
    with pytest.raises(ValueError):
        clean_close(price)


def test_close_signal_fills_one_bar_later():
    close = pd.Series([10.] * 35 + [11.] * 35 + [9.] * 35,
                      index=pd.bdate_range("2020-01-01", periods=105))
    entries, exits = execution_signals(close, 3, 10)
    assert entries.iloc[35] == False
    assert entries.iloc[36] == True
    assert exits.iloc[70] == False
    assert exits.iloc[71] == True


def test_round_trip_costs_hurt_and_no_pre_signal_return():
    close = pd.Series([100., 100., 110., 120., 90.])
    entry = pd.Series([False, False, True, False, False])
    exit_ = pd.Series([False, False, False, False, True])
    free = independent_equity(close, entry, exit_, 0, 0, 10000)
    costly = independent_equity(close, entry, exit_, .001, .0005, 10000)
    assert (free.iloc[:2] == 10000).all()
    assert costly.iloc[-1] < free.iloc[-1]
    assert np.isclose(free.iloc[-1], 10000 * 90 / 110)


def test_optional_vectorbt_cross_engine_parity():
    pytest.importorskip("vectorbt")
    close = pd.Series(
        100 * np.exp(np.cumsum(np.sin(np.arange(550) / 11) * .012)),
        index=pd.bdate_range("2021-01-01", periods=550), name="Close"
    )
    results, summary = run_research(close, [5, 10], [15, 25],
                                    fee=0.001, slippage=0.0005, tolerance=1e-4)
    assert summary["trial_count"] == 4
    assert summary["gate_eligible"] is False
    assert summary["all_engines_agree"], results.to_string()
    assert results["engine_agreement"].all()
