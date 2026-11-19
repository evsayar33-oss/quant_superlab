"""Offline contracts for H121; mock source data are never research findings."""
import csv
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from research import bridge_guard as b
from research.h121 import engine as h

NOW = datetime(2026, 11, 19, 20, tzinfo=timezone.utc)
HASH = "f" * 40


def fixture():
    state = {
        "updated_at": "2026-11-19T16:15:00+00:00",
        "last_bar": "2026-11-19 12:00:00",
        "approved": True, "why": "H054-MOM2 local PAPER_ACCEPT (simulation only)",
        "equity": 978.0, "targets": {"BTC/USDT": 0, "ETH/USDT": 0},
    }
    paper = {
        "fees_paid": 4, "funding_paid": -1,
        "spot": {"BTC/USDT": .01, "ETH/USDT": .1},
        "perp": {"BTC/USDT": {"qty": .01}, "ETH/USDT": {"qty": .1}},
    }
    eq = ("time,bar,mode,equity\n"
          "2026-11-18T16:00:00+00:00,2026-11-18 12:00:00,PAPER,1000\n"
          "2026-11-19T16:15:00+00:00,2026-11-19 12:00:00,PAPER,978\n")
    trades = "time,bar,mode,leg,symbol,side,usdt,ok,error\n"
    last = int(datetime(2026,11,19,12,tzinfo=timezone.utc).timestamp()*1000)
    tick = {"candle_ms": last, "observed_ms": last + 120000,
            "nav": 10000, "trades": 0,
            "quotes": {"BTC/USDT": {"ask": 65000, "bid": 64999}},
            "weights": {"BTC/USDT": 0, "ETH/USDT": 0,
                        "SOL/USDT": 0, "BNB/USDT": 0}}
    band = {
        "schema": "h054.regime_band30.bitget.paper.v1",
        "start_ms": last - 24*3600000, "end_ms": last + 90*86400000,
        "last_candle_ms": last, "finalized": False, "cash": 10000,
        "ticks": [tick], "continuity_gaps": [],
        "outages": [], "qty": {}, 
    }
    return {
        ("mom2", "state/state.json"): json.dumps(state),
        ("mom2", "state/paper.json"): json.dumps(paper),
        ("mom2", "logs/equity.csv"): eq,
        ("mom2", "logs/trades.csv"): trades,
        ("band30", "state.json"): json.dumps(band),
    }


def fake_get(bodies):
    seen = []
    def get(url):
        seen.append(url)
        if "/git/ref/heads/" in url:
            return json.dumps({"object": {"sha": HASH}})
        if "/compare/" in url:
            return json.dumps({"status": "ahead", "behind_by": 0})
        for (key,path), data in bodies.items():
            if url.endswith("/" + path) and (
                (key == "mom2" and "/"+HASH+"/" in url) or key=="band30"):
                return data
        raise AssertionError("unexpected URL " + url)
    return get, seen


