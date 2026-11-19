"""Independent regression checks for train-only stage pools and OOS trade provenance."""
from __future__ import annotations

import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

from lab import candidates as CD, strict_oos, validation
from lab.engine import Costs
from lab.panel import Panel


class FakeRule(CD.RuleCandidate):
    def __init__(self):
        self.staged = True
        self.stage2_top = 1

    def variants(self, stage=1, seeds=None):
        if stage == 2:
            return [CD.Variant(s.key + "_exit2", {"_exit": 1}) for s in (seeds or [])]
        return []

    def overlay_variants(self, seeds):
        return []


def series(data, index):
    return pd.Series(data, index=index, dtype=float)


def make_case(add_trades=False):
    idx = pd.bdate_range("2023-01-01", periods=27)
    p = Panel.from_close(
        pd.DataFrame({"C": np.linspace(100, 120, len(idx))}, index=idx),
        seed=1,
    )
    # First fold trains on first ten rows. A is strongest only in that
    # period, B wins on the complete observed series after the cutoff.
    rng = np.random.default_rng(11)
    a = np.r_[rng.normal(.02, .005, 10), rng.normal(-.002, .005, 17)]
    z = np.r_[rng.normal(-.02, .005, 10), rng.normal(.03, .005, 17)]
    x = np.r_[rng.normal(.03, .005, 10), rng.normal(-.02, .005, 17)]
    y = np.r_[rng.normal(-.02, .005, 10), rng.normal(.30, .005, 17)]
    def row(ret):
        trades = pd.DataFrame()
        if add_trades:
            trades = pd.DataFrame([
                {"entry": idx[9], "exit": idx[10], "ret": .10},
                {"entry": idx[11], "exit": idx[12], "ret": .02},
            ])
        return series(ret,idx), series(np.zeros(len(idx)),idx), trades
    records = {"A":row(a), "B":row(z), "A_exit2":row(x), "B_exit2":row(y)}
    start = [CD.Variant("A",{}), CD.Variant("B",{})]
    def mock_run(cand,panel,variants,costs):
        return {v.key: records[v.key] for v in variants}, {}
    return idx,p,start,records,mock_run


