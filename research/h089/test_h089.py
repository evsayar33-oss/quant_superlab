import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from forward import compute_one,collect,first_seen,read_chain
from venues import okx_meta,bitget_meta,funding,collect as collect_venue
from costs import calculate

T0=datetime(2026,11,14,10,16,tzinfo=timezone.utc)
T1=datetime(2026,11,17,12,tzinfo=timezone.utc)
T2=datetime(2026,11,18,12,tzinfo=timezone.utc)


def mark(close,day,when):
    return {"close":close,"closed_bar_date":day,
            "collected_at_utc":when.isoformat().replace("+00:00","Z"),
            "source":"YAHOO_FINANCE_DAILY_CLOSE_NOT_EXECUTABLE"}


class H089Tests(unittest.TestCase):
    def test_first_later_close_is_basis_not_profit(self):
        init={"seen":T0,"positions":{"YM=F":1},"closed_bar":"2026-11-13"}
        one=compute_one("H065",init,None,{"YM=F":mark(100,"2026-11-16",T1)},T1)
        self.assertEqual(one["status"],"BASELINE")
        self.assertAlmostEqual(one["nav_scenarios"]["base_5bps"],999.5)
        two=compute_one("H065",init,one,{"YM=F":mark(110,"2026-11-17",T2)},T2)
        self.assertEqual(two["status"],"MARK_TO_MARKET")
        self.assertAlmostEqual(two["nav_scenarios"]["base_5bps"],1099.45)
        self.assertFalse(two["forward_pnl_verified"])

    def test_reject_future_or_prior_marks(self):
        init={"seen":T0,"positions":{"YM=F":1}}
        self.assertEqual(compute_one("H065",init,None,{"YM=F":mark(100,"2026-11-13",T1)},T1)["status"],"AWAITING_POST_FIRST_SEEN_CLOSE")
        self.assertEqual(compute_one("H065",init,None,{"YM=F":mark(100,"2026-11-16",T0-timedelta(seconds=1))},T1)["status"],"PRICE_NOT_PROSPECTIVELY_OBSERVED")
        with self.assertRaises(ValueError):
            compute_one("H065",init,None,{},T0)

    def test_missing_price_never_backfilled(self):
        init={"seen":T0,"positions":{"YM=F":1}}
        self.assertEqual(compute_one("H065",init,None,{},T1)["status"],"MISSING_PRICE")

    def test_invalid_weights_and_earliest_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"obs.csv"
            with f.open("w",newline="") as out:
                w=csv.DictWriter(out,fieldnames=["idea","first_observed_utc","positions","latest_closed_bar","record_type"])
                w.writeheader()
                for date,pos in [("2026-11-16T12:00:00+00:00",{"YM=F":0}),
                                 ("2026-11-14T10:16:19+00:00",{"YM=F":1})]:
                    w.writerow({"idea":"H065","first_observed_utc":date,"positions":json.dumps(pos),
                                "latest_closed_bar":"2026-11-13","record_type":"FIRST_SEEN_SNAPSHOT_NOT_FORWARD_PNL"})
            r=first_seen(f)
            self.assertEqual(r["H065"]["positions"],{"YM=F":1.})
            f.write_text(f.read_text().replace('"{""YM=F"": 1}"','"{""YM=F"": 5}"'))
            with self.assertRaises(ValueError):first_seen(f)

    def test_official_okx_metadata_unit_gate(self):
        def ok(url):
            return {"code":"0","data":[{"instId":"BTC-USDT-SWAP",
                     "ctType":"linear","ctValCcy":"BTC","ctVal":"0.01"}]}
        x=okx_meta("BTCUSDT",ok)
        self.assertEqual(x["base_units_per_contract"],0.01)
        self.assertTrue(x["multiplier_verified_from_public_metadata"])
        def bad(url):
            return {"code":"0","data":[{"instId":"BTC-USDT-SWAP",
                     "ctType":"inverse","ctValCcy":"USD","ctVal":"100"}]}
        with self.assertRaises(ValueError):okx_meta("BTCUSDT",bad)

    def test_bitget_metadata_unknown_size_not_fake_capacity(self):
        def fake(url):
            return {"code":"00000","data":[{"symbol":"ETHUSDT",
                       "sizeMultiplier":"0.01","volumePlace":"2"}]}
        x=bitget_meta("ETHUSDT",fake)
        self.assertFalse(x["multiplier_verified_from_public_metadata"])
        self.assertIsNone(x["base_units_per_contract"])

    def test_funding_snapshot_is_not_h056_backtest(self):
        def fake(url):
            if "okx" in url:
                return {"code":"0","data":[{"fundingRate":"0.0001","fundingTime":"1794650000000"}]}
            return {"code":"00000","data":[{"fundingRate":"0.0002","nextUpdate":"1794650000000"}]}
        for venue in ("okx","bitget"):
            r=funding(venue,"BTCUSDT",fake)
            self.assertFalse(r["funding_rate_is_observed_payment"])
            self.assertFalse(r["historical_H056_strategy_replayed"])

    def test_cost_capacity_converts_okx_contracts_but_not_bitget(self):
        q={"bid":100.,"ask":100.1,"bid_size":100.,"ask_size":20.,"spread_bps":10.}
        okx={"base_units_per_contract":0.01,"multiplier_verified_from_public_metadata":True}
        r=calculate(q,okx,10,5)
        self.assertTrue(r["top_level_capacity_sufficient"])
        self.assertAlmostEqual(r["ask_top_notional_usdt"],20.02)
        self.assertAlmostEqual(r["indicative_roundtrip_spread_plus_fees_bps"],20.)
        large=calculate(q,okx,100,5)
        self.assertFalse(large["top_level_capacity_sufficient"])
        self.assertIsNone(large["indicative_roundtrip_spread_plus_fees_bps"])
        unknown=calculate(q,{"multiplier_verified_from_public_metadata":False},10,5)
        self.assertIsNone(unknown["top_level_capacity_sufficient"])
        self.assertIsNone(unknown["indicative_roundtrip_spread_plus_fees_bps"])
        self.assertFalse(r["real_fill_cost_verified"])

    def test_chain_broken_never_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"chain.jsonl"
            f.write_text('{"entry_sha256":"wrong","previous_sha256":"none"}\n')
            with self.assertRaises(ValueError):read_chain(f)


if __name__=="__main__":unittest.main()
