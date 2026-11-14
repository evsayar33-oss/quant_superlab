import unittest
from engine import HOUR,simulate,evaluate
class EngineTests(unittest.TestCase):
    def bars(self,n=160):
        return [{"ts":i*HOUR,"open":100+i*.01,"high":101+i*.01,
                 "low":99+i*.01,"close":100+i*.01} for i in range(n)]
    def test_fixed_scope_and_no_alpha(self):
        rows=evaluate(self.bars(),HOUR)
        self.assertEqual(len(rows),4)
        self.assertTrue(all(x["n"]==0 for x in rows))
    def test_stop_first(self):
        bars=self.bars()
        bars[74].update({"open":100,"low":95,"high":110})
        t=simulate(bars,74,"long",1,HOUR)
        self.assertEqual(t["exit_cause"],"STOP")
        self.assertAlmostEqual(t["gross_r"],-1)
        self.assertAlmostEqual(t["net_r"]["20"],-1.1)
    def test_gap_rejected(self):
        bars=self.bars()
        bars[74]["ts"]+=HOUR
        self.assertIsNone(simulate(bars,74,"long",1,HOUR))
if __name__=="__main__":unittest.main()
