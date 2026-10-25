"""Paper portfolio books on top of the arena (A / B / C ...): frozen membership, leverage, costs,
per-position liquidation cap, optional volatility target. Forward record = bars after the book was created.

Top-N = highest backtest Sharpe among ACTIVE members on the creation day, one strategy per coin.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lab import metrics, perp, protect


def _now():
    from lab.arena import now_iso
    return now_iso()


def ensure(path, ro: dict, cfg: dict) -> dict:
    """Create the frozen books once; later runs only add books that are new in the config."""
    bc = cfg.get("books", {})
    data = json.loads(path.read_text()) if path.exists() else {"books": {}}
    active = [m for m in ro["members"] if m["status"] == "active"]
    sharpe = {m["id"]: ((m.get("backtest") or {}).get("sharpe") or 0) for m in active}
    coin = {m["id"]: m["coin"] for m in active}
    ranked, seen = [], set()
    for i in sorted(sharpe, key=lambda k: -sharpe[k]):
        if coin[i] not in seen:
            ranked.append(i); seen.add(coin[i])
    changed = False
    for b in bc.get("list", []):
        if b["id"] in data["books"]:
            continue
        if b.get("select") == "core":
            ids = []
        else:
            ids = [m["id"] for m in active] if b.get("select") == "all" else ranked[: int(b.get("n", 5))]
        data["books"][b["id"]] = {**b, "members": ids, "created_at": _now()}
        changed = True
    if changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return data


def returns(book: dict, R: pd.DataFrame, X: pd.DataFrame, ro: dict, p, cps: float, mmr: float) -> pd.Series:
    if book.get("select") == "core":       # a fixed core rule on its own assets (lab/core.py)
        from lab import core
        closes = {a: p.c[a] for a in book.get("assets", []) if a in p.columns}
        if not closes:
            return pd.Series(0.0, index=R.index)
        r = core.book_returns(closes, book["rule"], dict(book.get("params") or {}), p.ppy, cps)
        r = r - float(book.get("funding_annual", 0.0)) / p.ppy * core.book_exposure(closes, book["rule"], dict(book.get("params") or {}), p.ppy)
        return r.reindex(R.index).fillna(0.0)
    ids = [i for i in book["members"] if i in R.columns]
    if not ids:
        return pd.Series(0.0, index=R.index)
    L = float(book.get("leverage", 1))
    by_id = {m["id"]: m for m in ro["members"]}
    alive = pd.DataFrame({i: p.c[by_id[i]["coin"]].notna() for i in ids}, index=R.index)
    for i in ids:                                    # retired -> its share goes to cash from that date
        z = by_id[i].get("retired_at")
        if by_id[i]["status"] == "retired" and z:
            alive.loc[alive.index >= pd.Timestamp(z).tz_localize(None), i] = False
    Rl = (R[ids] * L).clip(lower=-(1.0 - mmr * L))  # isolated margin: loss per bar capped at the margin
    if book.get("weighting") == "invvol":             # past 90 days, monthly; retired -> cash
        r = protect.weighted_book(Rl, X[ids], alive, ids, "invvol", cps * L, p.ppy)
    else:
        n0 = len(ids)
        W = alive.astype(float) / n0                # fixed 1/N slots: an empty slot stays in cash
        ones = pd.DataFrame(1.0, index=R.index, columns=ids)
        r = protect.book(Rl, X[ids], W, ones, cps * L)
    if book.get("vol_target"):
        sc = protect.vol_target_scale(r, float(book["vol_target"]), p.ppy)
        r = r * sc - sc.diff().abs().fillna(0) * cps * L
    return r


def expected_band(bt: pd.Series, days: int = 365, paths: int = 1000, block: int = 10, seed: int = 5) -> dict:
    """Range the forward record should stay in IF the book behaves like its backtest:
    block bootstrap of the backtest's daily returns -> 5th / 50th / 95th percentile of the cumulative
    return after 0..days days. Below the 5th percentile = worse than 95% of backtest-like paths."""
    d = ((1 + bt).groupby(bt.index.normalize()).prod() - 1).to_numpy()
    if len(d) < 120:
        return {}
    rng = np.random.default_rng(seed)
    nb = days // block + 1
    starts = rng.integers(0, len(d) - block, size=(paths, nb))
    sims = np.stack([np.concatenate([d[s:s + block] for s in row])[:days] for row in starts])
    cum = np.cumprod(1 + sims, axis=1) - 1
    q = np.percentile(cum, [5, 50, 95], axis=0)
    step = 7
    return {"day": list(range(0, days + 1, step)),
            "p5": [0.0] + [round(float(x), 4) for x in q[0][step - 1::step]],
            "p50": [0.0] + [round(float(x), 4) for x in q[1][step - 1::step]],
            "p95": [0.0] + [round(float(x), 4) for x in q[2][step - 1::step]]}


def band_status(band: dict, days: int, ret: float) -> dict:
    if not band or days < 7:
        return {"status": "early", "text": "çok erken (< 1 hafta)"}
    i = min(len(band["day"]) - 1, int(round(days / 7)))
    lo, mid, hi = band["p5"][i], band["p50"][i], band["p95"][i]
    if ret < lo:
        st, tx = "below", "⚠️ beklenen aralığın ALTINDA: backtest gibi davranmıyor olabilir"
    elif ret > hi:
        st, tx = "above", "aralığın üstünde: iyi, ama şans payı yüksek"
    else:
        st, tx = "inside", "beklenen aralıkta"
    return {"status": st, "text": tx, "p5": lo, "p50": mid, "p95": hi}


def timemachine_record(tf: str, cfg: dict) -> dict:
    """{book_id: {"inside": n, "total": m, "candidate": bool, "cutoffs": {...}}} from every replay on disk."""
    from lab.arena import BASE
    out: dict = {}
    need = int((cfg.get("timemachine") or {}).get("min_inside", 2))
    for f in sorted((BASE / "timemachine").glob(f"*/{tf}/summary.json")):
        try:
            o = json.loads(f.read_text())
        except Exception:  # noqa: BLE001
            continue
        for b in o.get("books", []):
            d = out.setdefault(b["id"], {"inside": 0, "total": 0, "cutoffs": {}})
            st = (b.get("band_status") or {}).get("status")
            d["total"] += 1
            d["inside"] += st in ("inside", "above")
            d["cutoffs"][o["cutoff"]] = {"status": st, "final_1000": (b.get("forward") or {}).get("final_1000")}
    for d in out.values():
        d["candidate"] = d["total"] >= need and d["inside"] >= need
    return out


def report(data: dict, R, X, ro, p, cps, cfg) -> list[dict]:
    tmr = timemachine_record(cfg.get("key", cfg.get("timeframe", "4h")), cfg)
    mmr = cfg.get("books", {}).get("maint_margin", 0.005)
    metrics.set_periods(p.ppy)
    end = R.index[-1]
    out = []
    for bid, b in data["books"].items():
        r = returns(b, R, X, ro, p, cps, mmr)
        a = pd.Timestamp(b["created_at"]).tz_localize(None)
        f = r[r.index > a]
        bt = r[r.index <= a]
        bt = bt[bt.ne(0).cummax()]
        band = expected_band(bt) if len(bt) else {}
        fdays = max(0, (end - a).days)
        fret = float((1 + f).prod() - 1) if len(f) else 0.0
        cum_f = ((1 + f).groupby(f.index.normalize()).prod()).cumprod() - 1 if len(f) else pd.Series(dtype=float)
        out.append({
            "band": band, "band_status": band_status(band, fdays, fret),
            "fwd_daily": [round(float(x), 4) for x in cum_f.to_numpy()[::max(1, len(cum_f) // 120)]] if len(cum_f) else [],
            "timemachine": tmr.get(bid),
            "id": bid, "name": b["name"], "members": b["members"], "leverage": b.get("leverage", 1),
            "vol_target": b.get("vol_target"), "created_at": b["created_at"][:10],
            "forward": {"days": max(0, (end - a).days), "ret": round(float((1 + f).prod() - 1), 4) if len(f) else 0.0,
                        "balance_1000": round(1000 * float((1 + f).prod()), 2) if len(f) else 1000.0,
                        "sharpe": round(metrics.sharpe(f), 2) if len(f) > 20 else None,
                        "max_dd": round(metrics.max_drawdown(f), 4) if len(f) else 0.0},
            "backtest": {"cagr": round(metrics.cagr(bt), 4) if len(bt) > 30 else None,
                         "max_dd": round(metrics.max_drawdown(bt), 4) if len(bt) else None,
                         "sharpe": round(metrics.sharpe(bt), 2) if len(bt) > 30 else None},
            "spark_fwd": perp.sparkline(f, 90), "spark_bt": perp.sparkline(bt, 120),
        })
    return out
