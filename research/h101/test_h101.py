import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit import instrument_audit,aggregate_report

def simulated(*args):
    return {"entry_ms":10,"exit_ms":20,"net_r":.5,"cause":"TARGET"}

class H101Tests(unittest.TestCase):
    def test_cost_conversion_and_no_false_oos(self):
        bars=[{"ts":i,"open":100., "high":105.,"low":95.,"close":100.} for i in range(35)]
        setups=[{"signal":{"kind":"BOS"},"side":"long","aligned":True,
                 "entry_index":10,"risk":10.}]
        with patch("audit.signals",return_value=setups),patch("audit.simulate",side_effect=simulated):
            r=instrument_audit(bars,bars,"BTC","15m",8)
        c=r["configurations"]["BOS:long:all"]
        self.assertAlmostEqual(c["cost_assumptions_bps"]["20"]["mean_net_r"],.5)
        self.assertAlmostEqual(c["cost_assumptions_bps"]["40"]["mean_net_r"],.48)
        self.assertAlmostEqual(c["cost_assumptions_bps"]["80"]["mean_net_r"],.44)
        t=r["ledger"][0]
        self.assertAlmostEqual(t["net_r_80bps"],.44)
        self.assertTrue(t["historical_tail"])
        self.assertFalse(r["alpha_accepted"])

    def test_missing_venues_fail_closed(self):
        r=aggregate_report({},{"BTC_15m_gate":{"category":"HTTP_451"}})
        self.assertEqual(r["configs_total"],96)
        self.assertEqual(r["configs_three_venue_n30"],0)
        self.assertEqual(r["configs_three_venue_positive_at_80bps"],0)
        self.assertFalse(r["historical_tail_is_fresh_oos"])
        self.assertFalse(r["alpha_accepted"])

    def test_below_30_per_venue_never_passes(self):
        cfg={}
        for fam in ("LIQ_SWEEP","MSS","BOS","OB_TOUCH","FVG_TOUCH","IFVG_CONFIRMED"):
            for side in ("long","short"):
                for cohort in ("all","htf_aligned"):
                    cfg[f"{fam}:{side}:{cohort}"]={
                      "cost_assumptions_bps":{
                        "20":{"n":29,"historical_tail_n":15,"mean_net_r":1},
                        "80":{"n":29,"historical_tail_n":15,"mean_net_r":.5,
                               "historical_tail_mean_net_r":.5}}}
        inputs={f"BTC_15m_{v}":{"configurations":cfg} for v in ("gate","bitget","mexc")}
        r=aggregate_report(inputs,{})
        self.assertEqual(r["configs_three_venue_n30"],0)

if __name__=="__main__":unittest.main()
