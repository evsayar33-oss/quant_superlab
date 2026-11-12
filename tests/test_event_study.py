from __future__ import annotations

import numpy as np
import pandas as pd

from lab.event_study import entry_index, measure_events, summarize
from lab.panel import Panel


def _panel():
    idx = pd.bdate_range("2022-01-03", periods=520)
    rng = np.random.default_rng(31)
    market = rng.normal(0.0002, 0.008, len(idx))
    stock = market + rng.normal(0.0001, 0.006, len(idx))
    sector = market + rng.normal(0.0001, 0.004, len(idx))
    # Inject a deterministic post-event drift for the test asset.
    stock[300:360] += 0.003
    closes = {
        "SPY": 400 * np.exp(np.cumsum(market)),
        "TST": 50 * np.exp(np.cumsum(stock)),
        "XLK": 150 * np.exp(np.cumsum(sector)),
    }
    c = pd.DataFrame(closes, index=idx)
    o = c.shift(1).fillna(c) * 1.001
    h = np.maximum(o, c) * 1.01
    l = np.minimum(o, c) * 0.99
    v = c * 0 + 1_000_000
    return Panel(o=o, h=h, l=l, c=c, v=v)


def test_exact_premarket_enters_same_session_and_intraday_waits():
    idx = pd.bdate_range("2024-01-02", periods=5)
    # 13:00 UTC is 08:00 ET in January; 16:00 UTC is 11:00 ET.
    assert entry_index("2024-01-03T13:00:00Z", "2024-01-03", idx) == 1
    assert entry_index("2024-01-03T16:00:00Z", "2024-01-03", idx) == 2
    assert entry_index("2024-01-03", "2024-01-03", idx) == 2


def test_event_measure_uses_next_open_and_reports_cost_stress():
    p = _panel()
    event = pd.DataFrame([{
        "event_id": "evt-1", "event_family": "federal_award", "category": "chips",
        "ticker": "TST", "known_at": "2023-03-01T15:00:00Z",
        "event_date": "2023-03-01", "sector_etf": "XLK",
        "amount_usd": 500_000_000, "timestamp_quality": "exact_utc",
    }])
    out = measure_events(event, p, per_side_cost=0.0005, horizons=(1, 5, 20), cooldown_days=0)
    assert set(out["horizon"]) == {1, 5, 20}
    assert (out["entry_date"] > out["event_date"]).all()  # 10:00 ET news -> next session open
    assert (out["net_spy_excess_2x"] <= out["net_spy_excess_1x"]).all()
    assert out["gross_sector_excess"].notna().all()


def test_event_summary_has_chronological_holdout_and_no_false_candidate():
    rows = []
    dates = pd.bdate_range("2020-01-01", periods=80)
    for i, d in enumerate(dates):
        rows.append({
            "event_id": f"e{i}", "event_family": "corporate_capex", "category": "chips",
            "known_at": d.isoformat(), "event_date": d.date().isoformat(), "horizon": 20,
            "net_spy_excess_2x": 0.01 if i < 70 else -0.01,
            "net_stock_return_2x": 0.02 if i < 70 else -0.02,
        })
    summary = summarize(pd.DataFrame(rows), min_events=50, min_split=10, bootstrap_n=200, q_limit=1.0)
    row = summary.iloc[0]
    assert row["discovery_excess_mean"] > 0 and row["validation_excess_mean"] > 0
    assert row["holdout_stock_mean"] < 0 and row["status"] == "REJECT"


def test_event_feed_excludes_unverified_action_date_proxies():
    from lab.event_study import executable_events
    feed = pd.DataFrame([
        {"event_id": "live-award", "timestamp_quality": "first_seen_utc"},
        {"event_id": "old-award", "timestamp_quality": "action_date_proxy"},
        {"event_id": "public-rule", "timestamp_quality": "date_only"},
    ])
    eligible = executable_events(feed)
    assert set(eligible["event_id"]) == {"live-award", "public-rule"}


def test_timestamp_filter_can_leave_no_eligible_rows():
    from lab.event_study import executable_events
    feed = pd.DataFrame([{"event_id": "old-award", "timestamp_quality": "action_date_proxy"}])
    assert executable_events(feed).empty


def test_locked_holdout_does_not_change_discovery_significance():
    rows = []
    dates = pd.bdate_range("2020-01-01", periods=80)
    for i, d in enumerate(dates):
        value = 0.01 if i < 70 else -0.01
        rows.append({
            "event_id": f"seal-{i}", "ticker": "TST", "event_family": "corporate_capex",
            "category": "chips", "known_at": d.isoformat(), "event_date": d.date().isoformat(),
            "horizon": 20, "net_spy_excess_2x": value, "net_stock_return_2x": value * 2,
        })
    first = summarize(pd.DataFrame(rows), min_events=50, min_split=10, bootstrap_n=200, q_limit=1.0).iloc[0]
    changed = [dict(row) for row in rows]
    for row in changed[-16:]:
        row["net_spy_excess_2x"] = 0.03
        row["net_stock_return_2x"] = 0.06
    second = summarize(pd.DataFrame(changed), min_events=50, min_split=10, bootstrap_n=200, q_limit=1.0).iloc[0]
    assert first["p_value"] == second["p_value"]
    assert first["q_value"] == second["q_value"]
    assert first["holdout_excess_mean"] != second["holdout_excess_mean"]
