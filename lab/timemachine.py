"""Time-machine test: replay the whole arena pipeline as if today were `cutoff`, then measure what the
frozen choices did AFTER the cutoff (data the choices never saw).

  1. Panel truncated at the cutoff -> screening funnel (stage 1 + stage 2, same thresholds as today).
  2. Roster built from that funnel (active = survivors, control = near-misses), join date = cutoff.
  3. Books (A / B / B2 / C / C2 from config) frozen at the cutoff, from the ACTIVE members of that day.
  4. The full panel is used only to compute what those frozen strategies did after the cutoff.
     Everything is causal, so a strategy's signals up to the cutoff are identical on both panels.
  5. Arena retirement rules are replayed month by month after the cutoff (retired share -> cash).
Outputs: per book backtest (<= cutoff) vs forward (> cutoff), expected-range band status, yearly
returns; active vs control members after the cutoff (does the funnel add value?); BTC buy-and-hold.

Honest limit: the thresholds were written in 2026 by someone who has seen 2024-2026; the funnel
itself never sees data after the cutoff, but the researcher did. Treat it as a strong, not a perfect test.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import replace

import numpy as np
import pandas as pd

from lab import arena, books, metrics, perp, screen
from lab.engine import Costs
from lab.panel import Panel


def truncate(p: Panel, cutoff: pd.Timestamp) -> Panel:
    def cut(x):
        return None if x is None else x.loc[:cutoff]
    q = replace(p, o=cut(p.o), h=cut(p.h), l=cut(p.l), c=cut(p.c), v=cut(p.v), bench=cut(p.bench),
                rf_annual=cut(p.rf_annual), fx=cut(p.fx), member=cut(p.member))
    q.macro = {k: cut(v) for k, v in (p.macro or {}).items()}
    q.fund = {k: cut(v) for k, v in (p.fund or {}).items()}
    q.extra = {k: (cut(v) if isinstance(v, (pd.DataFrame, pd.Series)) else v) for k, v in (p.extra or {}).items()}
    q.freq, q.market, q.costs_meta = p.freq, p.market, p.costs_meta
    return q


def replay_retirement(ro: dict, R: pd.DataFrame, cutoff: pd.Timestamp, cfg: dict) -> None:
    """Apply the arena retirement rules after the cutoff, checked at every month end."""
    rc = cfg.get("arena", {}).get("retire", {})
    months = pd.date_range(cutoff, R.index[-1], freq="ME")
    for m in ro["members"]:
        if m["status"] != "active" or m["id"] not in R.columns:
            continue
        r = R[m["id"]].dropna()
        bt_dd = (m.get("backtest") or {}).get("max_dd") or -0.2
        for t in months:
            f = r[(r.index > cutoff) & (r.index <= t)]
            if len(f) < 20:
                continue
            days = (t - cutoff).days
            why = None
            if metrics.max_drawdown(f) < rc.get("dd_mult", 1.5) * bt_dd:
                why = f"ileri düşüş {metrics.max_drawdown(f):.0%} < {rc.get('dd_mult', 1.5)}× backtest"
            elif days >= rc.get("min_forward_days", 120) and metrics.sharpe(f) < rc.get("min_forward_sharpe", 0.0):
                why = f"{days} gün sonra ileri Sharpe {metrics.sharpe(f):.2f}"
            if why:
                m.update(status="retired", retired_at=t.tz_localize("UTC").isoformat(), why=why)
                break


def _stats(r: pd.Series, ppy: float) -> dict:
    metrics.set_periods(ppy)
    r = r.dropna()
    if len(r) < 10:
        return {}
    yr = (1 + r).groupby(r.index.year).prod() - 1
    return {"start": str(r.index[0].date()), "end": str(r.index[-1].date()),
            "final_1000": round(1000 * float((1 + r).prod()), 0), "ret": round(float((1 + r).prod() - 1), 4),
            "cagr": round(metrics.cagr(r), 4), "sharpe": round(metrics.sharpe(r), 2),
            "max_dd": round(metrics.max_drawdown(r), 4),
            "yearly": {str(k): round(float(v), 4) for k, v in yr.items()}}


def run(p_full: Panel, costs: Costs, cfg: dict, cutoff: str) -> dict:
    T = pd.Timestamp(cutoff)
    tf = cfg["timeframe"]
    arena.use(f"timemachine/{T.date()}/{cfg.get('key', tf)}")
    if arena.DIR.exists():
        shutil.rmtree(arena.DIR)                 # always a fresh replay
    arena.DIR.mkdir(parents=True, exist_ok=True)
    tiso = T.tz_localize("UTC").isoformat()
    ppy = p_full.ppy

    # 1-2) funnel and roster on data up to the cutoff only
    p_cut = truncate(p_full, T)
    res = screen.run(p_cut, costs, cfg)
    if res.get("error"):
        return {"error": res["error"]}
    ro, note = arena.update_roster(res, cfg)
    for m in ro["members"]:
        m["added_at"] = tiso
    ro["created_at"] = tiso
    # 3) books frozen AT the cutoff (all survivors still active then)
    path = arena.DIR / "books.json"
    bdata = books.ensure(path, ro, cfg)
    for b in bdata["books"].values():
        b["created_at"] = tiso
    path.write_text(json.dumps(bdata, indent=1, ensure_ascii=False))
    # 4) what the frozen strategies did on the full panel
    R, X, _ = arena.compute(ro, p_full, costs)
    # 5) retirement replay after the cutoff (a retired member's share goes to cash)
    replay_retirement(ro, R, T, cfg)
    arena._write(arena.ROSTER, ro)
    cps = costs.per_turnover
    mmr = cfg.get("books", {}).get("maint_margin", 0.005)
    out_books = []
    for bid, b in bdata["books"].items():
        r = books.returns(b, R, X, ro, p_full, cps, mmr)
        bt = r[r.index <= T]
        bt = bt[bt.ne(0).cummax()]
        fw = r[r.index > T]
        band = books.expected_band(bt, days=min(730, max(7, (r.index[-1] - T).days)))
        out_books.append({"id": bid, "name": b["name"], "members": b["members"],
                          "backtest": _stats(bt, ppy), "forward": _stats(fw, ppy),
                          "band_status": books.band_status(band, (r.index[-1] - T).days,
                                                           float((1 + fw).prod() - 1)) if len(fw) else {},
                          "spark_fwd": perp.sparkline(fw, 90)})
    # active vs control after the cutoff (equal weight, 1x): does the funnel add value?
    def ew(ids):
        ids = [i for i in ids if i in R.columns]
        if not ids:
            return pd.Series(dtype=float)
        return R[ids].loc[R.index > T].fillna(0).mean(axis=1)
    act = [m["id"] for m in ro["members"] if m["status"] in ("active", "retired") and m.get("backtest", {}).get("stage") == "OK"]
    ctl = [m["id"] for m in ro["members"] if m["status"] == "control"]
    per_member = []
    for m in ro["members"]:
        if m["id"] not in R.columns:
            continue
        f = R[m["id"]][R.index > T].dropna()
        per_member.append({"id": m["id"], "coin": m["coin"], "rule": m["rule"],
                           "group": "aktif" if m["id"] in act else "kontrol",
                           "status": m["status"], "fwd_ret": round(float((1 + f).prod() - 1), 4) if len(f) else 0.0,
                           "fwd_sharpe": round(metrics.sharpe(f), 2) if len(f) > 20 else None,
                           "bt_sharpe": (m.get("backtest") or {}).get("sharpe")})
    pm = pd.DataFrame(per_member)
    groups = {}
    for g, ids in (("aktif", act), ("kontrol", ctl)):
        s = _stats(ew(ids), ppy)
        sub = pm[pm["group"] == g] if len(pm) else pm
        s.update({"n": len(ids), "share_profitable": round(float((sub["fwd_ret"] > 0).mean()), 3) if len(sub) else None,
                  "median_fwd_sharpe": round(float(sub["fwd_sharpe"].dropna().median()), 2) if len(sub) else None})
        groups[g] = s
    corr = None
    if len(pm) > 5 and pm["fwd_sharpe"].notna().sum() > 5:
        corr = round(float(pm[["bt_sharpe", "fwd_sharpe"]].dropna().corr(method="spearman").iloc[0, 1]), 3)
    btc = p_full.c["BTC/USDT"] if "BTC/USDT" in p_full.columns else p_full.bench
    btc_fwd = _stats(btc.pct_change(fill_method=None).fillna(0)[btc.index > T], ppy) if btc is not None else {}
    out = {"cutoff": str(T.date()), "timeframe": tf, "data_end": str(p_full.index[-1]),
           "funnel": res["funnel"], "funnel2": res.get("funnel2"), "stage2": res.get("stage2"),
           "n_trials": res["n_trials"], "coins_ok": len(res["coins"]), "note": note,
           "retired_after_cutoff": sum(1 for m in ro["members"] if m["status"] == "retired"),
           "books": out_books, "groups": groups, "rank_corr_bt_vs_fwd": corr, "btc_fwd": btc_fwd,
           "top_members": sorted(per_member, key=lambda x: -(x["fwd_ret"] or 0))[:10],
           "worst_members": sorted(per_member, key=lambda x: (x["fwd_ret"] or 0))[:5]}
    arena._write(arena.DIR / "summary.json", out)
    return out


def markdown(o: dict) -> str:
    f = lambda v: "–" if v is None else f"{v:+.0%}"   # noqa: E731
    L = [f"# Zaman makinesi testi — {o['timeframe']}, kesim {o['cutoff']}", "",
         f"Her seçim **sadece {o['cutoff']}'e kadarki veriyle** yapıldı (eleme {o['n_trials']} deneme, "
         f"{o['coins_ok']} coin). Sonra donmuş seçimlerin {o['cutoff']} → {o['data_end'][:10]} arası gerçek sonucu ölçüldü. "
         f"Kesimden sonra emekliye ayrılan üye: {o['retired_after_cutoff']}.", "",
         "## Portföyler: backtest (kesime kadar) ↔ ileri (kesimden sonra)", "",
         "| Portföy | Backtest yıllık | Backtest DD | **İleri: $1000 →** | İleri yıllık | İleri Sharpe | İleri maks. düşüş | Bant |",
         "|---|---|---|---|---|---|---|---|"]
    for b in o["books"]:
        bt, fw = b["backtest"], b["forward"]
        L.append(f"| {b['id']} {b['name']} | {f(bt.get('cagr'))} | {f(bt.get('max_dd'))} | **{fw.get('final_1000', 0):,.0f}** | "
                 f"{f(fw.get('cagr'))} | {fw.get('sharpe')} | {f(fw.get('max_dd'))} | {(b.get('band_status') or {}).get('text', '')} |")
    b = o.get("btc_fwd") or {}
    if b:
        L.append(f"| BTC al-tut | – | – | **{b.get('final_1000', 0):,.0f}** | {f(b.get('cagr'))} | {b.get('sharpe')} | {f(b.get('max_dd'))} | – |")
    L += ["", "## Eleme motoru işe yarıyor mu? (kesimden sonra, eşit ağırlık, 1x)", "",
          "| Grup | Strateji | $1000 → | Yıllık | Sharpe | Maks. düşüş | Kârlı strateji oranı | Medyan Sharpe |",
          "|---|---|---|---|---|---|---|---|"]
    for g, s in o["groups"].items():
        sp = s.get("share_profitable")
        sp_txt = "–" if sp is None else "%" + format(sp * 100, ".0f")
        L.append(f"| {g} | {s.get('n')} | {s.get('final_1000', 0):,.0f} | {f(s.get('cagr'))} | {s.get('sharpe')} | {f(s.get('max_dd'))} | "
                 f"{sp_txt} | {s.get('median_fwd_sharpe')} |")
    L += ["", f"Backtest Sharpe sırası ile ileri Sharpe sırası arasındaki ilişki (Spearman): **{o.get('rank_corr_bt_vs_fwd')}** "
          "(1 = backtest'te iyi olan ileride de iyi; 0 = ilişki yok).", "",
          "## En iyi / en kötü 10 / 5 üye (ileri getiri)", ""]
    for m in o["top_members"]:
        L.append(f"- ✅ {m['coin']} {m['rule']} ({m['group']}): {f(m['fwd_ret'])}, SR {m['fwd_sharpe']}")
    for m in o["worst_members"]:
        L.append(f"- ❌ {m['coin']} {m['rule']} ({m['group']}): {f(m['fwd_ret'])}, SR {m['fwd_sharpe']}")
    L += ["", "## Zayıf yönler", "",
          "- Eşikler 2026'da yazıldı; araştırmacı (ben) kesimden sonraki dönemi biliyordu. Eleme motoru o veriyi görmedi, ama tamamen kör değil.",
          "- Coin listesi bugünün listesidir: kesimden sonra borsadan silinen coinler yok (survivorship).",
          "- Tek bir kesim tarihi = tek bir senaryo. Başka bir tarihte sonuç farklı olabilir."]
    return "\n".join(L)
