"""Offline regression tests for H063-H065 paper-watch daily runs."""

from types import SimpleNamespace

import pandas as pd
import pytest

from lab import watch


@pytest.mark.parametrize(
    ("suffix", "expected_pick"),
    [("", 4), ("_h070", 2)],
)
def test_daily_reads_matching_leverage_artifact(tmp_path, monkeypatch, suffix, expected_pick):
    monkeypatch.setattr(watch, "OUT", tmp_path)
    (tmp_path / "leverage.json").write_text('{"ideas": {"H063": {"pick": 4}}}')
    (tmp_path / "leverage_h070.json").write_text('{"ideas": {"H063": {"pick": 2}}}')

    index = pd.date_range("2026-10-23", periods=2)
    positions = pd.DataFrame({"XAU": [1.0, 0.0]}, index=index)
    returns = pd.Series([0.01, 0.0], index=index)

    def fake_idea_returns(idea, panels, synthetic=False, only=None):
        return SimpleNamespace(ppy=252), returns, positions, None

    monkeypatch.setattr(watch, "idea_returns", fake_idea_returns)
    cfg = {"start": "2026-10-22", "ideas": {"H063": {"name": "test"}}, "tradable_only": False}
    state, _ = watch.daily(cfg, synthetic=True, suffix=suffix)
    assert state["ideas"]["H063"]["leverage_pick"] == expected_pick
    assert (tmp_path / "state.json").exists()


def test_daily_without_leverage_artifact_falls_back_to_one_x(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "OUT", tmp_path)
    index = pd.date_range("2026-10-23", periods=2)
    positions = pd.DataFrame({"XAU": [1.0, 1.0]}, index=index)
    returns = pd.Series([0.0, 0.0], index=index)
    monkeypatch.setattr(
        watch, "idea_returns",
        lambda idea, panels, synthetic=False, only=None:
        (SimpleNamespace(ppy=252), returns, positions, None),
    )
    state, _ = watch.daily(
        {"start": "2026-10-22", "ideas": {"H063": {"name": "test"}}},
        synthetic=True,
    )
    assert state["ideas"]["H063"]["leverage_pick"] == 1
