"""H077 implied-volatility range reversion (config/volrange.yaml). Report-only.

  python -m lab.volrange [--offline]
Output: decisions/volrange/result.json, report.md
"""
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats as st

from lab import assetdata, metrics, rules

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decisions" / "volrange"


def deribit_dvol(cur: str, offline: bool = False) -> pd.Series:
    p = assetdata.CACHE / f"dvol_{cur}.csv"
    if p.exists() and (offline or time.time() - p.stat().st_mtime < 20 * 3600):
        return pd.read_csv(p, index_col=0, parse_dates=True).iloc[:, 0]
    import requests
    rows, start = [], int(pd.Timestamp("2021-01-01").timestamp() * 1000)
    now = int(time.time() * 1000)
    while start < now:
        end = min(start + 900 * 86400000, now)
        r = requests.get("https://www.deribit.com/api/v2/public/get_volatility_index_data",
                         params={"currency": cur, "start_timestamp": start, "end_timestamp": end, "resolution": "1D"}, timeout=30)
        rows += r.json()["result"]["data"]
        start = end + 1
    s = pd.Series({pd.to_datetime(x[0], unit="ms"): x[4] for x in rows}).sort_index()
    assetdata.CACHE.mkdir(parents=True, exist_ok=True)
    s.to_csv(p)
    return s


def load_iv(src: str, idx: pd.DatetimeIndex, offline: bool) -> pd.Series:
    kind, sym = src.split(":")
    s = assetdata.yahoo(sym, "1990-01-01", offline)["Close"] if kind == "yahoo" else deribit_dvol(sym, offline)
    s.index = pd.DatetimeIndex(s.index).normalize()
    return s.reindex(idx, method="ffill")       # IV known at the same daily close (shift below keeps it causal)


def simulate(O, H, L, C, EM, k, n, max_hold, stop, side, cps, fund_bar):
    """Signal at close t: close outside R +- k*EM(t-n), R = close t-n. Fill next open. Exit at R (target),
    stop or max_hold. Stop first if both touch in one bar. Returns per-bar returns and trades."""
    T = len(C)
    R = np.zeros(T)
    trades = []
    pos, ent, tgt, stp, ei = 0, 0.0, 0.0, 0.0, 0
    for t in range(n + 1, T):
        if pos != 0:
            x = None
            if pos == 1:
                if stp and L[t] <= stp:
                    x = min(O[t], stp)
                elif H[t] >= tgt:
                    x = max(O[t], tgt)
            else:
                if stp and H[t] >= stp:
                    x = max(O[t], stp)
                elif L[t] <= tgt:
                    x = min(O[t], tgt)
            if x is None and t - ei >= max_hold:
                x = C[t]
            base = ent if t == ei else C[t - 1]
            if x is None:
                R[t] += pos * (C[t] / base - 1) - fund_bar
            else:
                R[t] += pos * (x / base - 1) - cps - fund_bar
                trades.append((ei, t, pos * (x / ent - 1)))
                pos = 0
            continue
        j = t - 1                                   # decision bar
        ref, em = C[j - n], EM[j - n]
        if not (em == em) or em <= 0:
            continue
        side_now = 1 if C[j] < ref - k * em else (-1 if side == "both" and C[j] > ref + k * em else 0)
        if side_now == 0:
            continue
        pos, ent, ei, tgt = side_now, O[t], t, ref
        stp = (ent - side_now * 2 * EM[j]) if stop == "em2" else 0.0
        R[t] -= cps
        # same-bar exits on the entry bar
        x = None
        if pos == 1:
            if stp and L[t] <= stp:
                x = stp
            elif H[t] >= tgt:
                x = tgt
        else:
            if stp and H[t] >= stp:
                x = stp
            elif L[t] <= tgt:
                x = tgt
        if x is not None:
            R[t] += pos * (x / ent - 1) - cps - fund_bar
            trades.append((ei, t, pos * (x / ent - 1)))
            pos = 0
        else:
            R[t] += pos * (C[t] / ent - 1) - fund_bar
    return R, trades


