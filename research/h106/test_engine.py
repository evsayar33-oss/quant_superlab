import unittest
from engine import HOUR,align,evaluate,simulate
class Tests(unittest.TestCase):
    def bars(self,scale=1):
        return [{"ts":i*HOUR,"open":scale*(100+i*.01),"high":scale*(101+i*.01),
          "low":scale*(99+i*.01),"close":scale*(100+i*.01)} for i in range(180)]
    def test_alignment(self):
        a=self.bars();b=self.bars();self.assertEqual(len(align(a,b[1:])),179)
    def test_no_signals_flat_relative(self):
        r=evaluate(self.bars(),self.bars(2));self.assertEqual(r["n"],0)
    def test_stop_first(self):
        a=self.bars();b=self.bars(2);a[60].update({"open":100,"low":90,"high":120})
        pairs=align(a,b);t=simulate(pairs,60,"BTC","long")
        self.assertEqual(t["cause"],"STOP")
        self.assertAlmostEqual(t["gross_r"],-1)
    def test_gaps_fail_closed(self):
        a=self.bars();b=self.bars();a[70]["ts"]+=2*HOUR
        self.assertEqual(len(align(a,b)),179)
if __name__=="__main__":unittest.main()
