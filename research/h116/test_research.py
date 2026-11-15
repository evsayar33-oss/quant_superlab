"""H116 deterministic unit tests only; empirical evidence job uses real Binance bars."""
import unittest
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from research import NAMES, TEST_START, banded, make_weights, simulate, stats, validate_source


def synthetic(n=1850):
    idx = pd.date_range("2020-01-01", periods=n, freq="4h")
    x = np.arange(n)
    opens = pd.DataFrame({
        s: (100 + x * (0.02 + j * 0.005) + 2 * np.sin(x / (17 + j)))
        for j, s in enumerate(("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"))
    }, index=idx)
    closes = opens * (1 + 0.001 * np.sin(x / 7)[:, None])
    return opens, closes


class H116Tests(unittest.TestCase):
    def test_all_candidates_and_no_leverage(self):
        o, c = synthetic()
        w = make_weights(c)
        self.assertEqual(tuple(w), NAMES)
        for n, x in w.items():
            self.assertTrue(x.ge(0).all().all(), n)
            self.assertTrue(x.sum(axis=1).le(1 + 1e-9).all(), n)

    def test_causal_no_future_close_leak(self):
        _, c = synthetic()
        w = make_weights(c)
        changed = c.copy()
        changed.iloc[-1, 0] *= 1.35
        future = make_weights(changed)
        for n in NAMES:
            pd.testing.assert_frame_equal(w[n].iloc[:-1], future[n].iloc[:-1])

    def test_turnover_cost_is_monotonic(self):
        o, c = synthetic(2400)
        w = make_weights(c)["h054_mom2"]
        low = simulate(o, w, 15)
        high = simulate(o, w, 45)
        self.assertGreaterEqual(float(low["net"].sum()), float(high["net"].sum()))

    def test_next_open_not_current_close(self):
        idx = pd.date_range("2020-12-30", periods=25, freq="4h")
        syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
        o = pd.DataFrame(100., index=idx, columns=syms)
        o.loc[idx[-4], "BTCUSDT"] = 100.0
        o.loc[idx[-3], "BTCUSDT"] = 110.0
        o.loc[idx[-2], "BTCUSDT"] = 110.0
        o.loc[idx[-1], "BTCUSDT"] = 110.0
        w = pd.DataFrame(0., index=idx, columns=syms)
        w.iloc[-5, 0] = 1.0
        out = simulate(o, w, 0)
        t = idx[-4]
        # Position from close[-5] entered at open[-4], then profits through open[-3].
        self.assertEqual(float(out.loc[t, "exposure"]), 1.)
        self.assertAlmostEqual(float(out.loc[t, "gross"]), .1, places=7)

    def test_bar_validation_rejects_duplicate(self):
        o, c = synthetic(200)
        frame = pd.DataFrame({"Open": o["BTCUSDT"], "Close": c["BTCUSDT"],
                "High": c["BTCUSDT"] * 1.1, "Low": o["BTCUSDT"] * .9,
                "Volume": 123.})
        frame.index = list(frame.index[:-1]) + [frame.index[-2]]
        with self.assertRaisesRegex(ValueError, "BAD_INDEX"):
            validate_source(frame, "BTCUSDT")

    def test_band_zero_exit_and_metrics(self):
        idx = pd.date_range("2021-01-01", periods=4, freq="4h")
        w = pd.DataFrame({"BTCUSDT": [.4, .35, 0, 0]}, index=idx)
        b = banded(w, .1)
        self.assertAlmostEqual(float(b.iloc[1, 0]), .4)
        self.assertEqual(float(b.iloc[2, 0]), 0.)
        led = pd.DataFrame({"net": [.10, -.05], "turnover": [1., 1.],
                            "exposure": [1., 1.]}, index=idx[:2])
        self.assertAlmostEqual(stats(led)["return_pct"], 4.5, places=5)


if __name__ == "__main__":
    unittest.main()
