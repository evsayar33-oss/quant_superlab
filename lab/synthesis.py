"""H072 synthesis study (config/synthesis.yaml): which published rules beat the US index itself, not cash?

  python -m lab.synthesis              # downloads free data once (data/cache/synthesis), then runs everything
  python -m lab.synthesis --offline    # cache only

Every candidate runs on the same dates as the index, at 1x and 2x costs. Cash earns the T-bill rate; borrowed
notional pays T-bill + spread. Signals use closes up to t; positions earn returns from t+lag. Acceptance C1-C7,
the plateau pick and the time machine are fixed in the config (written before any result was computed).
Output: decisions/synthesis/result.json, report.md, forward.json.
"""
from __future__ import annotations

import argparse
import io
import itertools
import json
import math
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from lab import metrics

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "synthesis"
OUT = ROOT / "decisions" / "synthesis"
KF = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
AQR_TSMOM = "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
MAX_AGE_H = float(os.environ.get("LAB_CACHE_HOURS", "20"))
OFFLINE = False


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "synthesis.yaml").read_text())


# ============================================================================================ data (free)
def _fetch(url: str, name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / name
    if p.exists() and (OFFLINE or time.time() - p.stat().st_mtime < MAX_AGE_H * 3600):
        return p
    import requests
    last = None
    for i in range(4):
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 quant_lab research"})
            r.raise_for_status()
            p.write_bytes(r.content)
            return p
        except Exception as e:  # network hiccup: retry, then fall back to a stale cache
            last = e
            time.sleep(2 ** i)
    if p.exists():
        return p
    raise RuntimeError(f"download failed: {url}: {last}")


def _kf_table(zname: str, block: int = 0) -> pd.DataFrame:
    """Table number `block` of a Ken French CSV zip, in decimals. -99.99 / -999 are missing."""
    z = zipfile.ZipFile(_fetch(KF + zname, zname))
    text = z.read(z.namelist()[0]).decode("latin-1")
    lines = text.splitlines()
    heads = [i for i, s in enumerate(lines) if s.startswith(",")]
    h = heads[block]
    cols = [c.strip() for c in lines[h].split(",")[1:]]
    rows = []
    for s in lines[h + 1:]:
        if not re.match(r"^\s*\d{6,8}\s*,", s):
            break
        parts = [x.strip() for x in s.split(",")]
        rows.append([parts[0]] + [float(x) for x in parts[1:len(cols) + 1]])
    df = pd.DataFrame(rows, columns=["d"] + cols)
    fmt = "%Y%m%d" if len(df["d"].iloc[0]) == 8 else "%Y%m"
    df.index = pd.to_datetime(df.pop("d"), format=fmt)
    return df.replace([-99.99, -999.0], np.nan) / 100.0


def load_us_daily() -> pd.DataFrame:
    """Ken French daily: mkt = total return of the CRSP value-weighted US market, rf = 1-month T-bill."""
    f = _kf_table("F-F_Research_Data_Factors_daily_CSV.zip")
    out = pd.DataFrame({"mkt": f["Mkt-RF"] + f["RF"], "rf": f["RF"]})
    mom = _kf_table("10_Portfolios_Prior_12_2_Daily_CSV.zip", 0)        # block 0 = value-weighted
    out["mom_top"] = mom["Hi PRIOR"].reindex(out.index)
    return out


def load_tsmom_monthly() -> pd.Series:
    x = pd.read_excel(_fetch(AQR_TSMOM, "aqr_tsmom.xlsx"), sheet_name=0, header=None)
    h = x.index[x.iloc[:, 1].astype(str).str.strip().eq("TSMOM")][0]      # header row: (blank), TSMOM, ...
    cols = ["Date"] + [str(c).strip() for c in x.iloc[h, 1:]]
    d = x.iloc[h + 1:].copy()
    d.columns = cols
    d = d[pd.to_datetime(d["Date"], errors="coerce").notna()]
    s = pd.Series(pd.to_numeric(d["TSMOM"], errors="coerce").to_numpy(),
                  index=pd.to_datetime(d["Date"]).dt.to_period("M").dt.to_timestamp("M"))
    return s.dropna()


def bond_tr_monthly(y_month_end: pd.Series, T: float = 10.0) -> pd.Series:
    """Constant-maturity par bond: bought at par with coupon y(t-1), sold one month later at yield y(t)."""
    y0, y1 = y_month_end.shift(1) / 100.0, y_month_end / 100.0
    n = 2 * (T - 1 / 12)
    p = (y0 / 2) * (1 - (1 + y1 / 2) ** (-n)) / (y1 / 2) + (1 + y1 / 2) ** (-n)
    return (p - 1 + y0 / 12).dropna()


BOND_SOURCE = {"name": None}


def load_bond_monthly() -> pd.Series:
    """10y Treasury yield at month end: FRED DGS10, or Yahoo ^TNX (same CBOE close yield) when FRED is down."""
    try:
        t = pd.read_csv(_fetch(FRED + "DGS10", "fred_dgs10.csv"))
        t.columns = ["d", "v"]
        s = pd.Series(pd.to_numeric(t["v"], errors="coerce").to_numpy(), index=pd.to_datetime(t["d"])).dropna()
        BOND_SOURCE["name"] = "FRED DGS10"
    except Exception as e:
        print("FRED unavailable, using Yahoo ^TNX:", e)
        p = CACHE / "tnx.csv"
        if not (p.exists() and (OFFLINE or time.time() - p.stat().st_mtime < MAX_AGE_H * 3600)):
            import yfinance as yf
            yf.download("^TNX", start="1962-01-01", auto_adjust=True, progress=False)["Close"]["^TNX"].to_csv(p)
        s = pd.read_csv(p, index_col=0, parse_dates=True).iloc[:, 0].dropna()
        BOND_SOURCE["name"] = "Yahoo ^TNX"
    return bond_tr_monthly(s.resample("ME").last())


def load_spy() -> pd.DataFrame:
    p = CACHE / "spy_irx.csv"
    if p.exists() and (OFFLINE or time.time() - p.stat().st_mtime < MAX_AGE_H * 3600):
        return pd.read_csv(p, index_col=0, parse_dates=True)
    import yfinance as yf
    raw = yf.download(["SPY", "^IRX"], start="1993-01-01", auto_adjust=True, progress=False)["Close"]
    df = pd.DataFrame({"px": raw["SPY"], "irx": raw["^IRX"].ffill()}).dropna(subset=["px"])
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_csv(p)
    return df


def _binance_vision_4h(sym: str, start: str = "2018-01") -> pd.Series:
    """Binance spot 4h closes from the free monthly files on data.binance.vision (fallback for Bitget)."""
    out = []
    months = pd.period_range(start, pd.Timestamp.today() - pd.offsets.MonthBegin(1), freq="M")
    for m in months:
        name = f"{sym}-4h-{m}.zip"
        try:
            z = zipfile.ZipFile(_fetch(f"https://data.binance.vision/data/spot/monthly/klines/{sym}/4h/{name}", name))
        except Exception:
            continue
        k = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
        ts = k[0].astype("int64")
        ts = np.where(ts > 1e14, ts // 1000, ts)                  # files from 2025 use microseconds
        out.append(pd.Series(k[4].to_numpy(float), index=pd.to_datetime(ts, unit="ms")))
    return pd.concat(out).sort_index() if out else pd.Series(dtype=float)


def load_h054_daily(cost_mult: float = 1.0) -> pd.Series | None:
    """H054 book (lab/core.py dual_trend_vt + 10% band) on 4h bars (Bitget, else Binance), per calendar day."""
    try:
        from lab import core, data
        cc = yaml.safe_load((ROOT / "config" / "core.yaml").read_text())
        try:
            closes = data.load_prices(["BTC/USDT", "ETH/USDT"], start="2018-01-01", timeframe="4h")
        except Exception:
            closes = pd.DataFrame()
        if closes.shape[1] < 2 or closes.dropna(how="all").empty:
            closes = pd.DataFrame({f"{s[:3]}/USDT": _binance_vision_4h(s) for s in ("BTCUSDT", "ETHUSDT")})
        cl = {c: closes[c] for c in closes.columns}
        prm = {"sma_days": 200, "horizons_days": [30, 90, 180], "target": 0.40, "lookback_days": 30}
        cps = (cc["costs"]["commission"] + cc["costs"]["slippage"]) * cost_mult
        r = core.book_returns(cl, "dual_trend_vt", prm, 6 * 365.0, cps, band=cc["risk_levels"]["band"])
        r.index = pd.DatetimeIndex(r.index).tz_localize(None) if getattr(r.index, "tz", None) else r.index
        return (1 + r).resample("D").prod() - 1
    except Exception as e:  # crypto data is optional for the study; the report says when it is missing
        print("H054 series unavailable:", e)
        return None


# ============================================================================================ engine
def apply_band(target: np.ndarray, band: float) -> np.ndarray:
    """Hold the current exposure until the target moves more than `band`; exits and entries always trade."""
    out = np.empty_like(target)
    cur = 0.0
    for i, t in enumerate(target):
        if np.isnan(t):
            t = 0.0
        if (t == 0.0) != (cur == 0.0) or abs(t - cur) > band:
            cur = t
        out[i] = cur
    return out


def year_frac(idx: pd.DatetimeIndex) -> np.ndarray:
    """Calendar time of each bar in years (weekends and holidays accrue into the next bar)."""
    d = np.diff(idx.values).astype("timedelta64[D]").astype(float)
    d = np.concatenate([[np.median(d) if len(d) else 1.0], d])
    return d / 365.25


def simulate(asset: pd.Series, rf: pd.Series, target: pd.Series, c: dict, mult: float, lag: int, band: float,
             asset_fee: float = 0.0) -> pd.Series:
    """Net return of a book that holds `exposure` x asset and the rest in T-bills (or borrows above 1x).

    target = exposure decided at the close of each bar. Held exposure = banded target shifted by `lag` bars.
    asset_fee = annual fee on the asset notional (index fee, momentum drag, ...), already in decimals.
    """
    dt = year_frac(asset.index)
    e = pd.Series(apply_band(target.to_numpy(dtype=float), band), index=target.index).shift(lag).fillna(0.0)
    e = e.to_numpy()
    r, f = asset.to_numpy(), rf.to_numpy()
    trade = np.abs(np.diff(e, prepend=0.0)) * c["trade_per_side"] * mult
    cash = np.clip(1 - e, 0, None) * (f - c["cash_fee_annual"] * mult * dt)
    borrow = np.clip(e - 1, 0, None) * (f + c["borrow_spread_annual"] * mult * dt)
    net = e * r - e * asset_fee * mult * dt + cash - borrow - trade
    return pd.Series(net, index=asset.index)


def bench(asset: pd.Series, c: dict, fee: float) -> pd.Series:
    return asset - fee * year_frac(asset.index) * c.get("benchmark_cost_multiplier", 1)


# ============================================================================================ metrics
def _yrs(r: pd.Series) -> float:
    return max((r.index[-1] - r.index[0]).days / 365.25, 1e-9) if len(r) > 1 else 1e-9


def cagr(r: pd.Series) -> float:
    g = float((1 + r).prod())
    return g ** (1 / _yrs(r)) - 1 if g > 0 else -1.0


def max_dd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def sharpe(r: pd.Series, rf: pd.Series) -> float:
    ex = (r - rf.reindex(r.index).fillna(0.0)).dropna()
    ppy = len(ex) / _yrs(ex)
    sd = ex.std()
    return float(ex.mean() / sd * math.sqrt(ppy)) if sd > 0 else 0.0


def vol(r: pd.Series) -> float:
    return float(r.std() * math.sqrt(len(r) / _yrs(r)))


def stats(r: pd.Series, rf: pd.Series) -> dict:
    return {"cagr": round(cagr(r), 4), "sharpe": round(sharpe(r, rf), 3), "max_dd": round(max_dd(r), 4),
            "vol": round(vol(r), 4), "final_1000": round(1000 * float((1 + r).prod()), 0),
            "start": str(r.index[0].date()), "end": str(r.index[-1].date())}


def windows(start: str, bounds: list[str], end) -> list[tuple]:
    edges = [pd.Timestamp(b) for b in bounds if pd.Timestamp(b) < pd.Timestamp(end)] + [pd.Timestamp(end)]
    edges[0] = max(edges[0], pd.Timestamp(start))
    return [(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]


def _cut(s: pd.Series, a, b, last: bool = False) -> pd.Series:
    return s[(s.index >= a) & ((s.index <= b) if last else (s.index < b))]


# ============================================================================================ candidates
def grid_points(grid: dict) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, v)) for v in itertools.product(*[grid[k] for k in keys])]


