"""Offline H122 contracts: no historical event alpha can be fabricated."""
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone

from research import bridge_guard as b
from research.h122 import engine as h

NOW = datetime(2026, 11, 19, 20, tzinfo=timezone.utc)
SHA = "b" * 40


def values():
    return {
        "h083_last_attempt.json": {
            "attempt_id": "2026-11-19T03:30:54+00:00|H083",
            "attempted_at_utc": "2026-11-19T03:30:54+00:00",
            "state": "SKIPPED", "reason": "OUTSIDE_17_ET_AFTERCLOSE_SLOT",
            "session": "2026-11-18", "counts_as_forward_month": False,
        },
        "event_watch_status.json": {
            "ok": True, "watch_only": True, "validated_alpha": False,
            "generated_at_utc": "2026-11-19T02:40:07+00:00",
            "feature_asof": "2026-11-18",
            "decision": "WATCH_ONLY_NO_TRADE",
            "eligible_tickers": 146, "priced_tickers": 123,
            "liquid_tickers": 109, "candidates": 7,
            "excluded_tickers": 37, "data_coverage_pct": .8425,
            "data_coverage_ok": True,
            "by_rule": {"monthly_low_beta": 5, "monthly_vol_squeeze": 2},
            "source_first_seen_forward_only": 22,
        },
        "economic_intelligence_status.json": {
            "ok": True, "research_only": True,
            "new_relationships": 0, "total_relationships": 4,
            "pending_primary_verification": 0,
            "generated_at_utc": "2026-11-18T21:40:23+00:00",
        },
        "h083_forward_status.json": None,
    }


def provider(info):
    seen = []
    def get(url):
        seen.append(url)
        if "/git/ref/heads/" in url:
            if url.endswith("/" + h.EXPANSION_BRANCH):
                if h.EXPANSION_PATH not in info:
                    raise urllib.error.HTTPError(url,404,"Not Found",{},None)
                return json.dumps({"object": {"sha": "d"*40}})
            return json.dumps({"object": {"sha": SHA}})
        if "/actions/workflows/" in url:
            return json.dumps({"workflow_runs": [
                {"id": 1, "event": "schedule", "conclusion": "success",
                 "status": "completed", "created_at": "2026-11-19T03:30:10Z",
                 "head_sha": SHA}
            ]})
        for path, value in info.items():
            if url.endswith("/" + path):
                if value is None:
                    raise urllib.error.HTTPError(url,404,"Not Found",{},None)
                return json.dumps(value)
        raise AssertionError("unexpected fetch "+url)
    return get, seen


