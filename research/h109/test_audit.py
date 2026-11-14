import unittest
from audit import null_test
class Tests(unittest.TestCase):
    def t(self,g,c=.2):return {"gross_r":g,"net_r":{"20":g-c}}
    def test_determinism(self):
        ts=[self.t(1),self.t(-.5),self.t(.3)]
        self.assertEqual(null_test(ts,100),null_test(ts,100))
    def test_empty(self):
        self.assertEqual(null_test([])["n"],0)
    def test_cost_preserved(self):
        r=null_test([self.t(1,.2)],100)
        self.assertAlmostEqual(r["observed_mean_net20_r"],.8)
        self.assertLess(r["null_mean_net20_r"],.8)
    def test_invalid_cost(self):
        with self.assertRaisesRegex(ValueError,"INVALID_TRADE"):null_test([self.t(1,-.1)])
if __name__=="__main__":unittest.main()