def neighbours(p: dict, grid: dict) -> list[dict]:
    out = []
    for k, vals in grid.items():
        i = vals.index(p[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(p)
                q[k] = vals[j]
                out.append(q)
    return out


def key(fam: str, p: dict) -> str:
    return fam + "|" + ",".join(f"{k}={v}" for k, v in p.items())


def target_a(fam: str, p: dict, D: pd.DataFrame, vol_n: int) -> tuple[pd.Series, pd.Series, str]:
    """Block A: (target exposure, traded asset returns, fee key) for a family and its parameters."""
    m = D["mkt"]
    tr = (1 + m).cumprod()
    rv = m.rolling(vol_n, min_periods=vol_n).std() * math.sqrt(252)
    one = pd.Series(1.0, index=D.index)
    if fam == "A0_const_lev":
        return one * p["L"], m, "index_fee_annual"
    if fam == "A1_trend_lev":
        on = (tr > tr.rolling(p["N"], min_periods=p["N"]).mean()).astype(float)
        return on * p["L"], m, "index_fee_annual"
    if fam == "A2_volman_lev":
        return (p["target"] / rv).clip(upper=p["Lmax"]).fillna(0.0), m, "index_fee_annual"
    if fam == "A3_trend_volman":
        on = (tr > tr.rolling(p["N"], min_periods=p["N"]).mean()).astype(float)
        return on * (p["target"] / rv).clip(upper=p["Lmax"]).fillna(0.0), m, "index_fee_annual"
    if fam == "A4_mom_trend":
        on = one if p["filter"] == "none" else (tr > tr.rolling(200, min_periods=200).mean()).astype(float)
        on = on.where(D["mom_top"].notna(), 0.0)
        return on * p["L"], D["mom_top"].fillna(0.0), "momentum_extra_annual"
    raise ValueError(fam)


def run_block_a(D: pd.DataFrame, cfg: dict) -> dict:
    """Simulate every Block A grid point at 1x, 2x and +1 delay on the full history (causal; slices later)."""
    c, A = cfg["costs"], cfg["block_a"]
    lag, band = cfg["lag_days"], cfg["no_trade_band"]
    runs = {}
    for fam, spec in A["families"].items():
        for p in grid_points(spec["grid"]):
            tgt, asset, fee_key = target_a(fam, p, D, A["vol_lookback_days"])
            fee = c[fee_key] + (c["index_fee_annual"] if fee_key != "index_fee_annual" else 0.0)
            band_f = 0.0 if fam in ("A0_const_lev", "A1_trend_lev", "A4_mom_trend") else band
            runs[key(fam, p)] = {
                "fam": fam, "p": p,
                "r1": simulate(asset, D["rf"], tgt, c, 1, lag, band_f, fee),
                "r2": simulate(asset, D["rf"], tgt, c, 2, lag, band_f, fee),
                "rd": simulate(asset, D["rf"], tgt, c, 1, lag + cfg["delay_test_extra_days"], band_f, fee)}
    return runs


def lev_control(asset: pd.Series, rf: pd.Series, L: float, c: dict, fee: float) -> pd.Series:
    return simulate(asset, rf, pd.Series(L, index=asset.index), c, 1, 0, 0.0, fee)


# ============================================================================================ acceptance
def c1(r: pd.Series, b: pd.Series, rf: pd.Series, tol: float) -> bool:
    return cagr(r) > cagr(b) and sharpe(r, rf) > sharpe(b, rf) and max_dd(r) >= max_dd(b) - tol


def evaluate(runs: dict, fams: dict, bh: pd.Series, rf: pd.Series, asset_for_control: pd.Series,
             subs: list[tuple], a0, a1, cfg: dict, ctrl_fee: float) -> dict:
    """Apply C1-C7 to every run on the window [a0, a1]. Returns per-key verdicts and the block pick."""
    acc, c = cfg["accept"], cfg["costs"]
    b = _cut(bh, a0, a1, True)
    rfw = _cut(rf, a0, a1, True)
    act_sr, rows = [], {}
    for k, v in runs.items():
        r = _cut(v["r1"], a0, a1, True)
        a = (r - b).dropna()
        act_sr.append(float(a.mean() / a.std()) if a.std() > 0 else 0.0)
    for k, v in runs.items():
        r1, r2, rd = (_cut(v[x], a0, a1, True) for x in ("r1", "r2", "rd"))
        ok1 = c1(r1, b, rfw, acc["C1_full"]["max_dd_tolerance"])
        sub = []
        for s0, s1 in subs:
            rs, bs = _cut(v["r1"], s0, s1), _cut(bh, s0, s1)
            rs2 = _cut(v["r2"], s0, s1)
            sub.append({"from": str(s0.date()), "cagr": round(cagr(rs), 4), "bh_cagr": round(cagr(bs), 4),
                        "max_dd": round(max_dd(rs), 4), "bh_max_dd": round(max_dd(bs), 4),
                        "ok": cagr(rs) > cagr(bs) and max_dd(rs) >= max_dd(bs) - acc["C2_subperiods"]["max_dd_tolerance"],
                        "ok_2x": cagr(rs2) > cagr(bs)})
        ok2 = all(s["ok"] for s in sub)
        ok3 = c1(r2, b, rfw, acc["C1_full"]["max_dd_tolerance"]) and \
            sum(not s["ok_2x"] for s in sub) <= acc["C3_high_cost"]["max_failed_subperiods"]
        ok4 = c1(rd, b, rfw, acc["C1_full"]["max_dd_tolerance"])
        lam = vol(r1) / vol(b) if vol(b) > 0 else 1.0
        ctrl = _cut(lev_control(asset_for_control, rf, lam, c, ctrl_fee), a0, a1, True)
        ok5 = cagr(r1) > cagr(ctrl)
        act = (r1 - b).dropna()
        d = metrics.dsr(act, cfg["n_trials"], act_sr)
        t_act = float(act.mean() / act.std() * math.sqrt(len(act))) if act.std() > 0 else 0.0
        rows[k] = {"fam": v["fam"], "p": v["p"], "stats": stats(r1, rfw), "stats_2x": stats(r2, rfw),
                   "stats_delay": stats(rd, rfw), "excess_cagr": round(cagr(r1) - cagr(b), 4),
                   "vol_matched_L": round(lam, 2), "vol_matched_cagr": round(cagr(ctrl), 4),
                   "dsr_active": round(d, 3), "t_active": round(t_act, 2), "subperiods": sub,
                   "checks": {"C1": ok1, "C2": ok2, "C3": ok3, "C4": ok4, "C5": ok5, "C7": d >= acc["C7_min_dsr"]}}
    for k, row in rows.items():
        grid = fams[row["fam"]]["grid"]
        nb = [rows[key(row["fam"], q)] for q in neighbours(row["p"], grid)]
        share = sum(n["checks"]["C1"] for n in nb) / len(nb) if nb else 0.0
        row["plateau_share"] = round(share, 2)
        row["checks"]["C6"] = share >= acc["C6_plateau"]
        med = float(np.median([n["excess_cagr"] for n in nb])) if nb else row["excess_cagr"]
        row["plateau_score"] = round(min(row["excess_cagr"], med), 4)
        row["pass"] = all(row["checks"].values())
        fails = [x for x, ok in row["checks"].items() if not ok]
        row["near_miss"] = (not row["pass"]) and fails in (["C2"], ["C3"], ["C2", "C3"]) and \
            sum(not s["ok"] for s in row["subperiods"]) <= 1
    passing = [k for k, r in rows.items() if r["pass"]]
    fam_pick = {}
    for f in fams:
        ks = [k for k in passing if rows[k]["fam"] == f]
        fam_pick[f] = max(ks, key=lambda k: rows[k]["plateau_score"]) if ks else None
    pick = max(passing, key=lambda k: rows[k]["plateau_score"]) if passing else None
    naive = max(rows, key=lambda k: rows[k]["stats"]["cagr"])
    return {"window": [str(pd.Timestamp(a0).date()), str(pd.Timestamp(a1).date())],
            "bh": stats(b, rfw), "rows": rows, "pick": pick, "family_pick": fam_pick, "naive": naive,
            "n_pass": len(passing)}


def ladder(ev: dict, limits: list[float]) -> list[dict]:
    out = []
    for lim in limits:
        ks = [k for k, r in ev["rows"].items() if r["pass"] and r["stats"]["max_dd"] >= lim]
        k = max(ks, key=lambda k: ev["rows"][k]["plateau_score"]) if ks else None
        out.append({"max_dd_limit": lim, "pick": k, "stats": ev["rows"][k]["stats"] if k else None})
    return out


def time_machine(runs: dict, fams: dict, bh: pd.Series, rf: pd.Series, asset: pd.Series, start: str,
                 bounds: list[str], cuts: list[str], cfg: dict, ctrl_fee: float) -> dict:
    end = bh.index[-1]
    reps = []
    for i, cut in enumerate(cuts):
        cut = pd.Timestamp(cut)
        nxt = pd.Timestamp(cuts[i + 1]) if i + 1 < len(cuts) else end
        subs = [w for w in windows(start, bounds, cut) if w[1] <= cut]
        ev = evaluate(runs, fams, bh, rf, asset, subs, pd.Timestamp(start), cut - pd.Timedelta(days=1), cfg, ctrl_fee)
        fb = _cut(bh, cut, nxt, nxt == end)
        tol = cfg["accept"]["C1_full"]["max_dd_tolerance"]

        def fwd(k):
            if not k:
                return None
            r = _cut(runs[k]["r1"], cut, nxt, nxt == end)
            return {"key": k, "cagr": round(cagr(r), 4), "max_dd": round(max_dd(r), 4),
                    "inside": cagr(r) > cagr(fb) and max_dd(r) >= max_dd(fb) - tol}
        reps.append({"cut": str(cut.date()), "to": str(nxt.date()), "n_pass_before_cut": ev["n_pass"],
                     "bh_forward": {"cagr": round(cagr(fb), 4), "max_dd": round(max_dd(fb), 4)},
                     "pick": fwd(ev["pick"]), "naive": fwd(ev["naive"]),
                     "family_picks": {f: fwd(k) for f, k in ev["family_pick"].items()}})
    need = math.ceil(cfg["timemachine"]["min_inside"] * len(cuts) - 1e-9)
    inside = sum(bool(r["pick"] and r["pick"]["inside"]) for r in reps)
    naive_in = sum(bool(r["naive"] and r["naive"]["inside"]) for r in reps)
    fam_pass = {f: sum(bool(r["family_picks"][f] and r["family_picks"][f]["inside"]) for r in reps) >= need for f in fams}
    return {"replays": reps, "inside": inside, "need": need, "passed": inside >= need, "naive_inside": naive_in,
            "family_passed": fam_pass}


# ============================================================================================ Block B (monthly)
def monthly(D: pd.DataFrame) -> pd.DataFrame:
    g = (1 + D[["mkt", "rf"]]).resample("ME").prod() - 1
    return g


def run_block_b(M: pd.DataFrame, cfg: dict) -> dict:
    """M columns: mkt, rf, bond, tsmom (excess). Monthly books; weights decided at month end t, held in t+1."""
    c, B = cfg["costs"], cfg["block_b"]
    X = pd.DataFrame({"eq": M["mkt"] - M["rf"], "bond": M["bond"] - M["rf"], "ts": M["tsmom"]})
    fees = {"eq": c["index_fee_annual"], "bond": c["bond_fee_annual"], "ts": c["trend_fee_annual"]}
    look = B["vol_lookback_months"]
    runs = {}

    def book(W: pd.DataFrame, mult: float, lag: int) -> pd.Series:
        Wh = W.shift(lag).fillna(0.0)
        gross = Wh.sum(axis=1)
        fee = sum(Wh[k] * fees[k] for k in fees) * mult / 12
        drift = (Wh.shift(1) * (X.shift(1).sub((Wh.shift(1) * X.shift(1)).sum(axis=1), axis=0)).abs()).sum(axis=1)
        turn = Wh.diff().abs().sum(axis=1).fillna(Wh.abs().sum(axis=1)) + drift.fillna(0.0)
        borrow = (gross - 1).clip(lower=0) * c["borrow_spread_annual"] * mult / 12
        cash = (1 - gross).clip(lower=0) * c["cash_fee_annual"] * mult / 12
        return M["rf"] + (Wh * X).sum(axis=1) - fee - borrow - cash - turn * c["trade_per_side"] * mult

    for fam, spec in B["families"].items():
        for p in grid_points(spec["grid"]):
            if fam == "B1_stack":
                W = pd.DataFrame({"eq": 1.0, "bond": 0.0, "ts": p["k"]}, index=X.index)
            else:
                sd = X.rolling(look, min_periods=24).std()
                w = (1 / sd).div((1 / sd).sum(axis=1), axis=0)
                pv = pd.Series(np.nan, index=X.index)
                for i in range(len(X)):
                    if i < 24 or w.iloc[i].isna().any():
                        continue
                    S = X.iloc[max(0, i - look + 1):i + 1].cov().to_numpy()
                    wi = w.iloc[i].to_numpy()
                    pv.iloc[i] = math.sqrt(max(wi @ S @ wi, 1e-12) * 12)
                s = (p["target"] / pv).clip(upper=p["Lmax"])
                W = w.mul(s, axis=0).fillna(0.0)
            runs[key(fam, p)] = {"fam": fam, "p": p, "r1": book(W, 1, 1), "r2": book(W, 2, 1), "rd": book(W, 1, 2)}
    return runs


# ============================================================================================ Block C
def spy_frame(S: pd.DataFrame) -> pd.DataFrame:
    r = S["px"].pct_change()
    rf = (1 + S["irx"].ffill() / 100.0) ** (1 / 252) - 1
    return pd.DataFrame({"mkt": r, "rf": rf, "mom_top": np.nan}).dropna(subset=["mkt"])


def replicate(fam: str, p: dict, S: pd.DataFrame, cfg: dict, start: str) -> dict:
    c = dict(cfg["costs"], index_fee_annual=0.0)        # SPY prices already carry the fund fee
    tgt, asset, _ = target_a(fam, p, S, cfg["block_a"]["vol_lookback_days"])
    band_f = 0.0 if fam in ("A0_const_lev", "A1_trend_lev") else cfg["no_trade_band"]
    out = {}
    bh = _cut(S["mkt"], pd.Timestamp(start), S.index[-1], True)
    rf = _cut(S["rf"], pd.Timestamp(start), S.index[-1], True)
    for m in (1, 2):
        r = _cut(simulate(asset, S["rf"], tgt, c, m, cfg["lag_days"], band_f, 0.0), pd.Timestamp(start), S.index[-1], True)
        out[f"{m}x"] = stats(r, rf)
        out[f"C1_{m}x"] = c1(r, bh, rf, cfg["accept"]["C1_full"]["max_dd_tolerance"])
        if m == 1:
            out["series"] = r
    out["bh"] = stats(bh, rf)
    out["yearly"] = {str(y): [round(float((1 + g).prod() - 1), 4)
                              for g in (out["series"][out["series"].index.year == y], bh[bh.index.year == y])]
                     for y in sorted(set(bh.index.year))}
    return out


def crypto_mix(core_r: pd.Series, crypto_r: pd.Series, c: float, cost: float) -> pd.Series:
    """Monthly rebalanced (1-c) core + c crypto; weights drift inside the month. Calendar-day index."""
    idx = crypto_r.index.union(core_r.index)
    a, b = core_r.reindex(idx).fillna(0.0), crypto_r.reindex(idx).fillna(0.0)
    va, vb, out, month = 1 - c, c, [], None
    for t, ra, rb in zip(idx, a.to_numpy(), b.to_numpy()):
        v = va + vb
        if month != (t.year, t.month):
            month = (t.year, t.month)
            ta, tb = (1 - c) * v, c * v
            v -= (abs(ta - va) + abs(tb - vb)) * cost
            va, vb = (1 - c) * v, c * v
        va, vb = va * (1 + ra), vb * (1 + rb)
        out.append((va + vb) / v - 1)
    return pd.Series(out, index=idx)


# ============================================================================================ forward record
def forward_record(prev: dict, series: dict, cfg: dict) -> dict:
    """Frozen picks and watch entries: realised months after `frozen_on`, and a degradation flag.

    series = {name: (key, strategy returns, benchmark returns)}. A pick is frozen: a later run never swaps
    the key of an existing name silently (the old key is kept and reported)."""
    F = cfg["forward"]
    frozen = pd.Timestamp(F["frozen_on"])
    out = {"frozen_on": F["frozen_on"], "picks": {}}
    for name, (k, r, b) in series.items():
        old = (prev.get("picks") or {}).get(name)
        row = {"key": k}
        if old and old.get("key") != k:
            row["note"] = f"frozen key {old['key']} differs from today's {k}; the frozen one is the record"
            row["key"] = old["key"]
        act_m = ((1 + r).resample("ME").prod() - (1 + b.reindex(r.index).fillna(0.0)).resample("ME").prod()).dropna()
        fwd = act_m[act_m.index > frozen + pd.offsets.MonthEnd(0)]
        row.update({"months": int(len(fwd)), "forward_active_sum": round(float(fwd.sum()), 4),
                    "last_month": str(act_m.index[-1].date()) if len(act_m) else None})
        if len(fwd) >= F["min_months"]:
            hist = act_m[act_m.index <= frozen].rolling(len(fwd)).sum().dropna()
            lo = float(np.percentile(hist, F["degrade_percentile"]))
            row.update({"p5": round(lo, 4), "degraded": bool(float(fwd.sum()) < lo)})
        else:
            row["degraded"] = None
        out["picks"][name] = row
    return out


# ============================================================================================ report
def _pct(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}%"


def _p(x, d=1):
    return "—" if x is None else f"{x * 100:.{d}f}%"


def report(res: dict) -> str:
    A, B, C = res["block_a"], res["block_b"], res["block_c"]
    L = ["# H072 sentez çalışması — endeksi yenen kurallar", "",
         f"Tarih: {res['run_at'][:10]}. Veri sonu: Blok A {A['bh']['end']}, Blok B {B['bh']['end']}. "
         f"Toplam deneme: **{res['n_trials']}** (DSR bu sayıyla hesaplandı).", "",
         "Kurallar sonuçlardan ÖNCE yazıldı: `config/synthesis.yaml` (commit `c1566c0`). Ölçüt nakit değil, "
         "**endeksin kendisi** (ABD piyasası toplam getiri, 1x).", ""]
    L += ["## Blok A — ABD piyasası, 1928 → bugün (günlük)", "",
          f"Endeks (al-tut): yıllık **{_p(A['bh']['cagr'])}**, Sharpe {A['bh']['sharpe']}, maks. düşüş "
          f"{_p(A['bh']['max_dd'])}, $1000 → ${A['bh']['final_1000']:,.0f}.", "",
          f"C1–C7'nin hepsini geçen nokta: **{A['n_pass']}** / {len(A['rows'])}.", "",
          "| Aile | Seçilen ayar | Yıllık | Endeks farkı | Sharpe | Maks. düşüş | 2x maliyet yıllık | DSR | Plato | Sonuç |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for fam, k in A["family_pick"].items():
        if k:
            r = A["rows"][k]
        else:
            ks = [x for x, r in A["rows"].items() if r["fam"] == fam]
            k = max(ks, key=lambda x: (sum(A["rows"][x]["checks"].values()), A["rows"][x]["plateau_score"]))
            r = A["rows"][k]
        fails = ",".join(x for x, ok in r["checks"].items() if not ok) or "—"
        verdict = "GEÇTİ" if r["pass"] else ("kıl payı" if r["near_miss"] else f"kaldı ({fails})")
        L.append(f"| {fam} | `{k.split('|')[1]}` | {_p(r['stats']['cagr'])} | {_pct(r['excess_cagr'])} | "
                 f"{r['stats']['sharpe']} | {_p(r['stats']['max_dd'])} | {_p(r['stats_2x']['cagr'])} | "
                 f"{r['dsr_active']} | {r['plateau_share']:.0%} | {verdict} |")
    L += ["", "Bir aile geçmediyse tabloda en çok kontrolü geçen ayarı gösterilir.", ""]
    pk = A["pick"]
    if pk:
        r = A["rows"][pk]
        L += [f"**Blok A seçimi (plato skoru en yüksek):** `{pk}`", "",
              "| Alt dönem | Strateji yıllık | Endeks yıllık | Strateji düşüş | Endeks düşüş | 2x maliyette endeksin üstünde |",
              "|---|---|---|---|---|---|"]
        for s in r["subperiods"]:
            L.append(f"| {s['from'][:4]}– | {_p(s['cagr'])} | {_p(s['bh_cagr'])} | {_p(s['max_dd'])} | "
                     f"{_p(s['bh_max_dd'])} | {'evet' if s['ok_2x'] else 'hayır'} |")
        L += ["", f"Aynı oynaklığa kaldıraçlanmış endeks ({r['vol_matched_L']}x): yıllık {_p(r['vol_matched_cagr'])}. "
              f"Strateji: {_p(r['stats']['cagr'])}. 1 gün daha geç işlem: {_p(r['stats_delay']['cagr'])}.", ""]
    L += ["### Kâr hedefi merdiveni (düşüş sınırına göre en sağlam geçen ayar)", "",
          "| Düşüş sınırı | Ayar | Yıllık | Maks. düşüş | $1000 → |", "|---|---|---|---|---|"]
    for x in A["ladder"]:
        s = x["stats"]
        money = f"${s['final_1000']:,.0f}" if s else "—"
        L.append(f"| {_p(x['max_dd_limit'], 0)} | `{x['pick'] or 'yok'}` | {_p(s['cagr']) if s else '—'} | "
                 f"{_p(s['max_dd']) if s else '—'} | {money} |")
    tm = A["timemachine"]
    L += ["", "### Zaman makinesi (seçim süreci geçmişte, ileri dönem görülmeden)", "",
          f"Geçme şartı: {tm['need']}/{len(tm['replays'])} kesimde ileri kayıt endeksin üstünde ve düşüş en çok 5 puan "
          f"derin. Sonuç: **{tm['inside']}/{len(tm['replays'])} → {'GEÇTİ' if tm['passed'] else 'KALDI'}**. "
          f"Kontrolsüz 'en yüksek getiri' seçimi: {tm['naive_inside']}/{len(tm['replays'])}.", "",
          "| Kesim | İleri dönem | Kesimden önce geçen | Seçim | İleri yıllık | Endeks ileri yıllık | İleri düşüş | Endeks düşüş | İçeride |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in tm["replays"]:
        p = r["pick"]
        L.append(f"| {r['cut']} | → {r['to']} | {r['n_pass_before_cut']} | `{p['key'] if p else 'yok'}` | "
                 f"{_p(p['cagr']) if p else '—'} | {_p(r['bh_forward']['cagr'])} | {_p(p['max_dd']) if p else '—'} | "
                 f"{_p(r['bh_forward']['max_dd'])} | {'evet' if p and p['inside'] else 'hayır'} |")
    L += ["", "Aile bazında zaman makinesi: " + ", ".join(f"{f} {'geçti' if ok else 'kaldı'}"
                                                         for f, ok in tm["family_passed"].items()), ""]
    L += ["## Blok B — çoklu varlık + trend takibi, 1988 → bugün (aylık)", "",
          f"Endeks: yıllık {_p(B['bh']['cagr'])}, Sharpe {B['bh']['sharpe']}, maks. düşüş {_p(B['bh']['max_dd'])}. "
          f"Geçen nokta: **{B['n_pass']}** / {len(B['rows'])}.", "",
          "| Ayar | Yıllık | Fark | Sharpe | Maks. düşüş | 2x maliyet | DSR | Plato | Sonuç |", "|---|---|---|---|---|---|---|---|---|"]
    for k, r in B["rows"].items():
        fails = ",".join(x for x, ok in r["checks"].items() if not ok) or "—"
        L.append(f"| `{k}` | {_p(r['stats']['cagr'])} | {_pct(r['excess_cagr'])} | {r['stats']['sharpe']} | "
                 f"{_p(r['stats']['max_dd'])} | {_p(r['stats_2x']['cagr'])} | {r['dsr_active']} | "
                 f"{r['plateau_share']:.0%} | {'GEÇTİ' if r['pass'] else ('kıl payı' if r['near_miss'] else 'kaldı (' + fails + ')')} |")
    tb = B["timemachine"]
    L += ["", f"Zaman makinesi (Blok B): **{tb['inside']}/{len(tb['replays'])} → {'GEÇTİ' if tb['passed'] else 'KALDI'}** "
          f"(şart {tb['need']}).", ""]
    only7 = [(k, r) for blk in (A, B) for k, r in blk["rows"].items()
             if not r["pass"] and [x for x, ok in r["checks"].items() if not ok] == ["C7"]]
    from scipy.stats import norm
    zb = norm.ppf(1 - 0.05 / res["n_trials"])
    L += ["### Sadece şans testinde (C7) kalanlar — bilgi, karar değil", "",
          "Kural değişmedi: bu satırlar KABUL DEĞİLDİR. C7 eşiği denemeler arası Sharpe dağılımından hesaplanır. "
          f"Ek bilgi olarak aktif getirinin t-değeri ve {res['n_trials']} deneme için Bonferroni eşiği "
          f"(tek yönlü %5: t ≥ {zb:.2f}) verilir.", "",
          "| Ayar | Yıllık fark | DSR | Aktif t | Bonferroni eşiği geçer mi |", "|---|---|---|---|---|"]
    for k, r in only7:
        L.append(f"| `{k}` | {_pct(r['excess_cagr'])} | {r['dsr_active']} | {r['t_active']} | "
                 f"{'evet' if r['t_active'] >= zb else 'hayır'} |")
    if not only7:
        L.append("| — | — | — | — | — |")
    L += [""]
    L += ["## Blok C — gerçek enstrüman (SPY) ve kripto kolu", ""]
    if C.get("replicate"):
        L += ["| Aile seçimi | SPY 1x yıllık | SPY 2x maliyet | SPY al-tut | C1 1x | C1 2x |", "|---|---|---|---|---|---|"]
        for k, r in C["replicate"].items():
            L.append(f"| `{k}` | {_p(r['1x']['cagr'])} (DD {_p(r['1x']['max_dd'])}) | {_p(r['2x']['cagr'])} | "
                     f"{_p(r['bh']['cagr'])} (DD {_p(r['bh']['max_dd'])}) | {'evet' if r['C1_1x'] else 'hayır'} | "
                     f"{'evet' if r['C1_2x'] else 'hayır'} |")
    else:
        L.append("Blok A'da geçen aile yok; SPY tekrarı yapılmadı.")
    cm = C.get("crypto")
    if cm:
        L += ["", f"Kripto kolu (H054) çekirdek: `{cm['core']}`.", "",
              "| c | Yıllık | Sharpe | Maks. düşüş | Çekirdek yıllık | Çekirdek düşüş | Kabul |", "|---|---|---|---|---|---|---|"]
        for cc, r in cm["rows"].items():
            L.append(f"| {cc} | {_p(r['mix']['cagr'])} | {r['mix']['sharpe']} | {_p(r['mix']['max_dd'])} | "
                     f"{_p(r['core']['cagr'])} | {_p(r['core']['max_dd'])} | {'evet' if r['accepted'] else 'hayır'} |")
    else:
        L += ["", "Kripto kolu: H054 serisi indirilemedi, test edilmedi."]
    fw = res.get("forward", {}).get("picks", {})
    L += ["", "## İleri kayıt (kendini güncelleyen döngü)", "",
          f"Dondurma tarihi: {res.get('forward', {}).get('frozen_on')}. Her aylık çalışma yeni ayları ekler. "
          "Bozulma = ileri aktif getiri, kendi geçmişindeki aynı uzunluktaki dönemlerin en kötü %5'inin altında.", "",
          "| Kayıt | Ay | İleri aktif getiri (toplam) | Bozuldu mu |", "|---|---|---|---|"]
    for n, r in fw.items():
        dg = "henüz erken" if r.get("degraded") is None else ("EVET" if r["degraded"] else "hayır")
        L.append(f"| `{n}` | {r['months']} | {_pct(r['forward_active_sum'])} | {dg} |")
    L += ["", "## Zayıf yönler (her zaman)", ""] + [f"- {w}" for w in res["weak_points"]]
    return "\n".join(L) + "\n"


WEAK = [
    "Blok A verisi CRSP tüm ABD piyasası (Ken French). S&P 500 ile korelasyonu çok yüksek ama aynı değildir.",
    "1928–1990 döneminde kaldıraçlı endeks fonu yoktu. Finansman maliyeti (T-bill + %1,25) bugünkü kaldıraçlı ETF ve vadeli işlem maliyetinden türetildi.",
    "Kaldıraç kenar yaratmaz. Geçen kurallarda kenar düşüşten kaçınmadan gelir (trend filtresi). V şeklindeki çöküşlerde (1987, 2020) bu koruma geç kalır.",
    "Momentum ailesi (A4) akademik portföydür. Gerçek ETF (ör. MTUM) daha az getiri verir; %1,5 yıllık ek maliyet bir tahmindir.",
    "AQR TSMOM serisi brüt yönetim ücretidir; %1 ücret düşüldü. Perakende yatırımcı için en yakın araç yönetilen vadeli fon ETF'leridir (2019+).",
    "Geçmişteki en kötü düşüş, gelecekteki en kötü düşüş değildir. Ladder tablosu bir üst sınırdır, hedef değil.",
    "Vergi, kur (TL) ve aracı kurum erişimi modellenmedi.",
    "Bu çalışma bir ön elemedir. Geçen kural yine de karar kapısından (validation.GATE) ve ileri kayıttan geçmelidir.",
]


# ============================================================================================ main
def _compact(ev: dict) -> dict:
    out = {k: v for k, v in ev.items() if k != "rows"}
    out["rows"] = {k: {x: y for x, y in r.items()} for k, r in ev["rows"].items()}
    return out


def main() -> None:
    global OFFLINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    OFFLINE = ap.parse_args().offline
    cfg = load_cfg()
    c = cfg["costs"]
    res = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n_trials": cfg["n_trials"],
           "weak_points": WEAK}

    # ---- Block A
    D = load_us_daily()
    A = cfg["block_a"]
    runs_a = run_block_a(D, cfg)
    bh_a = bench(D["mkt"], c, c["index_fee_annual"])
    fams_a = A["families"]
    a0, a1 = pd.Timestamp(A["start"]), D.index[-1]
    subs = windows(A["start"], A["subperiods"], a1 + pd.Timedelta(days=1))
    ev_a = evaluate(runs_a, fams_a, bh_a, D["rf"], D["mkt"], subs, a0, a1, cfg, c["index_fee_annual"])
    ev_a["ladder"] = ladder(ev_a, cfg["ladder_max_dd"])
    ev_a["timemachine"] = time_machine(runs_a, fams_a, bh_a, D["rf"], D["mkt"], A["start"], A["subperiods"],
                                       cfg["timemachine"]["block_a_cuts"], cfg, c["index_fee_annual"])
    res["block_a"] = _compact(ev_a)

    # ---- Block B
    B = cfg["block_b"]
    Md = monthly(D)
    ts = load_tsmom_monthly()
    bond = load_bond_monthly()
    M = pd.concat([Md, bond.rename("bond"), ts.rename("tsmom")], axis=1).dropna()
    runs_b = run_block_b(M, cfg)
    bh_b = bench(M["mkt"], c, c["index_fee_annual"])
    b0, b1 = pd.Timestamp(B["start"]), M.index[-1]
    subs_b = windows(B["start"], B["subperiods"], b1 + pd.Timedelta(days=1))
    ev_b = evaluate(runs_b, B["families"], bh_b, M["rf"], M["mkt"], subs_b, b0, b1, cfg, c["index_fee_annual"])
    ev_b["timemachine"] = time_machine(runs_b, B["families"], bh_b, M["rf"], M["mkt"], B["start"], B["subperiods"],
                                       cfg["timemachine"]["block_b_cuts"], cfg, c["index_fee_annual"])
    res["block_b"] = _compact(ev_b)

    # ---- Block C
    Cc = cfg["block_c"]
    resc, mixes = {}, {}
    try:
        S = spy_frame(load_spy())
        rep = {}
        for fam, k in ev_a["family_pick"].items():
            if k and fam != "A4_mom_trend":            # academic decile portfolio: no ETF with the same history
                rep[k] = replicate(fam, ev_a["rows"][k]["p"], S, cfg, "1994-01-01")
        core_key = ev_a["pick"]
        core_r = rep[core_key]["series"] if core_key in rep else _cut(S["mkt"], pd.Timestamp("1994-01-01"), S.index[-1], True)
        resc["replicate"] = {k: {x: y for x, y in v.items() if x != "series"} for k, v in rep.items()}
        h054 = {m: load_h054_daily(m) for m in (1, 2)}
        if h054[1] is not None:
            st = pd.Timestamp(Cc["crypto_start"])
            core = _cut(core_r, st, min(core_r.index[-1], h054[1].index[-1]), True)
            rf_d = S["rf"].reindex(pd.date_range(st, core.index[-1])).fillna(0.0)
            cal_core = core.reindex(pd.date_range(st, core.index[-1])).fillna(0.0)
            rows = {}
            for cw in Cc["crypto_grid"]["c"]:
                mix = crypto_mix(core, _cut(h054[1], st, core.index[-1], True), cw, c["trade_per_side"])
                mix2 = crypto_mix(core, _cut(h054[2], st, core.index[-1], True), cw, 2 * c["trade_per_side"])
                ok = []
                for w0 in [st] + [pd.Timestamp(x) for x in Cc["crypto_windows"]]:
                    m, b = mix[mix.index >= w0], cal_core[cal_core.index >= w0]
                    rfw = rf_d[rf_d.index >= w0]
                    ok.append(cagr(m) > cagr(b) and sharpe(m, rfw) > sharpe(b, rfw)
                              and max_dd(m) >= max_dd(b) - Cc["crypto_accept"]["max_extra_dd"])
                rows[str(cw)] = {"mix": stats(mix, rf_d), "mix_2x": stats(mix2, rf_d), "core": stats(cal_core, rf_d),
                                 "windows_ok": ok, "accepted": all(ok)}
                mixes[f"C2_crypto|c={cw}"] = (mix, cal_core)
            resc["crypto"] = {"core": core_key or "SPY al-tut", "rows": rows}
    except Exception as e:
        resc["error"] = str(e)
        print("Block C skipped:", e)
    res["block_c"] = resc
    res["data_sources"] = {"us_market": "Ken French daily (CRSP)", "trend": "AQR TSMOM monthly",
                           "bond10": BOND_SOURCE["name"], "etf": "Yahoo SPY + ^IRX",
                           "crypto": "lab/core.py H054 on 4h bars (Bitget via ccxt, else Binance Vision)"}

    # ---- forward record (self-improving loop)
    OUT.mkdir(parents=True, exist_ok=True)
    fp = OUT / "forward.json"
    prev = json.loads(fp.read_text()) if fp.exists() else {}
    series = {}
    for name, k in {"A": ev_a["pick"], **{f"A:{f}": k for f, k in ev_a["family_pick"].items()}}.items():
        if k:
            series[name] = (k, runs_a[k]["r1"], bh_a)
    for w in cfg["forward"].get("watch", []):
        if w in runs_b:
            series[f"watch:{w}"] = (w, runs_b[w]["r1"], bh_b)
        elif w in mixes:
            series[f"watch:{w}"] = (w, *mixes[w])
    res["forward"] = forward_record(prev, series, cfg)
    fp.write_text(json.dumps(res["forward"], indent=1, default=str))
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str))
    (OUT / "report.md").write_text(report(res))
    print(report(res))


if __name__ == "__main__":
    main()
