import unittest
from audit import analyze
class Tests(unittest.TestCase):
    def trade(self,g=1,drag=.1):
        return {"gross_r":g,"net_r":{"20":g-drag,"40":g-2*drag,"80":g-4*drag},
            "entry_ms":0,"exit_ms":3600000,"cause":"TIME"}
    def test_cost_decomposition(self):
        s=analyze([self.trade()])
        self.assertEqual(s["n"],1)
        self.assertAlmostEqual(s["mean_cost_drag20_r"],.1)
        self.assertAlmostEqual(s["mean_trade_break_even_bps"],200)
        self.assertEqual(s["mean_holding_hours"],2)
    def test_cost_mismatch(self):
        t=self.trade();t["net_r"]["80"]=1
        with self.assertRaisesRegex(ValueError,"COST_LINEARITY"):analyze([t])
    def test_invalid_duration(self):
        t=self.trade();t["exit_ms"]=-1
        with self.assertRaisesRegex(ValueError,"NEGATIVE_HOLD"):analyze([t])
    def test_empty(self):
        self.assertEqual(analyze([])["n"],0)
if __name__=="__main__":unittest.main()
