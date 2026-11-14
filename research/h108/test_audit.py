import unittest
from audit import metrics,block_bootstrap,WEEK_MS
class Tests(unittest.TestCase):
    def trade(self,g,drag,week):
        return {"gross_r":g,"net_r":{"20":g-drag},"entry_ms":week*WEEK_MS,"exit_ms":week*WEEK_MS+3600000}
    def test_aggregate_break_even(self):
        x=metrics([self.trade(1,.1,0),self.trade(-.5,.2,1)])
        self.assertAlmostEqual(x["aggregate_break_even_bps"],20*.5/.3)
        self.assertAlmostEqual(x["net20_mean_r"],.1)
    def test_weekly_determinism(self):
        ts=[self.trade(1,.2,0),self.trade(-1,.2,2),self.trade(.5,.2,3)]
        self.assertEqual(block_bootstrap(ts,100),block_bootstrap(ts,100))
        self.assertEqual(block_bootstrap(ts,100)["weekly_blocks"],4)
    def test_all_negative(self):
        ts=[self.trade(-1,.1,i) for i in range(4)]
        self.assertEqual(block_bootstrap(ts,100)["p_mean_le_zero"],1)
    def test_invalid_cost(self):
        with self.assertRaisesRegex(ValueError,"INVALID_COST"):metrics([self.trade(1,0,0)])
if __name__=="__main__":unittest.main()
