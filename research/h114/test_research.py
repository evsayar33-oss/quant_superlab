import sys, unittest
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).parent))
from research import normalized,sigs,net_daily,ETF_SCENARIOS,FUTURE_SCENARIOS,FAMILIES,PORTFOLIOS,STOCKS,scope,bh,positive_splits
def bars(n=520):
 x=np.arange(n,dtype=float)
 o=100+0.05*x+np.sin(x/3)
 c=o*(1+0.001*np.cos(x))
 b=pd.DataFrame({"Open":o,"Close":c,"High":np.maximum(o,c)+1,"Low":np.minimum(o,c)-1,
   "Volume":np.ones(n)*1e6},index=pd.bdate_range("2020-01-01",periods=n))
 b.attrs["ticker"]="SPY";return b
class Tests(unittest.TestCase):
 def test_registered_family(self):
  self.assertEqual(len(sigs(bars())),len(FAMILIES))
  self.assertEqual(len(STOCKS),30)
  self.assertEqual(len(PORTFOLIOS),5)
 def test_no_future_leak(self):
  b=bars(600);s=sigs(b)
  b2=b.copy();b2.iloc[-1,b2.columns.get_loc("Close")]*=1.1
  s2=sigs(b2)
  for k in FAMILIES:
   pd.testing.assert_series_equal(s[k].iloc[:-1],s2[k].iloc[:-1])
 def test_cost_increase_reduces_result(self):
  b=bars();s=pd.Series(np.where(np.arange(len(b))%2==0,1.,0.),index=b.index)
  a=net_daily(b,s,ETF_SCENARIOS["base"],"etf")
  z=net_daily(b,s,ETF_SCENARIOS["stress"],"etf")
  self.assertLess(z.net.sum(),a.net.sum())
 def test_next_open_and_no_same_day_close_fill(self):
  b=bars();s=pd.Series(0.,index=b.index)
  s.iloc[200]=1.
  x=net_daily(b,s,ETF_SCENARIOS["base"],"etf")
  self.assertEqual(x.loc[b.index[201],"pos"],1.)
  self.assertEqual(x.loc[b.index[200],"pos"],0.)
  self.assertGreater(x.loc[b.index[201],"turn"],0)
 def test_bh_all_family(self):
  q=bh([.01,.03,.2,1.])
  self.assertAlmostEqual(q[0],.04);self.assertEqual(q[-1],1.)
 def test_splits_are_nonoverlapping(self):
  b=bars(1500);s=pd.Series(1.,index=b.index)
  z=net_daily(b,s,ETF_SCENARIOS["base"],"etf")
  p=scope(z);self.assertEqual(sum(len(v) for v in p.values()),len(z))
 def test_split_arithmetic_positive_is_not_enough(self):
  s={x:{"return":.02,"avg_daily":.0001,"active_days":20}
    for x in ("discovery","validation","reused_holdout")}
  self.assertTrue(positive_splits(s))
  s["reused_holdout"]["return"]=-.001
  self.assertFalse(positive_splits(s))
 def test_future_one_contract_fee_scale(self):
  b=bars();b.attrs["ticker"]="NQ=F"
  s=pd.Series(1.,index=b.index)
  x=net_daily(b,s,FUTURE_SCENARIOS["base"],"future")
  self.assertGreater(float(x.unit_cost.iloc[0]),0)
 def test_invalid_duplicate_bars(self):
  b=bars();b.index=pd.DatetimeIndex(list(b.index[:-1])+[b.index[-2]])
  with self.assertRaisesRegex(ValueError,"DUPLICATE_BARS"):normalized(b)
if __name__=="__main__":unittest.main()
