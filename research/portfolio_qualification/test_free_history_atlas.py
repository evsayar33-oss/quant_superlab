"""Data source diligence and instrument-clock guard tests; no network calls."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.source_discovery.audit import load_catalog, assess, markdown
from research.source_discovery.telemetry import (
    SCHEMA as TRACE_SCHEMA, source_detail, trace_native_sources)
from research.portfolio_qualification.mesh import append_snapshot, read_chain, SCHEMA


class FreeHistoricalSourceDiligence(unittest.TestCase):
    def test_all_three_markets_and_no_silent_candidate_promotion(self):
        c=load_catalog()
        self.assertGreaterEqual(len(c["sources"]),35)
        self.assertEqual(set(x["market"] for x in c["sources"]),
                         {"BIST","US","CRYPTO"})
        self.assertTrue(all(x["historical_pit_ready"] is False and
                            x["alpha_validated"] is False and
                            x["automatic_download_enabled"] is False
                            for x in c["sources"]))

    def test_unlicensed_exchange_history_never_marked_free_api(self):
        d={x["id"]:x for x in load_catalog()["sources"]}
        self.assertIn("LICENSED",d["TR_BIST_DATASTORE"]["access_model"])
        self.assertIn("IP_ALLOWLIST",d["TR_MKK_KAP_API"]["access_model"])
        self.assertIn("historical_membership",
                      d["TR_BIST_PIT_RECONSTRUCTED"]["signals"])
        self.assertFalse(d["CR_TARDIS_SAMPLES"]["historical_pit_ready"])

    def test_repo_specific_diligence_and_report(self):
        z=assess()
        self.assertIn("quant_superlab",z["repository_sources"])
        self.assertIn("us_f1_bot",z["repository_sources"])
        self.assertEqual(z["verified_source_downloads"],0)
        self.assertEqual(z["automatically_promoted_alpha"],0)
        report=markdown()
        self.assertIn("TR_BIST_PIT_RECONSTRUCTED",report)
        self.assertIn("CR_OKX_HISTORY",report)

    def test_catalog_rejects_any_automatic_trade_authorization(self):
        c=load_catalog()
        c["sources"][0]["automatic_download_enabled"]=True
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"sources.json"
            f.write_text(json.dumps(c),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"CANNOT_PROMOTE"):
                load_catalog(f)

    def test_source_json_trace_does_not_copy_private_positions(self):
        raw=json.dumps({
            "updated_at":"2026-11-23T10:00:00Z",
            "entries":[{"status":"PAPER","ts":"2026-11-23T09:40:00Z",
                        "secret_position":"top secret", "price":1.123},
                       {"status":"WAIT","ts":"2026-11-23T09:50:00Z",
                        "secret_position":"broker account", "price":1.456}],
        }).encode("utf-8")
        meta={"sha256":hashlib.sha256(raw).hexdigest(),
              "commit":"abc123","reference":"state",
              "path":"paper/entries.json","bytes":len(raw)}
        result=source_detail("positions",raw,meta)
        self.assertEqual(result["records_total"],2)
        self.assertEqual(result["content_kind"],"JSON")
        self.assertEqual(result["event_timestamp_min_utc"],
                         "2026-11-23T09:40:00+00:00")
        self.assertEqual(result["categorical_status_counts"]["PAPER"],1)
        rendered=json.dumps(result)
        self.assertNotIn("top secret",rendered)
        self.assertNotIn("broker account",rendered)
        self.assertNotIn("1.456",rendered)

    def test_csv_date_only_not_promoted_to_live_event_timestamp(self):
        raw=b"date,symbol,close,status\n2021-02-01,ABC,50,OK\n2021-02-02,ABC,55,OK\n"
        meta={"path":"research.csv","reference":"main","commit":"0"*40,
              "sha256":hashlib.sha256(raw).hexdigest()}
        x=source_detail("historical_market_data",raw,meta)
        self.assertEqual(x["records_total"],2)
        self.assertIsNone(x["event_timestamp_min_utc"])
        self.assertEqual(x["date_only_period_min"],"2021-02-01")
        self.assertFalse(x["independent_pit_verified"])

    def test_utc_ms_and_microsecond_ranges(self):
        raw=b"ts,observed_at_ms,price\n2026-11-22T04:00:00Z,1795320000000,10\n"
        meta={"path":"tape.csv","sha256":"f"*64,
              "reference":"branch","commit":"a"*40}
        x=source_detail("real_tape",raw,meta)
        self.assertEqual(x["records_total"],1)
        self.assertTrue(x["event_timestamp_min_utc"].startswith("2026-"))
        self.assertFalse(x["historical_dates_are_not_prospective_signal_times"]
                         if "historical_dates_are_not_prospective_signal_times" in x else False)

    def test_invalid_report_never_validated(self):
        meta={"path":"foo.json","sha256":"b"*64,
              "reference":"branch","commit":"a"*40}
        x=source_detail("foo",b"{bad",meta)
        self.assertEqual(x["content_kind"],"STRUCTURE_INVALID")
        self.assertFalse(x["independent_pit_verified"])

    def test_metadata_trace_sources_cannot_be_unpinned(self):
        raw=b'{"status":"OK"}'
        with self.assertRaisesRegex(ValueError,"UNPINNED_SOURCE_INPUT"):
            trace_native_sources({"a":raw},{},{},"2026-11-23T12:00:00Z")

    def test_original_evidence_sha_chain_survives_metadata_upgrade(self):
        old={"schema":SCHEMA,"repo":"evsayar33-oss/eaverse",
             "captured_utc":"2026-11-23T09:00:00Z",
             "source_data_digest":"abc",
             "native_observation_utc":"2026-11-22T08:00:00Z",
             "data_status":"OBSERVED_UNPROMOTED"}
        current=copy.deepcopy(old)
        current["captured_utc"]="2026-11-23T09:30:00Z"
        current["source_telemetry"]={
            "schema":TRACE_SCHEMA,"collector_first_observed_utc":
            "2026-11-23T09:30:00+00:00"}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"observation.jsonl"
            self.assertEqual(append_snapshot(path,old)["recorded_snapshots"],1)
            upgrade=append_snapshot(path,current)
            self.assertEqual(upgrade["recorded_snapshots"],2)
            self.assertTrue(upgrade["same_observation_revision"])
            self.assertIn("NOT_NEW_MARKET",upgrade["status"])
            self.assertEqual(len(read_chain(path)),2)
            current["captured_utc"]="2026-11-23T10:00:00Z"
            self.assertIn("UNCHANGED",append_snapshot(path,current)["status"])
            self.assertEqual(len(read_chain(path)),2)


if __name__=="__main__":
    unittest.main()
