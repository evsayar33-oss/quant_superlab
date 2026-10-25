"""H074: the fixed H054 core rule on every Bitget asset (config/coreassets.yaml). 8 trials, no tuning.

  python -m lab.coreassets [--offline]
Output: decisions/coreassets/result.json and report.md
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from lab import assetdata, core

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decisions" / "coreassets"


def run(offline: bool = False) -> dict:
    cfg = yaml.safe_load((ROOT / "config" / "coreassets.yaml").read_text())
    ab = yaml.safe_load((ROOT / "config" / "assetbook.yaml").read_text())
    acc = cfg["accept"]
    rows = []
    for asset, spec in ab["assets"].items():
        df = assetdata.load(spec["data"], cfg["timeframe"], ab["start"], offline)
        c = df["Close"].astype(float)
        p = assetdata.panel(asset, df, cfg["timeframe"])
        ppy = p.ppy
        cps = spec["costs"]["commission"] + spec["costs"]["slippage"]
        fund = spec["costs"].get("funding_annual", 0.0)
        bh = c.pct_change().dropna()
        row = {"asset": asset, "bitget": spec["bitget"], "data": spec["data"], "first": str(c.index[0].date()),
               "last": str(c.index[-1].date()), "windows": {}, "checks": {}}
        series = {}
        for m in (1, 2):
            r = core.book_returns({asset: c}, cfg["rule"], cfg["params"], ppy, m * cps, cfg["band"], fund)
            ex = core.book_exposure({asset: c}, cfg["rule"], cfg["params"], ppy, cfg["band"])
            series[m] = r
            row[f"exposure_avg_{m}x"] = round(float(ex.mean()), 3)
        end = c.index[-1]
        warm = c.index[min(len(c) - 1, core._bars(cfg["params"]["sma_days"], ppy) + 1)]   # rule needs SMA200 first
        for wn, y in [("full", None)] + [(f"{y}y", y) for y in cfg["windows_years"]]:
            a = warm if y is None else end - pd.DateOffset(years=y)
            b = bh[bh.index >= a]
            w = {"bh": core.stats(b, ppy)}
            for m in (1, 2):
                w[f"rule_{m}x"] = core.stats(series[m][series[m].index >= a], ppy)
            row["windows"][wn] = {k: {x: v[x] for x in ("start", "final_1000", "cagr", "sharpe", "max_dd")} for k, v in w.items()}
            for m in (1, 2):
                s, bb = w[f"rule_{m}x"], w["bh"]
                row["checks"][f"{wn}_{m}x"] = {
                    "dd": s["max_dd"] >= bb["max_dd"] * (1 - acc["dd_reduction_vs_buyhold"]),
                    "sharpe": s["sharpe"] >= bb["sharpe"] - acc["max_sharpe_gap"],
                    "ret": s["final_1000"] > 1000}
        row["accepted"] = all(all(v.values()) for v in row["checks"].values())
        row["failed"] = [f"{k}:{x}" for k, v in row["checks"].items() for x, ok in v.items() if not ok]
        rows.append(row)
    return {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n_trials": len(rows), "rows": rows}


def _p(x):
    return "—" if x is None else f"{x * 100:+.1f}%"


def report(R: dict) -> str:
    L = ["# H074 — H054 çekirdek kuralı her Bitget varlığında (ayar değişmeden)", "",
         f"Tarih: {R['run_at'][:10]}. Kural ve kabul şartı sonuçlardan ÖNCE yazıldı: `config/coreassets.yaml`. "
         f"Deneme: **{R['n_trials']}** (varlık başına 1).", "",
         "Kural: kapanış SMA200'ün (takvim günü) üstünde VE 30/90/180 günlük getirilerden en az biri pozitif → long; "
         "boyut = min(1, %40 / son 30 gün oynaklığı); %10 işlem yapmama bandı; aksi halde nakit. Short ve kaldıraç yok.", "",
         "Kabul (her pencerede, 1x ve 2x maliyette): düşüş al-tutun en az 1/3 daha az derin, Sharpe en çok 0,10 düşük, getiri pozitif.", "",
         "| Varlık | Bitget | Veri | Pencere | Kural yıllık | Kural Sharpe | Kural düşüş | Al-tut yıllık | Al-tut Sharpe | Al-tut düşüş | 2x maliyet yıllık |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in R["rows"]:
        for wn, w in r["windows"].items():
            L.append(f"| {r['asset']} | {r['bitget']} | {r['first'][:4]}– | {wn} | {_p(w['rule_1x']['cagr'])} | {w['rule_1x']['sharpe']} | "
                     f"{_p(w['rule_1x']['max_dd'])} | {_p(w['bh']['cagr'])} | {w['bh']['sharpe']} | {_p(w['bh']['max_dd'])} | "
                     f"{_p(w['rule_2x']['cagr'])} |")
    L += ["", "## Sonuç", "", "| Varlık | Ortalama pozisyon | Kabul | Kalan kontroller |", "|---|---|---|---|"]
    for r in R["rows"]:
        L.append(f"| {r['asset']} | {r['exposure_avg_1x']:.0%} | {'**EVET**' if r['accepted'] else 'hayır'} | "
                 f"{', '.join(r['failed']) or '—'} |")
    L += ["", "Kabul edilen varlık bir ADAYDIR: varlık başına hipotez id + karar kapısı (run.py --hypothesis) gerekir.", ""]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    R = run(ap.parse_args().offline)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(R, indent=1, default=str))
    (OUT / "report.md").write_text(report(R))
    print(report(R))


if __name__ == "__main__":
    main()
