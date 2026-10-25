"""H076 learned per-asset model (config/mlbook.yaml). Walk-forward gradient boosting on every rule signal,
the Fibonacci zone position and regime features; long/cash or long/short/cash. Report-only.

  python -m lab.mlbook [--offline] [--jobs BTC:4h,...]
Output: decisions/mlbook/result.json, report.md
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats as st

from lab import assetdata, core, metrics, rules, screen
from lab import indicators as I
from lab.engine import Costs

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decisions" / "mlbook"


def features(p) -> pd.DataFrame:
    """Every column is known at the close of bar t."""
    col = p.columns[0]
    c, idx = p.c[col], p.index
    F = {}
    for name, r in rules.RULES.items():
        if r.family == "positioning":
            continue
        try:
            sg = r.fn(p, **screen._tuples({k: v[len(v) // 2] for k, v in (r.grid or {}).items()}))
        except Exception:  # noqa: BLE001 - a rule that cannot run on this asset is left out
            continue
        el = sg.entry_long[col].astype(bool).to_numpy()
        es = sg.entry_short[col].astype(bool).to_numpy() if sg.entry_short is not None else np.zeros(len(idx), bool)
        ev = pd.Series(np.where(el, 1.0, np.where(es, -1.0, np.nan)), idx)
        last = ev.ffill()
        age = pd.Series(np.arange(len(idx)), idx) - pd.Series(np.where(ev.notna(), np.arange(len(idx)), np.nan), idx).ffill()
        F[f"r_{name}"] = last.where(age <= 20, 0.0).fillna(0.0)
    sh, sl, _, _ = rules._swings(p, 5)
    rng = (sh - sl)[col]
    F["fib_pos"] = ((c - sl[col]) / rng.where(rng > 0)).clip(-1, 2)
    w = 11
    t_hi = rules._since(rules._b(p.h.shift(5) == p.h.rolling(w, min_periods=w).max()))[col]
    t_lo = rules._since(rules._b(p.l.shift(5) == p.l.rolling(w, min_periods=w).min()))[col]
    F["fib_leg_up"] = (t_hi < t_lo).astype(float)
    s200, s50 = c.rolling(200, min_periods=200).mean(), c.rolling(50, min_periods=50).mean()
    F["trend200"] = c / s200 - 1
    F["trend50_200"] = s50 / s200 - 1
    _, _, adx = I.dmi(p.h, p.l, p.c, 14)
    F["adx"] = adx[col]
    r1 = c.pct_change()
    F["vol30"] = r1.rolling(30, min_periods=15).std()
    for k in (1, 5, 20, 60):
        F[f"ret{k}"] = c.pct_change(k)
    F["atr_pct"] = I.atr(p.h, p.l, p.c, 14)[col] / c
    return pd.DataFrame(F, index=idx)


def labels(p, h: int) -> pd.Series:
    col = p.columns[0]
    c = p.c[col]
    fwd = c.shift(-h) / c - 1
    atrp = I.atr(p.h, p.l, p.c, 14)[col] / c
    y = np.sign(fwd).where(fwd.abs() >= 0.25 * atrp, 0.0)
    return y.where(fwd.notna())


def walk_forward(X: pd.DataFrame, y: pd.Series, h: int, cfg: dict) -> pd.DataFrame:
    """Out-of-sample class probabilities (columns -1, 0, 1). Each block is predicted by a model fit only on
    bars whose label was complete before the block started (embargo = horizon)."""
    from sklearn.ensemble import HistGradientBoostingClassifier
    wf = cfg["walk_forward"]
    idx = X.index
    valid = X.notna().mean(axis=1) > 0.8
    start = idx[valid.to_numpy()][0] + pd.DateOffset(years=wf["min_train_years"])
    edges = list(pd.date_range(start, idx[-1], freq=f"{wf['refit_months']}MS")) + [idx[-1] + pd.Timedelta(days=1)]
    P = pd.DataFrame(np.nan, index=idx, columns=[-1.0, 0.0, 1.0])
    for a, b in zip(edges[:-1], edges[1:]):
        ia = idx.searchsorted(a)
        tr = np.arange(max(0, ia - h))
        tr = tr[valid.to_numpy()[tr] & y.iloc[tr].notna().to_numpy()]
        if len(tr) < 300:
            continue
        m = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0,
                                           random_state=0)
        m.fit(X.iloc[tr], y.iloc[tr].astype(int))
        te = (idx >= a) & (idx < b)
        if te.any():
            pr = m.predict_proba(X.loc[te])
            for j, cl in enumerate(m.classes_):
                P.loc[te, float(cl)] = pr[:, j]
    return P


def book(p, pos: pd.Series, cps: float, fund: float, ppy: float) -> pd.Series:
    """Decision at close t, filled at the open of t+1: the gap close t -> open t+1 is held with the old position."""
    col = p.columns[0]
    o, c = p.o[col], p.c[col]
    prev = pos.shift(1).fillna(0.0)
    gap = (o / c.shift(1) - 1).fillna(0.0)
    intra = (c / o - 1).fillna(0.0)
    held_old, held_new = prev.shift(1).fillna(0.0), prev
    r = held_old * gap + held_new * intra
    r -= (held_new - held_old).abs() * cps + held_new.abs() * fund / ppy
    return r


def recovery_days(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    peak_t = eq.index.to_series().where(eq >= eq.cummax()).ffill()
    return float((eq.index.to_series() - peak_t).dt.days.max())


def wstats(r: pd.Series, ppy: float) -> dict:
    if len(r) < 30:
        return {}
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    eq = (1 + r).cumprod()
    sd = r.std()
    y = (1 + r).groupby(r.index.year).prod() - 1
    return {"start": str(r.index[0].date()), "end": str(r.index[-1].date()), "cagr": float(eq.iloc[-1] ** (1 / yrs) - 1),
            "max_dd": float((eq / eq.cummax() - 1).min()), "recovery_days": recovery_days(r),
            "sharpe": float(r.mean() / sd * math.sqrt(ppy)) if sd > 0 else 0.0,
            "sr_bar": float(r.mean() / sd) if sd > 0 else 0.0, "skew": float(st.skew(r)), "kurt": float(st.kurtosis(r, fisher=False)),
            "n": int(len(r)), "years": {str(k): round(float(v), 4) for k, v in y.items()},
            "exposure": None}


def run_job(asset: str, tf: str, cfg: dict, ab: dict, offline: bool) -> dict:
    spec = ab["assets"][asset]
    p = assetdata.panel(asset, assetdata.load(spec["data"], tf, ab["start"], offline), tf)
    ppy = p.ppy
    cps = spec["costs"]["commission"] + spec["costs"]["slippage"]
    fund = spec["costs"].get("funding_annual", 0.0)
    X = features(p)
    cut = p.index[-1] - pd.DateOffset(years=cfg["holdout_years"])
    rows = {}
    oos_start = None
    for h in cfg["grid"]["horizon"][tf]:
        P = walk_forward(X, labels(p, h), h, cfg)
        ok = P.notna().all(axis=1)
        oos_start = P.index[ok.to_numpy()][0] if ok.any() else None
        for th in cfg["grid"]["threshold"]:
            for side in cfg["grid"]["side"]:
                pos = pd.Series(np.where(P[1.0] > th, 1.0, np.where((side == "both") & (P[-1.0] > th), -1.0, 0.0)), P.index)
                pos = pos.where(ok, 0.0)
                key = f"h={h},th={th},side={side}"
                out = {}
                for m in (1, 2):
                    r = book(p, pos, m * cps, fund, ppy)
                    out[f"disc_{m}x"] = wstats(r[(r.index >= oos_start) & (r.index < cut)], ppy) if oos_start is not None else {}
                    out[f"hold_{m}x"] = wstats(r[r.index >= cut], ppy)
                out["exposure_long"] = round(float((pos[pos.index >= oos_start] > 0).mean()), 3) if oos_start is not None else None
                out["exposure_short"] = round(float((pos[pos.index >= oos_start] < 0).mean()), 3) if oos_start is not None else None
                rows[key] = out
    base = core.book_returns({asset: p.c.iloc[:, 0]}, "dual_trend_vt", {"sma_days": 200, "horizons_days": [30, 90, 180],
                             "target": 0.40, "lookback_days": 30}, ppy, cps, 0.10, fund)
    bh = p.c.iloc[:, 0].pct_change().fillna(0.0)
    ref = {}
    for nm, r in (("H054_rule", base), ("buy_hold", bh)):
        ref[nm] = {"disc": wstats(r[(r.index >= (oos_start or cut)) & (r.index < cut)], ppy), "hold": wstats(r[r.index >= cut], ppy)}
    return {"asset": asset, "tf": tf, "bitget": spec["bitget"], "oos_start": str(oos_start), "cut": str(cut.date()),
            "n_features": X.shape[1], "rows": rows, "ref": ref}


def judge(R: dict, cfg: dict) -> None:
    T, S = cfg["target"], cfg["strict"]
    n = sum(len(j["rows"]) for j in R["jobs"])
    for j in R["jobs"]:
        srs = [v["disc_1x"]["sr_bar"] for v in j["rows"].values() if v.get("disc_1x")]
        var = float(np.var(srs, ddof=1)) if len(srs) > 1 else 0.0
        star = metrics.expected_max_sharpe(n, var)
        for v in j["rows"].values():
            d, h, d2, h2 = (v.get(k) or {} for k in ("disc_1x", "hold_1x", "disc_2x", "hold_2x"))
            tgt = lambda s: bool(s) and s["cagr"] >= T["min_cagr"] and s["recovery_days"] <= T["max_recovery_days"]
            v["target_disc"], v["target_hold"] = tgt(d), tgt(h)
            if d:
                den = math.sqrt(max(1e-12, 1 - d["skew"] * d["sr_bar"] + (d["kurt"] - 1) / 4 * d["sr_bar"] ** 2))
                v["dsr"] = round(float(st.norm.cdf((d["sr_bar"] - star) * math.sqrt(d["n"] - 1) / den)), 3)
            v["S1"] = bool(d2 and h2 and d2["cagr"] > 0 and h2["cagr"] > 0)
            v["S2"] = v.get("dsr", 0) >= S["S2_min_dsr"]
            v["lead"] = v["target_disc"] and v["target_hold"] and v["S1"] and v["S2"]
            v["meets_target"] = v["target_disc"] and v["target_hold"]
    R["n_trials"] = n


def _p(x):
    return "—" if x is None else f"{x * 100:+.1f}%"


def report(R: dict) -> str:
    L = ["# H076 öğrenen model — varlık başına (long / long-short)", "",
         f"Tarih: {R['run_at'][:10]}. Kurallar sonuçlardan ÖNCE yazıldı: `config/mlbook.yaml` (commit `7ea3c19`). Deneme: **{R['n_trials']}**.", "",
         "Hedef (sahip): yıllık ≥ %25 ve en uzun toparlanma ≤ 600 gün, hem ileri test (walk-forward) döneminde hem kilitli son 2 yılda.", "",
         "| Varlık | TF | Ayar | İleri test yıllık | Toparlanma (gün) | Kilitli 2 yıl yıllık | Toparlanma | 2x maliyet kilitli | DSR | Long / short payı | Hedef | Aday |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for j in R["jobs"]:
        for k, v in j["rows"].items():
            d, h, h2 = (v.get(x) or {} for x in ("disc_1x", "hold_1x", "hold_2x"))
            L.append(f"| {j['asset']} | {j['tf']} | `{k}` | {_p(d.get('cagr'))} | {d.get('recovery_days', '—'):.0f} | "
                     f"{_p(h.get('cagr'))} | {h.get('recovery_days', float('nan')):.0f} | {_p(h2.get('cagr'))} | {v.get('dsr', '—')} | "
                     f"{v['exposure_long']:.0%} / {v['exposure_short']:.0%} | {'**EVET**' if v['meets_target'] else 'hayır'} | "
                     f"{'**ADAY**' if v['lead'] else '—'} |")
    L += ["", "## Karşılaştırma: aynı dönemlerde H054 kuralı ve al-tut", "",
          "| Varlık | TF | H054 ileri test | H054 toparlanma | H054 kilitli 2 yıl | Al-tut ileri test | Al-tut kilitli 2 yıl |", "|---|---|---|---|---|---|---|"]
    for j in R["jobs"]:
        a, b = j["ref"]["H054_rule"], j["ref"]["buy_hold"]
        L.append(f"| {j['asset']} | {j['tf']} | {_p(a['disc'].get('cagr'))} | {a['disc'].get('recovery_days', '—')} | {_p(a['hold'].get('cagr'))} | "
                 f"{_p(b['disc'].get('cagr'))} | {_p(b['hold'].get('cagr'))} |")
    meets = [(j["asset"], j["tf"], k) for j in R["jobs"] for k, v in j["rows"].items() if v["meets_target"]]
    leads = [(j["asset"], j["tf"], k) for j in R["jobs"] for k, v in j["rows"].items() if v["lead"]]
    L += ["", f"**Hedefi iki dönemde de karşılayan ayar: {len(meets)}. Sıkı kontrolleri de geçen (aday): {len(leads)}.**", ""]
    L += ["## Zayıf yönler", "",
          "- Model her 6 ayda geçmiş veriyle yeniden eğitilir; ileri test gerçek bir canlı kayıt değildir.",
          "- Kripto geçmişi 2017'den (SOL 2020'den); ilk 3 yıl sadece eğitimdir, ileri test dönemi kısadır.",
          "- Funding sabit oran (kripto %8, diğer %5); short tarafında da maliyet olarak sayıldı.",
          "- Hedefi karşılayan ama sıkı kontrolü geçmeyen ayar kanıt değildir; kâğıt üzerinde izlenmelidir."]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--jobs", default="")
    a = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "config" / "mlbook.yaml").read_text())
    ab = yaml.safe_load((ROOT / "config" / "assetbook.yaml").read_text())
    todo = [x.split(":") for x in (a.jobs.split(",") if a.jobs else cfg["jobs"])]
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for asset, tf in todo:
        t0 = datetime.now()
        jobs.append(run_job(asset, tf, cfg, ab, a.offline))
        print(f"{asset} {tf} done {(datetime.now() - t0).seconds}s", flush=True)
    R = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "jobs": jobs}
    judge(R, cfg)
    (OUT / "result.json").write_text(json.dumps(R, indent=1, default=str))
    (OUT / "report.md").write_text(report(R))
    print(report(R))


if __name__ == "__main__":
    main()
