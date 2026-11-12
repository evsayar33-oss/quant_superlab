"""H079 point-in-time and all-family retention tests."""
import numpy as np
import pandas as pd
import pytest

from lab.event_study_h079 import attach_point_in_time_cap, coverage_table, diagnostics


def sample_returns():
    return pd.DataFrame([
        {"event_id": "e1", "ticker": "AAA", "event_date": "2024-03-10",
         "event_family": "corporate_capex", "category": "factory",
         "sector_etf": "XLI", "horizon": 20, "amount_usd": 200.0,
         "net_stock_return_2x": 0.05, "net_spy_excess_2x": 0.02},
        {"event_id": "e2", "ticker": "BBB", "event_date": "2024-03-10",
         "event_family": "federal_award", "category": "grant",
         "sector_etf": "XLK", "horizon": 20, "amount_usd": 100.0,
         "net_stock_return_2x": -0.01, "net_spy_excess_2x": -0.03},
    ])


def test_no_pit_data_does_not_invent_market_cap():
    out = attach_point_in_time_cap(sample_returns(), None)
    assert out["amount_to_cap"].isna().all()
    assert out["market_cap_usd_pit"].isna().all()


def test_pit_asof_join_rejects_future_and_same_day_values():
    caps = pd.DataFrame([
        {"ticker": "AAA", "asof_date": "2024-03-01", "market_cap_usd": 1000},
        {"ticker": "AAA", "asof_date": "2024-03-10", "market_cap_usd": 10},
        {"ticker": "BBB", "asof_date": "2024-03-11", "market_cap_usd": 10},
    ])
    out = attach_point_in_time_cap(sample_returns(), caps)
    assert np.isclose(out.loc[0, "amount_to_cap"], 0.2)
    assert pd.isna(out.loc[1, "amount_to_cap"])


def test_missing_required_pit_fields_fails_closed():
    with pytest.raises(ValueError):
        attach_point_in_time_cap(sample_returns(), pd.DataFrame([{"ticker": "AAA"}]))


def test_all_families_and_zero_measured_groups_remain_visible():
    feed = pd.DataFrame([
        {"event_family": "corporate_capex", "category": "factory"},
        {"event_family": "federal_award", "category": "grant"},
        {"event_family": "policy_regulatory", "category": "rule"},
    ])
    coverage = coverage_table(feed, sample_returns())
    assert set(coverage["event_family"]) == {
        "corporate_capex", "federal_award", "policy_regulatory"
    }
    assert coverage.loc[coverage["event_family"].eq("policy_regulatory"), "measured_events"].iloc[0] == 0


def test_small_samples_are_retained_not_rejected():
    out = diagnostics(attach_point_in_time_cap(sample_returns(), None))
    assert len(out) == 2
    assert set(out["status"]) == {"INSUFFICIENT_SAMPLE"}


def test_pit_asof_handles_mixed_datetime_precision_and_multiple_tickers():
    caps = pd.DataFrame([
        {"ticker": "BBB", "asof_date": pd.Timestamp("2024-03-01").as_unit("us"), "market_cap_usd": 500},
        {"ticker": "AAA", "asof_date": pd.Timestamp("2024-03-01").as_unit("ns"), "market_cap_usd": 1000},
        {"ticker": "AAA", "asof_date": pd.Timestamp("2024-03-10").as_unit("us"), "market_cap_usd": 10},
    ])
    result = attach_point_in_time_cap(sample_returns(), caps)
    assert np.isclose(result.loc[0, "amount_to_cap"], 0.2)
    assert np.isclose(result.loc[1, "amount_to_cap"], 0.2)
    assert pd.to_datetime(result.loc[0, "cap_asof_date"]) < pd.Timestamp("2024-03-10")
