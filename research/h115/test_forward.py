"""Offline regression tests; they must not call Yahoo or place orders."""
import json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from research.h115.forward import (
 ARMS,STOCKS,SCENARIOS,digest,seed,verify,apply,note_outage,report,run,
 side_cost,compute_targets,normalize_history)
NOW=datetime(2026,11,16,16,30,tzinfo=timezone.utc)
def sample(session="2026-11-16",price=100.):
 d=pd.DataFrame({"Open":[99.],"High":[101.],"Low":[98.],"Close":[100.],"Volume":[1000.]},
  index=pd.DatetimeIndex(["2026-11-13"]))
 return {"session":session,"prices":{"SPY":price,"SLV":100.,"QQQ":100.,"GLD":100.},
  "history":{"SPY":d},"quote_times":{"SPY":NOW.isoformat()},
  "errors":{},"received_at":NOW.isoformat()}
class Tests(unittest.TestCase):
 def test_seed_and_frozen_180(self):
  s=seed(NOW)
  self.assertEqual((pd.Timestamp(s["end_date"])-pd.Timestamp(s["started_date"])).days,180)
  self.assertFalse(s["alpha_accepted"]);self.assertTrue(verify(s))
  self.assertGreaterEqual(len(ARMS),12)
 def test_tamper_chain(self):
  s=seed(NOW)
  with patch("research.h115.forward.compute_targets",return_value={"SPY_trend_efficiency":{"SPY":1.}}):
   apply(s,sample())
  self.assertTrue(verify(s))
  s["records"][0]["quotes"]["SPY"]=1.
  with self.assertRaisesRegex(ValueError,"TAMPERED"):verify(s)
 def test_session_replay_rejected(self):
  s=seed(NOW)
  with patch("research.h115.forward.compute_targets",return_value={"SPY_trend_efficiency":{"SPY":1.}}):
   apply(s,sample())
   with self.assertRaisesRegex(ValueError,"SESSION_REPLAY"):apply(s,sample())
 def test_no_fill_before_first_observation(self):
  s=seed(NOW)
  with patch("research.h115.forward.compute_targets",return_value={"SPY_trend_efficiency":{"SPY":1.}}):
   apply(s,sample())
  self.assertAlmostEqual(s["nav"]["SPY_trend_efficiency"]["base"],1-.00105)
  self.assertEqual(len(s["records"]),1)
 def test_next_observation_produces_causal_return(self):
  s=seed(NOW)
  with patch("research.h115.forward.compute_targets",return_value={"SPY_trend_efficiency":{"SPY":1.}}):
   apply(s,sample())
   apply(s,sample(session="2026-11-17",price=101.))
  self.assertAlmostEqual(s["nav"]["SPY_trend_efficiency"]["base"],(1-.00105)*1.01)
  self.assertEqual(s["bench_latest"],1.01)
 def test_cost_stress_monotone(self):
  for a in ("SPY","SI=F"):
   b=side_cost(a,100,"base");z=side_cost(a,100,"stress")
   self.assertLess(b,z)
 def test_outage_has_no_phantom_trade(self):
  s=seed(NOW);note_outage(s,NOW,RuntimeError("feed offline"))
  self.assertEqual(s["records"],[]);self.assertEqual(len(s["outages"]),1)
  self.assertEqual(report(s,NOW)["observed_sessions"],0)
 def test_start_only_once(self):
  with tempfile.TemporaryDirectory() as p:
   f=Path(p)/"state.json";o=Path(p)/"out"
   run("start",f,o,NOW)
   with self.assertRaisesRegex(ValueError,"ALREADY_STARTED"):run("start",f,o,NOW)
 def test_scheduled_without_start_does_not_retroactively_seed(self):
  with tempfile.TemporaryDirectory() as p:
   self.assertIsNone(run("tick",Path(p)/"missing.json",Path(p)/"out",NOW))
 def test_source_omission_closed(self):
  s=seed(NOW)
  with self.assertRaisesRegex(ValueError,"MISSING_EQUITY_MARKS"):compute_targets(sample())
  self.assertEqual(len(s["records"]),0)
 def test_freeze_detects_config_change(self):
  s=seed(NOW);s["freeze"]["h114_sha"]="not current"
  with self.assertRaisesRegex(ValueError,"FREEZE_MISMATCH"):verify(s)
 def test_future_diagnostic_does_not_approve(self):
  s=seed(NOW)
  self.assertFalse(report(s,NOW)["alpha_accepted"])
if __name__=="__main__":unittest.main()