def recovery_days(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    pk = eq.index.to_series().where(eq >= eq.cummax()).ffill()
    return float((eq.index.to_series() - pk).dt.days.max())


def wstats(R, trades, idx, cps, a, b, ppy):
    ia, ib = idx.searchsorted(a), idx.searchsorted(b)
    if ib - ia < 30:
        return {}
    ex = np.zeros(len(R))
    tw = []
    for e, x, g in trades:
        ex[e] += cps
        ex[x] += cps
        if ia <= x < ib:
            tw.append(g)
    r1 = pd.Series(R[ia:ib], idx[ia:ib])
    r2 = r1 - ex[ia:ib]
    net = np.array(tw) - 4 * cps
    w, l = net[net > 0], net[net <= 0]
    pay = float(w.mean() / -l.mean()) if len(w) and len(l) and l.mean() < 0 else None
    yrs = (r1.index[-1] - r1.index[0]).days / 365.25
    sd = r1.std()
    return {"trades": len(tw), "win_rate": float((net > 0).mean()) if len(net) else 0.0,
            "breakeven_wr": 1 / (1 + pay) if pay else None,
            "pf2": float(w.sum() / -l.sum()) if l.sum() < 0 else (99.0 if len(w) else 0.0),
            "worst_trade": float(net.min()) if len(net) else None,
            "ret2": float((1 + r2).prod() - 1), "cagr": float((1 + r1).prod() ** (1 / yrs) - 1),
            "cagr2": float((1 + r2).prod() ** (1 / yrs) - 1),
            "max_dd": float(((1 + r1).cumprod() / (1 + r1).cumprod().cummax() - 1).min()),
            "recovery_days": recovery_days(r1),
            "thirds2": [float((1 + x).prod() - 1) for x in np.array_split(r2.to_numpy(), 3)],
            "sr_bar": float(r1.mean() / sd) if sd > 0 else 0.0, "n": int(len(r1)),
            "skew": float(st.skew(r1)) if sd > 0 else 0.0, "kurt": float(st.kurtosis(r1, fisher=False)) if sd > 0 else 3.0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    off = ap.parse_args().offline
    cfg = yaml.safe_load((ROOT / "config" / "volrange.yaml").read_text())
    ab = yaml.safe_load((ROOT / "config" / "assetbook.yaml").read_text())
    pts = rules.grid_points(cfg["grid"])
    out = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "jobs": []}
    for a, spec in cfg["assets"].items():
        df = assetdata.load(spec["price"], "1d", "1990-01-01", off)
        df.index = pd.DatetimeIndex(df.index).normalize()
        iv = load_iv(spec["iv"], df.index, off)
        ok = iv.notna()
        df, iv = df[ok], iv[ok]
        crypto = spec["price"].startswith("binance")
        D = 365 if crypto else 252
        ppy = len(df) / ((df.index[-1] - df.index[0]).days / 365.25)
        c = ab["assets"][a]["costs"]
        cps, fund = c["commission"] + c["slippage"], c.get("funding_annual", 0.0) / ppy
        O, H, L, C = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        cut = df.index[-1] - pd.DateOffset(years=cfg["holdout_years"])
        job = {"asset": a, "bitget": spec["bitget"], "first": str(df.index[0].date()), "cut": str(cut.date()), "rows": {}}
        for p in pts:
            EM = C * iv.to_numpy() / 100 * np.sqrt(p["n"] / D)
            R, tr = simulate(O, H, L, C, EM, p["k"], p["n"], p["max_hold"], p["stop"], p["side"], cps, fund)
            key = ",".join(f"{k}={v}" for k, v in p.items())
            job["rows"][key] = {"p": p, "disc": wstats(R, tr, df.index, cps, df.index[0], cut, ppy),
                                "hold": wstats(R, tr, df.index, cps, cut, df.index[-1] + pd.Timedelta(days=1), ppy)}
        bh = df["Close"].pct_change().fillna(0.0)
        job["bh"] = {w: {"cagr": float((1 + x).prod() ** (365.25 / max((x.index[-1] - x.index[0]).days, 1)) - 1),
                         "recovery_days": recovery_days(x)} for w, x in (("disc", bh[bh.index < cut]), ("hold", bh[bh.index >= cut]))}
        out["jobs"].append(job)
        print(a, "done", flush=True)
    judge(out, cfg, len(pts) * len(cfg["assets"]))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(out, indent=1, default=str))
    (OUT / "report.md").write_text(report(out, cfg))
    print(report(out, cfg))


def judge(out, cfg, n_trials):
    d, h, T = cfg["discovery"], cfg["holdout"], cfg["owner_target"]
    out["n_trials"] = n_trials
    for j in out["jobs"]:
        rows = j["rows"]
        srs = [v["disc"]["sr_bar"] for v in rows.values() if v["disc"]]
        star = metrics.expected_max_sharpe(n_trials, float(np.var(srs, ddof=1)))
        for key, v in rows.items():
            s, p = v["disc"], v["p"]
            c = {}
            c["D1"] = bool(s) and s["trades"] >= d["min_trades"]
            c["D2"] = bool(s) and s["ret2"] > 0 and s["pf2"] >= d["min_profit_factor_2x"]
            c["D3"] = bool(s) and all(x > 0 for x in s["thirds2"])
            nb = []
            for kk, vals in (("k", cfg["grid"]["k"]), ("n", cfg["grid"]["n"])):
                i = vals.index(p[kk])
                for jj in (i - 1, i + 1):
                    if 0 <= jj < len(vals):
                        q = dict(p, **{kk: vals[jj]})
                        nb.append(rows[",".join(f"{a}={b}" for a, b in q.items())]["disc"])
            c["D4"] = bool(nb) and sum(bool(x) and x["pf2"] >= 1.10 for x in nb) / len(nb) >= d["plateau"]
            if s:
                den = math.sqrt(max(1e-12, 1 - s["skew"] * s["sr_bar"] + (s["kurt"] - 1) / 4 * s["sr_bar"] ** 2))
                v["dsr"] = round(float(st.norm.cdf((s["sr_bar"] - star) * math.sqrt(s["n"] - 1) / den)), 3)
            c["D6"] = v.get("dsr", 0) >= d["min_dsr"]
            hs = v["hold"]
            c["H"] = bool(hs) and hs["trades"] >= h["min_trades"] and hs["ret2"] > 0 and hs["pf2"] >= h["min_profit_factor_2x"]
            v["checks"] = c
            v["lead"] = all(c.values())
            v["owner_target"] = all(bool(x) and x["cagr"] >= T["min_cagr"] and x["recovery_days"] <= T["max_recovery_days"] for x in (s, hs))