class TestFederalIndependent(unittest.TestCase):
    def test_skipped_green_is_not_forward_success_or_event_alpha(self):
        get, seen = provider(values())
        with tempfile.TemporaryDirectory() as d:
            report = h.run(d,get,NOW)
            second = h.run(d,get,NOW)
            self.assertEqual(report["events_new"],0)
            self.assertEqual(second["events_new"],0)
            self.assertEqual(report["h083"]["last_attempt"]["state"],"SKIPPED")
            self.assertEqual(report["h083"]["forward_results_status"],
                             "NO_PUBLISHED_H083_FORWARD_JSON")
            self.assertIsNone(report["five_event_hypotheses"]["matured_positions"])
            self.assertEqual(report["five_event_hypotheses"]["SPY_relative_alpha"],
                             "NOT_EVALUATED")
            self.assertEqual(report["event_watch"]["watch_candidates"],7)
            self.assertEqual(report["alerts_pending"],0)
            self.assertEqual(len(report["five_event_hypotheses"]["fixed_names"]),5)
            self.assertTrue(all(h.SOURCE in u for u in seen))
            self.assertTrue(all("early_accumulation" not in u for u in seen))
            self.assertTrue(report["two_strategy_families_never_combined"])
            self.assertEqual(report["official_lab_accept"],"NOT_RUN")

    def test_three_distinct_skipped_sessions_warn_not_three_crons_same_session(self):
        data=values()
        sha, hashes, wf = SHA, {}, {}
        _, old, events = h.evaluate(sha,data,hashes,wf,{},NOW)
        self.assertEqual(events,[])
        self.assertEqual(old["h083_skipped_session_streak"],1)
        for i in range(2):
            data["h083_last_attempt.json"]["attempt_id"]=f"retry-{i}"
            _, old, ev = h.evaluate(sha,data,hashes,wf,old,NOW)
            self.assertEqual(ev,[])
            self.assertEqual(old["h083_skipped_session_streak"],1)
        for i, day in enumerate(("2026-11-19","2026-11-20"),start=1):
            data["h083_last_attempt.json"]["session"]=day
            data["h083_last_attempt.json"]["attempt_id"]=f"next-{i}"
            data["h083_last_attempt.json"]["attempted_at_utc"]=f"{day}T15:00:00+00:00"
            later=datetime(2026,11,21,tzinfo=timezone.utc)
            _, old, ev=h.evaluate(sha,data,hashes,wf,old,later)
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0]["kind"],"H083_REPEATED_SKIPPED_SESSIONS")
        self.assertFalse(ev[0]["broker_trade_authorized"])

    def test_completed_research_without_matured_month_is_valid(self):
        data = values()
        data["h083_last_attempt.json"].update({
            "state": "COMPLETED_RESEARCH",
            "reason": "AFTER_NYSE_CLOSE",
            "counts_as_forward_month": False,
        })
        data["h083_forward_status.json"] = {
            "ok": True, "broker_ordering": False, "information_only": True,
            "monitor_rules": ["monthly_low_beta", "monthly_vol_squeeze"],
            "research_approved_styles": 0,
            "generated_utc": "2026-11-19T11:30:00+00:00",
            "last_complete_nyse_session": "2026-11-18",
            "forward_months_closed": 0, "cohorts_frozen_this_run": 0,
            "approved_paper_rules": [], "data_coverage_ok": True,
        }
        report, _, events = h.evaluate(SHA, data, {}, {}, {}, NOW)
        self.assertEqual(events, [])
        self.assertFalse(report["h083"]["last_attempt"]["counts_as_forward_month"])
        self.assertEqual(report["h083"]["published_forward_report"]["forward_months_closed"], 0)
        self.assertTrue(report["no_official_alpha_approval"])

    def test_mature_month_is_not_trade_permission(self):
        data=values()
        f={
            "ok":True,"broker_ordering":False,"information_only":True,
            "monitor_rules":["monthly_low_beta","monthly_vol_squeeze"],
            "research_approved_styles":0,
            "generated_utc":"2026-11-19T11:30:00+00:00",
            "last_complete_nyse_session":"2026-11-18",
            "forward_months_closed":1,"cohorts_frozen_this_run":0,
            "approved_paper_rules":[],"data_coverage_ok":True,
        }
        data["h083_forward_status.json"]=f
        _, old, _ = h.evaluate(SHA,data,{}, {}, {}, NOW)
        data["h083_last_attempt.json"]["state"]="COMPLETED_RESEARCH"
        data["h083_last_attempt.json"]["counts_as_forward_month"]=True
        data["h083_last_attempt.json"]["attempt_id"]="completion"
        data["h083_last_attempt.json"]["attempted_at_utc"]="2026-11-19T16:15:00+00:00"
        f["forward_months_closed"]=2
        _, _, ev = h.evaluate(SHA,data,{}, {}, old,NOW)
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0]["kind"],"NEW_MATURED_H083_MONTH")
        self.assertEqual(ev[0]["official_lab_status"],"NOT_RUN")

    def test_rejects_fabricated_approval_or_bogus_watch_quality(self):
        data=values()
        data["event_watch_status.json"]["validated_alpha"]=True
        with self.assertRaisesRegex(ValueError,"MISREPRESENTED"):
            h.evaluate(SHA,data,{}, {}, {},NOW)
        data=values()
        data["event_watch_status.json"]["candidates"]=30
        with self.assertRaisesRegex(ValueError,"NOT_RECONCILED"):
            h.evaluate(SHA,data,{}, {}, {},NOW)
        data=values()
        data["h083_last_attempt.json"]["counts_as_forward_month"]=True
        with self.assertRaisesRegex(ValueError,"SKIPPED_CANNOT_COUNT"):
            h.evaluate(SHA,data,{}, {}, {},NOW)

    def test_real_source_watch_outage_is_preserved_and_alerted_once(self):
        data = values()
        _, old, _ = h.evaluate(SHA, data, {}, {}, {}, NOW)
        outage = values()
        outage["event_watch_status.json"].update({
            "ok": False, "data_coverage_ok": False,
            "data_coverage_pct": 0.726, "priced_tickers": 106, "liquid_tickers": 100,
            "excluded_tickers": 46, "candidates": 0,
            "by_rule": {"monthly_low_beta": 0, "monthly_vol_squeeze": 0},
            "reason": "INSUFFICIENT_PRICE_COVERAGE",
        })
        report, old2, events = h.evaluate(SHA, outage, {}, {}, old, NOW)
        self.assertEqual(report["event_watch"]["source_report_ok"], False)
        self.assertEqual(report["event_watch"]["source_failure_reason"],
                         "INSUFFICIENT_PRICE_COVERAGE")
        self.assertEqual(report["event_watch"]["watch_candidates"], 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "H083_COVERAGE_LOST")
        self.assertEqual(report["original_lab_gate"], "NOT_RUN")
        _, _, repeated = h.evaluate(SHA, outage, {}, {}, old2, NOW)
        self.assertEqual(repeated, [])
        outage["event_watch_status.json"]["candidates"] = 1
        with self.assertRaisesRegex(ValueError, "UNSAFE_WATCH_OUTAGE"):
            h.evaluate(SHA, outage, {}, {}, old, NOW)

    def test_source_coverage_ratio_and_healthy_flag_are_checked(self):
        data=values()
        data["event_watch_status.json"]["data_coverage_pct"]=.99
        with self.assertRaisesRegex(ValueError,"PERCENT_NOT_RECONCILED"):
            h.evaluate(SHA,data,{}, {}, {},NOW)
        data=values()
        data["event_watch_status.json"].update(priced_tickers=100,liquid_tickers=95,data_coverage_pct=round(100/146,4))
        with self.assertRaisesRegex(ValueError,"UNSAFE_HEALTHY_COVERAGE"):
            h.evaluate(SHA,data,{}, {}, {},NOW)

    def test_complete_benchmark_outage_remains_evidence_not_an_exception(self):
        data=values()
        _, old, _=h.evaluate(SHA,data,{}, {}, {},NOW)
        data["event_watch_status.json"].update(
            ok=False, reason="MISSING_REQUIRED_BENCHMARK_SESSION", data_coverage_ok=False,
            data_coverage_pct=0.0, priced_tickers=0, liquid_tickers=0, candidates=0,
            excluded_tickers=146, by_rule={"monthly_low_beta":0,"monthly_vol_squeeze":0},
            exclusion_detail_reasons={"MISSING_REQUIRED_BENCHMARK_SESSION":146},
            price_download={"total_recovered":2,"independent_recovered":2,"recovery_round":3})
        report, _, events=h.evaluate(SHA,data,{}, {}, old,NOW)
        self.assertEqual(report["event_watch"]["source_price_recovery"]["total_recovered"],2)
        self.assertEqual(report["event_watch"]["source_failure_reason"],"MISSING_REQUIRED_BENCHMARK_SESSION")
        self.assertIn("0/146",events[0]["message"])
        self.assertEqual(report["original_lab_gate"],"NOT_RUN")

    def test_failed_forward_envelope_preserves_last_success_and_deduplicates(self):
        data = values()
        good = {
            "ok": True, "broker_ordering": False, "information_only": True,
            "monitor_rules": ["monthly_low_beta", "monthly_vol_squeeze"],
            "research_approved_styles": 0,
            "generated_utc": "2026-11-19T11:30:00+00:00",
            "last_complete_nyse_session": "2026-11-18",
            "forward_months_closed": 2, "cohorts_frozen_this_run": 0,
            "approved_paper_rules": [], "data_coverage_ok": True,
        }
        data["h083_forward_status.json"] = good
        _, old, _ = h.evaluate(SHA, data, {}, {}, {}, NOW)
        data["h083_last_attempt.json"].update({
            "state": "FAILED", "reason": "RuntimeError", "attempt_id": "failure",
            "attempted_at_utc": "2026-11-19T16:00:00+00:00",
            "session": "", "counts_as_forward_month": False,
        })
        failure = {
            "ok": False, "information_only": True, "broker_ordering": False,
            "last_attempt_utc": "2026-11-19T16:00:00.006+00:00",
            "error_type": "RuntimeError", "error": "No new decision",
        }
        data["h083_forward_status.json"] = failure
        report, failed, ev = h.evaluate(SHA, data, {}, {}, old, NOW)
        self.assertEqual([x["kind"] for x in ev], ["H083_RUN_FAILED"])
        self.assertIsNone(report["h083"]["published_forward_report"])
        self.assertEqual(report["h083"]["forward_results_status"],
                         "SOURCE_FAILED_NO_NEW_FORWARD_RESULT")
        self.assertEqual(failed["forward"], old["forward"])
        self.assertEqual(report["h083"]["last_verified_forward_report"]["forward_months_closed"], 2)
        self.assertEqual(h.evaluate(SHA, data, {}, {}, failed, NOW)[2], [])
        data["h083_last_attempt.json"].update({
            "state": "SKIPPED", "reason": "WRONG_DST_CRON_SLOT",
            "attempt_id": "safe-skip", "session": "2026-11-19",
            "attempted_at_utc": "2026-11-19T17:00:00+00:00",
        })
        _, skipped, _ = h.evaluate(SHA, data, {}, {}, failed, NOW)
        self.assertEqual(skipped["forward"], old["forward"])
        failure["broker_ordering"] = True
        with self.assertRaisesRegex(ValueError, "UNSAFE_FORWARD_FAILURE"):
            h.evaluate(SHA, data, {}, {}, skipped, NOW)
        failure["broker_ordering"] = False
        failure["forward_months_closed"] = 99
        with self.assertRaisesRegex(ValueError, "UNSAFE_FORWARD_FAILURE"):
            h.evaluate(SHA, data, {}, {}, skipped, NOW)
        data["h083_forward_status.json"] = dict(good, forward_months_closed=1)
        with self.assertRaisesRegex(ValueError, "CLOSED_FORWARD_MONTHS_DISAPPEARED"):
            h.evaluate(SHA, data, {}, {}, skipped, NOW)
        data["h083_forward_status.json"] = dict(good, forward_months_closed=2)
        _, _, recovered = h.evaluate(SHA, data, {}, {}, skipped, NOW)
        self.assertEqual(recovered, [])

    def test_h083_source_missing_forward_never_claims_no_profit(self):
        data=values()
        result,_,_=h.evaluate(SHA,data,{}, {}, {},NOW)
        self.assertIsNone(result["executable_broker_pnl"])
        self.assertTrue(result["no_official_alpha_approval"])
        self.assertEqual(result["five_event_hypotheses"]["published_forward_20_session_net_scores"],
                         "NOT_AVAILABLE_AS_READABLE_SOURCE")




