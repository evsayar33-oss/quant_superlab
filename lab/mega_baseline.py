"""H062 survivors vs buy-and-hold and vs random entries (rule: config/mega.yaml -> baseline).

For each time-machine survivor and each cut where it was selected, on the forward period only:
  B1 random entry: the strategy's forward trades (same assets, count, holding bars, side) are moved to
     random entry dates inside the forward period, `random_draws` times. Pass when the real trades beat
     >= min_random_pct of the draws (mean over assets of summed net trade returns, 2x cost).
  B2 buy-and-hold: forward pooled Sharpe of the strategy >= forward Sharpe of an equal-weight
     buy-and-hold pool of the same class assets.
Pass = B1 and B2 at every cut where the survivor was selected.

  python -m lab.mega_baseline --parts parts --out decisions/mega/baseline.json --md decisions/mega/baseline.md
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from lab import mega, metrics, screen


def survivors(parts: list[dict]) -> dict:
    seen: dict[str, dict] = {}
    for p_ in parts:
        hy = int(p_.get("holdout_years", 2))
        for c in p_["candidates"]:
            k = f"{p_['cls']}|{p_['side']}|{c['key']}"
            seen.setdefault(k, {"cls": p_["cls"], "side": p_["side"], "key": c["key"], "spec": c["spec"], "cuts": {}})
            seen[k]["cuts"][hy] = {"cut": p_["cut"], "eligible": p_["eligible"], "fwd_ret_2x": c["sealed_holdout"]["pool_ret_2x"]}
    return {k: v for k, v in seen.items() if len(v["cuts"]) >= 2 and all(x["fwd_ret_2x"] > 0 for x in v["cuts"].values())}


def _trade_sum(rets: dict) -> float:
    return float(np.mean([sum(v) for v in rets.values()])) if rets else 0.0


def check_one(p, costs, spec, side, cut, assets, draws, rng) -> dict:
    q = screen.subpanel(p, assets)
    R, _, tr = screen.run_spec(q, spec, side, costs)
    cut = pd.Timestamp(cut)
    c2 = 4 * costs.per_turnover                      # 2x cost, both sides
    fw = R.loc[R.index >= cut]
    pool = fw.mean(axis=1, skipna=True).dropna()
    t = tr[tr["entry"] >= cut] if len(tr) else tr
    real = {a: list(t.loc[t["asset"] == a, "ret"] - c2) for a in assets} if len(t) else {}
    real = {a: v for a, v in real.items() if v}
    o = q.o.loc[q.o.index >= cut]
    L = len(o)
    rand = []
    if real and L > 10:
        for _ in range(draws):
            got = {}
            for a in real:
                ta = t[t["asset"] == a]
                px = o[a].to_numpy()
                v = []
                for _, row in ta.iterrows():
                    b = max(1, int(row["bars"]))
                    if b >= L - 1:
                        continue
                    i = int(rng.integers(0, L - 1 - b))
                    if np.isfinite(px[i]) and np.isfinite(px[i + b]) and px[i] > 0:
                        v.append(int(row["side"]) * (px[i + b] / px[i] - 1) - c2)
                got[a] = v
            rand.append(_trade_sum({a: v for a, v in got.items() if v}))
    m_real = _trade_sum(real)
    pct = float(np.mean([m_real > x for x in rand])) if rand else None
    bh = q.c.loc[q.c.index >= cut].pct_change(fill_method=None).mean(axis=1, skipna=True).dropna()
    return {"cut": str(cut.date()), "n_trades": int(len(t)), "trade_sum": round(m_real, 4),
            "random_median": round(float(np.median(rand)), 4) if rand else None, "random_pct": None if pct is None else round(pct, 3),
            "sharpe": round(metrics.sharpe(pool), 3) if len(pool) > 30 else None,
            "ret": round(float((1 + pool).prod() - 1), 4) if len(pool) else None,
            "bh_sharpe": round(metrics.sharpe(bh), 3) if len(bh) > 30 else None,
            "bh_ret": round(float((1 + bh).prod() - 1), 4) if len(bh) else None,
            "exposure": round(float((fw.notna() & (fw != 0)).mean().mean()), 3) if len(fw) else None}


def run(parts: list[dict], cfg: dict, seed: int = 62) -> dict:
    b = cfg["baseline"]
    sv = survivors(parts)
    rng = np.random.default_rng(seed)
    panels, out = {}, []
    for k, s in sorted(sv.items()):
        if s["cls"] not in panels:
            panels[s["cls"]] = mega.load_class(s["cls"], cfg)
        p, costs = panels[s["cls"]]
        metrics.set_periods(p.ppy)
        rows = {}
        for hy, c in sorted(s["cuts"].items(), reverse=True):
            r = check_one(p, costs, s["spec"], s["side"], c["cut"], c["eligible"], int(b["random_draws"]), rng)
            r["B1"] = r["random_pct"] is not None and r["random_pct"] >= b["min_random_pct"]
            r["B2"] = (r["sharpe"] is not None and r["bh_sharpe"] is not None and r["sharpe"] >= r["bh_sharpe"]) if b.get("beat_bh_sharpe", True) else True
            rows[hy] = r
        ok = all(r["B1"] and r["B2"] for r in rows.values())
        out.append({"cls": s["cls"], "side": s["side"], "key": s["key"], "spec": s["spec"], "cuts": rows,
                    "B1_all": all(r["B1"] for r in rows.values()), "B2_all": all(r["B2"] for r in rows.values()), "pass": ok})
        print(f"[baseline] {k[:90]} -> {'PASS' if ok else 'fail'}")
    return {"date": date.today().isoformat(), "n_survivors": len(out), "n_pass": sum(r["pass"] for r in out),
            "n_B1": sum(r["B1_all"] for r in out), "n_B2": sum(r["B2_all"] for r in out), "rows": out}


def markdown(o: dict, cfg: dict) -> str:
    f = lambda v: "—" if v is None else f"{v:+.0%}"   # noqa: E731
    b = cfg["baseline"]
    L = ["# H062 hayatta kalanlar: al-tut ve rastgele girişe karşı", "",
         "Kural sonuçlardan ÖNCE yazıldı (`config/mega.yaml` → baseline). Sadece ileri dönem (kesimden bugüne), 2x maliyet.", "",
         f"- **B1 rastgele giriş:** aynı varlık, aynı işlem sayısı, aynı tutma süresi ve yön; giriş tarihleri rastgele ({b['random_draws']} deneme). "
         f"Gerçek işlemler denemelerin en az %{b['min_random_pct']*100:.0f}'ini geçmeli.",
         "- **B2 al-tut:** stratejinin ileri Sharpe değeri, sınıfın eşit ağırlıklı al-tut Sharpe değerinden düşük olmamalı.",
         "- Geçmek için: seçildiği HER kesimde B1 ve B2.", "",
         f"Hayatta kalan: **{o['n_survivors']}**. B1'i her kesimde geçen: **{o['n_B1']}**. B2'yi her kesimde geçen: **{o['n_B2']}**. "
         f"İkisini de geçen: **{o['n_pass']}**.", ""]
    rows = sorted(o["rows"], key=lambda r: (not r["pass"], not r["B1_all"], -min((c["random_pct"] or 0) for c in r["cuts"].values())))
    L += ["| Sonuç | Sınıf | Yön | Strateji | Kesim | İleri getiri | Al-tut getiri | İleri Sharpe | Al-tut Sharpe | Rastgeleyi geçme | Pozisyonda |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows[:60]:
        for hy, c in sorted(r["cuts"].items(), key=lambda x: -int(x[0])):
            rp = "—" if c["random_pct"] is None else f"%{c['random_pct'] * 100:.0f}"
            ex = "—" if c["exposure"] is None else f"%{c['exposure'] * 100:.0f}"
            L.append(f"| {'✅' if r['pass'] else '❌'} | {r['cls']} | {r['side']} | `{r['key'][:80]}` | {c['cut']} | {f(c['ret'])} | "
                     f"{f(c['bh_ret'])} | {c['sharpe']} | {c['bh_sharpe']} | {rp} | {ex} |")
    L += ["", "## Zayıf yönler", "",
          "- Rastgele girişler açılış fiyatıyla hesaplandı; stratejinin stop dolumları biraz farklı olabilir.",
          "- Al-tut karşılaştırması long al-tut ile yapıldı (short ve iki yönlü stratejiler için de).",
          "- Kesimlerin ileri dönemleri üst üste biniyor; sonuçlar bağımsız değil.",
          "- Geçenler hâlâ binlerce aday içinden seçildi. Sonraki adım paper izleme ve karar kapısı."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True); ap.add_argument("--out", required=True); ap.add_argument("--md", required=True)
    ap.add_argument("--telegram", action="store_true")
    x = ap.parse_args(argv)
    cfg = mega.cfg_load()
    parts = [json.loads(p_.read_text()) for p_ in sorted(Path(x.parts).rglob("*.json"))]
    o = run(parts, cfg)
    Path(x.out).parent.mkdir(parents=True, exist_ok=True)
    Path(x.out).write_text(json.dumps(o, indent=1, default=str))
    Path(x.md).write_text(markdown(o, cfg))
    print(markdown(o, cfg)[:3000])
    if x.telegram:
        from run import telegram
        t = (f"📏 H062 al-tut/rastgele kontrolü: {o['n_survivors']} hayatta kalan → rastgeleyi geçen {o['n_B1']}, "
             f"al-tut'u geçen {o['n_B2']}, ikisi {o['n_pass']}.")
        for r in [r for r in o["rows"] if r["pass"]][:10]:
            t += f"\n✅ {r['cls']}/{r['side']} {r['key'][:70]}"
        telegram(t + "\n⚠️ Geçenler paper izlemeye adaydır, karar değildir.")


if __name__ == "__main__":
    main()
