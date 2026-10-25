"""H073 add-on (information, not a decision): does a rule that looked best in the past stay good?

For the 6-year and 4-year cuts only (their forward 2 years end BEFORE the locked holdout, so the holdout stays
sealed): rank every primary variant by its discovery Sharpe, then read the next 2 years. Reports the rank
correlation (discovery Sharpe vs forward Sharpe), and how the naive top 10 did vs the asset's buy-and-hold.

  python -m lab.assetbook_persist [--offline]
Output: decisions/assetbook/persistence.json and persistence.md
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from scipy import stats as st

from lab import assetbook as AB, assetdata, rules
from lab.engine import Costs


def job_table(asset: str, tf: str, cfg: dict, offline: bool, workers: int) -> dict:
    spec = cfg["assets"][asset]
    p = assetdata.panel(asset, assetdata.load(spec["data"], tf, cfg["start"], offline), tf)
    idx = p.index
    W = [w for w in AB.windows(idx, cfg) if not w["holdout"] and w["testable"]]
    AB._G.update(panel=p, D=AB._arrays(p), costs=Costs(**spec["costs"]), idx=idx, ppy=p.ppy, W=W, cfg=cfg, sw={}, conf={})
    for k in (3, 5, 10):
        AB._G["sw"][k] = AB.swing_arrays(p, k)
    w3 = cfg["families"]["F3_fib_confirm"]["within_bars"] + 1
    for cn in cfg["families"]["F3_fib_confirm"]["grid"]["confirm"]:
        sg = rules.RULES[cn].fn(p, **AB.screen._tuples(AB.mid(rules.RULES[cn].grid)))
        cl = sg.entry_long.iloc[:, 0].astype(float).rolling(w3, min_periods=1).max().to_numpy() > 0
        cs = (sg.entry_short.iloc[:, 0].astype(float).rolling(w3, min_periods=1).max().to_numpy() > 0
              if sg.entry_short is not None else np.zeros(len(idx), bool))
        AB._G["conf"][cn] = (cl, cs)
    prim = {}
    for prm in AB.f1_points(cfg):
        prim[AB.vkey("F1", prm)] = ("F1", prm)
    for prm in AB.f3_points(cfg):
        prim[AB.vkey("F3", prm)] = ("F3", prm)
    f2 = cfg["families"]["F2_catalog_x_fib"]
    for rn in AB.catalog(cfg):
        for ex in f2["exits"]:
            for sd in f2["side"]:
                for fl in f2["filter"]:
                    prm = {"rule": rn, "params": AB.mid(rules.RULES[rn].grid), "exit": ex, "side": sd, "filter": fl}
                    prim[AB.vkey("F2", prm)] = ("F2", prm)
    names = [w["name"] for w in W]
    res = {k: v for k, _, v, e in AB._pool_map([(k, f, prm, 0, names) for k, (f, prm) in prim.items()], workers) if v}
    out = {"asset": asset, "tf": tf, "cuts": {}}
    c = p.c.iloc[:, 0]
    for w in W:
        n = w["name"]
        rows = [(k, v[f"disc_{n}"], v[f"fwd_{n}"]) for k, v in res.items()
                if v.get(f"disc_{n}", {}).get("trades", 0) >= cfg["discovery"]["D1_min_trades"][tf] and v.get(f"fwd_{n}")]
        if len(rows) < 20:
            continue
        ds = np.array([r[1]["sr"] for r in rows])
        fs = np.array([r[2].get("sr", 0.0) for r in rows])
        rho = float(st.spearmanr(ds, fs).statistic)
        top = sorted(rows, key=lambda r: -r[1]["sr"])[:10]
        x = c[(c.index >= w["cut"]) & (c.index < w["fwd_end"])]
        bh = float(x.iloc[-1] / x.iloc[0] - 1)
        out["cuts"][n] = {"cut": str(w["cut"].date()), "fwd_end": str(pd.Timestamp(w["fwd_end"]).date()), "variants": len(rows),
                          "spearman_disc_vs_fwd_sharpe": round(rho, 3), "bh_fwd": round(bh, 4),
                          "top10": [{"key": k, "disc_sr": round(d["sr"], 2), "disc_ret2": round(d["ret2"], 3),
                                     "fwd_sr": round(f.get("sr", 0.0), 2), "fwd_ret2": round(f.get("ret2", 0.0), 3),
                                     "fwd_pf2": f.get("pf2"), "fwd_trades": f.get("trades")} for k, d, f in top],
                          "top10_fwd_positive": int(sum(f.get("ret2", 0) > 0 for _, _, f in top)),
                          "top10_beat_bh": int(sum(f.get("ret2", 0) > bh for _, _, f in top))}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    cfg = AB.load_cfg()
    jobs = [job_table(asset, tf, cfg, a.offline, a.workers) for asset, tf in AB.job_list(cfg)]
    (AB.OUT / "persistence.json").write_text(json.dumps(jobs, indent=1, default=str))
    L = ["# H073 ek: geçmişte en iyi görünen kural sonra da iyi mi? (bilgi, karar değil)", "",
         "Sadece 6 ve 4 yıl önceki kesimler. İleri 2 yıl kilitli dönemden önce biter; kilitli dönem okunmadı.", "",
         "| Varlık | TF | Kesim | Varyant | Sıra korelasyonu (geçmiş Sharpe → sonraki Sharpe) | En iyi 10: sonra kârda | En iyi 10: al-tutu geçen | Al-tut sonraki 2 yıl |",
         "|---|---|---|---|---|---|---|---|"]
    for j in jobs:
        for n, c in j["cuts"].items():
            L.append(f"| {j['asset']} | {j['tf']} | {c['cut']} | {c['variants']} | {c['spearman_disc_vs_fwd_sharpe']} | "
                     f"{c['top10_fwd_positive']}/10 | {c['top10_beat_bh']}/10 | {c['bh_fwd'] * 100:+.0f}% |")
    (AB.OUT / "persistence.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