class TestExpansionIsolation(unittest.TestCase):
    def expansion(self):
        return {"schema":"H083_EXPANSION_V1","scope":"ISOLATED_PROSPECTIVE_WATCH_ONLY",
                "watch_only":True,"validated_alpha":False,"paper_approved":False,
                "core_coverage_not_modified":True,"decision":"WATCH_ONLY_NO_TRADE",
                "generated_at_utc":"2026-11-19T02:40:07+00:00","feature_asof":"2026-11-18",
                "core_eligible_tickers":146,"eligible_tickers":54,"priced_tickers":49,
                "liquid_tickers":40,"candidates":10,"discovered_tickers":600,
                "pending_capacity":480,"pending_prior_history":66,
                "total_screened_tickers":200,"total_limit":200,"next_total_limit":200,
                "data_coverage_pct":round(49/54,4),"data_coverage_ok":True,"ok":True,
                "source_commit_sha":SHA}

    def test_expansion_success_does_not_hide_core_outage(self):
        d = values()
        d["event_watch_status.json"].update(ok=False, data_coverage_ok=False,
            priced_tickers=106, liquid_tickers=99, data_coverage_pct=round(106/146,4),
            candidates=0, by_rule={"monthly_low_beta":0,"monthly_vol_squeeze":0},
            reason="INSUFFICIENT_PRICE_COVERAGE")
        d[h.EXPANSION_PATH] = self.expansion()
        get, seen = provider(d)
        with tempfile.TemporaryDirectory() as state:
            r = h.run(state,get,NOW)
        self.assertEqual(r["h083_expansion"]["status"],"WATCH_ONLY_COVERAGE_OK")
        self.assertFalse(r["event_watch"]["data_coverage_ok"])
        self.assertFalse(r["h083_expansion"]["counts_toward_core_coverage"])
        self.assertEqual(r["h083_expansion"]["source_commit_sha"],"d"*40)
        self.assertTrue(any("/"+"d"*40+"/"+h.EXPANSION_PATH in u for u in seen))
        self.assertEqual(r["event_watch"]["priced_tickers"],106)

    def test_invalid_optional_expansion_never_interrupts_core(self):
        d = values()
        d[h.EXPANSION_PATH] = dict(self.expansion(), paper_approved=True)
        get, _ = provider(d)
        with tempfile.TemporaryDirectory() as state:
            r = h.run(state,get,NOW)
        self.assertTrue(r["event_watch"]["data_coverage_ok"])
        self.assertEqual(r["h083_expansion"]["status"],"INVALID_OR_UNAVAILABLE_EXPANSION_EVIDENCE")

    def test_stale_expansion_not_healthy_and_absent_is_optional(self):
        d = values()
        d[h.EXPANSION_PATH] = dict(self.expansion(), feature_asof="2026-11-17")
        get,_ = provider(d)
        with tempfile.TemporaryDirectory() as state:
            r = h.run(state,get,NOW)
        self.assertEqual(r["h083_expansion"]["status"],"STALE_OR_CORE_CHANGED")
        self.assertFalse(r["h083_expansion"]["data_coverage_ok"])
        get,_ = provider(values())
        with tempfile.TemporaryDirectory() as state:
            r = h.run(state,get,NOW)
        self.assertEqual(r["h083_expansion"]["status"],"NOT_YET_PUBLISHED")


if __name__=="__main__":
    unittest.main()
