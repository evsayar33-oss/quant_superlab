"""Offline H119 source, no-hindsight, official-gate, notification regression tests."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from research.h119 import engine as h
from research.h119 import notify as n

NOW = datetime(2026, 11, 19, 16, tzinfo=timezone.utc)
COMMIT = "a" * 40


def source_fixture():
    source = {key: {path: "" for path in paths}
              for key, paths in h.FILES.items()}
    for market in ("BIST", "US"):
        prefix = "research_archive/v12/" + market + "/"
        source["patterns"][prefix + "latest.json"] = json.dumps({
            "schema": "EAR.v12_equity_discovery.v1", "market": market,
            "asof_utc": NOW.isoformat(),
            "asof_observations_total": 20,
            "limitations": {"trade_authorized": False},
        })
    markets = {}
    for market in ("BIST", "US"):
        stats = []
        for i in range(16):
            for horizon in (1, 3, 5, 10):
                stats.append({"rule": "rule_" + str(i),
                              "horizon_sessions": horizon,
                              "passes_fixed_research_gates": False})
        markets[market] = {
            "all_trial_statistics": stats, "rule_horizon_trials": 64,
            "frozen_total": 0, "completed_forward_decisions_total": 0,
            "v12_matured_outcomes": {"1": 0, "3": 0, "5": 0, "10": 0},
        }
    source["equity"]["research_archive/v13/latest.json"] = json.dumps({
        "schema": "EAR.v13_costed_profitability_discovery.v1",
        "asof_utc": NOW.isoformat(),
        "methodology_sha256": "v13e",
        "paper_approved": False, "trade_authorized": False,
        "profitable_strategy_proven": False,
        "markets": markets,
    })
    stats = []
    for i in range(23):
        for side in ("LONG", "SHORT"):
            for horizon in (60, 240):
                stats.append({"rule": "crypto_rule_" + str(i),
                              "direction": side, "horizon_minutes": horizon,
                              "fixed_costed_research_gates_pass": False})
    source["crypto"]["research_archive/v13_crypto/latest.json"] = json.dumps({
        "schema": "EAR.v13_crypto_costed_research.v1",
        "asof_utc": NOW.isoformat(),
        "methodology_sha256": "v13c",
        "source_status": "FRESH_V8_RESEARCH_OBSERVATIONS",
        "source_age_minutes": 5,
        "strategy_variants_tested": 92,
        "all_rule_horizon_results": stats,
        "frozen_trials": 0, "completed_forward_trials": 0,
        "asof_observations": 0,
        "limitations": {"trade_authorized": False},
    })
    return source


def registry():
    return {"hypotheses": {
        "H052": {"verdict": "ACCEPT", "strategy": "core_dual_trend_vt",
                 "accepted_at": "2026-10-15", "dsr": .95,
                 "live": {"degraded": False}},
    }}


def good_equity():
    return {
        "passes_fixed_research_gates": True,
        "hypothetical_closed_trades": 40,
        "matched_control_events": 80,
        "distinct_symbols": 12, "signal_days": 14,
        "net_mean_pct": 1.12, "stressed_net_mean_pct": .65,
        "excess_vs_matched_control_pct": .85,
        "closed_profit_factor": 1.65,
        "stressed_ten_day_block_lower_bound_pct": .21,
    }


def good_crypto():
    return {
        "fixed_costed_research_gates_pass": True,
        "hypothetical_mark_trades": 45,
        "controls": 110, "distinct_symbols": 14, "distinct_days": 8,
        "mean_model_net_pct": .67, "stressed_mean_net_pct": .35,
        "excess_over_matched_controls_pct": .31,
        "profit_factor": 1.5, "multiplicity_screen_lower_pct": .12,
    }


def mock_remote(source, commit=COMMIT):
    def fetch(url):
        if "/git/ref/heads/" in url:
            return json.dumps({"object": {"sha": commit}})
        if "/compare/" in url:
            return json.dumps({"status": "ahead", "behind_by": 0, "ahead_by": 1})
        prefix = ("https://raw.githubusercontent.com/" + h.UPSTREAM +
                  "/" + commit + "/")
        if not url.startswith(prefix):
            raise AssertionError("UNEXPECTED_REMOTE_FETCH " + url)
        filename = url[len(prefix):]
        for record in source.values():
            if filename in record:
                return record[filename]
        raise AssertionError("UNKNOWN_REMOTE_FILE " + filename)
    return fetch


class H119Contracts(unittest.TestCase):
    def test_initial_three_market_search_counts_no_false_profit(self):
        events, report, _ = h.analyze(
            source_fixture(), {k: COMMIT for k in h.BRANCHES}, registry(), NOW)
        self.assertEqual(events, [])
        self.assertEqual(report["BIST"]["source_reported_variants"], 64)
        self.assertEqual(report["US"]["source_reported_variants"], 64)
        self.assertEqual(report["CRYPTO_PERPETUAL"]["source_reported_variants"], 92)
        self.assertEqual(sum(v["costed_research_candidates"] for v in report.values()), 0)

    def test_recheck_costs_prevents_fake_positive_flags(self):
        src = source_fixture()
        p = json.loads(src["equity"]["research_archive/v13/latest.json"])
        p["markets"]["BIST"]["all_trial_statistics"][0].update(good_equity())
        p["markets"]["BIST"]["all_trial_statistics"][0]["stressed_net_mean_pct"] = -.5
        src["equity"]["research_archive/v13/latest.json"] = json.dumps(p)
        a, _, _ = h.analyze(src, {k: COMMIT for k in h.BRANCHES}, registry(), NOW)
        self.assertFalse(any(x["kind"] == "COSTED_RESEARCH_CANDIDATE" for x in a))
        p["markets"]["BIST"]["all_trial_statistics"][0]["stressed_net_mean_pct"] = .65
        src["equity"]["research_archive/v13/latest.json"] = json.dumps(p)
        a, _, _ = h.analyze(src, {k: COMMIT for k in h.BRANCHES}, registry(), NOW)
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["lab_verdict"], "NOT_EVALUATED")
        self.assertFalse(a[0]["real_money_trade_authorized"])

    def test_crypto_positive_is_model_based_not_executable_alpha(self):
        src = source_fixture()
        p = json.loads(src["crypto"]["research_archive/v13_crypto/latest.json"])
        p["all_rule_horizon_results"][0].update(good_crypto())
        src["crypto"]["research_archive/v13_crypto/latest.json"] = json.dumps(p)
        a, _, _ = h.analyze(src, {k: COMMIT for k in h.BRANCHES}, registry(), NOW)
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["market"], "CRYPTO_PERPETUAL")
        self.assertEqual(a[0]["evidence"]["status"], "MODELLED_NOT_EXECUTABLE_PNL")
        self.assertFalse(a[0]["verified_actual_fills"])

    def test_duplicate_variant_fails_closed(self):
        src = source_fixture()
        p = json.loads(src["crypto"]["research_archive/v13_crypto/latest.json"])
        p["all_rule_horizon_results"][1] = copy.deepcopy(p["all_rule_horizon_results"][0])
        src["crypto"]["research_archive/v13_crypto/latest.json"] = json.dumps(p)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CRYPTO_VARIANT"):
            h.analyze(src, {k: COMMIT for k in h.BRANCHES}, registry(), NOW)

    def test_source_rewrite_is_rejected_before_ingestion(self):
        source = source_fixture()
        old = "b" * 40
        def fetch(u):
            if "/compare/" in u:
                return json.dumps({"status": "diverged", "behind_by": 1})
            return mock_remote(source)(u)
        with self.assertRaisesRegex(ValueError, "REWRITE_OR_REWIND"):
            h.fetch_sources({"equity": old}, fetch)

    def test_upstream_sha_chain_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source.jsonl"
            h.append_chain(path, [{"id": "a", "kind": "freeze"}], 1770000000000)
            self.assertEqual(len(h.verify_upstream_ledger(path.read_text())), 1)
            bad = path.read_text().replace('"freeze"', '"altered"')
            with self.assertRaisesRegex(ValueError, "UPSTREAM_SHA_CHAIN"):
                h.verify_upstream_ledger(bad)

    def test_bootstrap_idempotent_and_existing_lab_accept_not_realerted(self):
        with tempfile.TemporaryDirectory() as d:
            src = source_fixture()
            src_path = Path(d) / "registry.json"
            src_path.write_text(json.dumps(registry()))
            state = Path(d) / "state"
            first = h.run(state, src_path, fetch=mock_remote(src), when=NOW)
            self.assertEqual(first["new_hypotheses_or_milestones"], 0)
            self.assertEqual(first["new_lab_accepts"], 0)
            self.assertEqual(first["total_evidence_events"], 1)
            self.assertEqual(h.read_chain(state / "events.jsonl")[0]["kind"],
                             "NOTIFICATION_READY")
            second = h.run(state, src_path, fetch=mock_remote(src), when=NOW)
            self.assertEqual(second["total_evidence_events"], 1)
            self.assertEqual(second["new_lab_accepts"], 0)
            self.assertEqual(json.loads(src_path.read_text()), registry())

    def test_new_lab_accept_only_after_real_registry_transition(self):
        with tempfile.TemporaryDirectory() as d:
            state, path = Path(d) / "state", Path(d) / "registry.json"
            path.write_text(json.dumps(registry()))
            source = source_fixture()
            h.run(state, path, fetch=mock_remote(source), when=NOW)
            current = registry()
            current["hypotheses"]["H120"] = {
                "verdict": "ACCEPT", "strategy": "new_hypothesis",
                "dsr": .97, "accepted_at": "2026-11-19",
            }
            path.write_text(json.dumps(current))
            result = h.run(state, path, fetch=mock_remote(source), when=NOW)
            self.assertEqual(result["new_lab_accepts"], 1)
            self.assertEqual(h.read_chain(state / "events.jsonl")[-1]["kind"],
                             "NEW_LAB_ACCEPT")

    def test_notification_receipt_only_after_success_and_deduped(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d)
            ev = {
                "schema": h.SCHEMA, "id": "setup1",
                "kind": "NOTIFICATION_READY", "market": "QUANT_SUPERLAB",
                "evidence": {}, "lab_verdict": "NOT_EVALUATED",
            }
            h.append_chain(state / "events.jsonl", [ev], 1770000000000)
            sends = []
            def send(text, tok, chat):
                sends.append(text)
                return True
            result = n.notify(state, token="token", chat="chat",
                              transport=send, when=NOW)
            self.assertEqual(result["method"], "TELEGRAM")
            self.assertEqual(result["delivered"], 1)
            self.assertEqual(n.notify(state, token="token", chat="chat",
                                      transport=send, when=NOW)["delivered"], 0)
            self.assertEqual(len(sends), 1)

    def test_notification_failure_keeps_event_pending(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d)
            h.append_chain(state / "events.jsonl", [{
                "schema": h.SCHEMA, "id": "a1",
                "kind": "NOTIFICATION_READY", "market": "QUANT_SUPERLAB",
                "evidence": {},
            }], 1770000000000)
            with self.assertRaisesRegex(RuntimeError, "UNDELIVERED"):
                n.notify(state, token="", chat="", github_token="",
                         issue_transport=lambda *args: (False, None),
                         when=NOW)
            self.assertEqual(h.read_chain(state / "receipts.jsonl"), [])
            res = n.notify(state, token="", chat="", github_token="abc",
                           issue_transport=lambda *args: (True, "1"),
                           when=NOW)
            self.assertEqual(res["method"], "GITHUB_ISSUE_FALLBACK")
            self.assertEqual(len(h.read_chain(state / "receipts.jsonl")), 1)


if __name__ == "__main__":
    unittest.main()
