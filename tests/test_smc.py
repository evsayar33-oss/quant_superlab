"""SMC / divergence / pivot rules: they run, fire, and never use future bars."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from lab import rules
from lab.panel import Panel

NEW = ["smc_bos", "smc_choch", "smc_fvg", "smc_order_block", "smc_liquidity_sweep", "smc_ote",
       "rsi_divergence", "macd_divergence", "pivot_bounce"]


def _panel(seed=0, n=1500):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.03, (n, 3)), axis=0)), idx, ["A", "B", "C"])
    return Panel.from_close(c, seed=seed)


def test_no_lookahead_and_fires():
    p = _panel()
    cut = 1000
    q = _panel()
    for f in ("o", "h", "l", "c"):                      # scramble everything after the cut
        df = getattr(q, f).copy()
        df.iloc[cut:] = df.iloc[cut:].values[::-1] * 1.7
        setattr(q, f, df)
    for name in NEW:
        r = rules.RULES[name]
        prm = {k: v[0] for k, v in r.grid.items()}
        a, b = r.fn(p, **prm), r.fn(q, **prm)
        for fld in ("entry_long", "exit_long", "entry_short", "exit_short"):
            x, y = getattr(a, fld), getattr(b, fld)
            if x is None:
                continue
            assert x.iloc[:cut].equals(y.iloc[:cut]), f"{name}.{fld} uses future bars"
        assert a.entry_long.values.sum() > 0 and a.entry_short.values.sum() > 0, f"{name} never fires"


if __name__ == "__main__":
    test_no_lookahead_and_fires(); print("ok test_no_lookahead_and_fires")
