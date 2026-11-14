"""Synthetic contract tests only; real-provider smoke is a separate CI job."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from detectors import detect,check_bars,HOUR

def bars(values):
    return [{"ts":i*HOUR,"open":o,"high":h,"low":l,"close":c}
            for i,(o,h,l,c) in enumerate(values)]

class H095Tests(unittest.TestCase):
    def test_pivot_waits_for_right_confirmation(self):
        b=bars([(10,11,9,10),(10,12,9,11),(11,15,10,14),
                (14,14.5,11,12),(12,13,10,11),(11,12,9,10)])
        before=detect(b[:4],"BTC",left=2,right=2)
        self.assertFalse(any(x["kind"]=="SWING_HIGH" for x in before["events"]))
        after=detect(b,"BTC",left=2,right=2)
        found=[x for x in after["events"] if x["kind"]=="SWING_HIGH"]
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["bar_index"],4)
        self.assertEqual(found[0]["attrs"]["pivot_bar"],2)
        self.assertEqual(found[0]["observed_at_ms"],5*HOUR)

    def test_fvg_requires_third_closed_candle(self):
        b=bars([(100,102,99,101),(101,103,100,102),
                (107,109,106,108),(108,110,107,109)])
        x=detect(b[:2],"ETH",left=1,right=1)
        self.assertFalse(any(e["kind"]=="FVG_FORMED" for e in x["events"]))
        y=detect(b[:3],"ETH",left=1,right=1)
        f=[e for e in y["events"] if e["kind"]=="FVG_FORMED"]
        self.assertEqual(len(f),1)
        self.assertEqual(f[0]["attrs"]["low"],102)
        self.assertEqual(f[0]["attrs"]["high"],106)

    def test_ifvg_only_after_close_through_zone(self):
        b=bars([(100,102,99,101),(101,103,100,102),
                (107,109,106,108),(107,108,103,104),
                (104,105,101,102),(102,103,99,100)])
        a=detect(b[:4],"BTC",left=1,right=1)
        self.assertFalse(any(e["kind"]=="IFVG_CONFIRMED" for e in a["events"]))
        c=detect(b,"BTC",left=1,right=1)
        inv=[e for e in c["events"] if e["kind"]=="IFVG_CONFIRMED"]
        self.assertTrue(any(e["side"]=="short" and e["bar_index"]==5 for e in inv))

    def test_ob_only_after_break_and_future_touch(self):
        b=bars([(10,11,9,10),(10,12,9,11),(11,15,10,14),
                (14,14.5,11,12),(12,13,10,11),(11,12,9,10),
                (10,14,9.5,13),(13,16,12.5,15.5),
                (15.5,16,10,12)])
        x=detect(b,"BTC",left=2,right=2)
        formed=[e for e in x["events"] if e["kind"]=="OB_FORMED"]
        self.assertTrue(formed)
        self.assertTrue(all(e["attrs"]["formed_bar"]==e["bar_index"] for e in formed))
        touched=[e for e in x["events"] if e["kind"]=="OB_TOUCH"]
        self.assertTrue(all(e["bar_index"]>e["attrs"]["formed_bar"] for e in touched))

    def test_gap_does_not_allow_pivot_across_missing_data(self):
        b=bars([(10,11,9,10),(10,15,9,14),(14,14,10,12),
                (12,13,10,11),(11,12,9,10)])
        b[3]["ts"]+=HOUR;b[4]["ts"]+=HOUR
        x=detect(b,"ETH",left=1,right=1)
        self.assertTrue(all(e["attrs"].get("pivot_bar",0)<3 for e in x["events"]
                            if e["kind"]=="SWING_HIGH"))
        self.assertFalse(x["historical_alpha_verified"])

    def test_invalid_bars_and_timeframe_rejected(self):
        b=bars([(10,11,9,10),(10,12,9,11)])
        bad=[dict(x) for x in b];bad[1]["ts"]=0
        with self.assertRaises(ValueError):detect(bad,"BTC")
        bad=[dict(x) for x in b];bad[0]["low"]=12
        with self.assertRaises(ValueError):detect(bad,"BTC")
        with self.assertRaises(ValueError):detect(b,"BTC","15m")
        with self.assertRaises(ValueError):detect(b,"SOL")

    def test_deterministic_and_no_live_execution(self):
        b=bars([(100+i*.1,102+i*.1,99+i*.1,101+i*.1) for i in range(50)])
        a=detect(b,"BTC");c=detect(b,"BTC")
        self.assertEqual(a,c)
        self.assertFalse(a["real_fill_verified"])
        self.assertFalse(a["first_seen_prospective"])
        self.assertEqual(len({x["event_id"] for x in a["events"]}),len(a["events"]))

if __name__=="__main__":unittest.main()
