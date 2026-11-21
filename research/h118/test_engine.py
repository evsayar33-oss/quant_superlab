"""H118 deterministic offline regression suite."""
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
from decision_diagnostics import explain
import sys
sys.path.insert(0, str(Path(__file__).parent))
from engine import BAR_MS, CAPITAL, MODELS, SYMBOLS, apply, run, seed, validate


def snapshot(t):
    q={s:{"bid":100.0,"ask":100.2,"quote_ms":t-2000} for s in SYMBOLS}
    weights={m:{s:0. for s in SYMBOLS} for m in MODELS}
    for m in MODELS:
        weights[m][SYMBOLS[0]]=0.5
    return {"last_candle_ms":t-BAR_MS,"quotes":q,"target_weights":weights,
            "candle_sha256":{s:"a"*64 for s in SYMBOLS},"venue":"okx"}


class Tests(unittest.TestCase):
    def test_downtrend_carries_explicit_cash_reasons(self):
        i=np.arange(1350)
        prices=np.exp(-0.00035*i+0.017*np.sin(i/19))
        close=pd.DataFrame({a:prices*100 for a in SYMBOLS},
                           index=pd.date_range("2025-01-01",periods=len(i),
                                               freq="4h",tz="UTC"))
        target={m:{a:0.0 for a in SYMBOLS} for m in MODELS}
        trace=explain(close,target)
        self.assertFalse(trace["btc_regime_on"])
        self.assertEqual(trace["models"]["regime_band30"]["reason"],"BTC_REGIME_OFF")
        self.assertEqual(trace["models"]["regime_7d_band20"]["reason"],"BTC_REGIME_OFF")
        self.assertEqual(trace["models"]["mom2_baseline"]["reason"],"NO_ELIGIBLE_BTC_ETH")
        self.assertTrue(trace["diagnostic_only"])

    def test_trace_does_not_change_accounting_or_duplicate_fills(self):
        t=100*BAR_MS
        first=seed(t);second=seed(t)
        observed=snapshot(t)
        withtrace=snapshot(t)
        withtrace["signal_trace"]={"version":1,"models":{"mom2_baseline":{"reason":"ACTIVE_TARGET"}}}
        self.assertTrue(apply(first,t,observed))
        self.assertTrue(apply(second,t,withtrace))
        self.assertEqual(first["accounts"],second["accounts"])
        self.assertEqual(first["ticks"][0]["paper_fills"],second["ticks"][0]["paper_fills"])
        self.assertNotIn("signal_trace",first["ticks"][0])
        self.assertIn("signal_trace",second["ticks"][0])
        self.assertFalse(apply(second,t+1,withtrace))
        self.assertEqual(len(second["ticks"]),1)

    def test_study_clock_and_accounts(self):
        t=100*BAR_MS
        s=seed(t);validate(s)
        self.assertEqual(s["ends_ms"]-t,90*86400000)
        self.assertEqual(set(s["accounts"]),set(MODELS))

    def test_costs_no_realization_and_nonnegative_cash(self):
        t=100*BAR_MS
        s=seed(t);self.assertTrue(apply(s,t,snapshot(t)))
        for m in MODELS:
            self.assertTrue(0<s["accounts"][m]["nav"]<CAPITAL)
            self.assertGreaterEqual(s["accounts"][m]["cash"],0)
        self.assertFalse(apply(s,t+2000,snapshot(t)))
        self.assertEqual(len(s["ticks"]),1)

    def test_future_bar_rejected_atomically(self):
        t=100*BAR_MS;s=seed(t);snap=snapshot(t)
        snap["last_candle_ms"]=t
        with self.assertRaisesRegex(ValueError,"FUTURE_OR_UNCLOSED_BAR"):
            apply(s,t,snap)
        self.assertEqual(len(s["ticks"]),0)

    def test_leverage_fail_closed(self):
        t=100*BAR_MS;s=seed(t);snap=snapshot(t)
        snap["target_weights"][MODELS[2]][SYMBOLS[0]]=1.1
        with self.assertRaisesRegex(ValueError,"TARGET_LEVERAGE"):
            apply(s,t,snap)
        self.assertEqual(s["accounts"][MODELS[0]]["cash"],CAPITAL)

    def test_paper_exit_to_cash_and_end(self):
        t=100*BAR_MS;s=seed(t);apply(s,t,snapshot(t))
        q=snapshot(t+BAR_MS)
        for m in MODELS:q["target_weights"][m][SYMBOLS[0]]=0.
        apply(s,t+BAR_MS,q)
        for m in MODELS:self.assertAlmostEqual(s["accounts"][m]["qty"][SYMBOLS[0]],0.)
        end=s["ends_ms"]+BAR_MS
        apply(s,end,snapshot(end))
        self.assertTrue(s["finalized"])
        self.assertFalse(apply(s,end+BAR_MS,snapshot(end+BAR_MS)))

    def test_outage_record_recovery_and_no_restart(self):
        t=100*BAR_MS
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/"state.json";out=Path(folder)/"out"
            def outage(t):raise TimeoutError("offline injected")
            a=run("start",state,out,now_ms=t,snapshot_fn=outage)
            self.assertEqual(len(a["outages"]),1)
            self.assertTrue(state.exists())
            with self.assertRaisesRegex(ValueError,"ALREADY_STARTED"):
                run("start",state,out,now_ms=t+BAR_MS,snapshot_fn=outage)
            b=run("tick",state,out,now_ms=t+BAR_MS,snapshot_fn=snapshot)
            self.assertEqual(len(b["ticks"]),1)
            self.assertEqual(len(b["outages"]),1)
            self.assertEqual(json.loads((out/"summary.json").read_text())["status"],"ACTIVE")


if __name__=="__main__":
    unittest.main()
