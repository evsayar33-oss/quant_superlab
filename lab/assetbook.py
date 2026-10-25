"""H073 per-asset strategy book (config/assetbook.yaml): one simple rule per asset for one bot on Bitget perps.

  python -m lab.assetbook                       # every job (asset x timeframe), then the report
  python -m lab.assetbook --jobs BTC:1d,SPX:1d  # some jobs only
  python -m lab.assetbook --offline             # cached data only

Families (fixed in the config before any result):
  F1  Fibonacci premium / discount (ICT OTE) entries with Fibonacci stops and targets (own simulator below)
  F2  every lab/rules.py rule (grid centre) alone and with the fib_pd filter, 3 exits, 3 sides (lab.screen)
  F3  Fibonacci OTE + a second signal within 3 bars
Every variant runs once over the whole history. Selection at a cut reads only bars before the cut; the next
2 years are the forward check. The last cut is the locked holdout. Output: decisions/assetbook/.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats as st

from lab import assetdata, metrics, rules, screen
from lab.engine import Costs

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "decisions" / "assetbook"
_G: dict = {}


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "assetbook.yaml").read_text())


def job_list(cfg: dict) -> list[tuple[str, str]]:
    return [(a, tf) for a, s in cfg["assets"].items() for tf in s["tf"]]


# ============================================================================================ swings (causal)
def swing_arrays(p, k: int) -> dict:
    """Last CONFIRMED swing high/low (known k bars after the swing), the previous distinct levels, and
    whether the most recent confirmed swing was the high (bullish leg: low first, then high)."""
    sh, sl, shp, slp = rules._swings(p, k)
    w = 2 * k + 1
    t_hi = rules._since(rules._b(p.h.shift(k) == p.h.rolling(w, min_periods=w).max()))
    t_lo = rules._since(rules._b(p.l.shift(k) == p.l.rolling(w, min_periods=w).min()))
    col = p.columns[0]
    return {"sh": sh[col].to_numpy(), "sl": sl[col].to_numpy(), "shp": shp[col].to_numpy(),
            "slp": slp[col].to_numpy(), "bull": (t_hi < t_lo)[col].to_numpy(), "bear": (t_lo < t_hi)[col].to_numpy()}


# ============================================================================================ F1 / F3 simulator
def fib_decisions(D: dict, sw: dict, prm: dict, conf: tuple | None = None) -> dict:
    """Entry decisions at each bar close for the Fibonacci zone family (vectorised, data up to t only)."""
    O, H, L, C, A, S = D["O"], D["H"], D["L"], D["C"], D["A"], D["SMA"]
    z_lo, z_hi = prm["zone"]
    sh, sl = sw["sh"], sw["sl"]
    R = sh - sl
    with np.errstate(invalid="ignore"):
        big = R >= 2 * A
        bull = sw["bull"] & big & (C > sl)
        bear = sw["bear"] & big & (C < sh)
        lz_hi, lz_lo = sh - z_lo * R, sh - z_hi * R            # discount zone of a bullish leg (hi = nearest)
        sz_lo, sz_hi = sl + z_lo * R, sl + z_hi * R            # premium zone of a bearish leg (lo = nearest)
        if prm["filter"] == "sma200":
            bull &= C > S
            bear &= C < S
        elif prm["filter"] == "structure":
            bull &= sl > sw["slp"]
            bear &= sh < sw["shp"]
        if prm["side"] == "long":
            bear = np.zeros_like(bear)
        elif prm["side"] == "short":
            bull = np.zeros_like(bull)
        if prm["trigger"] == "confirm":
            el = bull & (L <= lz_hi) & (C >= lz_lo) & (C > O)
            es = bear & (H >= sz_lo) & (C <= sz_hi) & (C < O)
        else:                                                   # limit order rests at the near edge
            el, es = bull.copy(), bear.copy()
        if conf is not None:
            el &= conf[0]
            es &= conf[1]
    tg = prm["target"]
    ext = {"swing": 0.0, "ext1272": 0.272, "ext1618": 0.618}.get(tg)
    return {"el": np.nan_to_num(el).astype(bool), "es": np.nan_to_num(es).astype(bool),
            "lim_l": lz_hi, "lim_s": sz_lo,
            "stop_l": sl - 0.1 * A, "stop_s": sh + 0.1 * A,
            "tgt_l": None if ext is None else sh + ext * R, "tgt_s": None if ext is None else sl - ext * R}


def sim_fib(D: dict, dec: dict, prm: dict, cps: float, fund_bar: float, delay: int = 0, max_hold: int = 60):
    """One position at a time. Limit fills at min(open, level); no target on the limit-fill bar; stop before
    target inside one bar; gaps fill at the open. Returns per-bar net returns (1x) and trades
    (entry_i, exit_i, gross_return, side)."""
    O, H, L, C, A = (D[k].tolist() for k in ("O", "H", "L", "C", "A"))
    el, es = dec["el"].tolist(), dec["es"].tolist()
    lim_l, lim_s = dec["lim_l"].tolist(), dec["lim_s"].tolist()
    st_l, st_s = dec["stop_l"].tolist(), dec["stop_s"].tolist()
    tg_l = None if dec["tgt_l"] is None else dec["tgt_l"].tolist()
    tg_s = None if dec["tgt_s"] is None else dec["tgt_s"].tolist()
    limit = prm["trigger"] == "limit"
    atr_stop = prm["stop"] == "atr"
    T = len(C)
    R = [0.0] * T
    trades = []
    pos, ent, stop, tgt, ei = 0, 0.0, 0.0, 0.0, 0
    for t in range(1, T):
        if pos == 0:
            j = t - 1 - delay
            if j < 0:
                continue
            side = 1 if el[j] else (-1 if es[j] else 0)
            if side == 0:
                continue
            if limit:
                lvl = lim_l[j] if side == 1 else lim_s[j]
                if lvl != lvl:
                    continue
                if side == 1 and L[t] <= lvl:
                    ent = min(O[t], lvl)
                elif side == -1 and H[t] >= lvl:
                    ent = max(O[t], lvl)
                else:
                    continue
            else:
                ent = O[t]
            a = A[j]
            if atr_stop:
                stop = ent - 1.5 * a if side == 1 else ent + 1.5 * a
            else:
                stop = st_l[j] if side == 1 else st_s[j]
            if stop != stop:
                continue
            risk = (ent - stop) * side
            if risk <= 0:                                      # opened beyond the stop: stopped at once
                R[t] = -2 * cps - fund_bar
                trades.append((t, t, 0.0, side))
                continue
            if prm["target"] == "r2":
                tgt = ent + 2 * risk * side
            else:
                tgt = tg_l[j] if side == 1 else tg_s[j]
                if (tgt - ent) * side <= 0:
                    tgt = ent + 2 * risk * side                # target already passed: fall back to 2R
            pos, ei = side, t
            x = None
            if (side == 1 and L[t] <= stop) or (side == -1 and H[t] >= stop):
                x = stop
            elif not limit and ((side == 1 and H[t] >= tgt) or (side == -1 and L[t] <= tgt)):
                x = tgt
            if x is not None:
                R[t] = side * (x / ent - 1) - 2 * cps - fund_bar
                trades.append((t, t, side * (x / ent - 1), side))
                pos = 0
            else:
                R[t] = side * (C[t] / ent - 1) - cps - fund_bar
            continue
        x = None
        if pos == 1:
            if O[t] <= stop:
                x = O[t]
            elif L[t] <= stop:
                x = stop
            elif O[t] >= tgt:
                x = O[t]
            elif H[t] >= tgt:
                x = tgt
        else:
            if O[t] >= stop:
                x = O[t]
            elif H[t] >= stop:
                x = stop
            elif O[t] <= tgt:
                x = O[t]
            elif L[t] <= tgt:
                x = tgt
        if x is None and t - ei >= max_hold:
            x = C[t]
        if x is None:
            R[t] = pos * (C[t] / C[t - 1] - 1) - fund_bar
        else:
            R[t] = pos * (x / C[t - 1] - 1) - cps - fund_bar
            trades.append((ei, t, pos * (x / ent - 1), pos))
            pos = 0
    return np.array(R), trades


# ============================================================================================ window statistics
def wstats(R: np.ndarray, trades: list, idx: pd.DatetimeIndex, cps: float, a, b, ppy: float) -> dict:
    """Stats of one variant on bars [a, b): 1x and 2x cost (2x = one more cps at every entry and exit)."""
    ia, ib = idx.searchsorted(a), idx.searchsorted(b)
    if ib - ia < 30:
        return {"bars": int(ib - ia), "trades": 0}
    ex = np.zeros(len(R))
    tw = []
    for e, x, g, s in trades:
        if e < 0 or x < 0:
            continue
        ex[e] += cps
        ex[x] += cps
        if ia <= x < ib:
            tw.append(g)
    r1 = R[ia:ib]
    r2 = r1 - ex[ia:ib]
    net2 = np.array(tw) - 4 * cps
    win, loss = net2[net2 > 0], net2[net2 <= 0]
    pf = float(win.sum() / -loss.sum()) if loss.sum() < 0 else (99.0 if len(win) else 0.0)
    payoff = float(win.mean() / -loss.mean()) if len(win) and len(loss) and loss.mean() < 0 else None
    be = 1 / (1 + payoff) if payoff else None
    thirds = [float(np.prod(1 + x) - 1) for x in np.array_split(r2, 3)]
    sd = r1.std()
    return {"bars": int(ib - ia), "trades": len(tw), "ret1": float(np.prod(1 + r1) - 1),
            "ret2": float(np.prod(1 + r2) - 1), "pf2": round(pf, 3),
            "wr2": float((net2 > 0).mean()) if len(net2) else 0.0, "be": be, "thirds2": thirds,
            "sr_bar": float(r1.mean() / sd) if sd > 0 else 0.0, "sr": float(r1.mean() / sd * math.sqrt(ppy)) if sd > 0 else 0.0,
            "skew": float(st.skew(r1)) if sd > 0 else 0.0, "kurt": float(st.kurtosis(r1, fisher=False)) if sd > 0 else 3.0,
            "max_dd": float((np.cumprod(1 + r2) / np.maximum.accumulate(np.cumprod(1 + r2)) - 1).min())}


def windows(idx: pd.DatetimeIndex, cfg: dict) -> list[dict]:
    end = idx[-1]
    out = []
    for y in sorted(cfg["timemachine_years_ago"] + [cfg["holdout_years"]], reverse=True):
        c = end - pd.DateOffset(years=y)
        f = c + pd.DateOffset(years=cfg["holdout_years"])
        disc_years = (c - idx[0]).days / 365.25
        out.append({"name": f"{y}y", "cut": c, "fwd_end": end + pd.Timedelta(days=1) if f >= end else f,
                    "testable": disc_years >= cfg["min_discovery_years"], "holdout": y == cfg["holdout_years"]})
    return out


# ============================================================================================ variants
def f1_points(cfg: dict) -> list[dict]:
    return rules.grid_points(cfg["families"]["F1_fib_zone"]["grid"])


def f3_points(cfg: dict) -> list[dict]:
    f = cfg["families"]["F3_fib_confirm"]
    return [{**f["base"], **g} for g in rules.grid_points(f["grid"])]


def catalog(cfg: dict) -> list[str]:
    return [n for n, r in rules.RULES.items() if r.family != "positioning"]


def mid(grid: dict) -> dict:
    return {k: v[len(v) // 2] for k, v in (grid or {}).items()}


def vkey(fam: str, prm: dict) -> str:
    return fam + "|" + json.dumps(prm, sort_keys=True, default=str)


def f2_neighbours(rule: str, prm: dict) -> list[dict]:
    g = rules.RULES[rule].grid or {}
    out = []
    for k, vals in g.items():
        if len(vals) < 2:
            continue
        i = vals.index(prm[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(prm)
                q[k] = vals[j]
                out.append(q)
    return out


def ordered_neighbours(prm: dict, grid: dict, ordered: list[str]) -> list[dict]:
    out = []
    for k in ordered:
        vals = grid[k]
        i = vals.index(prm[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(prm)
                q[k] = vals[j]
                out.append(q)
    return out


# ============================================================================================ one run
def _arrays(p) -> dict:
    from lab import indicators as I
    col = p.columns[0]
    return {"O": p.o[col].to_numpy(float), "H": p.h[col].to_numpy(float), "L": p.l[col].to_numpy(float),
            "C": p.c[col].to_numpy(float), "A": I.atr(p.h, p.l, p.c, 14)[col].to_numpy(float),
            "SMA": p.c[col].rolling(200, min_periods=200).mean().to_numpy(float)}


def run_one(task: tuple) -> tuple:
    """task = (key, fam, prm, delay, windows_to_compute) -> (key, delay, {window: stats}) or error."""
    key, fam, prm, delay, wsel = task
    p, D, costs, idx, ppy, W = (_G[k] for k in ("panel", "D", "costs", "idx", "ppy", "W"))
    cps = costs.per_turnover
    try:
        if fam in ("F1", "F3"):
            if prm["k"] not in _G["sw"]:
                _G["sw"][prm["k"]] = swing_arrays(p, prm["k"])
            sw = _G["sw"][prm["k"]]
            conf = _G["conf"][prm["confirm"]] if fam == "F3" else None
            dec = fib_decisions(D, sw, prm, conf)
            R, trades = sim_fib(D, dec, prm, cps, costs.funding_annual / ppy, delay,
                                _G["cfg"]["families"]["F1_fib_zone"]["max_hold_bars"])
        else:
            R_, _, tl = screen.run_variant(p, prm["rule"], screen._tuples(prm["params"]), prm["exit"], prm["side"],
                                           costs, delay, prm["filter"])
            R = R_.iloc[:, 0].fillna(0.0).to_numpy()
            ei = idx.get_indexer(pd.to_datetime(tl["entry"])) if len(tl) else []
            xi = idx.get_indexer(pd.to_datetime(tl["exit"])) if len(tl) else []
            trades = [(int(e), int(x), float(g), int(s)) for e, x, g, s in
                      zip(ei, xi, tl["ret"] if len(tl) else [], tl["side"] if len(tl) else [])]
        out = {}
        for w in W:
            if w["name"] not in wsel:
                continue
            out[f"disc_{w['name']}"] = wstats(R, trades, idx, cps, idx[0], w["cut"], ppy)
            if delay == 0:
                out[f"fwd_{w['name']}"] = wstats(R, trades, idx, cps, w["cut"], w["fwd_end"], ppy)
        return key, delay, out, None
    except Exception as e:  # noqa: BLE001 - a broken rule must not stop the job; it is reported
        return key, delay, None, f"{type(e).__name__}: {e}"


def _pool_map(tasks: list, workers: int) -> list:
    if workers <= 1 or len(tasks) < 8:
        return [run_one(t) for t in tasks]
    ctx = mp.get_context("fork")
    with ctx.Pool(workers) as pool:
        return pool.map(run_one, tasks, chunksize=max(1, len(tasks) // (workers * 8)))


# ============================================================================================ checks
def d123(s: dict, d: dict, tf: str) -> dict:
    if not s or s.get("trades", 0) == 0:
        return {"D1": False, "D2": False, "D3": False}
    be = s.get("be")
    return {"D1": s["trades"] >= d["D1_min_trades"][tf],
            "D2": s["ret2"] > 0 and s["pf2"] >= d["D2"]["min_profit_factor_2x"] and be is not None and s["wr2"] > be,
            "D3": all(x > 0 for x in s["thirds2"])}


def psr_star(s: dict, sr_star: float) -> float:
    n, sr = s["bars"], s["sr_bar"]
    den = math.sqrt(max(1e-12, 1 - s["skew"] * sr + (s["kurt"] - 1) / 4 * sr ** 2))
    return float(st.norm.cdf((sr - sr_star) * math.sqrt(max(n - 1, 1)) / den))


def inside(s: dict, h: dict, tf: str) -> bool:
    return bool(s and s.get("trades", 0) >= h["H3_min_trades"][tf] and s["ret2"] > 0 and s["pf2"] >= h["H2_min_profit_factor_2x"])


# ============================================================================================ job
def run_job(asset: str, tf: str, cfg: dict, offline: bool = False, workers: int | None = None) -> dict:
    spec = cfg["assets"][asset]
    df = assetdata.load(spec["data"], tf, cfg["start"], offline)
    p = assetdata.panel(asset, df, tf)
    costs = Costs(**spec["costs"])
    idx, ppy = p.index, p.ppy
    W = windows(idx, cfg)
    _G.update(panel=p, D=_arrays(p), costs=costs, idx=idx, ppy=ppy, W=W, cfg=cfg, sw={}, conf={})
    workers = workers or int(os.environ.get("LAB_WORKERS", os.cpu_count() or 1))
    allw = [w["name"] for w in W]
    d, h = cfg["discovery"], cfg["holdout"]

    prim = {}
    for prm in f1_points(cfg):
        prim[vkey("F1", prm)] = ("F1", prm)
    for prm in f3_points(cfg):
        prim[vkey("F3", prm)] = ("F3", prm)
    f2 = cfg["families"]["F2_catalog_x_fib"]
    for rn in catalog(cfg):
        for ex in f2["exits"]:
            for sd in f2["side"]:
                for fl in f2["filter"]:
                    prm = {"rule": rn, "params": mid(rules.RULES[rn].grid), "exit": ex, "side": sd, "filter": fl}
                    prim[vkey("F2", prm)] = ("F2", prm)
    for k_ in (3, 5, 10):                                        # shared by every worker (fork)
        _G["sw"][k_] = swing_arrays(p, k_)
    w3 = cfg["families"]["F3_fib_confirm"]["within_bars"] + 1
    for cn in cfg["families"]["F3_fib_confirm"]["grid"]["confirm"]:
        sg = rules.RULES[cn].fn(p, **screen._tuples(mid(rules.RULES[cn].grid)))
        cl = sg.entry_long.iloc[:, 0].astype(float).rolling(w3, min_periods=1).max().to_numpy() > 0
        cs = (sg.entry_short.iloc[:, 0].astype(float).rolling(w3, min_periods=1).max().to_numpy() > 0
              if sg.entry_short is not None else np.zeros(len(idx), bool))
        _G["conf"][cn] = (cl, cs)
    out1 = _pool_map([(k, f, prm, 0, allw) for k, (f, prm) in prim.items()], workers)
    res = {k: v for k, _, v, e in out1 if v}
    errs = {k: e for k, _, v, e in out1 if e}
    fams = dict(prim)

    # ---- neighbours of F2 candidates (lazy): run them, they count as trials
    cands = {k for k in res for w in W if all(d123(res[k].get(f"disc_{w['name']}"), d, tf).values())}
    extra = {}
    for k in cands:
        f, prm = fams[k]
        if f == "F2":
            for q in f2_neighbours(prm["rule"], prm["params"]):
                nk = vkey("F2", {**prm, "params": q})
                if nk not in res and nk not in extra:
                    extra[nk] = ("F2", {**prm, "params": q})
    for k, _, v, e in _pool_map([(k, f, prm, 0, allw) for k, (f, prm) in extra.items()], workers):
        if v:
            res[k] = v
    fams.update(extra)
    n_trials = len(res)

    def nbrs(k):
        f, prm = fams[k]
        if f == "F1":
            g = cfg["families"]["F1_fib_zone"]
            return [vkey("F1", q) for q in ordered_neighbours(prm, g["grid"], g["ordered"])]
        if f == "F3":
            g = cfg["families"]["F3_fib_confirm"]
            return [vkey("F3", q) for q in ordered_neighbours(prm, {**{x: [v] for x, v in g["base"].items()}, **g["grid"]}, g["ordered"])]
        return [vkey("F2", {**prm, "params": q}) for q in f2_neighbours(prm["rule"], prm["params"])]

    # ---- per cut: D1-D4, then delay (D5) for survivors, DSR (D6), pick, forward
    cuts = {}
    delay_need = set()
    for w in W:
        wn = w["name"]
        rows = {}
        for k, v in res.items():
            if k not in prim:
                continue                                          # neighbours are judged only as neighbours
            s = v.get(f"disc_{wn}")
            c = d123(s, d, tf)
            if not all(c.values()):
                continue
            nb = [res[x][f"disc_{wn}"] for x in nbrs(k) if x in res and res[x].get(f"disc_{wn}")]
            share = (sum((x.get("pf2") or 0) >= 1.10 and x.get("trades", 0) > 0 for x in nb) / len(nb)) if nb else 0.0
            c["D4"] = share >= d["D4_plateau"]
            med = float(np.median([x.get("sr", 0.0) for x in nb])) if nb else 0.0
            rows[k] = {"checks": c, "plateau_share": round(share, 2), "plateau_score": round(min(s["sr"], med), 3)}
            if c["D4"]:
                delay_need.add(k)
        cuts[wn] = rows
    dres = {k: v for k, _, v, e in _pool_map([(k, *fams[k], 1, allw) for k in delay_need], workers) if v}
    out_cuts = {}
    for w in W:
        wn = w["name"]
        srs = [v[f"disc_{wn}"]["sr_bar"] for k, v in res.items() if k in prim and v.get(f"disc_{wn}", {}).get("trades", 0) > 0]
        var = float(np.var(srs, ddof=1)) if len(srs) > 1 else 0.0
        sr_star = metrics.expected_max_sharpe(n_trials, var)
        surv = []
        for k, r in cuts[wn].items():
            c = r["checks"]
            if c.get("D4"):
                s, sd_ = res[k][f"disc_{wn}"], (dres.get(k) or {}).get(f"disc_{wn}")
                c["D5"] = bool(sd_ and sd_.get("ret2", -1) > 0 and sd_["ret2"] >= d["D5_delay"] * s["ret2"])
                dsr = psr_star(s, sr_star)
                r["dsr"] = round(dsr, 3)
                c["D6"] = dsr >= d["D6_min_dsr"]
            r["pass"] = all(c.get(x, False) for x in ("D1", "D2", "D3", "D4", "D5", "D6"))
            if r["pass"]:
                surv.append(k)
        pick = max(surv, key=lambda k: cuts[wn][k]["plateau_score"]) if surv else None
        f1s = [k for k in surv if k.startswith("F1")]
        f1_pick = max(f1s, key=lambda k: cuts[wn][k]["plateau_score"]) if f1s else None
        funnel = {"trials": n_trials,
                  "D1-D3": len(cuts[wn]), "D4": sum(r["checks"].get("D4", False) for r in cuts[wn].values()),
                  "D5": sum(r["checks"].get("D5", False) for r in cuts[wn].values()), "D6 (all)": len(surv)}
        fw = {k: res[k].get(f"fwd_{wn}") for k in surv}
        out_cuts[wn] = {"cut": str(w["cut"].date()), "fwd_end": str(pd.Timestamp(w["fwd_end"]).date()),
                        "testable": w["testable"], "holdout": w["holdout"], "funnel": funnel, "sr_star_bar": round(sr_star, 4),
                        "pick": pick, "f1_pick": f1_pick, "n_surv_f1": len(f1s),
                        "n_surv_f3": sum(k.startswith("F3") for k in surv), "n_surv_f2_fib": sum(k.startswith("F2") and '"fib_pd"' in k for k in surv),
                        "pick_disc": res[pick][f"disc_{wn}"] if pick else None,
                        "pick_fwd": fw.get(pick) if pick else None,
                        "pick_inside": inside(fw.get(pick), h, tf) if pick else False,
                        "f1_pick_fwd": fw.get(f1_pick) if f1_pick else None,
                        "survivors": [{"key": k, "plateau_score": cuts[wn][k]["plateau_score"], "dsr": cuts[wn][k]["dsr"],
                                       "disc": _brief(res[k][f"disc_{wn}"]), "fwd": _brief(fw.get(k)),
                                       "inside": inside(fw.get(k), h, tf)} for k in
                                      sorted(surv, key=lambda k: -cuts[wn][k]["plateau_score"])[:15]],
                        "near": _near(cuts[wn], res, wn)}
    testable = [w["name"] for w in W if w["testable"]]
    n_in = sum(out_cuts[n]["pick_inside"] for n in testable)
    hold = [w["name"] for w in W if w["holdout"]][0]
    tm_pass = len(testable) >= 2 and n_in >= cfg["timemachine"]["min_inside"]
    hc = out_cuts[hold]
    lead = bool(hc["pick"] and hc["pick_inside"] and tm_pass)
    return {"asset": asset, "tf": tf, "bitget": spec["bitget"], "data": spec["data"], "first_bar": str(idx[0]),
            "last_bar": str(idx[-1]), "bars": len(idx), "n_trials": n_trials, "errors": len(errs),
            "error_sample": dict(list(errs.items())[:10]), "cuts": out_cuts, "timemachine": {"testable": testable, "inside": n_in, "passed": tm_pass},
            "lead": lead, "fib_test": fib_test(res, prim, W, cfg, tf), "bh": _bh(p, W, costs)}


def _brief(s: dict | None) -> dict | None:
    if not s:
        return None
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()
            if k in ("trades", "ret2", "pf2", "wr2", "be", "sr", "max_dd")}


def _near(rows: dict, res: dict, wn: str) -> list:
    """Best candidates that failed only one of D4-D6 (information, never a pick)."""
    out = []
    for k, r in rows.items():
        fails = [x for x in ("D4", "D5", "D6") if not r["checks"].get(x, False)]
        if len(fails) == 1:
            out.append({"key": k, "failed": fails[0], "plateau_score": r["plateau_score"], "dsr": r.get("dsr"),
                        "disc": _brief(res[k][f"disc_{wn}"])})
    return sorted(out, key=lambda x: -x["plateau_score"])[:5]


def fib_test(res: dict, prim: dict, W: list, cfg: dict, tf: str) -> dict:
    """Paired test: the same F2 variant with and without the fib_pd filter (pre-registered)."""
    ft = cfg["fib_filter_help"]
    hold = [w["name"] for w in W if w["holdout"]][0]
    out = {}
    for part in ("disc", "fwd"):
        deltas = []
        for k, (f, prm) in prim.items():
            if f != "F2" or prm["filter"] != "none":
                continue
            k2 = vkey("F2", {**prm, "filter": "fib_pd"})
            a, b = (res.get(k) or {}).get(f"{part}_{hold}"), (res.get(k2) or {}).get(f"{part}_{hold}")
            if a and b and a.get("trades", 0) >= ft["min_trades"] and b.get("trades", 0) >= ft["min_trades"]:
                deltas.append(min(b["pf2"], 10) - min(a["pf2"], 10))
        deltas = np.array(deltas)
        out[part] = {"pairs": int(len(deltas)), "median_delta_pf": round(float(np.median(deltas)), 3) if len(deltas) else None,
                     "share_improved": round(float((deltas > 0).mean()), 3) if len(deltas) else None}
    f = out["fwd"]
    out["helps"] = bool(f["pairs"] and f["median_delta_pf"] > 0 and f["share_improved"] > ft["min_share"])
    return out


def _bh(p, W: list, costs: Costs) -> dict:
    c = p.c.iloc[:, 0]
    out = {}
    for w in W:
        x = c[(c.index >= w["cut"]) & (c.index < w["fwd_end"])]
        out[w["name"]] = round(float(x.iloc[-1] / x.iloc[0] - 1), 4) if len(x) > 1 else None
    return out


# ============================================================================================ describe a rule
def describe(key: str) -> str:
    f, prm = key.split("|", 1)
    prm = json.loads(prm)
    if f in ("F1", "F3"):
        z = prm["zone"]
        side = {"long": "sadece long", "short": "sadece short", "both": "long ve short"}[prm["side"]]
        trig = "zon kenarında limit emir" if prm["trigger"] == "limit" else "zona girip ters yönde kapanan mum, sonraki açılışta piyasa emri"
        stop = "salınım ucunun 0,1 ATR ötesi (1.0 seviyesi)" if prm["stop"] == "swing" else "girişten 1,5 ATR"
        tgt = {"swing": "salınım ucu (0 seviyesi)", "ext1272": "1.272 uzantı", "ext1618": "1.618 uzantı", "r2": "2R"}[prm["target"]]
        flt = {"none": "filtre yok", "sma200": "SMA200 yönünde", "structure": "yapı (yükselen dip / alçalan tepe)"}[prm["filter"]]
        s = (f"Fibonacci {z[0]}–{z[1]} bölgesi (long: discount, short: premium), salınım k={prm['k']}, {trig}, "
             f"stop: {stop}, hedef: {tgt}, {flt}, {side}")
        if f == "F3":
            s += f", onay: {prm['confirm']} (son 3 bar)"
        return s
    fl = " + Fibonacci premium/discount filtresi" if prm["filter"] == "fib_pd" else ""
    from lab.trade_engine import EXIT_GRID
    return (f"{prm['rule']} {json.dumps(prm['params'])}{fl}, çıkış: {EXIT_GRID[prm['exit']].label()}, yön: {prm['side']}")


# ============================================================================================ report
def _p(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}%"


def report(R: dict) -> str:
    L = ["# H073 varlık başına strateji kitabı (tek platform: Bitget perp)", "",
         f"Tarih: {R['run_at'][:10]}. Kurallar sonuçlardan ÖNCE yazıldı: `config/assetbook.yaml` (commit `c50eac5`). "
         f"Toplam deneme: **{R['n_trials']:,}**.", "",
         "Seçim her kesimde sadece kesimden önceki barları okur. Kilitli dönem = son 2 yıl. "
         "Zaman makinesi = aynı seçim 6 ve 4 yıl önce yapılmış gibi.", "",
         "## Varlık başına sonuç", "",
         "| Varlık | TF | Bitget | Deneme | D1–D3 | D4 | D5 | D6 (hepsi) | Seçilen kural | Kilitli 2 yıl (2x maliyet) | PF | İşlem | Al-tut 2 yıl | Zaman makinesi | Sonuç |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for j in R["jobs"]:
        hc = [c for c in j["cuts"].values() if c["holdout"]][0]
        fu = hc["funnel"]
        pf = hc["pick_fwd"] or {}
        tm = j["timemachine"]
        L.append(f"| {j['asset']} | {j['tf']} | {j['bitget']} | {j['n_trials']:,} | {fu['D1-D3']} | {fu['D4']} | {fu['D5']} | "
                 f"{fu['D6 (all)']} | {('`' + hc['pick'][:60] + '…`') if hc['pick'] else 'yok'} | {_p(pf.get('ret2'))} | "
                 f"{pf.get('pf2', '—')} | {pf.get('trades', '—')} | {_p(j['bh'].get('2y'))} | {tm['inside']}/{len(tm['testable'])} | "
                 f"{'**ADAY**' if j['lead'] else 'kaldı'} |")
    L += ["", "D1 işlem sayısı · D2 2x maliyette kâr, PF ≥ 1,20, kazanma oranı başa baş oranının üstünde · "
          "D3 her üçte birde kârlı · D4 plato · D5 1 bar gecikme · D6 şans testi (DSR ≥ 0,95).", ""]
    leads = [j for j in R["jobs"] if j["lead"]]
    L += ["## Aday kurallar (karar kapısına gidecek)", ""]
    if not leads:
        L += ["**Daha iyisi bulunamadı.** Önceden yazılan kurala göre hiçbir varlıkta, kilitli 2 yılı ve zaman "
              "makinesini birlikte geçen bir kural çıkmadı.", ""]
    for j in leads:
        hc = [c for c in j["cuts"].values() if c["holdout"]][0]
        L += [f"### {j['asset']} {j['tf']} ({j['bitget']})", "", describe(hc["pick"]), "",
              f"Keşif: {json.dumps(_brief(hc['pick_disc']))}", "", f"Kilitli 2 yıl: {json.dumps(_brief(hc['pick_fwd']))}", ""]
    L += ["## Zaman makinesi ayrıntısı", "", "| Varlık | TF | Kesim | Test edilebilir | Seçim | İleri 2 yıl (2x) | PF | İşlem | İçeride |",
          "|---|---|---|---|---|---|---|---|---|"]
    for j in R["jobs"]:
        for n, c in j["cuts"].items():
            pf = c["pick_fwd"] or {}
            L.append(f"| {j['asset']} | {j['tf']} | {c['cut']} | {'evet' if c['testable'] else 'hayır'} | "
                     f"{('`' + c['pick'][:50] + '…`') if c['pick'] else 'yok'} | {_p(pf.get('ret2'))} | {pf.get('pf2', '—')} | "
                     f"{pf.get('trades', '—')} | {'evet' if c['pick_inside'] else 'hayır'} |")
    L += ["", "## Fibonacci sorusu", "", "### 1) Fibonacci premium/discount filtresi diğer kuralları iyileştiriyor mu? (eşli test)", "",
          "| Varlık | TF | Çift | Keşif: medyan PF farkı | Keşif: iyileşen | Kilitli: medyan PF farkı | Kilitli: iyileşen | Yardım ediyor |",
          "|---|---|---|---|---|---|---|---|"]
    helps = 0
    for j in R["jobs"]:
        f = j["fib_test"]
        helps += f["helps"]
        L.append(f"| {j['asset']} | {j['tf']} | {f['fwd']['pairs']} | {f['disc']['median_delta_pf']} | {f['disc']['share_improved']} | "
                 f"{f['fwd']['median_delta_pf']} | {f['fwd']['share_improved']} | {'evet' if f['helps'] else 'hayır'} |")
    need = R["cfg_fib"]["min_jobs"]
    L += ["", f"Genel karar (ön kayıt: en az {need} işte yardım etmeli): **{helps}/{len(R['jobs'])} → "
          f"{'YARDIM EDİYOR' if helps >= need else 'YARDIM ETMİYOR'}**.", "",
          "### 2) Saf Fibonacci giriş ailesi (F1) — her varlıkta en sağlam ayar", "",
          "| Varlık | TF | F1 geçen (D1–D6) | F1 seçimi | Kilitli 2 yıl (2x) | PF | İşlem |", "|---|---|---|---|---|---|---|"]
    for j in R["jobs"]:
        hc = [c for c in j["cuts"].values() if c["holdout"]][0]
        n1 = hc["n_surv_f1"]
        pf = hc["f1_pick_fwd"] or {}
        L.append(f"| {j['asset']} | {j['tf']} | {n1} | {describe(hc['f1_pick']) if hc['f1_pick'] else 'yok'} | {_p(pf.get('ret2'))} | "
                 f"{pf.get('pf2', '—')} | {pf.get('trades', '—')} |")
    L += ["", "## Keşifte en iyi görünen ama bir kontrolde kalanlar (bilgi, karar değil)", "",
          "| Varlık | TF | Kural | Kaldığı | Keşif 2x getiri | PF | DSR |", "|---|---|---|---|---|---|---|"]
    for j in R["jobs"]:
        hc = [c for c in j["cuts"].values() if c["holdout"]][0]
        for x in hc["near"][:2]:
            L.append(f"| {j['asset']} | {j['tf']} | `{x['key'][:70]}` | {x['failed']} | {_p(x['disc']['ret2'])} | {x['disc']['pf2']} | {x['dsr']} |")
    L += ["", "## Zayıf yönler", ""] + [f"- {w}" for w in WEAK]
    return "\n".join(L) + "\n"


WEAK = [
    "Endeks ve metal perp'leri için fiyat vekili kullanıldı (^GSPC, ^NDX, GLD, SLV, CPER). Bitget perp fiyatı, işlem saatleri ve funding farklı olabilir.",
    "Endeks ve metallerde ücretsiz 4 saatlik uzun geçmiş yok; bu varlıklar sadece günlükte test edildi.",
    "SOL geçmişi kısa (2020-08). Zaman makinesi için yeterli kesim yok; kural gereği SOL aday olamaz.",
    "Maliyet: taker %0,06 + kayma; funding sabit yıllık oran (kripto %8, diğer %5). Gerçek funding değişir.",
    "Tek pozisyon, 1x büyüklük. Kaldıraç kenar yaratmaz; sadece kârı ve zararı büyütür.",
    "Aday kural bile karar değildir: hipotez id + run.py --hypothesis (karar kapısı) + ileri kayıt gerekir.",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--workers", type=int, default=0)
    a = ap.parse_args()
    cfg = load_cfg()
    todo = job_list(cfg)
    if a.jobs:
        want = {tuple(x.split(":")) for x in a.jobs.split(",")}
        todo = [j for j in todo if j in want]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "jobs").mkdir(exist_ok=True)
    for asset, tf in todo:
        t0 = datetime.now()
        r = run_job(asset, tf, cfg, a.offline, a.workers or None)
        (OUT / "jobs" / f"{asset}_{tf}.json").write_text(json.dumps(r, indent=1, default=str))
        print(f"{asset} {tf}: trials {r['n_trials']}, lead {r['lead']}, {(datetime.now() - t0).seconds}s", flush=True)
    jobs = []
    for asset, tf in job_list(cfg):
        f = OUT / "jobs" / f"{asset}_{tf}.json"
        if f.exists():
            jobs.append(json.loads(f.read_text()))
    R = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n_trials": sum(j["n_trials"] for j in jobs),
         "jobs": jobs, "cfg_fib": cfg["fib_filter_help"]}
    (OUT / "result.json").write_text(json.dumps({k: v for k, v in R.items()}, indent=1, default=str))
    (OUT / "report.md").write_text(report(R))
    print(report(R))


if __name__ == "__main__":
    main()
