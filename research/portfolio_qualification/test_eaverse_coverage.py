import json
import unittest
from research.portfolio_qualification import eaverse_coverage as c


def row():
    evidence = {"discovery": [.1, -.05], "validation": [.02, .03]}
    evidence["sha256"] = c.digest(evidence)
    return {"asset":"BTC", "version":"coverage-2", "id":"x", "spec":"{}",
            "policy":"{}", "snapshot":"a"*64,
            "discovered":json.dumps({"metrics":{"net":.045}, "return_evidence":evidence}),
            "validated":json.dumps({"metrics":{"net":.0506}})}


class CoverageGate(unittest.TestCase):
    def test_real_path_arithmetic_never_approves(self):
        r = c.audit_record(row())
        self.assertTrue(r["path_net_reproduced"])
        self.assertFalse(r["central_lab_accept"])
        self.assertTrue(r["gate"]["blockers"])

    def test_tamper(self):
        r = row()
        r["validated"] = '{"metrics":{"net":0.9}}'
        with self.assertRaisesRegex(ValueError, "RETURN_PATH_NET_MISMATCH"):
            c.audit_record(r)

    def test_no_path_no_reproduction(self):
        r = row()
        r["discovered"] = "{}"
        self.assertFalse(c.audit_record(r)["path_net_reproduced"])
