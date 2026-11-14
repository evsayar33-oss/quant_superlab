import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from engine import HOUR,FOUR,SCHEMA,seed,tick,summary,close_trade
from research.h111.run import run
class Tests(unittest.TestCase):
 def test_seed_30_days(self):
  s=seed(100*HOUR)
  self.assertEqual(s["ends_ms"]-s["started_ms"],720*HOUR)
  self.assertFalse(s["alpha_accepted"])
 def test_missing_study_no_auto_start(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertIsNone(run("tick",Path(d)/"none.json",Path(d)/"out",now_ms=100*HOUR))
 def test_no_replay(self):
  s=seed(100*HOUR);s["last_tick_ms"]=100*HOUR
  with self.assertRaisesRegex(ValueError,"NON_MONOTONIC"):tick(s,100*HOUR,{})
 def test_two_venues_required(self):
  with self.assertRaisesRegex(ValueError,"BOTH_VENUES_REQUIRED"):tick(seed(0),HOUR,{"okx":{}})
 def test_cost_and_close(self):
  s=seed(0);p={"key":"x","entry":100,"risk":2,"direction":1}
  s["positions"]["x"]=p
  close_trade(s,"x",p,102,HOUR,"TIME_QUOTE_PROXY")
  self.assertAlmostEqual(s["trades"][0]["net_r"]["16"],.92)
  self.assertNotIn("x",s["positions"])
 def test_outage_persists_no_phantom(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"state.json";out=Path(d)/"out"
   with patch("research.h111.run.snapshot",side_effect=ValueError("NETWORK_DOWN")):
    state=run("start",path,out,now_ms=100*HOUR)
   self.assertEqual(len(state["outages"]),1)
   self.assertEqual(len(state["ticks"]),0)
   self.assertEqual(len(state["trades"]),0)
   self.assertTrue(path.exists())
 def test_summary_no_promotion(self):
  r=summary(seed(0))
  self.assertFalse(r["alpha_accepted"])
  self.assertFalse(r["execution_verified"])
if __name__=="__main__":unittest.main()
