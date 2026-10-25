"""H061 CPPI capital protection (config/cppi.yaml). Needs network (run in GitHub Actions).

  python -m lab.cppi
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from lab import xsec

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decisions" / "cppi"


def cppi(risky: pd.Series, safe: pd.Series, c: dict) -> pd.DataFrame:
    v, peak, e = 1.0, 1.0, None
    rows = []
    for t, rr, rs in zip(risky.index, risky.to_numpy(), safe.to_numpy()):
        floor = c["floor_pct"] * peak
        target = min(c["multiplier"] * max(v - floor, 0.0), v)
        if e is None or abs(target - e) > c["band"] * v:
            v -= abs(target - (e or 0.0)) * c["cost"]
            e = target
        v_new = v + e * rr + (v - e) * rs
        e = e * (1 + rr)                                  # exposure drifts with the risky asset
        v = max(v_new, 1e-9)
        peak = max(peak, v)
        rows.append((t, v, e / v, c["floor_pct"] * peak))
    return pd.DataFrame(rows, columns=["t", "v", "exposure", "floor"]).set_index("t")


def main() -> None:
    c = yaml.safe_load((ROOT / "config" / "cppi.yaml").read_text())
    xc = yaml.safe_load((ROOT / "config" / "xsec.yaml").read_text())
    D = xsec.load(xc)
    s = xc["strategies"]["H056"]
    h056 = xsec.book(D, xc, s["signal"], s["lookback"], s["long"])["r"]
    bot = xsec.bot_returns(D)
    from lab import funding as F
    cc = yaml.safe_load((ROOT / "config" / "core.yaml").read_text())
    fund = pd.concat([F.daily_funding(F.load(a, "2020-01")) for a in cc["funding_arb"]["assets"]], axis=1).mean(axis=1)
    idx = bot.index.intersection(h056.index).intersection(fund.index)
    idx = idx[idx >= c["start"]]
    safe = 0.5 * fund.reindex(idx).fillna(0.0)
    risky = {"mix": 0.5 * bot.reindex(idx) + 0.5 * h056.reindex(idx), "bot": bot.reindex(idx)}
    out = {"data_end": str(idx[-1].date()), "rows": {}}
    for name, r in risky.items():
        book = cppi(r, safe, c)
        rb = book["v"].pct_change().fillna(book["v"].iloc[0] - 1)
        row = {"cppi": xsec.stats(rb), "raw": xsec.stats(r), "safe": xsec.stats(safe),
               "avg_exposure": round(float(book["exposure"].mean()), 3),
               "min_v_over_floor": round(float((book["v"] / book["floor"]).min()), 4), "windows": {}}
        for cut in c["cutoffs"]:
            m = idx > cut
            sub = cppi(r[m], safe[m], c)
            w = xsec.stats(sub["v"].pct_change().fillna(sub["v"].iloc[0] - 1))
            row["windows"][cut] = {"cppi": w, "raw": xsec.stats(r[m]), "safe": xsec.stats(safe[m])}
        a = c["accept"]
        row["checks"] = {
            "max_dd": row["cppi"]["max_dd"] >= a["max_dd"] and all(w["cppi"]["max_dd"] >= a["max_dd"] for w in row["windows"].values()),
            "windows_grow": all(w["cppi"]["final_1000"] > 1000 for w in row["windows"].values()),
            "beat_safe": all(w["cppi"]["cagr"] > w["safe"]["cagr"] for w in row["windows"].values()),
        }
        row["accepted"] = all(row["checks"].values()) if name == "mix" else None
        out["rows"][name] = row
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: (v["cppi"], v["checks"]) for k, v in out["rows"].items()}, indent=1, default=str))


if __name__ == "__main__":
    main()
