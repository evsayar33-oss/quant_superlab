"""H090 deterministic contract tests; all fixtures synthetic, no alpha claimed."""
from __future__ import annotations
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from engine import Event, evaluate_recipe, load_recipes, validate_recipe
from audit import audit, load_catalog, render_markdown
from orchestrator import route, scan

def ev(id,kind,tf,at,*,side="long",attrs=None,symbol="BTC",source="synthetic_fixture"):
    return {"event_id":id,"symbol":symbol,"kind":kind,"timeframe":tf,"side":side,
            "occurred_at":at,"observed_at":at,"source":source,"attrs":attrs or {}}


class H090Contracts(unittest.TestCase):
    def setUp(self):
        self.recipes={r["id"]:r for r in load_recipes()}

    def test_catalog_reports_gaps_and_never_claims_alpha(self):
        report=audit()
        self.assertFalse(report["research_complete"])
        self.assertFalse(report["portfolio_alpha_verified"])
        self.assertFalse(report["real_fills_verified"])
        self.assertIn("technical_macro_event_join",report["unverified_capabilities"])
        self.assertIn("base_ob_all_tf",report["unverified_requirements"])
        self.assertIn("NOT A BACKTEST",render_markdown(report))

    def test_all_recipe_contracts_and_explicit_order(self):
        for recipe in self.recipes.values():
            validate_recipe(recipe)
            self.assertGreater(len(recipe["sequence"]),0)
            self.assertIn(recipe["side"],("long","short"))
        r=self.recipes["H090_LIQ_MSS_OB_TARGET"]
        self.assertEqual([s["kind"] for s in r["sequence"]],
                         ["LIQ_SWEEP","MSS_CONFIRM","OB_TOUCH"])

    def test_sweep_mss_ob_sequence_and_liquidity_tp(self):
        r=self.recipes["H090_LIQ_MSS_OB_TARGET"]
        a=[
          ev("f4","FIB_POSITION","H4","2026-11-01T00:00:00Z",attrs={"position":"below_05","range_anchored_asof":"2026-10-31"}),
          ev("f1","FIB_POSITION","H1","2026-11-01T00:00:00Z",attrs={"position":"below_05","range_anchored_asof":"2026-10-31"}),
          ev("tp","LIQ_TARGET","H4","2026-11-01T00:00:00Z",attrs={"price":120.0}),
          ev("s","LIQ_SWEEP","H4","2026-11-01T01:00:00Z"),
          ev("m","MSS_CONFIRM","H1","2026-11-01T02:00:00Z"),
          ev("o","OB_TOUCH","M15","2026-11-01T03:00:00Z",attrs={"price":100.0}),
        ]
        x=evaluate_recipe(a,r,asof="2026-11-01T04:00:00Z")
        self.assertEqual(len(x),1)
        self.assertEqual(x[0]["event_ids"],["s","m","o"])
        self.assertEqual(x[0]["target_family"],"LIQ_TARGET")
        self.assertFalse(x[0]["profitability_verified"])
        self.assertFalse(evaluate_recipe(a,r,asof="2026-11-01T02:59:00Z"))
        wrong=[z for z in a if z["event_id"]!="m"]
        self.assertFalse(evaluate_recipe(wrong,r,asof="2026-11-01T04:00:00Z"))

    def test_ob_out_of_order_and_distant_confirmation_rejected(self):
        r=self.recipes["H090_LIQ_MSS_OB_TARGET"]
        a=[
          ev("f4","FIB_POSITION","H4","2026-11-01T00:00:00Z",attrs={"position":"below_05","range_anchored_asof":"x"}),
          ev("f1","FIB_POSITION","H1","2026-11-01T00:00:00Z",attrs={"position":"below_05","range_anchored_asof":"x"}),
          ev("tp","LIQ_TARGET","H4","2026-11-01T00:00:00Z",attrs={"price":120.0}),
          ev("m","MSS_CONFIRM","H1","2026-11-01T01:00:00Z"),
          ev("s","LIQ_SWEEP","H4","2026-11-01T02:00:00Z"),
          ev("o","OB_TOUCH","M15","2026-11-01T03:00:00Z",attrs={"price":100.0})]
        self.assertEqual(evaluate_recipe(a,r,asof="2026-11-01T04:00:00Z"),[])
        a[3]["observed_at"]=a[3]["occurred_at"]="2026-11-04T01:00:00Z"
        self.assertFalse(evaluate_recipe(a,r,asof="2026-11-05T00:00:00Z"))

    def test_explicit_unswept_must_certify_window_and_reject_sweep(self):
        r=self.recipes["H090_UNSWEPT_OB_FVG"]
        a=[
          ev("pd","FIB_POSITION","D","2026-11-01T00:00:00Z",attrs={"position":"below_05","range_anchored_asof":"a"}),
          ev("p4","FIB_POSITION","H4","2026-11-01T00:00:00Z",attrs={"position":"below_05","range_anchored_asof":"a"}),
          ev("target","BLOCK_TARGET","D","2026-11-01T00:00:00Z",attrs={"price":125}),
          ev("no","LIQ_NOT_TAKEN","H4","2026-11-01T01:00:00Z",attrs={"window_start":"2026-10-31T00:00:00Z","window_end":"2026-11-01T00:00:00Z"}),
          ev("ob","OB_TOUCH","H1","2026-11-01T02:00:00Z"),
          ev("fvg","FVG_TOUCH","M15","2026-11-01T03:00:00Z",attrs={"price":100}),
        ]
        x=evaluate_recipe(a,r,asof="2026-11-01T04:00:00Z")
        self.assertEqual(x[0]["target_family"],"BLOCK_TARGET")
        self.assertEqual(len(x),1)
        self.assertFalse(evaluate_recipe(a[:3]+a[4:],r,asof="2026-11-01T04:00:00Z"))
        a.append(ev("sweep","LIQ_SWEEP","H4","2026-10-31T12:00:00Z"))
        self.assertFalse(evaluate_recipe(a,r,asof="2026-11-01T04:00:00Z"))

    def test_pit_fundamental_context_no_lookahead(self):
        r=self.recipes["H090_EQUITY_PIT_FUNDAMENTAL_OB"]
        a=[ev("tp","BLOCK_TARGET","D","2026-11-01T00:00:00Z",attrs={"price":120},symbol="SPX"),
           ev("structure","STRUCTURE_BREAK","D","2026-11-01T01:00:00Z",symbol="SPX"),
           ev("entry","OB_TOUCH","H4","2026-11-01T02:00:00Z",attrs={"price":100},symbol="SPX"),
           ev("future","FUNDAMENTAL_AVAILABLE","D","2026-11-02T00:00:00Z",
              attrs={"field":"quality_rank_available","value":"high"},symbol="SPX")]
        self.assertFalse(evaluate_recipe(a,r,asof="2026-11-01T03:00:00Z"))
        a[3]["occurred_at"]=a[3]["observed_at"]="2026-11-01T00:30:00Z"
        self.assertEqual(len(evaluate_recipe(a,r,asof="2026-11-01T03:00:00Z")),1)

    def test_macro_and_fundamental_ablation_filters(self):
        r=self.recipes["H090_CRYPTO_TECH_FUND_MACRO"]
        a=[ev("tp","LIQ_TARGET","H4","2026-11-01T00:00:00Z",attrs={"price":120}),
           ev("fund","FUNDAMENTAL_AVAILABLE","D","2026-11-01T00:01:00Z",
              attrs={"field":"onchain_quality_regime","value":"supportive"}),
           ev("mac","MACRO_AVAILABLE","D","2026-11-01T00:01:00Z",
              attrs={"field":"usd_liquidity_regime","value":"easing"}),
           ev("s","LIQ_SWEEP","H4","2026-11-01T01:00:00Z"),
           ev("m","MSS_CONFIRM","H1","2026-11-01T02:00:00Z"),
           ev("f","FVG_TOUCH","M15","2026-11-01T03:00:00Z",attrs={"price":100})]
        self.assertEqual(len(evaluate_recipe(a,r,asof="2026-11-01T04:00:00Z")),1)
        self.assertFalse(evaluate_recipe(a[:2]+a[3:],r,asof="2026-11-01T04:00:00Z"))
        self.assertFalse(evaluate_recipe(a[:1]+a[2:],r,asof="2026-11-01T04:00:00Z"))

    def test_unknown_target_and_wrong_direction_rejected(self):
        r=self.recipes["H090_FVG_IFVG_CONFIRM"]
        a=[ev("break","STRUCTURE_BREAK","H4","2026-11-01T01:00:00Z",side="short"),
           ev("entry","IFVG_CONFIRM","H1","2026-11-01T02:00:00Z",
              side="short",attrs={"price":100}),
           ev("wrong","FVG_TARGET","D","2026-11-01T00:00:00Z",
              side="short",attrs={"price":120})]
        self.assertFalse(evaluate_recipe(a,r,asof="2026-11-01T03:00:00Z"))
        a[2]["attrs"]["price"]=80
        self.assertEqual(len(evaluate_recipe(a,r,asof="2026-11-01T03:00:00Z")),1)

    def test_duplicate_events_future_timestamps_and_catalog_forgery_fail(self):
        r=self.recipes["H090_FVG_IFVG_CONFIRM"]
        a=ev("x","FVG_TOUCH","H1","2026-11-01T01:00:00Z")
        with self.assertRaises(ValueError):
            evaluate_recipe([a,a],r,asof="2026-11-02T00:00:00Z")
        b=copy.deepcopy(a)
        b["occurred_at"]="2026-11-03T00:00:00Z"
        with self.assertRaises(ValueError):Event.parse(b)
        c=load_catalog()
        c["research_requirements"][0]["state"]="FORWARD_VERIFIED"
        with self.assertRaises(ValueError):audit(c)
        c=load_catalog()
        c["capabilities"][0]["source"]="../../etc/passwd"
        with self.assertRaises(ValueError):audit(c)

    def test_multi_strategy_opposing_signals_abstain(self):
        base={"kind":"RESEARCH_SIGNAL_NOT_ORDER_NOT_BACKTEST","symbol":"BTC",
              "entry_at_utc":"2026-11-01T03:00:00Z","event_ids":["s","m","o"]}
        long={**base,"recipe_id":"long","side":"long"}
        short={**base,"recipe_id":"short","side":"short"}
        result=route([long,short])
        self.assertEqual(result["accepted_research_intents"],[])
        self.assertEqual(len(result["rejected_research_intents"]),2)
        self.assertTrue(all(x["reason"]=="OPPOSING_SIGNALS_ABSTAIN"
                            for x in result["rejected_research_intents"]))
        self.assertEqual(result["executed_orders"],0)

    def test_multi_strategy_risk_cap_and_duplicate_protection(self):
        base={"kind":"RESEARCH_SIGNAL_NOT_ORDER_NOT_BACKTEST","symbol":"BTC",
              "side":"long","entry_at_utc":"2026-11-01T03:00:00Z","event_ids":["a"]}
        a={**base,"recipe_id":"r1"}
        b={**base,"recipe_id":"r2"}
        c={**base,"recipe_id":"r3"}
        result=route([a,b,c],max_total_risk=0.01,
                     max_symbol_risk=0.01,per_signal_risk=0.005)
        self.assertEqual(len(result["accepted_research_intents"]),2)
        self.assertEqual(len(result["rejected_research_intents"]),1)
        self.assertAlmostEqual(result["total_risk_intent_fraction"],0.01)
        with self.assertRaises(ValueError):route([a,a])
        with self.assertRaises(ValueError):route([a],per_signal_risk=0.02,
                                                  max_symbol_risk=0.01)
        with self.assertRaises(ValueError):route([{**a,"kind":"LIVE_ORDER"}])

    def test_recipe_rejects_missing_condition_or_unknown_side(self):
        x=copy.deepcopy(self.recipes["H090_EQUITY_PIT_FUNDAMENTAL_OB"])
        del x["fundamental"]
        with self.assertRaises(ValueError):validate_recipe(x)
        x=copy.deepcopy(self.recipes["H090_LIQ_MSS_OB_TARGET"])
        x["side"]="both"
        with self.assertRaises(ValueError):validate_recipe(x)


if __name__=="__main__":
    unittest.main()
