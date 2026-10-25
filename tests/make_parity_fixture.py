"""Regenerate tests/fixtures/h054_parity.json from lab/core.py, then copy it to h054_spot_bot/tests/fixtures/.
Run only when the H054 rule in lab/core.py was changed on purpose (and update bot/signal.py to match)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import core  # noqa: E402

rng = np.random.default_rng(54)
n = 5000
idx = pd.date_range("2021-01-01", periods=n, freq="4h")
k = np.arange(n)
drift = np.where((k // 700) % 3 == 2, -0.0010, 0.0007)          # long up legs, short down legs
vol = np.where((k // 500) % 2 == 0, 0.004, 0.014)               # calm and wild periods (vol target varies)
close = pd.Series(100 * np.exp(np.cumsum(drift + rng.normal(0, vol))), idx)
prm = {"sma_days": 200, "horizons_days": [30, 90, 180], "target": 0.40, "lookback_days": 30}
ppy = 6 * 365.25
e = core.exposure(close, "dual_trend_vt", prm, ppy)
b = core.apply_band(e, 0.10)
fx = {"timeframe": "4h", "ppy": ppy, "rule": "dual_trend_vt", "params": prm, "band": 0.10,
      "close": [round(float(x), 8) for x in close.values], "index_start": str(idx[0]),
      "exposure_raw": [round(float(x), 10) for x in e.values], "exposure_band": [round(float(x), 10) for x in b.values]}
out = ROOT / "tests" / "fixtures" / "h054_parity.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(fx))
print(f"bars {n}, raw distinct {len(set(fx['exposure_raw']))}, band distinct {len(set(fx['exposure_band']))}, "
      f"share long {(b > 0).mean():.2f}, band changes {(b.diff().abs() > 0).sum()}")
