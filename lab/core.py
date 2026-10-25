"""Core study: simple, literature-based crypto rules with FIXED settings (config/core.yaml).

No parameter search and no selection: every rule runs once with its textbook setting, so the number of
trials is tiny (rules x 3 books) and the Deflated Sharpe penalty is small. Rules are evaluated on the full
history and on each forward window after the time-machine cutoffs (the rules never change, so a forward
window is simply "after that date"). Acceptance (written before results): see config/core.yaml.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lab import metrics, perp, regime

CRISES_KEY = "crypto"


def _bars(days, ppy):
    return regime.bars(days, ppy)


def exposure(close: pd.Series, rule: str, prm: dict, ppy: float) -> pd.Series:
    """Target exposure in [0, 1] decided at the close of each bar (used from the next bar)."""
    r = close.pct_change(fill_method=None)
    one = pd.Series(1.0, index=close.index)
    if rule == "buy_hold":
        e = one
    elif rule == "vol_target":
        e = _vt(r, prm, ppy)
    elif rule == "trend_sma200":
        e = (close > close.rolling(_bars(prm["sma_days"], ppy), min_periods=_bars(prm["sma_days"], ppy)).mean()).astype(float)
    elif rule == "tsmom":
        e = _tsmom(close, prm, ppy)
    elif rule == "tsmom_vt":
        e = _tsmom(close, prm, ppy) * _vt(r, prm, ppy)
    elif rule == "dual_trend_vt":
        n = _bars(prm["sma_days"], ppy)
        up = (close > close.rolling(n, min_periods=n).mean()).astype(float)
        e = up * (_tsmom(close, prm, ppy) > 0).astype(float) * _vt(r, prm, ppy)
    elif rule == "dual_trend_vt_ls":   # long as dual_trend_vt; SHORT only when below SMA200 AND every horizon is negative
        n = _bars(prm["sma_days"], ppy)
        sma = close.rolling(n, min_periods=n).mean()
        ts = _tsmom(close, prm, ppy)
        side = ((close > sma) & (ts > 0)).astype(float) - ((close < sma) & (ts == 0) & sma.notna()).astype(float)
        e = side * _vt(r, prm, ppy)
        return e.where(close.notna()).fillna(0.0).clip(-1, 1)
    else:
        raise ValueError(rule)
    return e.where(close.notna()).fillna(0.0).clip(0, 1)


def apply_band(e: pd.Series, band: float) -> pd.Series:
    """No-trade band: keep the current position until the target moves more than `band` away from it."""
    if not band:
        return e
    v = e.to_numpy()
    out = np.empty_like(v)
    cur = 0.0
    for i, t in enumerate(v):
        if abs(t - cur) > band or (t == 0.0 and cur != 0.0):
            cur = t
        out[i] = cur
    return pd.Series(out, e.index)


def _vt(r, prm, ppy):
    look = _bars(prm.get("lookback_days", 30), ppy)
    vol = r.rolling(look, min_periods=look // 2).std() * math.sqrt(ppy)
    return (prm.get("target", 0.4) / vol).clip(upper=1.0).fillna(0.0)


def _tsmom(close, prm, ppy):
    sig = [(close / close.shift(_bars(h, ppy)) - 1 > 0).astype(float) for h in prm["horizons_days"]]
    return sum(sig) / len(sig)


def book_returns(closes: dict, rule: str, prm: dict, ppy: float, cps: float, band: float = 0.0,
                 funding_annual: float = 0.0) -> pd.Series:
    """Equal capital across the assets in `closes`; each asset follows the rule; costs on exposure changes;
    optional no-trade band and perp funding on |exposure|. Assets join the book when their data starts."""
    parts = []
    for _, c in closes.items():
        e = apply_band(exposure(c, rule, prm, ppy), band).shift(1).fillna(0.0)   # decided at t-1, held during t
        r = c.pct_change(fill_method=None).fillna(0.0)
        parts.append(e * r - e.diff().abs().fillna(e.abs()) * cps - e.abs() * funding_annual / ppy)
    alive = sum(c.notna().astype(float) for c in closes.values()).replace(0, np.nan)
    out = (sum(parts) / alive).fillna(0.0)            # equal capital across the coins that exist at t
    first = min(c.first_valid_index() for c in closes.values())
    return out[out.index >= first]


def book_exposure(closes: dict, rule: str, prm: dict, ppy: float, band: float = 0.0) -> pd.Series:
    ex = [apply_band(exposure(c, rule, prm, ppy), band).shift(1).fillna(0.0) for c in closes.values()]
    return sum(ex) / len(ex)


def stats(r: pd.Series, ppy: float) -> dict:
    metrics.set_periods(ppy)
    r = r.dropna()
    if len(r) < 30:
        return {}
    yr = (1 + r).groupby(r.index.year).prod() - 1
    return {"start": str(r.index[0].date()), "final_1000": round(1000 * float((1 + r).prod()), 0),
            "cagr": round(metrics.cagr(r), 4), "sharpe": round(metrics.sharpe(r), 2),
            "max_dd": round(metrics.max_drawdown(r), 4), "worst_year": round(float(yr.min()), 4),
            "yearly": {str(k): round(float(v), 4) for k, v in yr.items()}}


def run(p, cfg: dict) -> dict:
    from lab import protect
    ppy = p.ppy
    cps = cfg["costs"]["commission"] + cfg["costs"]["slippage"]
    assets = [a for a in cfg["universe_assets"] if a in p.columns]
    books = {a.split("/")[0]: {a: p.c[a]} for a in assets}
    if len(assets) >= 2:
        books["BTC+ETH"] = {a: p.c[a] for a in assets}
    crises = protect.load_cfg(CRISES_KEY)["crises"]
    acc = cfg.get("accept", {})
    rows, series = [], {}
    for bname, closes in books.items():
        for rule, prm in cfg["rules"].items():
            r = book_returns(closes, rule, prm or {}, ppy, cps)
            series[(bname, rule)] = r
            row = {"book": bname, "rule": rule, "full": stats(r, ppy), "crises": protect.crisis_table(r, crises),
                   "windows": {c: stats(r[r.index > pd.Timestamp(c)], ppy) for c in cfg["cutoffs"]}}
            rows.append(row)
    # acceptance vs buy-and-hold of the same book, in every forward window
    n_trials = len(rows)
    srs = [series[k].mean() / series[k].std() for k in series if series[k].std() > 0]
    for row in rows:
        bh = next(x for x in rows if x["book"] == row["book"] and x["rule"] == "buy_hold")
        row["dsr"] = round(metrics.dsr(series[(row["book"], row["rule"])], n_trials, srs), 3)
        if row["rule"] == "buy_hold":
            row["approved"] = None
            continue
        chk = {}
        for c in cfg["cutoffs"]:
            w, b = row["windows"].get(c) or {}, bh["windows"].get(c) or {}
            if not w or not b:
                chk[c] = False
                continue
            dd_ok = w["max_dd"] >= b["max_dd"] * (1 - acc.get("dd_reduction_vs_buyhold", 0.33))
            sr_ok = w["sharpe"] >= b["sharpe"] - acc.get("max_sharpe_gap", 0.10)
            ret_ok = (w["final_1000"] > 1000) if acc.get("positive_return", True) else True
            chk[c] = {"dd": dd_ok, "sharpe": sr_ok, "ret": ret_ok}
        row["checks"] = chk
        row["approved"] = all(isinstance(v, dict) and all(v.values()) for v in chk.values())
    return {"timeframe": p.freq, "data_end": str(p.index[-1]), "n_trials": n_trials, "rows": rows,
            "spark": {f"{b}|{r}": perp.sparkline(s, 120) for (b, r), s in series.items()}}


NAMES = {"buy_hold": "Al-tut", "vol_target": "Volatilite hedefi %40", "trend_sma200": "Trend (SMA200)",
         "tsmom": "Zaman serisi momentumu (30/90/180g)", "tsmom_vt": "Momentum + vol hedefi",
         "dual_trend_vt": "SMA200 + momentum + vol hedefi"}


def markdown(o: dict, cfg: dict) -> str:
    f = lambda v: "–" if v is None else f"{v:+.0%}"   # noqa: E731
    cut = cfg["cutoffs"]
    L = [f"# Çekirdek çalışma — {o['timeframe']}", "",
         f"Sabit ayarlı {len(cfg['rules'])} kural × {len({r['book'] for r in o['rows']})} portföy = **{o['n_trials']} deneme** "
         "(ayar taraması yok). Kabul kuralları sonuçlardan önce yazıldı (`config/core.yaml`): her ileri pencerede aynı "
         "varlığın al-tutuna göre düşüş ≥ 1/3 az, Sharpe en fazla 0.10 düşük, getiri pozitif.", ""]
    for book in dict.fromkeys(r["book"] for r in o["rows"]):
        L += [f"## {book}", "", "| Kural | Tüm geçmiş $1000 → | Yıllık | Sharpe | Maks. düşüş | "
              + " | ".join(f"{c[:7]} → $" for c in cut) + " | " + " | ".join(f"{c[:7]} DD" for c in cut) + " | Onay |",
              "|---|---|---|---|---|" + "---|" * (2 * len(cut)) + "---|"]
        for r in [x for x in o["rows"] if x["book"] == book]:
            fu, w = r["full"], r["windows"]
            ap = "–" if r["approved"] is None else ("✅" if r["approved"] else "❌")
            L.append(f"| {NAMES.get(r['rule'], r['rule'])} | {fu.get('final_1000', 0):,.0f} | {f(fu.get('cagr'))} | {fu.get('sharpe')} | "
                     f"{f(fu.get('max_dd'))} | " + " | ".join(f"{(w.get(c) or {}).get('final_1000', 0):,.0f}" for c in cut) + " | "
                     + " | ".join(f(((w.get(c) or {}).get('max_dd'))) for c in cut) + f" | {ap} |")
        L.append("")
    L += ["## Zayıf yönler", "",
          "- Kurallar literatürden; ama kriptoda bu literatür kısa (2014 sonrası). Ayarlar (200 gün, 30/90/180 gün, %40) standart değerlerdir, kriptoya göre seçilmedi.",
          "- Sadece BTC/ETH: alt-coin getirisi yok; buna karşılık survivorship riski çok düşük.",
          "- Spot varsayımı: perp ile yapılırsa funding maliyeti eklenir.",
          "- Üç ileri pencere iç içedir (2022 penceresi 2023 ve 2024'ü de içerir); bağımsız üç test değildir."]
    return "\n".join(L)


def run_variants(cfg: dict, panel_of) -> dict:
    """Compare the pre-registered variants with the H052 baseline (config core.yaml `variants`)."""
    vc = cfg["variants"]
    cps = cfg["costs"]["commission"] + cfg["costs"]["slippage"]
    fa = vc.get("funding_annual", 0.0)
    prm = cfg["rules"]["dual_trend_vt"]
    acc = vc.get("accept", {})
    base_cache, rows = {}, []

    def series(v):
        p = panel_of(v["timeframe"], v["assets"])
        closes = {a: p.c[a] for a in v["assets"] if a in p.columns}
        return book_returns(closes, v["rule"], prm, p.ppy, cps, v.get("band", 0.0), fa), p.ppy

    def evaluate(r, ppy):
        return {"full": stats(r, ppy), "windows": {c: stats(r[r.index > pd.Timestamp(c)], ppy) for c in cfg["cutoffs"]}}

    for v in vc["list"]:
        b = vc["baseline"]                  # always H052 as registered (4h): the 1h variant is judged against it
        if b["timeframe"] not in base_cache:
            rb, ppb = series(b)
            base_cache[b["timeframe"]] = (rb, ppb, evaluate(rb, ppb))
        rb, ppb, eb = base_cache[b["timeframe"]]
        try:
            rv, ppv = series(v)
        except Exception as e:  # noqa: BLE001
            rows.append({**v, "error": str(e)})
            continue
        # compare on the common period only
        start = max(rv.index[0], rb.index[0])
        ev = evaluate(rv[rv.index >= start], ppv)
        eb2 = evaluate(rb[rb.index >= start], ppb)
        sr_ok = ev["full"].get("sharpe", -9) > eb2["full"].get("sharpe", 9) and all(
            (ev["windows"].get(c) or {}).get("sharpe", -9) > (eb2["windows"].get(c) or {}).get("sharpe", 9) for c in cfg["cutoffs"])
        dd_ok = ev["full"].get("max_dd", -1) >= eb2["full"].get("max_dd", 0) - acc.get("max_extra_dd", 0.05)
        rows.append({**v, "variant": ev, "baseline": eb2, "sharpe_ok": bool(sr_ok), "dd_ok": bool(dd_ok),
                     "approved": bool(sr_ok and dd_ok)})
    return {"rows": rows}


def markdown_variants(o: dict, cfg: dict) -> str:
    f = lambda v: "–" if v is None else f"{v:+.0%}"   # noqa: E731
    cut = cfg["cutoffs"]
    L = ["", "## H052 varyantları (4 deneme, kabul kuralları önceden yazıldı)", "",
         "Kabul: tüm geçmişte VE her ileri pencerede Sharpe temel kuraldan (H052) yüksek, maks. düşüş en fazla 5 puan derin. "
         "Karşılaştırma aynı zaman diliminde ve ortak dönemde; perp funding her ikisinde de düşüldü.", "",
         "| Varyant | Sharpe (tüm) | Temel | Maks. düşüş | Temel | " + " | ".join(f"{c[:7]} SR v/t" for c in cut) + " | Onay |",
         "|---|---|---|---|---|" + "---|" * len(cut) + "---|"]
    for r in o["rows"]:
        if r.get("error"):
            L.append(f"| {r['name']} | hata: {r['error'][:60]} |" + " |" * (4 + len(cut) + 1))
            continue
        v, b = r["variant"], r["baseline"]
        L.append(f"| {r['name']} | {v['full'].get('sharpe')} | {b['full'].get('sharpe')} | {f(v['full'].get('max_dd'))} | "
                 f"{f(b['full'].get('max_dd'))} | " + " | ".join(
                     f"{(v['windows'].get(c) or {}).get('sharpe')}/{(b['windows'].get(c) or {}).get('sharpe')}" for c in cut)
                 + f" | {'✅' if r['approved'] else '❌'} |")
    return "\n".join(L)


def run_risk_levels(cfg: dict, panel_of) -> dict:
    rl = cfg["risk_levels"]
    cps = cfg["costs"]["commission"] + cfg["costs"]["slippage"]
    fa = cfg["variants"].get("funding_annual", 0.0)
    p = panel_of("4h", ["BTC/USDT", "ETH/USDT"])
    closes = {a: p.c[a] for a in ["BTC/USDT", "ETH/USDT"] if a in p.columns}
    rows, series = [], {}
    for t in rl["targets"]:
        prm = {**cfg["rules"]["dual_trend_vt"], "target": t}
        r = book_returns(closes, "dual_trend_vt", prm, p.ppy, cps, rl.get("band", 0.10), fa)
        series[t] = r
        w = {c: stats(r[r.index > pd.Timestamp(c)], p.ppy) for c in cfg["cutoffs"]}
        f = stats(r, p.ppy)
        ok = f.get("max_dd", -1) >= rl["max_dd_floor"] and all((w[c] or {}).get("max_dd", -1) >= rl["max_dd_floor"] for c in w)
        rows.append({"target": t, "full": f, "windows": w, "within_floor": bool(ok)})
    allowed = [r["target"] for r in rows if r["within_floor"]]
    return {"rows": rows, "chosen": max(allowed) if allowed else None, "series": series}


def run_funding(cfg: dict, h054_daily: pd.Series | None) -> dict:
    from lab import funding as F
    fc = cfg["funding_arb"]
    daily = {}
    for sym in fc["assets"]:
        try:
            daily[sym] = F.daily_funding(F.load(sym, fc.get("start", "2020-01")))
        except Exception as e:  # noqa: BLE001
            print(f"[funding] {sym} failed: {e}")
    if not daily:
        return {"error": "no funding data"}
    rows = []
    for rule, prm in fc["rules"].items():
        books = [F.book(d, rule, prm or {}, fc["hedge_share"], fc["cost_per_leg"]) for d in daily.values()]
        r = F.combine(books)
        row = {"rule": rule, "full": F.stats(r), "windows": {c: F.stats(r[r.index > pd.Timestamp(c)]) for c in cfg["cutoffs"]}}
        if h054_daily is not None:
            h = h054_daily.reindex(r.index).dropna()
            rr = r.reindex(h.index).fillna(0.0)
            combo = 0.5 * h + 0.5 * rr
            row["corr_with_h054"] = round(float(np.corrcoef(h, rr)[0, 1]), 3) if len(h) > 30 else None
            row["combo"] = {"full": F.stats(combo), "windows": {c: F.stats(combo[combo.index > pd.Timestamp(c)]) for c in cfg["cutoffs"]}}
            row["h054"] = {"full": F.stats(h), "windows": {c: F.stats(h[h.index > pd.Timestamp(c)]) for c in cfg["cutoffs"]}}
        acc = fc.get("accept", {})
        ok = True
        for c in cfg["cutoffs"]:
            w = row["windows"].get(c) or {}
            ok &= bool(w) and (w.get("final_1000", 0) > 1000 or not acc.get("positive_return", True))
            ok &= w.get("max_dd", -1) >= acc.get("max_dd_floor", -0.05)
            if acc.get("combo_beats_h054_sharpe", True) and row.get("combo"):
                ok &= (row["combo"]["windows"].get(c) or {}).get("sharpe", -9) > (row["h054"]["windows"].get(c) or {}).get("sharpe", 9)
        row["approved"] = bool(ok)
        rows.append(row)
    return {"rows": rows, "data": {k: [str(v.index[0].date()), str(v.index[-1].date())] for k, v in daily.items()}}


def markdown_risk_funding(rl: dict, fu: dict, cfg: dict) -> str:
    f = lambda v: "–" if v is None else f"{v:+.0%}"   # noqa: E731
    cut = cfg["cutoffs"]
    L = ["", "## H054 risk seviyeleri (kaldıraç yok; seçim kuralı önceden yazıldı)", "",
         f"Kural: tüm geçmişte ve her ileri pencerede maks. düşüş ≥ {cfg['risk_levels']['max_dd_floor']:.0%} kalan EN YÜKSEK hedef.", "",
         "| Vol hedefi | $1000 → | Yıllık | Sharpe | Maks. düşüş | " + " | ".join(f"{c[:7]} → $ / DD" for c in cut) + " | Sınırda |",
         "|---|---|---|---|---|" + "---|" * len(cut) + "---|"]
    for r in rl["rows"]:
        fu_ = r["full"]
        L.append(f"| %{r['target'] * 100:.0f} | {fu_.get('final_1000', 0):,.0f} | {f(fu_.get('cagr'))} | {fu_.get('sharpe')} | {f(fu_.get('max_dd'))} | "
                 + " | ".join(f"{(r['windows'].get(c) or {}).get('final_1000', 0):,.0f} / {f((r['windows'].get(c) or {}).get('max_dd'))}" for c in cut)
                 + f" | {'✅' if r['within_floor'] else '❌'} |")
    L.append(f"\n**Seçilen:** {'%' + format(rl['chosen'] * 100, '.0f') if rl.get('chosen') else 'hiçbiri'}")
    L += ["", "## Funding arbitrajı (spot long + perp short)", ""]
    if fu.get("error"):
        L.append(f"Veri alınamadı: {fu['error']}")
        return "\n".join(L)
    L.append(f"Veri (Binance, Bitget için vekil): {fu.get('data')}")
    L += ["", "| Kural | $1000 → | Yıllık | Sharpe | Maks. düşüş | H054 ile korelasyon | 50/50 H054+arb Sharpe | H054 Sharpe | Onay |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in fu["rows"]:
        fu_ = r["full"]
        L.append(f"| {r['rule']} | {fu_.get('final_1000', 0):,.0f} | {f(fu_.get('cagr'))} | {fu_.get('sharpe')} | {f(fu_.get('max_dd'))} | "
                 f"{r.get('corr_with_h054')} | {(r.get('combo') or {}).get('full', {}).get('sharpe')} | {(r.get('h054') or {}).get('full', {}).get('sharpe')} | "
                 f"{'✅' if r['approved'] else '❌'} |")
        for c in cut:
            w, cw, hw = r["windows"].get(c) or {}, (r.get("combo") or {}).get("windows", {}).get(c) or {}, (r.get("h054") or {}).get("windows", {}).get(c) or {}
            L.append(f"|  ↳ {c[:7]} → | {w.get('final_1000', 0):,.0f} | {f(w.get('cagr'))} | {w.get('sharpe')} | {f(w.get('max_dd'))} | | "
                     f"{cw.get('sharpe')} (DD {f(cw.get('max_dd'))}) | {hw.get('sharpe')} (DD {f(hw.get('max_dd'))}) | |")
    L += ["", "Sınırlar: spot–perp baz farkı ve Binance/Bitget farkı modellenmez; büyük yükselişte short perp için marjin eklemek gerekir."]
    return "\n".join(L)


def run_idle_arb(cfg: dict, panel_of) -> dict:
    """H054 + funding arbitrage on the cash H054 leaves idle. Daily bookkeeping."""
    from lab import funding as F
    ic, fc, rl = cfg["idle_arb"], cfg["funding_arb"], cfg["risk_levels"]
    cps = cfg["costs"]["commission"] + cfg["costs"]["slippage"]
    fa = cfg["variants"].get("funding_annual", 0.0)
    prm = cfg["rules"]["dual_trend_vt"]
    band = rl.get("band", 0.10)
    p = panel_of("4h", ["BTC/USDT", "ETH/USDT"])
    closes = {a: p.c[a] for a in ["BTC/USDT", "ETH/USDT"] if a in p.columns}
    h = book_returns(closes, "dual_trend_vt", prm, p.ppy, cps, band, fa)
    ex = book_exposure(closes, "dual_trend_vt", prm, p.ppy, band)
    h_d = (1 + h).groupby(h.index.normalize()).prod() - 1
    idle = (1 - ex.groupby(ex.index.normalize()).mean()).clip(0, 1)
    daily = {}
    for sym in fc["assets"]:
        try:
            daily[sym] = F.daily_funding(F.load(sym, fc.get("start", "2020-01")))
        except Exception as e:  # noqa: BLE001
            print(f"[idle_arb] {sym}: {e}")
    if not daily:
        return {"error": "no funding data"}
    fund = pd.concat(daily.values(), axis=1).mean(axis=1)          # equal BTC/ETH hedge
    idx = h_d.index.intersection(fund.index)
    h_d, fund, idle_ = h_d.reindex(idx), fund.reindex(idx), idle.reindex(idx).fillna(0)
    rows = [{"name": "H054 tek başına", "id": "h054", "r": h_d}]
    for rule in ic["rules"]:
        on = F.book(fund, rule, fc["rules"].get(rule) or {}, 1.0, 0.0) / 1.0   # funding earned per unit hedged
        on_flag = (on != 0).astype(float) if rule != "always_on" else pd.Series(1.0, index=idx)
        if rule == "positive_only":   # recompute the on/off state to size the hedge
            ann = fund.rolling(fc["rules"][rule].get("lookback_days", 3), min_periods=1).mean() * 365
            st, cur = [], 0.0
            for v in ann.to_numpy():
                if cur == 0 and v > fc["rules"][rule].get("enter_ann", 0.10):
                    cur = 1.0
                elif cur == 1 and v < fc["rules"][rule].get("exit_ann", 0.0):
                    cur = 0.0
                st.append(cur)
            on_flag = pd.Series(st, index=idx).shift(1).fillna(0.0)
        hedge = (idle_.shift(1).fillna(0) * ic["hedge_share"] * on_flag)          # notional / capital, decided at t-1
        cost = hedge.diff().abs().fillna(hedge) * 2 * fc["cost_per_leg"]          # spot + perp resize
        r = h_d + hedge * fund - cost
        rows.append({"name": f"H054 + boştaki nakitle arbitraj ({rule})", "id": f"idle_{rule}", "r": r,
                     "avg_hedge": round(float(hedge.mean()), 3)})
    out, base = [], rows[0]["r"]
    for row in rows:
        r = row.pop("r")
        row["full"] = F.stats(r)
        row["windows"] = {c: F.stats(r[r.index > pd.Timestamp(c)]) for c in cfg["cutoffs"]}
        if row["id"] != "h054":
            ok = True
            for c in cfg["cutoffs"]:
                w, b = row["windows"][c] or {}, (out[0]["windows"][c] or {})
                ok &= w.get("final_1000", 0) > b.get("final_1000", 0)
                ok &= w.get("max_dd", -1) >= b.get("max_dd", 0) - ic.get("max_extra_dd", 0.03)
            row["approved"] = bool(ok)
        out.append(row)
    acc = [r for r in out if r.get("approved")]
    best = max(acc, key=lambda r: sum((r["windows"][c] or {}).get("final_1000", 0) for c in cfg["cutoffs"])) if acc else out[0]
    return {"rows": out, "chosen": best["id"], "avg_idle": round(float(idle_.mean()), 3)}


def markdown_idle(o: dict, cfg: dict) -> str:
    f = lambda v: "–" if v is None else f"{v:+.0%}"   # noqa: E731
    cut = cfg["cutoffs"]
    if o.get("error"):
        return f"\n## Boştaki nakitle arbitraj\n\nVeri yok: {o['error']}"
    L = ["", "## Boştaki nakitle funding arbitrajı (kriter: ileri dönemlerde en yüksek kâr)", "",
         f"H054'ün ortalama boştaki nakdi: %{o['avg_idle'] * 100:.0f}. Kabul: her ileri pencerede H054'ten fazla kazanmalı, "
         "düşüşü en fazla 3 puan derin olmalı. Kabul edilenlerden ileri dönemlerde en çok kazanan seçilir.", "",
         "| Seçenek | Tüm geçmiş → | Yıllık | Maks. düşüş | " + " | ".join(f"{c[:7]} →" for c in cut) + " | Onay |",
         "|---|---|---|---|" + "---|" * len(cut) + "---|"]
    for r in o["rows"]:
        fu = r["full"]
        ap = "–" if "approved" not in r else ("✅" if r["approved"] else "❌")
        L.append(f"| {r['name']} | {fu.get('final_1000', 0):,.0f} | {f(fu.get('cagr'))} | {f(fu.get('max_dd'))} | "
                 + " | ".join(f"{(r['windows'][c] or {}).get('final_1000', 0):,.0f}" for c in cut) + f" | {ap} |")
    L.append(f"\n**Bot için seçilen:** `{o['chosen']}`")
    return "\n".join(L)
