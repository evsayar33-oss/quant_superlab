import unittest
from reassess import PROFILES,mean_net,score,decide
class Tests(unittest.TestCase):
 def t(self):
  return {"gross_r":.5,"entry":100,"risk":2,"entry_ms":100,"exit_ms":110,"net_r":{"20":.4}}
 def test_cost(self):
  self.assertAlmostEqual(mean_net([self.t()],12),.44)
 def test_sensitivity(self):
  self.assertGreater(mean_net([self.t()],12),mean_net([self.t()],20))
 def test_maker_not_executable(self):
  self.assertFalse(PROFILES["maker_maker_optimistic"]["executable_proxy"])
  self.assertTrue(PROFILES["taker_base"]["executable_proxy"])
 def test_empty(self):
  self.assertIsNone(mean_net([],12))
 def test_corrupt_trade(self):
  t=self.t();t["net_r"]["20"]=.8
  with self.assertRaisesRegex(ValueError,"ORIGINAL_COST_MISMATCH"):mean_net([t],12)
 def test_no_promotion(self):
  self.assertEqual(decide({"sample_ok":False}),"INSUFFICIENT_SAMPLE")
  x={"sample_ok":True,"base_both_positive":True,"mid_both_positive":True,
   "tail_both_positive":True,"validation_both_positive":True,"stress_both_positive":True}
  self.assertEqual(decide(x),"RESEARCH_WATCHLIST_ONLY")
if __name__=="__main__":unittest.main()
