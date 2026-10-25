"""Parity: bot/signal.py must give the same exposure as quant_lab lab/core.py (fixture made there)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from bot.signal import apply_band, exposure  # noqa: E402


def test_parity_with_quant_lab():
    fx = json.loads((ROOT / "tests" / "fixtures" / "h054_parity.json").read_text())
    idx = pd.date_range(fx["index_start"], periods=len(fx["close"]), freq="4h")
    c = pd.Series(fx["close"], idx)
    e = exposure(c, fx["ppy"], fx["params"])
    assert np.allclose(e.to_numpy(), fx["exposure_raw"], atol=1e-8)
    assert np.allclose(apply_band(e, fx["band"]).to_numpy(), fx["exposure_band"], atol=1e-8)


if __name__ == "__main__":
    test_parity_with_quant_lab(); print("ok")
