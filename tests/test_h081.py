import pandas as pd
import pytest
from lab.event_study_h081 import source_evidence_audit, evidence_override, spy_prior_regimes


def feed():
    return pd.DataFrame([
        {"event_id":"a","event_family":"federal","category":"defense",
         "timestamp_quality":"action_date_proxy","event_date":"2024-03-10","known_at":""},
        {"event_id":"b","event_family":"capex","category":"factory",
         "timestamp_quality":"date_only","event_date":"2024-03-11","known_at":""},
    ])


def test_preserve_all_families():
    a = source_evidence_audit(feed())
    assert len(a) == 2
    assert a.loc[a.category.eq("defense"), "decision"].iloc[0] == "SOURCE_TIMESTAMP_REQUIRED"


def test_unverified_evidence_never_promotes():
    ev = pd.DataFrame([{"event_id":"a","published_at_utc":"2024-03-09T10:00:00Z",
                        "evidence_url":"https://example.com/a","verified":False}])
    upgraded, decisions = evidence_override(feed(), ev)
    assert upgraded.loc[0, "timestamp_quality"] == "action_date_proxy"
    assert decisions.loc[0, "decision"] == "REJECT"


def test_verified_source_promotes_with_explicit_utc():
    ev = pd.DataFrame([{"event_id":"a","published_at_utc":"2024-03-09T10:00:00Z",
                        "evidence_url":"https://example.com/a","verified":True}])
    upgraded, decisions = evidence_override(feed(), ev)
    assert upgraded.loc[0, "timestamp_quality"] == "exact_utc"
    assert decisions.loc[0, "decision"] == "ACCEPT"


def test_missing_timezone_rejected():
    ev = pd.DataFrame([{"event_id":"a","published_at_utc":"2024-03-09 10:00:00",
                        "evidence_url":"https://example.com/a","verified":True}])
    upgraded, decisions = evidence_override(feed(), ev)
    assert decisions.loc[0, "decision"] == "REJECT"


def test_regime_uses_completed_sessions_only():
    idx = pd.bdate_range("2024-01-01", periods=220)
    close = pd.Series(range(1, 221), index=idx, dtype=float)
    r = spy_prior_regimes(close)
    assert len(r) == 21
    assert r["regime"].eq("RISK_ON").all()
    assert r["available_at"].iloc[0].date() == idx[199].date()


def test_duplicate_evidence_fails_closed():
    ev = pd.DataFrame([{"event_id":"a","published_at_utc":"2024-03-09T10:00:00Z",
                        "evidence_url":"https://example.com/a","verified":True}] * 2)
    with pytest.raises(ValueError):
        evidence_override(feed(), ev)
