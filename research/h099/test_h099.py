import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from replicate import pair,bootstrap_ci,compare_trades

def trade(t,r,side="long"):
    return {"entry_ms":t,"exit_ms":t+1,"family":"BOS","side":side,"net_r":r}

class H099Tests(unittest.TestCase):
    def test_exact_entry_matching(self):
        p=pair([trade(10,1),trade(20,-1)],[trade(10,.5),trade(21,2)])
        self.assertEqual(p["matched_n"],1)
        self.assertEqual(p["primary_only"],1)
        self.assertEqual(p["secondary_only"],1)
        self.assertAlmostEqual(p["mean_secondary_minus_primary_r"],-.5)
        self.assertFalse(p["alpha_accepted"])

    def test_no_nearest_match(self):
        self.assertEqual(pair([trade(10,1)],[trade(11,1)])["matched_n"],0)

    def test_empty_and_zero_variance(self):
        self.assertIsNone(pair([],[])["mean_primary_matched_net_r"])
        self.assertEqual(bootstrap_ci([1]*50)["ci_95"],[1,1])

    def test_bootstrap_deterministic(self):
        a=bootstrap_ci([i/10 for i in range(50)],seed=11)
        b=bootstrap_ci([i/10 for i in range(50)],seed=11)
        self.assertEqual(a,b)
        self.assertFalse(a["alpha_accepted"])

    def test_small_samples_fail_closed(self):
        self.assertEqual(bootstrap_ci([1]*29)["status"],"INSUFFICIENT_SAMPLE")
        r=compare_trades([trade(10,1)],[trade(10,.5)])
        self.assertFalse(r["statistical_significance_verified"])
        self.assertEqual(r["secondary_bootstrap"]["status"],"INSUFFICIENT_SAMPLE")

if __name__=="__main__":unittest.main()
