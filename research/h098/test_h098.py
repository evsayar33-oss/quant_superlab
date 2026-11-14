import sys
import unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from venues import fetch,validate,TF
from evidence import compare,event_concordance,cost_sensitivity,evidence_gate,snapshot,funding_observed

class H098Tests(unittest.TestCase):
    def test_binance_real_format_and_closed(self):
        step=TF["15m"]
        def mock(url):
            return [[i*step,"100","102","98","101"] for i in range(60)]
        from datetime import datetime,timezone
        r=fetch("BTC","15m",get=mock,now=datetime.fromtimestamp(60*step/1000,timezone.utc))
        self.assertEqual(r["count"],60)
        self.assertEqual(r["gap_count"],0)

    def test_bybit_real_format(self):
        step=TF["1H"]
        def mock(url):
            return {"retCode":0,"result":{"list":[[i*step,"100","102","98","101"]
                                               for i in reversed(range(70))]}}
        from datetime import datetime,timezone
        r=fetch("ETH","1H",get=mock,now=datetime.fromtimestamp(70*step/1000,timezone.utc))
        self.assertEqual(r["count"],70)

    def test_duplicate_conflict_and_future(self):
        step=TF["5m"]
        rows=[{"ts":0,"open":100,"high":102,"low":98,"close":101},
              {"ts":0,"open":100,"high":103,"low":98,"close":101}]
        with self.assertRaises(ValueError):validate(rows,"5m",step*5)
        self.assertEqual(len(validate(rows[:1],"5m",step*5)),1)

    def test_exact_join_not_nearest(self):
        step=TF["15m"]
        def b(t):return {"ts":t,"open":100,"high":102,"low":98,"close":101}
        a=[b(i*step) for i in range(50)]
        shifted=[b(i*step+step//2) for i in range(50)]
        self.assertFalse(compare(a,shifted,step)["comparable"])
        self.assertEqual(compare(a,a,step)["overlap"],50)
        self.assertEqual(compare(a,a,step)["median_close_difference_bps"],0)

    def test_cost_debit_and_no_measured_claim(self):
        r=cost_sensitivity(100,101,"long",8,5,5,2,.001)
        self.assertAlmostEqual(r["assumed_net_return"],.007)
        self.assertFalse(r["measured_execution_costs"])
        with self.assertRaises(ValueError):cost_sensitivity(100,101,"long",-1,0,0,0)

    def test_funding_side_and_unverified_coverage(self):
        obs=[{"funding_time_ms":5,"realized_rate":.001}]
        trade={"entry_ms":1,"exit_ms":10,"side":"short"}
        r=funding_observed(trade,obs)
        self.assertEqual(r["estimated_unit_notional_debit"],-.001)
        self.assertFalse(r["exact_funding_verified"])

    def test_prospective_and_gate_always_fail_closed(self):
        e={"observed_at_ms":10,"event_id":"e","kind":"MSS","side":"long"}
        s=snapshot("BTC","15m",[e],"hash",10)
        self.assertEqual(len(s["events"]),1)
        self.assertFalse(s["persistent_first_seen_verified"])
        self.assertFalse(evidence_gate([{"comparable":True}],True,[s])["alpha_accepted"])
        self.assertEqual(event_concordance([e],[e])["jaccard"],1)

if __name__=="__main__":unittest.main()
