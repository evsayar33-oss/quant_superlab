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

    def test_h083_source_missing_forward_never_claims_no_profit(self):
        data=values()
        result,_,_=h.evaluate(SHA,data,{}, {}, {},NOW)
        self.assertIsNone(result["executable_broker_pnl"])
        self.assertTrue(result["no_official_alpha_approval"])
        self.assertEqual(result["five_event_hypotheses"]["published_forward_20_session_net_scores"],
                         "NOT_AVAILABLE_AS_READABLE_SOURCE")


if __name__=="__main__":
    unittest.main()
