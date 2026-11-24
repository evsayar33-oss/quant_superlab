import unittest
from research.portfolio_qualification import eaverse_report_gate as g

class ReportGateTests(unittest.TestCase):
    def test_all_known_report_types(self):
        for schema,key in g.REPORTS.items():
            report={"schema":schema,"paper_eligible":False}
            if key:
                report[key]=[{"id":"x"}]
            result=g.review_report(report)
            self.assertTrue(result["registered_schema"])
            self.assertTrue(result["records"][0]["gate"]["blockers"])
            self.assertFalse(result["central_lab_accept"])
    def test_unknown_and_promotion(self):
        self.assertEqual(g.review_report({"schema":"unknown"})["classification"],"UNMAPPED_REPORT_BLOCKED")
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED"):
            g.review_report({"schema":"unknown","live_allowed":True})
    def test_cohort_hash(self):
        with self.assertRaisesRegex(ValueError,"HASH"):
            g.review_cohort({"panel":{"sha256":"bad"}})