class StrictWalkForwardTests(unittest.TestCase):
    def test_later_winner_cannot_generate_earlier_fold_seed(self):
        idx,p,first,data,mock_run = make_case()
        with patch.object(CD, "run_all", side_effect=mock_run):
            out = strict_oos.nested_walk_forward(
                FakeRule(),p,Costs(),first, {k:data[k] for k in ("A","B")},
                train_years=1.0,test_months=6,warm=0,ppy=10)
        self.assertGreater(len(out["folds"]),0)
        self.assertEqual(out["folds"][0]["variant"],"A_exit2")
        self.assertTrue(out["folds"][0]["train_only_seed_selection"])
        self.assertEqual(out["folds"][0]["test_start"],str(idx[10]))
        self.assertNotIn("B_exit2",out["folds"][0]["variant"])
        self.assertIn("A_exit2",out["cache"])
        self.assertTrue(out["complete"])

    def test_count_ledger_only_for_selected_fold_closed_trades(self):
        _,p,first,data,mock_run = make_case(add_trades=True)
        with patch.object(CD, "run_all", side_effect=mock_run):
            out = strict_oos.nested_walk_forward(
                FakeRule(),p,Costs(),first,{k:data[k] for k in ("A","B")},
                train_years=1,test_months=6,warm=0,ppy=10)
        self.assertEqual(len(out["trades"]),1)
        self.assertEqual(out["cross_boundary_trades"],1)
        self.assertFalse(out["fold_execution_verified"])

    def test_all_missing_folds_fail_closed(self):
        _,p,first,data,_ = make_case()
        with patch.object(CD,"run_all",return_value=({},{"A_exit2":"failed"})):
            bad=dict(data)
            bad["A"]=(pd.Series(np.nan,index=p.index),bad["A"][1],bad["A"][2])
            with self.assertRaisesRegex(ValueError,"NO_TRAIN_QUALIFIED_VARIANT"):
                strict_oos.nested_walk_forward(
                    FakeRule(),p,Costs(),first,{"A":bad["A"],"B":bad["A"]},
                    train_years=1,test_months=6,warm=0,ppy=10)

    def test_verdict_never_accepts_unverified_folds_or_missing_pbo(self):
        base = {
            "oos":{"years":4.0,"max_dd":-.10},
            "gate_sharpe":1.2,"gate_sharpe_basis":"USD",
            "dsr":.97,"n_trials":2,
            "oos_usd":None,"bootstrap":{"p_sharpe_pos":.99},
            "yearly_sharpe":{"2020":1,"2021":1,"2022":1,"2023":1},
            "stress_2x_cost":{"sharpe":1},"benchmark":{"sharpe":0},
            "pbo":None,"reality_check_p":None,"kind":"strategy",
            "robustness_studies_requested":True,
            "oos_selection_provenance":{
                "train_only_seeds":True, "independent_fold_count":4,
                "fold_execution_verified":False,"test_return_gaps":0,
            }
        }
        verdict,reasons=validation.verdict(base)
        self.assertNotEqual(verdict,"ACCEPT")
        self.assertTrue(any("fold boundary" in r for r in reasons))
        self.assertTrue(any("PBO" in r for r in reasons))
        # Even after a replay, missing significance cannot pass.
        base["oos_selection_provenance"]["fold_execution_verified"]=True
        self.assertNotEqual(validation.verdict(base)[0],"ACCEPT")

    def test_monte_carlo_separates_new_path_risk_from_permutation(self):
        from lab import robustness as rb
        values = np.random.default_rng(19).normal(.0005, .011, 140)
        block = validation.block_bootstrap(pd.Series(values), n=200, block=5, seed=99)
        self.assertEqual(block["method"], "CIRCULAR_STATIONARY_RETURN_BLOCK_BOOTSTRAP")
        self.assertEqual(block["simulated_paths"], 200)
        self.assertGreater(block["cagr_p05"], -1.01)
        self.assertLess(block["cagr_p05"], 1.0)
        self.assertLess(block["maxdd_p05"], 0.0)
        ledger = pd.DataFrame({"ret": [.04,-.03,.02,-.01,.03,-.02,.04,-.01,.02,-.03],
                               "weight": [1.] * 10})
        shuffle = rb.mc_trade_shuffle(ledger, n=200, seed=99)
        self.assertEqual(shuffle["method"],"TRADE_ORDER_PERMUTATION_DRAWDOWN_ONLY")
        self.assertTrue(shuffle["terminal_wealth_order_invariant"])
        self.assertAlmostEqual(shuffle["final_p05"],shuffle["final_median"],places=3)

    def test_rule_needs_genuine_fold_trades_and_robustness(self):
        base = {
            "oos":{"years":4.0,"max_dd":-.10},
            "gate_sharpe":1.2,"gate_sharpe_basis":"USD",
            "dsr":.97,"n_trials":1,"oos_usd":None,
            "bootstrap":{"p_sharpe_pos":.99},
            "yearly_sharpe":{"2020":1,"2021":1,"2022":1,"2023":1},
            "stress_2x_cost":{"sharpe":1},"benchmark":{"sharpe":0},
            "pbo":None,"reality_check_p":None,"kind":"rule",
            "trade_stats":{"n_trades":0},"robustness":{},
            "robustness_studies_requested":False,
            "oos_selection_provenance":{
                "train_only_seeds":True,"independent_fold_count":4,
                "fold_execution_verified":True,"test_return_gaps":0,
            }
        }
        verdict,reasons=validation.verdict(base)
        self.assertNotEqual(verdict,"ACCEPT")
        self.assertTrue(any("genuine fold-closed OOS trades" in r for r in reasons))
        self.assertTrue(any("mandatory rule robustness" in r for r in reasons))


if __name__=="__main__":
    unittest.main()
