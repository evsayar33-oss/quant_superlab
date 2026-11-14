import json, tempfile, unittest, hashlib
from pathlib import Path
from audit import analyze

class DiagnosticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"trade_ledgers").mkdir()
        self.trade={"config":"BOS:long:all","entry_price":100.0,"risk_price":10.0,
          "entry_ms":0,"exit_ms":60000,"historical_tail":False,
          "stop_first_exit_cause":"TARGET","net_r_20bps":0.98,
          "net_r_40bps":0.96,"net_r_80bps":0.92}
        self.write()
    def write(self):
        raw=json.dumps([self.trade]).encode()
        (self.root/"trade_ledgers"/"BTC_1H_okx.json").write_bytes(raw)
        summary={"alpha_accepted":False,"real_execution_cost_verified":False,
          "venue_results":{"BTC_1H_okx":{"ledger_sha256":hashlib.sha256(raw).hexdigest()}}}
        (self.root/"summary.json").write_text(json.dumps(summary))
    def test_economics_and_gate(self):
        r=analyze(self.root,self.root/"result.json")
        x=r["cells"][0]
        self.assertAlmostEqual(x["gross_mean_r"],1)
        self.assertAlmostEqual(x["break_even_roundtrip_bps"],1000)
        self.assertEqual(r["eligible_n30_cells"],0)
        self.assertFalse(r["alpha_accepted"])
    def test_tamper_detected(self):
        self.trade["net_r_80bps"]=2
        self.write()
        with self.assertRaisesRegex(ValueError,"COST_INCONSISTENCY"):
            analyze(self.root,self.root/"result.json")
    def test_hash_mismatch(self):
        self.trade["net_r_20bps"]=0.9
        with open(self.root/"trade_ledgers"/"BTC_1H_okx.json","w") as f: json.dump([self.trade],f)
        with self.assertRaisesRegex(ValueError,"HASH_MISMATCH"):
            analyze(self.root,self.root/"result.json")

if __name__=="__main__":unittest.main()