def _p(x):
    return "—" if x is None else f"{x * 100:+.1f}%"


def report(out, cfg):
    L = ["# H077 — opsiyon beklenen aralığı dışına çıkınca geri dönüş (videodaki strateji)", "",
         f"Tarih: {out['run_at'][:10]}. Kurallar sonuçlardan ÖNCE yazıldı: `config/volrange.yaml` (commit `f8f3d1a`). Deneme: **{out['n_trials']}**.", "",
         "## Varlık başına en iyi 3 ayar (keşif dönemi kâr faktörüne göre) ve kilitli son 2 yıl", "",
         "| Varlık | Ayar | Keşif: işlem / kazanma / başa baş / en kötü işlem / yıllık / toparlanma | Kilitli 2 yıl: işlem / kazanma / en kötü / yıllık | DSR | Kalan | Aday |",
         "|---|---|---|---|---|---|---|"]
    for j in out["jobs"]:
        top = sorted(j["rows"].items(), key=lambda kv: -(kv[1]["disc"].get("pf2", 0) if kv[1]["disc"].get("trades", 0) >= 30 else -1))[:3]
        for key, v in top:
            s, h = v["disc"], v["hold"] or {}
            fails = ",".join(k for k, ok in v["checks"].items() if not ok) or "—"
            be = s.get("breakeven_wr")
            L.append(f"| {j['asset']} | `{key}` | {s.get('trades')} / {s.get('win_rate', 0):.0%} / {('%.0f%%' % (be * 100)) if be else '—'} / "
                     f"{_p(s.get('worst_trade'))} / {_p(s.get('cagr'))} / {s.get('recovery_days', 0):.0f} g | "
                     f"{h.get('trades', '—')} / {h.get('win_rate', 0):.0%} / {_p(h.get('worst_trade'))} / {_p(h.get('cagr'))} | "
                     f"{v.get('dsr', '—')} | {fails} | {'**ADAY**' if v['lead'] else '—'} |")
    leads = [(j["asset"], k) for j in out["jobs"] for k, v in j["rows"].items() if v["lead"]]
    tg = [(j["asset"], k) for j in out["jobs"] for k, v in j["rows"].items() if v["owner_target"]]
    hundred = [(j["asset"], k, v["disc"]["trades"]) for j in out["jobs"] for k, v in j["rows"].items()
               if v["disc"] and v["disc"]["trades"] >= 10 and v["disc"]["win_rate"] >= 0.999]
    L += ["", f"**Aday (tüm kontroller + kilitli 2 yıl): {len(leads)}.** Sahibin hedefini (yıllık ≥ %25, toparlanma ≤ 600 gün) iki dönemde de karşılayan: {len(tg)}.",
          f"Keşifte %100 kazanma oranı (≥ 10 işlem) gösteren ayar: {len(hundred)}.", "",
          "## Al-tut (aynı dönemler)", "", "| Varlık | Keşif yıllık | Kilitli 2 yıl yıllık |", "|---|---|---|"]
    for j in out["jobs"]:
        L.append(f"| {j['asset']} | {_p(j['bh']['disc']['cagr'])} | {_p(j['bh']['hold']['cagr'])} |")
    L += ["", "## Zayıf yönler", "",
          "- Endeks ve altın için fiyat vekili (^GSPC, ^NDX, GLD); oynaklık endeksi kapanışı fiyat kapanışıyla aynı saatte değildir.",
          "- Kripto DVOL 2021'den başlar; keşif dönemi kısa (yaklaşık 3,5 yıl).",
          "- Stopsuz ayarlarda tek bir kötü işlem uzun toparlanma yaratabilir; en kötü işlem sütununa bakın.",
          "- Aday bile karar değildir: yeni hipotez id + karar kapısı + ileri kayıt gerekir."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