class H121Contracts(unittest.TestCase):
    def test_books_never_combine_and_initial_boot_quiet(self):
        values = fixture()
        get, seen = fake_get(values)
        with tempfile.TemporaryDirectory() as d:
            a = h.run(d, get, NOW)
            second = h.run(d, get, NOW)
            self.assertEqual(a["events_new"], 0)
            self.assertEqual(second["events_new"], 0)
            self.assertEqual(second["alerts_pending"], 0)
            self.assertEqual(a["mom2"]["nav"], 978)
            self.assertEqual(a["band30"]["paper_nav"], 10000)
            self.assertEqual(a["book_isolation"],
                "MOM2_MAIN_AND_BAND30_DISTINCT_NO_COMBINED_NAV")
            self.assertTrue(a["mom2"]["full_history_not_mom2_forward_pnl"])
            self.assertFalse(a["live_trading_enabled"])
            self.assertEqual(a["official_lab_accept"], "NOT_RUN")
            self.assertTrue(all(h.SOURCE in u for u in seen))
            self.assertTrue(all("early_accumulation" not in u for u in seen))

    def test_new_gap_is_notice_not_fake_trade_or_profit(self):
        old_m = h.parse_mom2(fixture())
        band = json.loads(fixture()[("band30", "state.json")])
        old_b = h.parse_band30({("band30","state.json"): json.dumps(band)})
        old = {"mom2": old_m, "band30": old_b,
               "mom2_delay_bars": 0, "band30_delay_bars": 0}
        band["continuity_gaps"].append({"count": 1})
        new_b = h.parse_band30({("band30","state.json"): json.dumps(band)})
        events, _, _ = h.evaluate(old_m, new_b, old, NOW)
        self.assertTrue(any(e["kind"] == "NEW_UNOBSERVED_CANDLE" for e in events))
        self.assertFalse(any("profit" in e["kind"].lower() for e in events))
        self.assertTrue(all(e["live_order"] is False for e in events))
        self.assertEqual(new_b["trade_count"], 0)

    def test_no_source_rewrite_and_missing_log_fail_closed(self):
        base = fixture()
        mom = h.parse_mom2(base)
        band = h.parse_band30(base)
        old = {"mom2": mom, "band30": band}
        data = json.loads(base[("band30", "state.json")])
        data["ticks"] = []
        data["last_candle_ms"] = None
        newer = h.parse_band30({("band30", "state.json"): json.dumps(data)})
        with self.assertRaisesRegex(ValueError, "HISTORY_DISAPPEARED"):
            h.evaluate(mom, newer, old, NOW)
        before = {"mom2": "a"*40}
        get, _ = fake_get(base)
        badget = lambda url: json.dumps({"status": "diverged", "behind_by": 1}) if "/compare/" in url else get(url)
        with self.assertRaisesRegex(ValueError, "SOURCE_HISTORY_REWRITTEN"):
            h.collect({"sources": before}, badget)

    def test_does_not_treat_hedge_funding_as_verified_spot_alpha(self):
        data = fixture()
        parsed = h.parse_mom2(data)
        self.assertEqual(parsed["funding_paid_raw_accounting"], -1)
        self.assertEqual(parsed["fees_paid_raw_accounting"], 4)
        self.assertEqual(parsed["reported_total_change_pct"], -2.2)

    def test_bid_ask_cost_telemetry_does_not_claim_fill_or_depth(self):
        input_data = fixture()
        report = h.parse_band30(input_data)
        q = report["execution_quality"]
        self.assertEqual(q["observed_top_of_book_quote_count"], 1)
        self.assertGreater(q["observed_median_spread_bps"], 0)
        self.assertEqual(q["observed_spread_p95_bps"], q["observed_median_spread_bps"])
        self.assertIsNone(q["observed_max_quote_age_ms"])
        self.assertEqual(q["quotes_without_displayed_depth"], 1)
        self.assertFalse(q["broker_executed_fills_verified"])
        self.assertFalse(q["order_size_market_impact_calibrated"])
        mom = h.parse_mom2(input_data)
        self.assertFalse(mom["contemporaneous_bid_ask_per_fill_available"])
        self.assertFalse(mom["actual_orderbook_impact_or_queue_position_verified"])

    def test_quote_telemetry_rejects_future_or_crossed_book(self):
        data = fixture()
        raw = json.loads(data[("band30","state.json")])
        quote = raw["ticks"][0]["quotes"]["BTC/USDT"]
        quote["received_ms"] = 1_000
        quote["ts"] = 50_000
        data[("band30","state.json")] = json.dumps(raw)
        with self.assertRaisesRegex(ValueError, "UNRELIABLE_FUTURE"):
            h.parse_band30(data)
        quote["received_ms"] = quote["ts"] + 100
        quote["bid"] = quote["ask"] + 1
        data[("band30","state.json")] = json.dumps(raw)
        with self.assertRaisesRegex(ValueError,"CROSSED_ORDERBOOK"):
            h.parse_band30(data)

    def test_source_security_and_hash_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "events.jsonl"
            b.append(p, h.SCHEMA, [{"id":"x","lane":"H121","kind":"GAP","message":"test"}])
            self.assertEqual(len(b.journal(p, h.SCHEMA)),1)
            value = p.read_text().replace('"message":"test"', '"message":"gain"')
            p.write_text(value)
            with self.assertRaisesRegex(ValueError, "TAMPERED"):
                b.journal(p, h.SCHEMA)


if __name__ == "__main__":
    unittest.main()
