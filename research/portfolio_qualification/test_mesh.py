"""Offline QA: native evidence, temporal integrity, and domain interpretation."""
import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from research.portfolio_qualification.mesh import (
    SCHEMA, NATIVE_SOURCES, append_snapshot, bist_training_only,
    digest, f1_shadow_study, ict_holdout, native_study, native_summary,
    read_chain, snapshot,
)


def record(t, sha="a", asof=None):
    return {"schema": SCHEMA, "repo": "evsayar33-oss/h054_spot_bot",
            "source_data_digest": sha, "data_status": "OBSERVED_UNPROMOTED",
            "captured_utc": t, "native_observation_utc": asof,
            "input_errors": {}, "inputs": {}, "native_metrics": {},
            "research": {"status": "INDEPENDENT_PAPER_OBSERVATION_ONLY"},
            "paper_approved_by_mesh": False, "live_trade_authorized_by_mesh": False}


class MeshEvidenceContract(unittest.TestCase):
    def test_all_ten_projects_have_native_source_contracts(self):
        self.assertEqual(len(NATIVE_SOURCES), 10)
        from research.portfolio_qualification.audit import load_catalog
        self.assertEqual(set(NATIVE_SOURCES),
                         {p["name"] for p in load_catalog()["projects"]})
        self.assertTrue(all(t[3] for p in NATIVE_SOURCES.values()
                            for t in p[:1]))

    def test_append_sha_chain_and_identical_native_source_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ledger.jsonl"
            x = record("2026-11-23T02:00:00Z", sha="a",
                       asof="2026-11-22T16:00:00+00:00")
            self.assertEqual(append_snapshot(f, x)["recorded_snapshots"], 1)
            y = record("2026-11-23T03:00:00Z", sha="a",
                       asof="2026-11-22T16:00:00+00:00")
            self.assertIn("UNCHANGED", append_snapshot(f, y)["status"])
            self.assertEqual(len(read_chain(f)), 1)
            z = record("2026-11-23T04:00:00Z", sha="b",
                       asof="2026-11-23T00:00:00+00:00")
            self.assertEqual(append_snapshot(f, z)["recorded_snapshots"], 2)
            self.assertEqual(len(read_chain(f)), 2)

    def test_same_native_asof_is_revision_not_a_new_first_seen(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ledger.jsonl"
            a = "2026-11-22T17:00:00Z"
            append_snapshot(f, record("2026-11-23T03:00:00Z", "a", a))
            ret = append_snapshot(f, record("2026-11-23T04:00:00Z", "b", a))
            self.assertTrue(ret["same_observation_revision"])
            self.assertTrue(read_chain(f)[-1]["source_revision_same_observation"])

    def test_past_native_asof_rewind_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ledger.jsonl"
            append_snapshot(f, record("2026-11-23T03:00:00Z", "a",
                                      "2026-11-22T17:00:00Z"))
            with self.assertRaisesRegex(ValueError, "SOURCE_ASOF_REWIND"):
                append_snapshot(f, record("2026-11-23T04:00:00Z", "b",
                                          "2026-11-21T17:00:00Z"))

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ledger.jsonl"
            append_snapshot(f, record("2026-11-23T01:00:00Z"))
            x = json.loads(f.read_text())
            x["source_data_digest"] = "forged"
            f.write_text(json.dumps(x) + "\n")
            with self.assertRaisesRegex(ValueError, "MESH_SHA_CHAIN_TAMPERED"):
                read_chain(f)

    def test_missing_primary_does_not_create_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ledger.jsonl"
            item = record("2026-11-23T01:00:00Z")
            item["data_status"] = "MISSING_REQUIRED_PRIMARY_EVIDENCE"
            ret = append_snapshot(f, item)
            self.assertIn("NO_APPEND", ret["status"])
            self.assertFalse(f.exists())

    def test_bist_candidate_chosen_from_training_only(self):
        native = {"variants": [
            {"name": "base", "cagr_h1_pct": 50, "cagr_h2_pct": 100},
            {"name": "training_winner", "cagr_h1_pct": 80, "cagr_h2_pct": 10},
            {"name": "holdout_winner", "cagr_h1_pct": 30, "cagr_h2_pct": 999}]}
        result = bist_training_only(native)
        self.assertEqual(result["selected"]["name"], "training_winner")
        self.assertEqual(result["second_half_excess_pct_points"], -90)
        self.assertFalse(result["ready_for_paper"])

    def test_f1_pending_does_not_fabricate_completed_trades(self):
        x = f1_shadow_study({}, {"sessions": 6, "control": {"closed_cycles": []},
                                    "candidate": {"closed_cycles": []}})
        self.assertEqual(x["sessions"], 6)
        self.assertEqual(x["control_closed_cycles"], 0)
        self.assertIn("WAITING", x["status"])

    def test_ict_holdout_is_not_scanned_to_select_past_winners(self):
        book = "| NQ | sample | m | s | 2 | none | 262 | 0.334 | 31 | -0.147 | 1 | 1 |\n" + (
               "| XAU | sample | m | s | 2 | none | 393 | 0.218 | 48 | 0.006 | 1 | 1 |\n")
        r = ict_holdout(book)
        self.assertEqual(r["selected"], 2)
        self.assertEqual(r["selected_positive_holdout"], 1)
        self.assertFalse(r["selection_from_holdout_permitted"])

    def test_federal_h083_research_is_distinct_from_event_alpha(self):
        contents = {"h083": b'{"state":"COMPLETED_RESEARCH","counts_as_forward_month":false}',
                    "forward": b'{"forward_months_closed":0}'}
        r = native_study("federal-incentive-radar", contents)
        self.assertEqual(r["h083_months"], 0)
        self.assertEqual(r["separate_causal_event_alpha_hypotheses"], 5)
        self.assertFalse(r["validated_alpha"])

    def test_source_missing_never_means_proven_alpha(self):
        with tempfile.TemporaryDirectory() as d:
            # No repo files, and Git remote not present: fail closed on primary.
            with patch("research.portfolio_qualification.mesh.git",
                       side_effect=FileNotFoundError("no repository")):
                s = snapshot(d, "early_accumulation_radar")
            self.assertEqual(s["data_status"], "MISSING_REQUIRED_PRIMARY_EVIDENCE")
            self.assertFalse(s["paper_approved_by_mesh"])

    def test_capital_flow_issued_time_not_future_target(self):
        data = {
            "2027-12-01/TIC": {
                "target": "2027-12-01",
                "issued": "2026-11-22T08:49:23Z",
                "estimate": 10}}
        m, asof = native_summary("global_capital_radar", {
            "forecasts": json.dumps(data).encode()})
        self.assertEqual(asof, "2026-11-22T08:49:23+00:00")

    def test_live_bist_session_not_stale_historical_variant_date(self):
        data = {"last_run": {"utc": "2026-11-23T03:00:00Z",
                              "mode": "REFRESH", "status": "OK"},
                "last_eod_date": "2026-11-20"}
        _, asof = native_summary("bist_orderflow_quant", {
            "daily_state": json.dumps(data).encode(),
            "variants": b'{"generated_at":"2026-10-15T16:13:20Z","variants":[]}'})
        self.assertEqual(asof, "2026-11-23T03:00:00Z")

    def test_tier1_real_observation_clock_and_future_only_horizon(self):
        import csv, io
        from research.portfolio_qualification.mesh import tier1_asof_flow_study
        start = datetime(2026, 11, 23, 1, tzinfo=timezone.utc)
        rows = []
        for offset, price in ((0, 100), (240, 102), (300, 103), (480, 104)):
            observed = start + timedelta(minutes=offset, seconds=180)
            rows.append({"ts": observed.replace(minute=0, second=0).isoformat(),
                         "observed_at_ms": str(int(observed.timestamp() * 1000)),
                         "asset": "BTC", "market": "spot", "status": "OK_SAMPLE",
                         "reference_price": str(price), "imbalance": "0.45",
                         "book_imbalance": "0.3",
                         "book_ts": str(int((observed -
                                             timedelta(seconds=40)).timestamp() * 1000))})
        output = io.StringIO()
        w = csv.DictWriter(output, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        z = tier1_asof_flow_study(output.getvalue().encode())
        self.assertEqual(z["status"], "TIER1_PROSPECTIVE_SIGNED_FLOW_EXPLORATORY")
        self.assertEqual(z["tested"]["signed_taker_only"]["assets"]["BTC"]
                         ["nonoverlapping_matured_n"], 2)
        self.assertEqual(z["tested"]["signed_taker_and_book_agree"]["assets"]["BTC"]
                         ["nonoverlapping_matured_n"], 2)
        self.assertFalse(z["readiness_for_paper"])

    def test_tier1_book_future_timestamp_never_qualifies(self):
        import csv, io
        from research.portfolio_qualification.mesh import tier1_asof_flow_study
        start = datetime(2026, 11, 23, 1, tzinfo=timezone.utc)
        rows = []
        for offset, price in ((0, 100), (300, 110)):
            obs = start + timedelta(minutes=offset, seconds=120)
            rows.append({"ts": obs.replace(minute=0, second=0).isoformat(),
                         "observed_at_ms": str(int(obs.timestamp()*1000)),
                         "asset": "ETH", "market": "spot", "status": "OK_SAMPLE",
                         "reference_price": str(price), "imbalance": "0.5",
                         "book_imbalance": "0.2",
                         "book_ts": str(int((obs + timedelta(seconds=120)).timestamp()*1000))})
        f = io.StringIO()
        w = csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        r = tier1_asof_flow_study(f.getvalue().encode())
        self.assertEqual(r["tested"]["signed_taker_only"]["assets"]["ETH"]
                         ["nonoverlapping_matured_n"], 1)
        self.assertEqual(r["tested"]["signed_taker_and_book_agree"]["assets"]["ETH"]
                         ["nonoverlapping_matured_n"], 0)

    def test_eaverse_real_release_published_clock_is_used(self):
        x = {"published_at": "2026-11-23T08:00:00Z",
             "entries": [{"id": "x"}, {"id": "y"}],
             "research": {"state": "paper"}}
        m, a = native_summary("eaverse", {
            "release_panel": json.dumps(x).encode()})
        self.assertEqual(a, "2026-11-23T08:00:00Z")
        self.assertEqual(m["reported_entries"], 2)

    def test_h054_paper_denial_not_live(self):
        m, _ = native_summary("h054_spot_bot", {
            "paper_status": b'{"equity":987,"why":"PAPER_ONLY"}',
            "local_registry": b'{"hypotheses":{"H054-MOM2":{"verdict":"PAPER_ACCEPT","live_verdict":"DENY"}}}'})
        self.assertEqual(m["live_verdicts"]["H054-MOM2"], "DENY")


if __name__ == "__main__":
    unittest.main()
