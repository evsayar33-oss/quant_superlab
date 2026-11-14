"""P11 operational invariants; offline, deterministic, no orders or network."""
from datetime import datetime, timedelta, timezone
import json
import urllib.error

import pandas as pd

from lab import client, funding, watch


def test_client_urls_and_future_staleness():
    assert "/quant_superlab/main/" in client.URL
    assert "/quant_superlab/main/" in client.ARENA_URL
    now = datetime.now(timezone.utc)
    assert client._fresh({"validated_at": (now - timedelta(days=1)).isoformat()})
    assert not client._fresh({"validated_at": (now - timedelta(days=11)).isoformat()})
    assert not client._fresh({"validated_at": (now + timedelta(days=1)).isoformat()})


def test_client_never_reuses_accept_on_network_failure(monkeypatch):
    approval = {"hypotheses": {"H054": {
        "verdict": "ACCEPT", "validated_at": datetime.now(timezone.utc).isoformat()
    }}}
    calls = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps(approval).encode()

    def urlopen(url, timeout):
        calls.append(url)
        if len(calls) == 1:
            return Response()
        raise OSError("offline")

    monkeypatch.setattr(client.urllib.request, "urlopen", urlopen)
    client._cache.clear()
    try:
        assert len(client.approved(url="https://example.org/registry.json")) == 1
        assert client.approved(url="https://example.org/registry.json") == []
        assert len(calls) == 2
    finally:
        client._cache.clear()


def test_negative_cache_only_for_missing_funding_months(tmp_path, monkeypatch):
    monkeypatch.setattr(funding, "CACHE", tmp_path)
    hits = []

    def error_404(url, timeout=30):
        hits.append(url)
        raise urllib.error.HTTPError(url, 404, "missing", None, None)

    monkeypatch.setattr(funding.urllib.request, "urlopen", error_404)
    start = (pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=3)).strftime("%Y-%m")
    assert funding.load("FAKEUSDT", start=start).empty
    first_count = len(hits)
    assert first_count > 0
    assert funding.load("FAKEUSDT", start=start).empty
    assert len(hits) == first_count
    assert (tmp_path / "funding_FAKEUSDT.missing.json").exists()


def test_paper_first_seen_snapshots_are_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "OUT", tmp_path)
    state = {"date": "2026-11-14", "ideas": {
        "H063": {"bar": "2026-11-13", "held": {"XAU": 1.0}, "paper_1x": {"final_1000": 1012}},
        "H064": {"bar": "2026-11-13", "held": {}, "paper_1x": {"final_1000": 1000}}
    }}
    watch.append_observations(state)
    watch.append_observations(state)
    df = pd.read_csv(tmp_path / "observations.csv")
    assert len(df) == 2
    assert set(df["record_type"]) == {"FIRST_SEEN_SNAPSHOT_NOT_FORWARD_PNL"}
    assert set(df["run_date"]) == {"2026-11-14"}
