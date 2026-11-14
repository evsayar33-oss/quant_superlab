import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence import parse,executable_proxy,collect,append_chain
from watch_capture import capture


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.ts=1794654000000
        self.b={"symbol":"BTCUSDT","bidPrice":"100","askPrice":"100.1",
                "bidQty":"20","askQty":"15","time":self.ts}
        self.y={"retCode":0,"time":self.ts,"result":{"list":[{
            "symbol":"BTCUSDT","bid1Price":"100.01","ask1Price":"100.11",
            "bid1Size":"20","ask1Size":"15"}]}}

    def test_provider_quotes_and_provenance(self):
        a=parse("binance","BTCUSDT",self.b,self.ts+1000)
        b=parse("bybit","BTCUSDT",self.y,self.ts+1000)
        self.assertTrue(a["event_timestamp_verified"])
        self.assertAlmostEqual(a["spread_bps"],9.995002498750625)
        self.assertNotEqual(a["mid"],b["mid"])

    def test_reject_stale_future_crossed(self):
        with self.assertRaises(ValueError):
            parse("binance","BTCUSDT",self.b,self.ts+121000)
        with self.assertRaises(ValueError):
            parse("binance","BTCUSDT",self.b,self.ts-11000)
        with self.assertRaises(ValueError):
            parse("binance","ETHUSDT",self.b,self.ts+1000)
        self.b["bidPrice"]="102"
        with self.assertRaises(ValueError):
            parse("binance","BTCUSDT",self.b,self.ts+1000)

    def test_cost_never_claims_fill_and_requires_size(self):
        q=parse("binance","BTCUSDT",self.b,self.ts+1000)
        r=executable_proxy(q,1000,6)
        self.assertFalse(r["actual_execution_cost_verified"])
        self.assertTrue(r["top_of_book_covers_notional"])
        self.assertAlmostEqual(r["indicative_roundtrip_spread_plus_fees_bps"],q["spread_bps"]+12)
        large=executable_proxy(q,100000,6)
        self.assertFalse(large["top_of_book_covers_notional"])
        self.assertIsNone(large["indicative_roundtrip_spread_plus_fees_bps"])
        self.assertIsNone(executable_proxy(q,1000)["indicative_roundtrip_spread_plus_fees_bps"])

    def test_missing_venue_no_synthetic_fallback(self):
        def fake(provider,symbol):
            if provider=="bybit":raise TimeoutError("blocked")
            b=dict(self.b);b["symbol"]=symbol
            return parse("binance",symbol,b,self.ts+1000)
        rec=collect(fetcher=fake,clock=lambda:datetime(2026,11,14,tzinfo=timezone.utc))
        self.assertFalse(rec["complete"])
        self.assertEqual(len(rec["sources"]),2)
        self.assertTrue(all(not pairs for pairs in rec["comparisons"].values()))
        self.assertEqual(len(rec["errors"]),6)

    def test_okx_bitget_are_same_contract_class_but_multiplier_unknown(self):
        raw_okx={"code":"0","data":[{"instId":"BTC-USDT-SWAP",
              "bidPx":"100","askPx":"101","bidSz":"5","askSz":"3","ts":str(self.ts)}]}
        raw_bitget={"code":"00000","data":[{"symbol":"BTCUSDT",
              "bidPr":"100.1","askPr":"100.2","bidSz":"4","askSz":"6","ts":str(self.ts)}]}
        for provider,raw in [("okx",raw_okx),("bitget",raw_bitget)]:
            q=parse(provider,"BTCUSDT",raw,self.ts+1000)
            self.assertEqual(q["instrument_class"],"USDT_LINEAR_PERPETUAL")
            self.assertFalse(q["size_in_base_units_verified"])
            cost=executable_proxy(q,1000,4)
            self.assertIsNone(cost["top_of_book_covers_notional"])
            self.assertIsNone(cost["indicative_roundtrip_spread_plus_fees_bps"])
        with self.assertRaises(ValueError):
            parse("okx","ETHUSDT",raw_okx,self.ts+1000)

    def test_two_valid_independent_venues_suffice_while_errors_recorded(self):
        def fake(provider,symbol):
            if provider in ("binance","bybit"):raise TimeoutError("venue blocked")
            base=symbol.replace("USDT","")
            if provider=="okx":
                raw={"code":"0","data":[{"instId":f"{base}-USDT-SWAP",
                     "bidPx":"100","askPx":"100.1","bidSz":"2","askSz":"5",
                     "ts":str(self.ts)}]}
            else:
                raw={"code":"00000","data":[{"symbol":symbol,
                     "bidPr":"100","askPr":"100.2","bidSz":"2","askSz":"5",
                     "ts":str(self.ts)}]}
            return parse(provider,symbol,raw,self.ts+1000)
        rec=collect(fetcher=fake,clock=lambda:datetime(2026,11,14,tzinfo=timezone.utc))
        self.assertTrue(rec["complete"])
        self.assertEqual(len(rec["sources"]),4)
        self.assertEqual(len(rec["errors"]),4)
        self.assertEqual(len(rec["comparisons"]["BTCUSDT"]),1)
        self.assertEqual(rec["comparisons"]["BTCUSDT"][0]["venues"],["bitget","okx"])

    def test_hash_chain_detects_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"evidence.jsonl"
            first={"collected_at_utc":"2026-11-14T12:00:00.000Z","v":1}
            second={"collected_at_utc":"2026-11-15T12:00:00.000Z","v":2}
            append_chain(first,f)
            append_chain(second,f)
            with self.assertRaises(ValueError):
                append_chain(second,f)
            s=f.read_text().replace('"v":1','"v":9')
            f.write_text(s)
            with self.assertRaisesRegex(ValueError,"CHAIN_BROKEN"):
                append_chain({"collected_at_utc":"2026-11-16T12:00:00.000Z"},f)

    def test_watch_capture_is_not_backfilled_pnl(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"state.json"
            f.write_text(json.dumps({"date":"2026-11-14","ideas":{
                "H063":{"held":{"BTC":0.5},"bar":"2026-11-13","leverage_pick":1}}}))
            rec=capture(datetime(2026,11,14,12,tzinfo=timezone.utc),f)
            self.assertTrue(rec["all_fresh"])
            self.assertNotIn("pnl",json.dumps(rec).lower().replace("not_forward_pnl",""))
            old=capture(datetime(2026,11,25,12,tzinfo=timezone.utc),f)
            self.assertFalse(old["all_fresh"])
            self.assertTrue(old["decisions"][0]["stale_gt_3_days"])


if __name__=="__main__":unittest.main()
