"""Cross-repo source pins, independent CSCV reproduction and no-promotion."""
import copy
import json
import random
import unittest
from datetime import datetime, timedelta, timezone

from research.portfolio_qualification import eaverse_bridge as bridge


def signed(obj,prev="GENESIS"):
    x={**obj,"prev_sha256":prev}
    x["sha256"]=bridge.digest(x)
    return json.dumps(x,sort_keys=True)+"\n"


def fixture():
    gen=random.Random(55)
    dates=[(datetime(2023,1,8,tzinfo=timezone.utc)+timedelta(weeks=i)).isoformat()
           for i in range(96)]
    keys=[f"V7_FIXED_{i}" for i in range(32)]
    matrix=[[round(gen.gauss(.0001*(j%6),.002+(.0001*j)),12)
             for j in range(32)] for i in range(96)]
    study_rows=[{"id":key,"spec":{"direction":1}} for key in keys]
    study_rows.extend([{"id":f"RISK_{i}","spec":{"direction":-1}}
                       for i in range(32)])
    study_digest=bridge.digest(study_rows)
    source_sha="a"*64
    policy="b"*64
    panel={"dates_utc_week_end":dates,"variant_ids":keys,"net_return_paths":matrix}
    panel["sha256"]=bridge.digest(panel)
    chosen=max(range(32),key=lambda col:bridge._sharpe(
        [row[col] for row in matrix[:64]]))
    pbo=bridge.reproduce_pbo(matrix)
    stats={
        "schema":"eaverse.v7.aligned_empirical_trials.v1",
        "symbol":"BTCUSDT","source_venue":"BINANCE_SPOT",
        "source_digest":source_sha,"source_policy_sha256":policy,
        "source_hypotheses_sha256":study_digest,
        "registered_total_trial_family_per_asset":64,
        "registered_long_trial_count":32,
        "cross_asset_long_trial_family":256,
        "weekly_panel":panel,"weekly_discovery_rows":64,
        "weekly_validation_rows":32,
        "selected_discovery_variant_id":keys[chosen],
        "candidate_events_validation":[15]*32,
        "paper_eligible":False,"live_allowed":False,
        "untouched_holdout_read":False,
        "independent_prospective_validated":False,
        "pbo":pbo, "dsr":{"dsr":0.41},
    }
    study={
        "asset":"BTCUSDT","source_digest":source_sha,
        "policy_sha256":policy,"study_digest":study_digest,
        "full_hypothesis_studies":study_rows,
        "paper_eligible":False,"forward_validated":False,
    }
    return stats,study


class BridgeTests(unittest.TestCase):
    def test_no_auto_promotion_despite_replicated_real_cscv(self):
        stats,study=fixture()
        report=bridge.audit_one("BTCUSDT",signed(stats),signed(study),"c"*40)
        self.assertEqual(report["status"],
                         "INDEPENDENTLY_REPRODUCED_HISTORICAL_CSCV_ONLY_NO_ACCEPT")
        self.assertEqual(report["reproduced_pbo"]["partitions"],70)
        self.assertTrue(report["central_passport_evaluated"])
        self.assertFalse(report["central_lab_backtest_invoked"])
        self.assertFalse(report["central_lab_accept"])
        self.assertEqual(report["central_gate_status"],"NOT_ELIGIBLE_FOR_PAPER_REVIEW")
        self.assertIn("independent_oos_verified",report["central_gate_blockers"])

    def test_source_ledger_tamper_detected(self):
        stats,study=fixture()
        original=json.loads(signed(stats))
        original["pbo"]["pbo"]=0.99
        with self.assertRaisesRegex(ValueError,"CHAIN_TAMPER"):
            bridge.audit_one("BTCUSDT",json.dumps(original),signed(study),"c"*40)

    def test_return_vector_digest_and_recomputed_pbo(self):
        stats,study=fixture()
        stats["pbo"]["pbo"]=1.0-stats["pbo"]["pbo"]
        with self.assertRaisesRegex(ValueError,"PBO_REPLICATION_MISMATCH"):
            bridge.audit_one("BTCUSDT",signed(stats),signed(study),"c"*40)
        stats,study=fixture()
        stats["weekly_panel"]["net_return_paths"][0][0]+=0.1
        with self.assertRaisesRegex(ValueError,"MATRIX_SHA_MISMATCH"):
            bridge.audit_one("BTCUSDT",signed(stats),signed(study),"c"*40)

    def test_tampered_foreign_variant_or_authorization_rejected(self):
        stats,study=fixture()
        stats["weekly_panel"]["variant_ids"][0]="UNKNOWN"
        stats["weekly_panel"]["sha256"]=bridge.digest({
            k:v for k,v in stats["weekly_panel"].items() if k!="sha256"})
        with self.assertRaisesRegex(ValueError,"UNREGISTERED_HYPOTHESIS_IN_PANEL"):
            bridge.audit_one("BTCUSDT",signed(stats),signed(study),"c"*40)
        stats,study=fixture()
        stats["paper_eligible"]=True
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_HISTORICAL_TO_FORWARD"):
            bridge.audit_one("BTCUSDT",signed(stats),signed(study),"c"*40)

    def test_missing_evidence_never_counted_as_alpha(self):
        def missing(url,token):
            raise OSError("missing requested source")
        summary=bridge.run(fetch=missing)
        self.assertEqual(summary["assets_checked"],8)
        self.assertEqual(summary["reproduced"],0)
        self.assertFalse(summary["source_data_promoted_to_trading"])
        self.assertEqual(summary["central_lab_accepted_by_bridge"],0)


if __name__=="__main__":
    unittest.main()
