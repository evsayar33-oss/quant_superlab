"""H120 cross-repository contracts: isolated Tier1 source, no model promotion."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from research.h120 import engine as h
from research.h120 import notify as n

T = datetime(2026, 11, 19, 17, tzinfo=timezone.utc)
SHA = "f" * 40


def raw_audit():
    rows = []
    for i in range(8):
        rows.append({
            "asset": h.ASSETS[i % 6], "observed_utc": "2026-11-19T11:30:00+00:00",
            "publication_utc": "2026-11-19T11:01:00+00:00",
            "entry_allowed": False, "price_source": "YAHOO_HOURLY_DELAYED_NON_EXECUTABLE",
            "horizons": {
                "4": {"status": "GRADED", "gross_return": 0.01,
                      "baseline_long_return": -0.01},
                "24": {"status": "PENDING_PRICE"},
            },
        })
    def metric(sample, hit, baseline):
        return {
            "independent_by_asset_n": sample,
            "model_hit": hit,
            "always_long_hit": baseline,
            "multiple_testing_adjusted_p_bonferroni_12": .75,
            "independent_assets_assumption_verified": False,
            "missing_labels": 2, "pending_labels": 2,
            "hypothetical_cost_scenarios_bps": {
                "0": {"hypothetical_mean_bps": 100},
                "40": {"hypothetical_mean_bps": 60},
            },
            "verdict": "INSUFFICIENT",
        }
    summary = {
        "as_of_utc": "2026-11-19T11:49:35+00:00",
        "start_utc": "2026-11-14T06:24:26+00:00",
        "end_utc": "2026-12-14T06:24:26+00:00",
        "entry_allowed": 0,
        "horizons": {
            "4": metric(4, 1, 0),
            "24": metric(7, .8571, .1429),
        },
    }
    ledger = {
        "schema": "1.0", "calls": rows, "snapshots": [],
        "last_audit_utc": summary["as_of_utc"],
    }
    return {
        "summary": summary, "ledger": ledger, "decision_docs": [],
        "source_commits": {h.AUDIT: SHA},
        "source_hashes": {"summary": "a"*64, "ledger": "b"*64},
    }


def mock_fetch_from(evidence):
    urls = []
    def fetch(url):
        urls.append(url)
        if "git/ref/heads/" in url:
            if url.endswith("/" + h.AUDIT):
                return json.dumps({"object": {"sha": SHA}})
            raise urllib.error.HTTPError(url, 404, "not found", {}, None)
        if "/compare/" in url:
            return json.dumps({"status": "ahead", "behind_by": 0, "ahead_by": 1})
        if url.endswith("summary.json"):
            return json.dumps(evidence["summary"])
        if url.endswith("ledger.json"):
            return json.dumps(evidence["ledger"])
        raise AssertionError("UNEXPECTED_FETCH")
    return fetch, urls


class TestTier1OnlyBridge(unittest.TestCase):
    def test_realistic_underpowered_audit_never_becomes_profit_claim(self):
        e = raw_audit()
        result, notices = h.evaluate(e, {}, T)
        self.assertEqual(result["grades"]["4"]["observations"], 4)
        self.assertEqual(result["grades"]["24"]["observations"], 7)
        self.assertEqual(result["replication_leads_not_accepts"], 0)
        self.assertEqual(result["entry_allowed"], 0)
        self.assertEqual(notices, [])
        self.assertEqual(result["official_gate"], "NOT_RUN")
        self.assertTrue(result["research_only"])
        self.assertTrue(all(not x["selection_allowed"]
                            for x in result["descriptive_asset_diagnostics"]))

    def test_no_early_radar_endpoint_or_h119_cross_import(self):
        fetch, urls = mock_fetch_from(raw_audit())
        r = h.fetch_evidence({}, fetch)
        self.assertEqual(r["source_commits"], {h.AUDIT: SHA})
        self.assertGreaterEqual(len(urls), 5)
        self.assertTrue(all(h.UPSTREAM in u for u in urls))
        self.assertTrue(all("early_accumulation" not in u and "/h119" not in u
                            for u in urls))

    def test_research_candidates_need_source_verified_independence_and_entry(self):
        base = raw_audit()
        x = base["summary"]["horizons"]["4"]
        x.update({
            "independent_by_asset_n": 100, "model_hit": .70,
            "always_long_hit": .43,
            "multiple_testing_adjusted_p_bonferroni_12": .009,
            "independent_assets_assumption_verified": True,
            "verdict": "DESCRIPTIVE_ONLY",
            "missing_labels": 10,
        })
        # Explicitly add enough auditor calls, no fictitious independent trades.
        base["ledger"]["calls"] *= 14
        base["summary"]["entry_allowed"] = 32
        _, events = h.evaluate(base, {}, T)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "PROSPECTIVE_REPLICATION_LEAD")
        self.assertFalse(events[0]["live_orders_allowed"])
        self.assertEqual(events[0]["quant_superlab_verdict"], "NOT_EVALUATED")
        base["summary"]["entry_allowed"] = 0
        _, e = h.evaluate(base, {}, T)
        self.assertEqual(len(e), 0)

    def test_source_can_omit_unobserved_horizon_without_false_grades(self):
        e = raw_audit()
        e["ledger"]["calls"][0]["horizons"] = {"4": {"status": "PENDING_PRICE"}}
        e["ledger"]["calls"][1]["horizons"] = {}
        result, notices = h.evaluate(e, {}, T)
        self.assertEqual(notices, [])
        self.assertEqual(result["grades"]["24"]["observations"], 7)
        self.assertTrue(all(not d["selection_allowed"]
                            for d in result["descriptive_asset_diagnostics"]))
        e["ledger"]["calls"][1]["horizons"] = {"12": {"status": "GRADED"}}
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_FORECAST_HORIZON"):
            h.evaluate(e, {}, T)

    def test_future_and_stale_source_fails_closed(self):
        e = raw_audit()
        e["ledger"]["calls"][0]["publication_utc"] = "2026-11-19T12:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "PUBLICATION_AFTER_FIRST_SEEN"):
            h.evaluate(e, {}, T)
        e = raw_audit()
        e["summary"]["horizons"]["4"]["independent_by_asset_n"] = 900
        with self.assertRaisesRegex(ValueError, "EXCEEDS_OBSERVED_CALLS"):
            h.evaluate(e, {}, T)
        e = raw_audit()
        e["summary"]["as_of_utc"] = "2027-11-19T11:49:35+00:00"
        with self.assertRaisesRegex(ValueError, "INVALID_PROSPECTIVE_WINDOW"):
            h.evaluate(e, {}, T)

    def test_only_sealed_final_research_only_study_decisions(self):
        e = raw_audit()
        final = {
            "schema": 1, "study_id": "tier1_v2_forward", "stage": "FINAL",
            "as_of_utc": "2026-11-19T11:49:35+00:00",
            "auto_applied": "RESEARCH_STATUS_ONLY",
            "production_logic_modified": False, "live_orders": False,
            "assessment": {"decision": "NO_DEMONSTRATED_ADVANTAGE"},
        }
        e["decision_docs"] = [{
            "data": final, "path": h.STUDY_FILES[0],
            "branch": h.STUDIES, "commit": SHA, "sha256": "d"*64,
        }]
        r, events = h.evaluate(e, {}, T)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "SEALED_STUDY_DECISION")
        self.assertEqual(r["final_study_decisions"][0]["decision"], "NO_DEMONSTRATED_ADVANTAGE")
        e["decision_docs"][0]["data"]["live_orders"] = True
        with self.assertRaisesRegex(ValueError, "UNTRUSTED_STUDY_DECISION"):
            h.evaluate(e, {}, T)

    def test_rejects_branch_history_rewrites_and_missing_study_branch(self):
        with self.assertRaisesRegex(ValueError, "REWRITTEN_OR_ROLLED_BACK"):
            h.check_ancestry(h.AUDIT, "a"*40, SHA,
                             lambda u: json.dumps({"status": "diverged",
                                                   "behind_by": 2, "ahead_by": 1}))
        fetch, _ = mock_fetch_from(raw_audit())
        with self.assertRaisesRegex(ValueError, "BRANCH_DISAPPEARED"):
            h.fetch_evidence({h.STUDIES: "b"*40}, fetch)

    def test_replay_is_idempotent_and_keeps_state_separate(self):
        with tempfile.TemporaryDirectory() as d:
            e, state = raw_audit(), Path(d)/"tier1-evidence"
            fetch, _ = mock_fetch_from(e)
            first = h.run(state, fetch, T)
            second = h.run(state, fetch, T)
            self.assertEqual(first["new_events"], 0)
            self.assertEqual(second["new_events"], 0)
            self.assertEqual(second["source"], h.UPSTREAM)
            self.assertEqual(second["state_branch"], "research/h120-tier1-evidence")
            self.assertEqual(second["pending_notifications"], 0)
            self.assertEqual(h.read_ledger(state/"events.jsonl"), [])

    def test_staleness_notified_once_and_receipt_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            e = raw_audit()
            state = Path(d)
            old = datetime(2026, 11, 21, 20, tzinfo=timezone.utc)
            report, events = h.evaluate(e, {}, old)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["kind"], "SOURCE_AUDIT_STALE")
            h.append_ledger(state / "events.jsonl", events)
            (state/"latest.json").write_text(json.dumps(report))
            sends = []
            def succeed(msg, tok, chat):
                sends.append(msg)
                return True
            result = n.notify(state, sender=succeed, token="t", chat="c", now=old)
            self.assertEqual(result["delivered"], 1)
            self.assertEqual(result["method"], "TELEGRAM")
            self.assertEqual(n.notify(state, sender=succeed, token="t", chat="c")["delivered"], 0)
            self.assertEqual(len(sends), 1)
            self.assertEqual(len(h.read_ledger(state/"receipts.jsonl")), 1)
            after = json.loads((state/"latest.json").read_text())
            self.assertEqual(after["pending_notifications"], 0)

    def test_failed_delivery_leaves_evidence_for_retry(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d)
            h.append_ledger(state/"events.jsonl", [{
                "id": "event1", "kind": "SOURCE_AUDIT_STALE",
                "evidence": {"last_audit_utc": T.isoformat(),
                             "hours_without_audit": 26},
            }])
            with self.assertRaisesRegex(RuntimeError, "UNDELIVERED"):
                n.notify(state, token="", chat="", github_token="",
                         fallback=lambda *args: (False, None))
            self.assertEqual(h.read_ledger(state/"receipts.jsonl"), [])
            r = n.notify(state, token="", chat="", github_token="testing",
                         fallback=lambda *args: (True, "49"))
            self.assertEqual(r["method"], "ASSIGNED_GITHUB_ISSUE")
            self.assertEqual(len(h.read_ledger(state/"receipts.jsonl")), 1)

    def test_source_authentication_scoped_to_api_only(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{}'
        seen = []
        def intercept(request, timeout):
            seen.append(request)
            return Response()
        with patch.dict("os.environ", {"GITHUB_TOKEN": "mock-ephemeral"}):
            with patch.object(h.urllib.request, "urlopen", side_effect=intercept):
                h.http_text("https://api.github.com/repos/a/b")
                h.http_text("https://raw.githubusercontent.com/a/b/main/file")
        self.assertEqual(seen[0].get_header("Authorization"), "Bearer mock-ephemeral")
        self.assertIsNone(seen[1].get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
