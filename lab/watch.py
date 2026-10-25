"""Paper forward watch and leverage test for H063-H065 (rules: config/watch.yaml).

  python -m lab.watch lev    -> decisions/watch/leverage.json + leverage.md   (backtest, pre-registered pick)
  python -m lab.watch daily  -> decisions/watch/state.json + report.md        (paper record since `start`)

Signals use closed daily bars only. Paper only: no orders are sent.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab import mega, metrics, screen  # noqa: E402

OUT = ROOT / "decisions" / "watch"


def cfg_load(path: str | None = None) -> dict:
    return yaml.safe_load((Path(path) if path else ROOT / "config" / "watch.yaml").read_text())


def start_leverage(pick) -> int:
    return max(1, int((pick or 1) // 2))


def tradable_assets() -> set | None:
    f = OUT / "venues.json"
    if not f.exists():
        return None
    v = json.loads(f.read_text())
    return {t for t, x in v.get("assets", {}).items() if x.get("markets")}


def idea_returns(idea: dict, panels: dict, synthetic: bool = False, only: set | None = None):
    cls = idea["cls"]
    if cls not in panels:
        panels[cls] = mega.load_class(cls, mega.cfg_load(), synthetic)
    p, costs = panels[cls]
    if only is not None:
        keep = [a for a in p.columns if a in only]
        if not keep:
            return p, pd.Series(dtype=float), None, None
        p = screen.subpanel(p, keep)
    R, X, tr = screen.run_spec(p, idea["spec"], idea["side"], costs)
    pool = R.mean(axis=1, skipna=True).dropna()
    return p, pool, X, tr


def lever(r: pd.Series, L) -> pd.Series:
    return (r * L).clip(lower=-1.0)


def vt_scale(r: pd.Series, vt: dict, ppy: float) -> pd.Series:
    n = int(vt["lookback_days"] * ppy / 365.25)
    vol = r.rolling(n, min_periods=n // 2).std() * np.sqrt(ppy)
    return (vt["target"] / vol).clip(upper=vt["max_leverage"]).shift(1).fillna(1.0)


def _st(r: pd.Series) -> dict:
    if len(r) < 30:
        return {}
    eq = (1 + r).cumprod()
    return {"final_1000": round(float(1000 * eq.iloc[-1]), 0), "cagr": round(metrics.cagr(r), 4),
            "sharpe": round(metrics.sharpe(r), 3), "max_dd": round(metrics.max_drawdown(r), 4),
            "worst_day": round(float(r.min()), 4), "ruined": bool((eq <= 0.01).any())}


def leverage(cfg: dict, synthetic: bool = False) -> dict:
    lv = cfg["leverage"]
    panels, out = {}, {}
    for hid, idea in cfg["ideas"].items():
        p, pool, _, _ = idea_returns(idea, panels, synthetic)
        metrics.set_periods(p.ppy)
        bh = p.c.pct_change(fill_method=None).mean(axis=1, skipna=True).dropna()
        rows = {}
        for L in lv["static"]:
            r = lever(pool, L)
            rows[f"{L}x"] = {"full": _st(r), "windows": {w: _st(r[r.index >= pd.Timestamp(w)]) for w in lv["windows"]}}
        s = vt_scale(pool, lv["vol_target"], p.ppy)
        rv = (pool * s).clip(lower=-1.0)
        rows["vt"] = {"full": _st(rv), "windows": {w: _st(rv[rv.index >= pd.Timestamp(w)]) for w in lv["windows"]},
                      "avg_leverage": round(float(s.mean()), 2)}
        ok = []
        for L in lv["static"]:
            x = rows[f"{L}x"]
            parts = [x["full"]] + [v for v in x["windows"].values() if v]
            if x["full"] and all(v and v["max_dd"] >= lv["max_dd_floor"] and v["worst_day"] >= lv["worst_day_floor"] and not v["ruined"] for v in parts):
                ok.append(L)
        pick = max(ok) if ok else None
        out[hid] = {"name": idea["name"], "rows": rows, "pick": pick,
                    "bh": {"full": _st(bh), "windows": {w: _st(bh[bh.index >= pd.Timestamp(w)]) for w in lv["windows"]}}}
        print(f"[watch] {hid}: pick {pick}x")
    return {"date": date.today().isoformat(), "ideas": out}


def lev_markdown(o: dict, cfg: dict) -> str:
    f = lambda v: "—" if v is None else f"{v:+.0%}"   # noqa: E731
    lv = cfg["leverage"]
    L = [f"# {', '.join(o['ideas'])} kaldıraç testi", "",
         f"Kural sonuçlardan ÖNCE yazıldı (`config/watch.yaml`): en yüksek kaldıraç seçilir, şu şartla: tüm geçmişte VE her pencerede "
         f"maks. düşüş ≥ %{lv['max_dd_floor']*100:.0f}, hiçbir gün %{lv['worst_day_floor']*100:.0f}'ten kötü değil, kasa hiç sıfırlanmamış.", ""]
    for hid, x in o["ideas"].items():
        L += [f"## {hid} — {x['name']}", "", f"Seçilen kaldıraç: **{'yok (1x bile şartı geçmedi)' if x['pick'] is None else str(x['pick']) + 'x'}**", "",
              "| Kaldıraç | Tüm geçmiş: $1000 → | Yıllık | Sharpe | Maks. düşüş | En kötü gün | " +
              " | ".join(f"{w} → bugün yıllık / DD" for w in lv["windows"]) + " |",
              "|---|---|---|---|---|---|" + "---|" * len(lv["windows"])]
        for k, v in list(x["rows"].items()) + [("al-tut", x["bh"])]:
            fu = v["full"]
            if not fu:
                continue
            ws = " | ".join(f"{f(v['windows'][w].get('cagr'))} / {f(v['windows'][w].get('max_dd'))}" for w in lv["windows"])
            name = f"vol hedefi %{lv['vol_target']['target']*100:.0f} (ort. {v.get('avg_leverage')}x)" if k == "vt" else k
            L.append(f"| {name} | {fu['final_1000']:,.0f} | {f(fu['cagr'])} | {fu['sharpe']} | {f(fu['max_dd'])} | {f(fu['worst_day'])} | {ws} |")
        L.append("")
    L += ["## Zayıf yönler", "",
          "- Kaldıraç kenar yaratmaz; kârı ve zararı aynı oranda büyütür. Sharpe değişmez.",
          "- Geçmişteki en kötü düşüş, gelecekteki en kötü düşüş değildir. Seçilen kaldıraç bu yüzden bir üst sınırdır, hedef değil.",
          "- Vadeli işlem kontrat büyüklüğü hesaba katılmadı (küçük kasada mikro kontrat gerekir). Roll maliyeti modellenmedi.",
          "- Bu üç fikir binlerce aday içinden seçildi. Paper kayıt gerçek testtir."]
    return "\n".join(L) + "\n"


def daily(cfg: dict, synthetic: bool = False) -> tuple[dict, list[str]]:
    OUT.mkdir(parents=True, exist_ok=True)
    prev = json.loads((OUT / "state.json").read_text()) if (OUT / "state.json").exists() else {}
    levj = json.loads((OUT / f"leverage{suffix}.json").read_text()) if (OUT / f"leverage{suffix}.json").exists() else {"ideas": {}}
    start = pd.Timestamp(cfg["start"])
    panels, st, msgs = {}, {"date": date.today().isoformat(), "start": cfg["start"], "ideas": {}}, []
    for hid, idea in cfg["ideas"].items():
        p, pool, X, tr = idea_returns(idea, panels, synthetic)
        metrics.set_periods(p.ppy)
        last = X.index[-1]
        held = {a: round(float(X.loc[last, a]), 3) for a in X.columns if abs(X.loc[last, a]) > 1e-9}
        pick = (levj["ideas"].get(hid) or {}).get("pick") or 1
        sl = start_leverage(pick)
        fw = pool[pool.index >= start]
        tr_ok = tradable_assets() if cfg.get("tradable_only") else None
        tfw = None
        if tr_ok is not None:
            _, tpool, _, _ = idea_returns(idea, {}, synthetic, tr_ok)
            tfw = tpool[tpool.index >= start] if len(tpool) else pd.Series(dtype=float)
        rec = {"name": idea["name"], "bar": str(last.date()), "held": held, "leverage_pick": pick,
               "paper_1x": _st(fw) or {"final_1000": round(float(1000 * (1 + fw).prod()), 0) if len(fw) else 1000.0, "days": int(len(fw))},
               f"paper_{pick}x": _st(lever(fw, pick)) or {"final_1000": round(float(1000 * (1 + lever(fw, pick)).prod()), 0) if len(fw) else 1000.0},
               "start_leverage": sl,
               "paper_start": _st(lever(fw, sl)) or {"final_1000": round(float(1000 * (1 + lever(fw, sl)).prod()), 0) if len(fw) else 1000.0},
               "tradable_assets": None if tr_ok is None else sorted(a for a in X.columns if a in tr_ok),
               "paper_tradable_1x": None if tfw is None else (_st(tfw) or {"final_1000": round(float(1000 * (1 + tfw).prod()), 0) if len(tfw) else 1000.0})}
        old = ((prev.get("ideas") or {}).get(hid) or {}).get("held", {})
        if held != old:
            ch = [f"{a}: {old.get(a, 0):+.2f} → {held.get(a, 0):+.2f}" for a in sorted(set(held) | set(old)) if held.get(a, 0) != old.get(a, 0)]
            msgs.append(f"{hid} {idea['name']} ({last.date()}): " + "; ".join(ch))
        st["ideas"][hid] = rec
    (OUT / "state.json").write_text(json.dumps(st, indent=1, default=str))
    return st, msgs


def append_history(st: dict) -> Path:
    """One row per idea per run, kept forever (decisions/watch/history.csv). The owner can send this file by hand."""
    f = OUT / "history.csv"
    rows = []
    for hid, r in st["ideas"].items():
        pk = r["leverage_pick"]
        rows.append({"run_date": st["date"], "idea": hid, "bar": r["bar"],
                     "held": ";".join(f"{a}:{v:+.2f}" for a, v in r["held"].items()) or "cash",
                     "paper_1x_1000": r["paper_1x"].get("final_1000", 1000), "leverage": pk,
                     "paper_lev_1000": r.get(f"paper_{pk}x", {}).get("final_1000", 1000),
                     "start_leverage": r.get("start_leverage"), "paper_start_1000": (r.get("paper_start") or {}).get("final_1000", 1000),
                     "paper_tradable_1x_1000": (r.get("paper_tradable_1x") or {}).get("final_1000"),
                     "max_dd_1x": r["paper_1x"].get("max_dd"), "max_dd_lev": r.get(f"paper_{pk}x", {}).get("max_dd")})
    new = pd.DataFrame(rows)
    if f.exists():
        old = pd.read_csv(f)
        old = old[~((old["run_date"] == st["date"]) & old["idea"].isin(new["idea"]))]   # one row per idea per day
        new = pd.concat([old, new], ignore_index=True)
    new.to_csv(f, index=False)
    return f


def reminders(cfg: dict, today: date | None = None) -> list[str]:
    """Telegram reminders around each review date. Before: 7 days and 1 day ahead. After: every Monday until
    the review file decisions/watch/review_YYYY-MM.md exists (the scheduled review may fail or be forgotten)."""
    today = today or date.today()
    out = []
    for d in cfg.get("review", {}).get("dates", []):
        rd = date.fromisoformat(d)
        done = (OUT / f"review_{rd:%Y-%m}.md").exists()
        left = (rd - today).days
        if left in (7, 1):
            out.append(f"⏰ Hatırlatma: H063–H065 paper kontrolü {left} gün sonra ({d}). Zamanlanmış görev raporu yazacak.")
        elif left <= 0 and not done and (left == 0 or today.weekday() == 0):
            out.append(f"⚠️ {d} paper kontrolü YAPILMADI (decisions/watch/review_{rd:%Y-%m}.md yok). "
                       "Lütfen bana yaz: 'H063–H065 kontrolünü yap'. Sistem okuyamazsa decisions/watch/OZET.md ve history.csv dosyalarını bana gönder.")
    return out


def daily_markdown(st: dict) -> str:
    L = ["# Paper izleme: H063–H065", "", f"Başlangıç: {st['start']}. Son çalışma: {st['date']}. Sadece sanal para; emir gönderilmez.", "",
         "| Hipotez | Fikir | Son bar | Pozisyon (+1 = varlığın 1/N payı tam long, −1 = tam short) | Paper 1x $1000 → | Başlangıç kaldıraç | Paper başlangıç $1000 → | Seçilen (tavan) kaldıraç | Paper tavan $1000 → | Sadece işlenebilir varlıklar 1x |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for hid, r in st["ideas"].items():
        pos = ", ".join(f"{a} {v:+.2f}" for a, v in r["held"].items()) or "nakit"
        pk = r["leverage_pick"]
        tp = r.get("paper_tradable_1x")
        tps = "venues.json yok" if tp is None else f"{tp.get('final_1000', 1000):,.0f} ({', '.join(r.get('tradable_assets') or []) or 'hiçbiri'})"
        L.append(f"| {hid} | {r['name']} | {r['bar']} | {pos} | {r['paper_1x'].get('final_1000', 1000):,.0f} | {r.get('start_leverage')}x | "
                 f"{(r.get('paper_start') or {}).get('final_1000', 1000):,.0f} | {pk}x | {r.get(f'paper_{pk}x', {}).get('final_1000', 1000):,.0f} | {tps} |")
    L += ["", "Kontrol: 2027-01-22 (ara) ve 2027-04-22 (karar). Kural: `config/mega.yaml` baseline (rastgele giriş + al-tut).",
          "Tüm geçmiş kayıt: `decisions/watch/history.csv` (her gün bir satır). Kontrol yapılmazsa bu iki dosyayı (OZET.md, history.csv) Claude'a gönder."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["lev", "daily"])
    ap.add_argument("--synthetic", action="store_true"); ap.add_argument("--telegram", action="store_true")
    ap.add_argument("--cfg", default=None, help="other idea file; leverage output then goes to leverage_<stem>.json/md")
    x = ap.parse_args(argv)
    cfg = cfg_load(x.cfg)
    suffix = "" if not x.cfg else "_" + Path(x.cfg).stem.replace("watch_", "")
    OUT.mkdir(parents=True, exist_ok=True)
    if x.cmd == "lev":
        o = leverage(cfg, x.synthetic)
        (OUT / f"leverage{suffix}.json").write_text(json.dumps(o, indent=1, default=str))
        md = lev_markdown(o, cfg)
        (OUT / f"leverage{suffix}.md").write_text(md)
        print(md)
        if x.telegram:
            from run import telegram
            telegram(f"🏋️ {', '.join(o['ideas'])} kaldıraç testi\n" + "\n".join(
                f"{h} {v['name']}: seçilen {v['pick'] or 'yok'}x" +
                (f" → yıllık {v['rows'][str(v['pick']) + 'x']['full']['cagr']:+.0%}, DD {v['rows'][str(v['pick']) + 'x']['full']['max_dd']:+.0%}" if v["pick"] else "")
                for h, v in o["ideas"].items()) + "\n⚠️ Kaldıraç kenar yaratmaz; paper kayıt gerçek testtir.")
    else:
        st, msgs = daily(cfg, x.synthetic)
        md = daily_markdown(st)
        (OUT / "report.md").write_text(md)
        (OUT / "OZET.md").write_text(md)
        append_history(st)
        print(md)
        rem = reminders(cfg)
        if x.telegram and rem:
            from run import telegram
            telegram("\n".join(rem))
        if x.telegram and (msgs or date.today().weekday() == 4):
            from run import telegram
            body = "\n".join(msgs) if msgs else "Pozisyon değişikliği yok."
            summ = "\n".join(f"{h}: 1x ${r['paper_1x'].get('final_1000', 1000):,.0f} | {r['leverage_pick']}x "
                             f"${r.get('paper_' + str(r['leverage_pick']) + 'x', {}).get('final_1000', 1000):,.0f}" for h, r in st["ideas"].items())
            telegram("👀 Paper izleme (H063–H065, sanal para)\n" + body + "\n" + summ)


if __name__ == "__main__":
    main()
