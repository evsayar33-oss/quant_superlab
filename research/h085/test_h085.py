"""H085 tests: frozen inputs, strictly prior weights, costs and event timing."""
import pandas as pd
import pytest
from h085 import VARIANTS, COST_PER_TURN, weights_for_month, simulate_months, event_causal_audit


def test_no_current_month_outcome_in_selection():
    idx = pd.date_range("2024-01-31", periods=11, freq="ME")
    rates = pd.DataFrame({"A": [.01]*9+[.9,-.9],
                          "B": [.02]*11, "C": [.03]*11, "D": [.04]*11}, index=idx)
    spy = pd.Series([0.]*11, index=idx)
    base = simulate_months(rates, spy, "winner_top3_3m")
    revised = rates.copy()
    revised.iloc[9,0] = -0.9
    alt = simulate_months(revised, spy, "winner_top3_3m")
    # A current-month price edit cannot change the exposure chosen before that month.
    assert base.iloc[9]["turnover"] == pytest.approx(alt.iloc[9]["turnover"])
    assert base.iloc[:9]["return_net"].equals(alt.iloc[:9]["return_net"])
    assert len(VARIANTS) == len(set(VARIANTS))


def test_cost_stress_never_increases_same_weight_returns():
    idx = pd.date_range("2024-01-31", periods=13, freq="ME")
    rates = pd.DataFrame({"A":[.02]*13,"B":[-.01]*13,
                          "C":[.01]*13,"D":[0.]*13}, index=idx)
    spy = pd.Series([.01]*13, index=idx)
    cheap = simulate_months(rates, spy, "blend50_6m", COST_PER_TURN[0])
    dear = simulate_months(rates, spy, "blend50_6m", COST_PER_TURN[1])
    assert (dear.return_net <= cheap.return_net + 1e-12).all()
    assert dear.nav.iloc[-1] <= cheap.nav.iloc[-1]
    assert (cheap.turnover >= 0).all()


def test_no_short_history_fails_closed_to_cash():
    idx = pd.date_range("2025-01-31", periods=2, freq="ME")
    known = pd.DataFrame({"a":[.1,.1],"b":[-.1,-.1],
                          "c":[0.,0.],"d":[.01,.01]}, index=idx)
    spy = pd.Series([.03,.03], index=idx)
    assert weights_for_month("winner_top3_6m", known, spy).sum() == 0
    assert weights_for_month("risk_parity_6m", known, spy).sum() == 0
    assert weights_for_month("EW10", known, spy).sum() == 1


def test_event_outcome_at_same_day_exit_is_unknown():
    sample = pd.DataFrame([
        dict(name="baseline/20/time", ticker="AA", event_id="1", entry_date="2025-01-01",
             exit_date="2025-02-01", sector_etf="XLI", category="factory",
             midas_net=200, excess_vs_spy=.08, split="REUSED_TEST"),
        dict(name="baseline/20/time", ticker="BB", event_id="2", entry_date="2025-02-01",
             exit_date="2025-02-25", sector_etf="XLI", category="factory",
             midas_net=-100, excess_vs_spy=-.02, split="REUSED_TEST"),
    ])
    audit = event_causal_audit(sample)
    assert len(audit) == 2
    assert not bool(audit.iloc[1]["market_mean_90d"])
    assert not bool(audit.iloc[1]["sector_mean_180d"])
    sample.loc[0,"exit_date"] = "2025-02-02"
    audit2 = event_causal_audit(sample)
    assert not bool(audit2.iloc[1]["market_mean_90d"])


def test_event_missing_and_duplicate_fails_closed():
    with pytest.raises(ValueError):
        event_causal_audit(pd.DataFrame({"ticker":["A"]}))
    sample = pd.DataFrame([
        dict(name="baseline/20/time",ticker="X",event_id="same",entry_date="2025-01-01",
             exit_date="2025-01-10",sector_etf="XLI",category="plant",
             midas_net=10,excess_vs_spy=.01,split="REUSED_TEST"),
        dict(name="baseline/20/time",ticker="Y",event_id="same",entry_date="2025-02-01",
             exit_date="2025-02-10",sector_etf="XLI",category="plant",
             midas_net=12,excess_vs_spy=.01,split="REUSED_TEST"),
    ])
    with pytest.raises(ValueError):
        event_causal_audit(sample)
