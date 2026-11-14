import json
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[0]/"h093"))
sys.path.insert(0,str(HERE.parents[0]/"h094"))
from market import parse_okx,parse_bitget,fetch_okx,compare_venues,HOUR_MS
from baseline import compress,features,trade,research
from sequence import chronology_research
from fusion import asof_context,same_cohort_ablation
from gates import classify


def make_bars(n=400,start=1794000000000):
    start=(start//HOUR_MS)*HOUR_MS
    result=[]
    for i in range(n):
        p=100+i*.04
        if i%25==0:p+=7
        if i%25==1:p-=6
        result.append({"ts":start+i*HOUR_MS,"open":p,"high":p+1,
                       "low":p-1,"close":p+.1})
    return result


class ResearchTests(unittest.TestCase):
    def test_okx_parsing_closed_bars_only(self):
        ok={"code":"0","data":[
            ["1794000000000","100","110","90","105","1","1","1","1"],
            ["1794003600000","106","108","102","105","1","1","1","0"]]}
        # use hour aligned timestamp in test fixture
        ok["data"][0][0]=str((1794000000000//HOUR_MS)*HOUR_MS)
        ok["data"][1][0]=str((1794003600000//HOUR_MS)*HOUR_MS)
        rows=parse_okx(ok)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["close"],105)
        with self.assertRaises(ValueError):
            parse_okx({"code":"4","data":[]})

    def test_okx_real_api_pagination_mock_and_coverage(self):
        src=make_bars(205)
        def fake(url):
            from urllib.parse import parse_qs,urlparse
            q=parse_qs(urlparse(url).query)
            after=int(q["after"][0]) if "after" in q else 10**20
            rows=[b for b in reversed(src) if b["ts"]<after][:100]
            return {"code":"0","data":[[str(b["ts"]),str(b["open"]),
                str(b["high"]),str(b["low"]),str(b["close"]),"1","1","1","1"] for b in rows]}
        at=datetime.fromtimestamp((src[-1]["ts"]+2*HOUR_MS)/1000,timezone.utc)
        r=fetch_okx("BTC",pages=5,get=fake,now=at,pause=0)
        self.assertEqual(r["bar_count"],205)
        self.assertEqual(r["gaps"],[])
        self.assertEqual(r["independent_price_source_count"],1)

    def test_bitget_independent_close_check(self):
        src=make_bars(30)
        mock={"code":"00000","data":[[str(x["ts"]),str(x["open"]),str(x["high"]),
                                         str(x["low"]),str(x["close"]),"1","2"] for x in src]}
        cand=parse_bitget(mock)
        c=compare_venues(src,cand)
        self.assertEqual(c["matched_closed_bars"],30)
        self.assertTrue(c["independent_venue_overlap_verified"])
        self.assertFalse(c["same_underlying_independent_economic_market"])
        self.assertAlmostEqual(c["max_close_divergence_bps"],0)

    def test_four_hour_compression_only_complete_groups(self):
        source=make_bars(12,start=0)
        b=compress(source,4)
        self.assertEqual(len(b),3)
        cut=source[:11]
        self.assertEqual(len(compress(cut,4)),2)

    def test_no_lookahead_and_stop_first(self):
        source=make_bars(70)
        sig={"signal_index":30,"signal_time_ms":source[30]["ts"],
             "family":"LIQ_SWEEP","side":"long","atr":1,
             "stop_reference":source[31]["open"]-1,
             "previous_high":source[31]["open"]+3,"previous_low":90}
        entry=source[31]["open"]
        source[31]["low"]=entry-2
        source[31]["high"]=entry+5
        res=trade(source,sig,1,"fixed_1r",10)
        self.assertEqual(res["exit_cause"],"STOP")
        self.assertLess(res["net_R"],0)
        sig["signal_index"]=len(source)-1
        self.assertIsNone(trade(source,sig,1,"fixed_2r",10))

    def test_exploratory_result_has_no_winner(self):
        r=research(make_bars(540),"BTC")
        self.assertEqual(r["trial_count"],36)
        self.assertIsNone(r["selected_winner"])
        self.assertFalse(r["historical_oos_is_new_unseen_data"])
        self.assertFalse(r["fill_verified"])
        self.assertTrue(all(x["hold_unvalidated"] for x in r["trials"]))

    def test_real_bar_proxy_sequence_is_not_confirmed_mss(self):
        r=chronology_research(make_bars(540),"BTC")
        self.assertEqual(r["schema"],"H092.chronology_proxy.v1")
        self.assertEqual(r["trial_count"],18)
        self.assertEqual(r["coverage"][0]["status"],"NOT_TESTABLE_SHORT_HISTORY")
        self.assertFalse(r["forward_alpha_verified"])
        self.assertTrue(all(x["event_sequences_proxy_only"] for x in r["rows"]))

    def test_pit_future_release_and_stale_macro_not_used(self):
        entry="2026-11-12T12:00:00Z"
        base={"field":"usd_regime","value":"risk_off","symbol":"BTC",
              "available_at":"2026-11-13T00:00:00Z","source_id":"official"}
        filt=[{"field":"usd_regime","equals":"risk_off","max_age_hours":24}]
        self.assertEqual(asof_context(entry,[base],symbol="BTC",required=filt)["status"],
                         "NOT_TESTABLE_NO_POINT_IN_TIME_FACTOR")
        base["available_at"]="2026-11-12T00:00:00Z"
        self.assertEqual(asof_context(entry,[base],symbol="BTC",required=filt)["status"],"ELIGIBLE")
        self.assertEqual(asof_context(entry,[],symbol="BTC",required=filt)["status"],
                         "NOT_TESTABLE_NO_POINT_IN_TIME_FACTOR")

    def test_ablation_identical_cohort_and_gate_blocks(self):
        trades=[{"trade_id":"a","source_hash":"123","arms":{"technical":0.1}},
                {"trade_id":"b","source_hash":"234","arms":{"technical":-1}}]
        self.assertEqual(same_cohort_ablation(trades,variant="full")["status"],
                         "NOT_TESTABLE_INCOMPLETE_IDENTICAL_COHORT")
        r=research(make_bars(540),"BTC")
        a=classify(r)
        self.assertEqual(a["verdict"],"NOT_VERIFIED")
        self.assertFalse(a["live_trading_authorized"])
        self.assertIn("PROSPECTIVE_SAMPLE_INSUFFICIENT",a["reasons"])
        self.assertIn("TRUE_FINANCING_SLIPPAGE_COST_UNVERIFIED",a["reasons"])


if __name__=="__main__":unittest.main()
