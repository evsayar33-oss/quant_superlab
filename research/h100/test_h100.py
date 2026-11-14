import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit import screen

def fixture(means=(.1,.2,.3),n=40,frac=.75):
    results={}
    for venue,mu in zip(("gate","bitget","mexc"),means):
        results["BTC_15m_"+venue]={"status":"DESCRIPTIVE_TRADE_PROXY_COMPARISON",
          "configurations":{"BOS:long:all":{
            "matched_n":n,"match_fraction_primary":frac,
            "mean_secondary_matched_net_r":mu,
            "mean_primary_matched_net_r":.1,
            "secondary_bootstrap":{"ci_95":[mu-.05,mu+.05]}}}}
    return {"schema":"H099.independent_trade_proxy.v1","alpha_accepted":False,
            "results":results}

class H100Tests(unittest.TestCase):
    def test_three_positive_venues_descriptive_only(self):
        r=screen(fixture())
        x=r["configurations"]["BTC_15m:BOS:long:all"]
        self.assertEqual(x["status"],"DESCRIPTIVE_CONSISTENT_POSITIVE")
        self.assertTrue(x["all_venue_bootstrap_lower_bounds_positive"])
        self.assertFalse(x["alpha_accepted"])
        self.assertFalse(r["untouched_oos_verified"])
        self.assertEqual(r["configuration_count"],96)

    def test_one_negative_venue_blocks_consistency(self):
        x=screen(fixture((.1,-.2,.3)))["configurations"]["BTC_15m:BOS:long:all"]
        self.assertEqual(x["status"],"DESCRIPTIVE_MIXED_OR_NEGATIVE")

    def test_missing_venue_fails_closed(self):
        f=fixture()
        del f["results"]["BTC_15m_mexc"]
        x=screen(f)["configurations"]["BTC_15m:BOS:long:all"]
        self.assertEqual(x["status"],"INSUFFICIENT_INDEPENDENT_REPLICATION")

    def test_low_match_count_fails_closed(self):
        x=screen(fixture(n=29))["configurations"]["BTC_15m:BOS:long:all"]
        self.assertEqual(x["venue_count"],0)

    def test_low_match_fraction_fails_closed(self):
        x=screen(fixture(frac=.49))["configurations"]["BTC_15m:BOS:long:all"]
        self.assertEqual(x["venue_count"],0)

    def test_invalid_alpha_gate_rejected(self):
        f=fixture();f["alpha_accepted"]=True
        with self.assertRaises(ValueError):screen(f)

    def test_no_cost_stress_claim(self):
        r=screen(fixture())
        self.assertIn("NOT_TESTABLE",r["cost_stress_status"])
        self.assertFalse(r["research_complete"])

if __name__=="__main__":unittest.main()
