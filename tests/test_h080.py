import numpy as np
import pandas as pd
import pytest

from lab.event_study_h080 import (timestamp_audit, enrich_with_verified_fundamentals,
                                  attach_prior_regimes, regime_diagnostics)


def sample():
    return pd.DataFrame([
        dict(event_id="a", ticker="AAA", event_date="2024-03-10",
             event_family="corporate_capex", category="factory", horizon=20,
             amount_usd=200, net_stock_return_2x=.04, net_spy_excess_2x=.02),
        dict(event_id="b", ticker="BBB", event_date="2024-03-10",
             event_family="federal_award", category="grant", horizon=20,
             amount_usd=100, net_stock_return_2x=-.01, net_spy_excess_2x=-.02),
    ])


def test_historical_cap_never_uses_later_publication():
    cap = pd.DataFrame([
        dict(ticker="AAA", asof_date="2024-03-01", available_at="2024-03-02", market_cap_usd=1000),
        dict(ticker="AAA", asof_date="2024-03-09", available_at="2024-03-10", market_cap_usd=10),
        dict(ticker="BBB", asof_date="2024-03-01", available_at="2024-03-11", market_cap_usd=10),
    ])
    out = enrich_with_verified_fundamentals(sample(), cap)
    assert np.isclose(out.loc[0, "amount_to_pit_cap"], .2)
    assert pd.isna(out.loc[1, "amount_to_pit_cap"])


def test_no_current_cap_backfill_and_missing_availability_fails_closed():
    assert enrich_with_verified_fundamentals(sample(), None)["amount_to_pit_cap"].isna().all()
    with pytest.raises(ValueError):
        enrich_with_verified_fundamentals(sample(), pd.DataFrame([dict(ticker="AAA", asof_date="2024-03-01", market_cap_usd=10)]))


def test_regime_is_known_before_event_not_same_day():
    regime = pd.DataFrame([
        dict(available_at="2024-03-01", regime="RISK_ON"),
        dict(available_at="2024-03-10", regime="RISK_OFF"),
    ])
    out = attach_prior_regimes(sample(), regime)
    assert set(out["prior_regime"]) == {"RISK_ON"}


def test_missing_regime_is_explicit_and_groups_retained():
    out = attach_prior_regimes(enrich_with_verified_fundamentals(sample(), None), None)
    stats = regime_diagnostics(out)
    assert set(stats["event_family"]) == {"corporate_capex", "federal_award"}
    assert set(stats["prior_regime"]) == {"UNAVAILABLE"}
    assert set(stats["status"]) == {"INSUFFICIENT_SAMPLE"}


def test_federal_timestamp_gap_retained_without_returns():
    feed = pd.DataFrame([
        dict(event_family="federal_award", category="grant", timestamp_quality="action_date_proxy"),
        dict(event_family="policy_regulatory", category="rule", timestamp_quality="date_only"),
    ])
    audit = timestamp_audit(feed, pd.DataFrame())
    assert len(audit) == 2
    assert audit.loc[audit["category"].eq("grant"), "readiness"].iloc[0] == "TIMESTAMP_GAP"
    assert audit.loc[audit["category"].eq("rule"), "readiness"].iloc[0] == "PRICE_OR_MAPPING_GAP"
