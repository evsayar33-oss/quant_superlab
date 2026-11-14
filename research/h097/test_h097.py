import sys
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[0]/"h096"))
from audit import folds,configuration,bonferroni_one_sided,audit,regimes
from funding import parse,fetch,funding_for_trade
from detectors import detect,TF_MS


def bars(n,tf="5m"):
    step=TF_MS[tf]
    return [{"ts":i*step,"open":100+i*.01,"high":101+i*.01,
             "low":99+i*.01,"close":100.1+i*.01} for i in range(n)]


class H097Tests(unittest.TestCase):
    def test_anchored_expanding_and_embargo(self):
        fs=folds(500)
        self.assertGreaterEqual(len(fs),3)
        self.assertEqual(fs[0]["train_end"],100)
        for f in fs:
            self.assertEqual(f["test_start"]-f["train_end"],24)
            self.assertLessEqual(f["test_end"],500)
        self.assertEqual(fs[1]["train_end"],fs[0]["train_end"]+60)

    def test_small_sample_no_folds(self):
        self.assertEqual(folds(150),[])
        with self.assertRaises(ValueError):folds(0)

    def test_multiple_testing_never_claims_valid_p(self):
        self.assertEqual(len(configuration()),216)
        a=bonferroni_one_sided([1,2,3,4],216)
        self.assertEqual(a["status"],"HEURISTIC_ONLY_NOT_DEPENDENCE_ROBUST")
        self.assertGreaterEqual(a["p_bonferroni_heuristic"],a["p_heuristic"])
        self.assertEqual(bonferroni_one_sided([1,1,1],216)["status"],
                         "NOT_TESTABLE_INSUFFICIENT_VARIANCE")

    def test_no_accept_even_with_data(self):
        b=bars(280)
        events=detect(b,"BTC","5m")["events"]
        r=audit(b,events,[],"5m",{"sha256":"fixture"})
        self.assertEqual(r["configuration_count"],216)
        self.assertFalse(r["alpha_accepted"])
        self.assertFalse(r["fresh_out_of_sample"])
        self.assertFalse(r["live_fills_confirmed"])
        self.assertTrue(all(not x["alpha_accepted"] for x in r["results"]))
        self.assertTrue(all(x["evidence_status"]=="INSUFFICIENT_WALK_FORWARD_EVIDENCE"
                            for x in r["results"]))

    def test_real_funding_parse_and_missing_cost(self):
        row={"fundingTime":"1700000000000","realizedRate":"0.0001"}
        self.assertEqual(parse({"code":"0","data":[row]})[0]["realized_rate"],.0001)
        self.assertIsNone(funding_for_trade({"entry_ms":0,"exit_ms":1800000000000},
                                             parse({"code":"0","data":[row]}))["applied_cost"])
        with self.assertRaises(ValueError):parse({"code":"0","data":[row,row]})
        with self.assertRaises(ValueError):parse({"code":"500","data":None})

    def test_funding_pagination_and_provider_failure(self):
        row={"fundingTime":"1700000000000","realizedRate":"0.0001"}
        f=fetch("BTC",pages=1,get=lambda url:{"code":"0","data":[row]})
        self.assertEqual(f["count"],1)
        self.assertFalse(f["exact_trade_funding_costs_verified"])
        with self.assertRaises(ValueError):
            fetch("BTC",pages=1,get=lambda url:{"code":"500","data":[]})

if __name__=="__main__":unittest.main()
