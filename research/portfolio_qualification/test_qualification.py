"""Offline non-regression tests for fail-closed cross-repo observation."""
import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock
from research.portfolio_qualification.audit import interpret, collect, load_catalog
from research.portfolio_qualification.synthesis import plan
from research.portfolio_qualification.gate import review, no_automatic_promotion


class Qualification(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()
        self.projects = {x["name"]: x for x in self.catalog["projects"]}

    def item(self, name, evidence):
        return interpret(self.projects[name], {"repo": "evsayar33-oss/" + name,
            "evidence": evidence, "ref_pins": {}, "errors": {}, "observed_sources": list(evidence)})

    def test_all_ten_projects_are_distinct(self):
        self.assertEqual(len(self.projects), 10)

    def test_lab_watch_and_reject_never_promoted(self):
        r = self.item("quant_superlab", {"registry": {"hypotheses": {
            "H1": {"verdict": "WATCH"}, "H2": {"verdict": "REJECT"},
            "H3": {"verdict": "ACCEPT"}}}})
        self.assertEqual(r["metrics"]["accepted_ids"], ["H3"])
        self.assertFalse(r["new_live_approval"])

    def test_h083_research_completion_and_skips_not_forward(self):
        for name in ("COMPLETED_RESEARCH", "SKIPPED"):
            r = self.item("federal-incentive-radar", {
                "h083": {"state": name, "counts_as_forward_month": False},
                "forward": {"forward_months_closed": 0},
                "watch": {"validated_alpha": False}})
            self.assertEqual(r["metrics"]["months_completed"], 0)
            self.assertFalse(r["new_paper_approval"])

    def test_early_green_not_alpha(self):
        r = self.item("early_accumulation_radar", {"crypto": {
            "strategy_variants_tested": 92, "modeled_outcomes": 0,
            "pending_future_outcomes": 152},
            "association": {"matured_case_control_samples": 0}})
        self.assertEqual(r["status"], "RESEARCH_NO_MATURED_OUTCOMES")
        self.assertFalse(r["trade_authorized"])

    def test_paper_approval_is_not_live_approval(self):
        r = self.item("h054_spot_bot", {"registry": {"hypotheses": {
            "H054-MOM2": {"verdict": "PAPER_ACCEPT", "live_verdict": "DENY"}}}})
        self.assertEqual(r["status"], "LOCAL_PAPER_APPROVAL_LIVE_DENIED")
        self.assertFalse(r["new_live_approval"])

    def test_demo_loss_not_confused_with_prospective_alpha(self):
        r = self.item("us_f1_bot", {"demo": {
            "capital_usd": 10000, "risk_snapshot": {"nav_usd": 7734.06}}})
        self.assertEqual(r["metrics"]["demo_nav_vs_initial_pct"], -22.66)
        self.assertFalse(r["new_paper_approval"])

    def test_no_false_pit_proof(self):
        r = self.item("bist_orderflow_quant", {"backtest": {
            "portfolio": {"cagr_pct": 72.38}}})
        self.assertEqual(r["status"], "HISTORICAL_BACKTEST_PIT_NOT_VERIFIED")

    def test_missing_source_fail_closed(self):
        project = self.projects["h054_spot_bot"]
        output = collect(project, fetch=lambda *_: (_ for _ in ()).throw(ValueError("failed")))
        self.assertFalse(output["evidence"])
        self.assertEqual(len(output["errors"]), 2)
        r = interpret(project, output)
        self.assertEqual(r["status"], "UNKNOWN_SOURCE_EVIDENCE")
        self.assertFalse(r["new_live_approval"])

    def test_public_source_ref_is_commit_pinned(self):
        seen = []
        def fake(url, token):
            seen.append(url)
            if "git/ref/heads/" in url:
                return '{"object":{"sha":"' + "a" * 40 + '"}}'
            return '{"hypotheses":{}}'
        project = self.projects["h054_spot_bot"]
        data = collect(project, fetch=fake)
        self.assertEqual(data["ref_pins"]["main"], "a" * 40)
        self.assertTrue(all("/" + "a" * 40 + "/" in u for u in seen if "raw." in u))
        self.assertEqual(len([u for u in seen if "git/ref/" in u]), 1)

    def test_bounded_designs_are_not_registered_signals(self):
        d = plan(self.catalog)
        self.assertFalse(d["auto_promote"])
        self.assertLess(sum(len(v) for v in d["projects"].values()), 200)
        self.assertTrue(all(x["validation"] == "NOT_RUN" and
                            not x["paper_approved"] for x in d["projects"]["early_accumulation_radar"]))

    def test_all_designs_deterministic(self):
        self.assertEqual(plan(self.catalog), plan(self.catalog))

    def test_new_paper_gate_rejects_missing_receipts(self):
        r = review({"hypothesis_id": "H123", "independent_oos_verified": True})
        self.assertEqual(r["status"], "NOT_ELIGIBLE_FOR_PAPER_REVIEW")
        self.assertFalse(r["paper_approved"])

    def test_paper_gate_review_does_not_auto_promote_even_complete(self):
        dates = ["2026-01-01T00:00:00Z", "2026-01-10T00:00:00Z",
                 "2026-01-11T00:00:00Z", "2026-03-01T00:00:00Z",
                 "2026-03-10T00:00:00Z"]
        p = {k: True for k in (
            "asof_only", "quality_verified", "universe_bias_accounted",
            "registered_before_outcomes", "matched_controls_verified",
            "independent_oos_verified", "cost_stress_verified",
            "realistic_fill_assumptions_verified", "multi_testing_adjusted",
            "regime_robustness_verified", "prospective_outcomes_matured")}
        p.update(methodology_sha256="b"*64, source_evidence_sha256="a"*64,
                 hypothesis_id="H999", source_repository="owner/repo",
                 strategy_definition="frozen", benchmark="index",
                 registered_utc=dates[0], train_end_utc=dates[1],
                 oos_start_utc=dates[2], oos_end_utc=dates[3],
                 latest_outcome_at_utc=dates[4],
                 distinct_time_blocks=10, completed_trades_or_events=40,
                 read_only_research=True)
        r = review(p)
        self.assertEqual(r["status"], "READY_FOR_INDEPENDENT_PAPER_REVIEW")
        self.assertFalse(r["paper_approved"])
        p["oos_start_utc"] = "2026-01-05T00:00:00Z"
        self.assertIn("INVALID_TEMPORAL_OR_PREREGISTRATION_ORDER",
                      review(p)["blockers"])

    def test_promotion_is_never_an_api(self):
        with self.assertRaises(PermissionError):
            no_automatic_promotion("anything")


if __name__ == "__main__":
    unittest.main()
