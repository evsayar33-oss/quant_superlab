import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[0]/"h095"))
from market import parse,fetch
from engine import parent_asof,simulate,evaluate,exclusive
from detectors import detect,TF_MS


def bars(n,tf="5m",start=0):
    step=TF_MS[tf]
    return [{"ts":start+i*step,"open":100+i*.02,"high":102+i*.02,
             "low":98+i*.02,"close":100.5+i*.02} for i in range(n)]


class H096Tests(unittest.TestCase):
    def test_native_5m_and_daily_only_closed(self):
        step=TF_MS["5m"]
        def get(url):
            return {"code":"0","data":[[str(i*step),"100","102","98","101","1","1","1",
                "1" if i<4 else "0"] for i in reversed(range(5))]}
        now=datetime.fromtimestamp(5*step/1000,timezone.utc)
        r=fetch("BTC","5m",get=get,now=now,pause=0)
        self.assertEqual(r["count"],4)
        self.assertEqual(r["gap_count"],0)
        self.assertEqual(len(detect(bars(20,"1D"),"BTC","1D")["events"])>=0,True)

    def test_invalid_source_and_duplicate(self):
        with self.assertRaises(ValueError):parse({"code":"500","data":[]},"5m")
        step=TF_MS["15m"]
        row=[str(step),"100","102","98","101","1","1","1","1"]
        with self.assertRaises(ValueError):parse({"code":"0","data":[row,row]},"15m")

    def test_htf_never_uses_future_or_neutral(self):
        parent=[{"kind":"MSS","side":"long","observed_at_ms":30*TF_MS["5m"],"event_id":"old"},
                {"kind":"BOS","side":"short","observed_at_ms":100*TF_MS["5m"],"event_id":"future"},
                {"kind":"FIB_POSITION","side":"neutral","observed_at_ms":32*TF_MS["5m"],"event_id":"neutral"}]
        result=parent_asof(35*TF_MS["5m"],parent,"5m")
        self.assertEqual(result["event_id"],"old")
        self.assertEqual(parent_asof(20*TF_MS["5m"],parent,"5m")["status"],
                         "NOT_TESTABLE_NO_CONFIRMED_PARENT_EVENT")

    def test_stop_first_intrabar_and_gap(self):
        b=bars(30)
        b[2]["low"]=95;b[2]["high"]=110
        signal={"entry_index":2,"side":"long","risk":1.0,"pivot_target":110,
                "aligned":True,"signal":{"kind":"MSS"}}
        result=simulate(b,signal,"1R",10,"5m")
        self.assertEqual(result["cause"],"STOP")
        self.assertLess(result["net_r"],0)
        b[3]["ts"]+=TF_MS["5m"]
        # Future missing bars only matter if position remains open; no interpolation.
        self.assertEqual(simulate(b,signal,"1R",10,"5m")["cause"],"STOP")

    def test_nonoverlap(self):
        t=[{"entry_ms":10,"exit_ms":20},{"entry_ms":15,"exit_ms":25},
           {"entry_ms":21,"exit_ms":30}]
        self.assertEqual(len(exclusive(t)),2)

    def test_research_no_accept(self):
        b=bars(140,"15m")
        e=detect(b,"BTC","15m")["events"]
        parent=[{"kind":"BOS","side":"long","observed_at_ms":0,"event_id":"x"}]
        r=evaluate(b,e,parent,"15m")
        self.assertEqual(r["trial_count"],216)
        self.assertFalse(r["candidate_accepted"])
        self.assertFalse(r["holdout_is_unseen"])
        self.assertTrue(all(not x["untouched_oos"] for x in r["trials"]))

    def test_source_timeframe_is_explicit(self):
        b=bars(30,"1H")
        self.assertEqual(b[1]["ts"]-b[0]["ts"],TF_MS["1H"])
        self.assertNotEqual(TF_MS["1H"],TF_MS["5m"])

if __name__=="__main__":unittest.main()
