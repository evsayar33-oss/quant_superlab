"""H117 no-lookahead, cost, and exposure invariants."""
import unittest
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from research.h117.research import MODELS, build, spaced_rebalance, wide_band, mix
from research.h116 import research as h116


def synthetic(n=1850):
    idx = pd.date_range("2020-01-01", periods=n, freq="4h")
    x = np.arange(n)
    return pd.DataFrame({
        sym: 100 + x * (0.03 + k * 0.01) + 2 * np.sin(x / (19 + k))
        for k, sym in enumerate(h116.SYMBOLS)}, index=idx)


class Tests(unittest.TestCase):
    def test_all_and_no_leverage(self):
        w = build(synthetic())
        self.assertEqual(tuple(w), MODELS)
        for name, v in w.items():
            self.assertTrue(v.ge(0).all().all(), name)
            self.assertTrue(v.sum(axis=1).le(1 + 1e-10).all(), name)

    def test_no_future_information(self):
        c = synthetic()
        orig = build(c)
        changed = c.copy()
        changed.iloc[-1, 0] *= 1.37
        new = build(changed)
        for name in MODELS:
            pd.testing.assert_frame_equal(orig[name].iloc[:-1], new[name].iloc[:-1])

    def test_forced_cash_exit_and_weekly_holding(self):
        idx = pd.date_range("2020-01-01", periods=5, freq="4h")
        x = pd.DataFrame({"BTCUSDT": [.5,.7,.6,0,.5]}, index=idx)
        z = spaced_rebalance(x, 10)
        self.assertEqual(list(z.iloc[:,0]), [.5,.5,.5,0,0])

    def test_wide_band_reduces_changes_and_preserves_cash(self):
        x = pd.DataFrame({"BTCUSDT": [0,.4,.55,.59,0.]})
        y = wide_band(x, .2)
        self.assertEqual(list(y.iloc[:,0]), [0,.4,.4,.4,0.])

    def test_blend_math(self):
        x = pd.DataFrame({"BTCUSDT": [.4,.2]})
        y = pd.DataFrame({"BTCUSDT": [0,.4]})
        result = mix(x,y,.25)
        self.assertAlmostEqual(float(result.iloc[0,0]),.1)
        self.assertAlmostEqual(float(result.iloc[1,0]),.35)


if __name__ == "__main__":
    unittest.main()
