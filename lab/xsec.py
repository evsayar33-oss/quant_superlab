"""Market-neutral cross-sectional study on Binance USDT-M perps (config/xsec.yaml).

H055 momentum, H056 funding carry, H058 low volatility. Free data: data.binance.vision monthly files
(daily klines + funding), DELISTED symbols included (survivorship control). Daily bookkeeping:
weights fixed at the Monday rebalance (signals from data up to the Sunday close), held to the next one.
Return = sum w * perp return - sum w * funding (long pays, short receives) - costs on turnover.

  python -m lab.xsec            (needs network; run in GitHub Actions)
  python -m lab.xsec --synthetic
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "xsec"
OUT = ROOT / "decisions" / "xsec"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FILE = "https://data.binance.vision/"
PPY = 365


# ------------------------------------------------------------------ data
def _get(url: str, tries: int = 3) -> bytes | None:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if "404" in str(e):
                return None
            time.sleep(1 + i * 2)
    return None


def _list(prefix: str, dirs: bool) -> list[str]:
    out, marker = [], ""
    while True:
        raw = _get(f"{S3}?delimiter=/&prefix={prefix}&marker={marker}")
        if raw is None:
            break
        t = raw.decode()
        items = re.findall(r"<Prefix>([^<]+)</Prefix>", t) if dirs else re.findall(r"<Key>([^<]+)</Key>", t)
        items = [x for x in items if x != prefix]
        out += items
        if "<IsTruncated>true</IsTruncated>" not in t or not items:
            break
        nm = re.findall(r"<NextMarker>([^<]+)</NextMarker>", t)
        marker = nm[0] if nm else items[-1]
    return out


def _zip_csv(raw: bytes) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(raw))
    df = pd.read_csv(z.open(z.namelist()[0]), header=None)
    if not str(df.iloc[0, 0]).replace(".", "").isdigit():
        df = df.iloc[1:]
    return df


def _symbol(sym: str, start: str) -> tuple[pd.DataFrame | None, pd.Series | None]:
    pk, pf = CACHE / f"{sym}_k.csv", CACHE / f"{sym}_f.csv"
    k = pd.read_csv(pk, index_col=0, parse_dates=True) if pk.exists() else None
    f = pd.read_csv(pf, index_col=0, parse_dates=True).iloc[:, 0] if pf.exists() else None
    have_k = set(k.index.to_period("M").astype(str)) if k is not None else set()
    have_f = set(f.index.to_period("M").astype(str)) if f is not None else set()
    last_full = str((pd.Timestamp.utcnow().tz_localize(None) - pd.offsets.MonthBegin(1)).to_period("M") - 1)
    kparts, fparts = [k] if k is not None else [], [f] if f is not None else []
    for key in _list(f"data/futures/um/monthly/klines/{sym}/1d/", dirs=False):
        if not key.endswith(".zip"):
            continue
        m = key[-11:-4]
        if m < start or (m in have_k and m < last_full):
            continue
        raw = _get(FILE + key)
        if raw is None:
            continue
        d = _zip_csv(raw)
        idx = pd.to_datetime(d[0].astype("int64"), unit="ms").dt.normalize()
        kparts.append(pd.DataFrame({"close": d[4].astype(float).values, "qv": d[7].astype(float).values},
                                   index=idx.values))
    for key in _list(f"data/futures/um/monthly/fundingRate/{sym}/", dirs=False):
        if not key.endswith(".zip"):
            continue
        m = key[-11:-4]
        if m < start or (m in have_f and m < last_full):
            continue
        raw = _get(FILE + key)
        if raw is None:
            continue
        d = _zip_csv(raw)
        s = pd.Series(d[2].astype(float).values, index=pd.to_datetime(d[0].astype("int64"), unit="ms"))
        fparts.append(s.groupby(s.index.normalize()).sum())
    k = pd.concat(kparts).sort_index() if kparts else None
    f = pd.concat(fparts).sort_index() if fparts else None
    if k is not None:
        k = k[~k.index.duplicated(keep="last")]
        k.to_csv(pk)
    if f is not None:
        f = f[~f.index.duplicated(keep="last")]
        f.rename("funding").to_csv(pf)
    return k, f


def load(cfg: dict) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    dirs = _list("data/futures/um/monthly/klines/", dirs=True)
    syms = sorted({d.rstrip("/").split("/")[-1] for d in dirs})
    ex = tuple(cfg["universe"]["exclude"])
    syms = [s for s in syms if s.endswith("USDT") and not s[:-4].startswith(ex) and "_" not in s]
    print(f"[xsec] {len(syms)} USDT-M symbols (delisted included)")
    with ThreadPoolExecutor(16) as pool:
        res = list(pool.map(lambda s: (s, *_symbol(s, cfg["start"])), syms))
    C = pd.DataFrame({s: k["close"] for s, k, _ in res if k is not None and len(k)})
    Q = pd.DataFrame({s: k["qv"] for s, k, _ in res if k is not None and len(k)})
    F = pd.DataFrame({s: f for s, _, f in res if f is not None and len(f)}).reindex(C.index).fillna(0.0)
    return {"C": C.sort_index(), "Q": Q.reindex(C.index), "F": F.reindex(columns=C.columns).fillna(0.0)}


def synthetic(n: int = 80, days: int = 2200, seed: int = 3) -> dict:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=days, freq="D")
    mkt = rng.normal(0.001, 0.035, days)
    R = mkt[:, None] * rng.uniform(0.7, 1.5, n) + rng.normal(0, 0.04, (days, n))
    C = pd.DataFrame(100 * np.exp(np.cumsum(R, axis=0)), idx, [f"C{i}USDT" for i in range(n)])
    for i in range(0, n, 7):                                    # staggered listings and delistings
        C.iloc[: rng.integers(0, days // 2), i] = np.nan
        if i % 2:
            C.iloc[rng.integers(days // 2, days):, i] = np.nan
    Q = pd.DataFrame(rng.lognormal(16, 1, (days, n)), idx, C.columns).where(C.notna())
    F = pd.DataFrame(rng.normal(0.0003, 0.0004, (days, n)), idx, C.columns).where(C.notna()).fillna(0.0)
    return {"C": C, "Q": Q, "F": F}


# ------------------------------------------------------------------ portfolio
def _leg(sig: pd.Series, vol: pd.Series, cap: float) -> pd.Series:
    w = (1 / vol.reindex(sig.index)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    w = w / w.sum() if w.sum() > 0 else pd.Series(1 / len(sig), sig.index)
    for _ in range(10):                                         # cap one coin at `cap` of its leg
        over = w > cap
        if not over.any():
            break
        extra = (w[over] - cap).sum()
        w[over] = cap
        rest = ~over
        w[rest] += extra * w[rest] / w[rest].sum() if w[rest].sum() > 0 else 0
    return w


def book(D: dict, cfg: dict, signal: str, lookback: int, long: str, phase: int | None = None,
         cost_mult: float = 1.0, delist_stress: float = 0.0) -> dict:
    C, Q, F = D["C"], D["Q"], D["F"]
    u, pc = cfg["universe"], cfg["portfolio"]
    R = C.pct_change(fill_method=None)
    age = C.notna().cumsum()
    medq = Q.rolling(30, min_periods=20).median()
    vol = R.rolling(pc["vol_lookback"], min_periods=20).std()
    if signal == "momentum":
        S = C / C.shift(lookback) - 1
    elif signal == "funding":
        S = F.where(C.notna()).rolling(lookback, min_periods=max(2, lookback // 2)).mean()
    elif signal == "lowvol":
        S = R.rolling(lookback, min_periods=int(lookback * 0.8)).std()
    else:
        raise ValueError(signal)
    wd = pc["rebalance_weekday"] if phase is None else phase
    W = pd.DataFrame(0.0, C.index, C.columns)
    cur = pd.Series(0.0, index=C.columns)
    for t in C.index:
        if t.weekday() == wd:
            ok = C.loc[t].notna() & (age.loc[t] >= u["min_age_days"]) & S.loc[t].notna() & vol.loc[t].notna()
            elig = medq.loc[t][ok].dropna().sort_values(ascending=False).head(u["top_n"]).index
            cur = pd.Series(0.0, index=C.columns)
            if len(elig) >= 15:
                s = S.loc[t, elig].sort_values(ascending=(long == "low"))
                n = len(s) // pc["quantile"]
                lg, sh = s.index[:n], s.index[-n:]
                cur[lg] = 0.5 * _leg(s[lg], vol.loc[t], pc["leg_cap"])
                cur[sh] = -0.5 * _leg(s[sh], vol.loc[t], pc["leg_cap"])
        W.loc[t] = cur
    Wh = W.shift(1).fillna(0.0)                                  # decided at close t-1, held during t
    alive = C.notna()
    gone = alive.shift(1, fill_value=False) & ~alive             # first missing day after the last bar
    Wh = Wh.where(alive | gone, 0.0)
    raw = (Wh * R.fillna(0.0)).sum(axis=1) - (Wh * F).sum(axis=1)
    if delist_stress:
        raw = raw - (Wh.abs() * gone).sum(axis=1) * delist_stress
    # vol target on the unscaled book (uses returns up to t-1), max gross
    rv = raw.rolling(pc["vol_window"], min_periods=30).std() * np.sqrt(PPY)
    k = (pc["vol_target"] / rv).clip(upper=pc["max_gross"]).shift(1).fillna(0.0)
    Ws = Wh.mul(k, axis=0)
    turn = Ws.diff().abs().sum(axis=1).fillna(Ws.abs().sum(axis=1))
    cps = (cfg["costs"]["fee"] + cfg["costs"]["slippage"]) * cost_mult
    r = raw * k - turn * cps
    gross = Ws.abs().sum(axis=1)
    fund = -(Ws * F).sum(axis=1)
    r = r[r.index >= cfg["test_start"]]
    return {"r": r, "turnover_week": float(turn[r.index].mean() * 7), "gross": float(gross[r.index].mean()),
            "funding_ann": float(fund[r.index].mean() * PPY)}


# ------------------------------------------------------------------ stats
def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 60:
        return {}
    eq = (1 + r).cumprod()
    lr = np.log1p(r.clip(lower=-0.99))
    yrs = len(r) / PPY
    yr = (1 + r).groupby(r.index.year).prod() - 1
    wk = (1 + r).resample("W").prod() - 1
    sd = r.std()
    return {"start": str(r.index[0].date()), "final_1000": round(1000 * float(eq.iloc[-1]), 0),
            "cagr": round(float(eq.iloc[-1] ** (1 / yrs) - 1), 4),
            "sharpe": round(float(r.mean() / sd * np.sqrt(PPY)) if sd > 0 else 0.0, 2),
            "t_log": round(float(lr.mean() / lr.std() * np.sqrt(len(lr))) if lr.std() > 0 else 0.0, 2),
            "max_dd": round(float((eq / eq.cummax() - 1).min()), 4),
            "worst_week": round(float(wk.min()), 4),
            "yearly": {str(k): round(float(v), 4) for k, v in yr.items()}}


def _weekly(r: pd.Series) -> pd.Series:
    return (1 + r).resample("W").prod() - 1


def bot_returns(D: dict) -> pd.Series | None:
    """The live bot: H054 + idle-cash funding arb (always_on), daily, from the core study code."""
    try:
        sys.path.insert(0, str(ROOT))
        import run as R
        from lab import core
        from lab import funding as Fm
        cc = yaml.safe_load((ROOT / "config" / "core.yaml").read_text())
        p = R._core_panel_loader(cc, False)("4h", ["BTC/USDT", "ETH/USDT"])
        closes = {a: p.c[a] for a in ["BTC/USDT", "ETH/USDT"]}
        cps = cc["costs"]["commission"] + cc["costs"]["slippage"]
        prm, band = cc["rules"]["dual_trend_vt"], cc["risk_levels"].get("band", 0.10)
        h = core.book_returns(closes, "dual_trend_vt", prm, p.ppy, cps, band, cc["variants"].get("funding_annual", 0.0))
        ex = core.book_exposure(closes, "dual_trend_vt", prm, p.ppy, band)
        h_d = (1 + h).groupby(h.index.normalize()).prod() - 1
        idle = (1 - ex.groupby(ex.index.normalize()).mean()).clip(0, 1)
        fund = pd.concat([Fm.daily_funding(Fm.load(s, "2020-01")) for s in cc["funding_arb"]["assets"]], axis=1).mean(axis=1)
        idx = h_d.index.intersection(fund.index)
        hedge = idle.reindex(idx).fillna(0).shift(1).fillna(0) * cc["idle_arb"]["hedge_share"]
        cost = hedge.diff().abs().fillna(hedge) * 2 * cc["funding_arb"]["cost_per_leg"]
        return h_d.reindex(idx) + hedge * fund.reindex(idx) - cost
    except Exception as e:  # noqa: BLE001
        print(f"[xsec] bot series unavailable: {e}")
        return None


# ------------------------------------------------------------------ study
def run(D: dict, cfg: dict) -> dict:
    a = cfg["accept"]
    btc = D["C"]["BTCUSDT"].pct_change(fill_method=None) if "BTCUSDT" in D["C"] else None
    bot = bot_returns(D) if "BTCUSDT" in D["C"] else None
    out = {"data_end": str(D["C"].index[-1].date()), "n_symbols": int(D["C"].shape[1]),
           "n_delisted": int((D["C"].iloc[-1].isna() & D["C"].notna().any()).sum()), "strategies": {}}
    trials = 0
    for hid, sc in cfg["strategies"].items():
        base = book(D, cfg, sc["signal"], sc["lookback"], sc["long"]); trials += 1
        r = base["r"]
        st = stats(r)
        c2 = stats(book(D, cfg, sc["signal"], sc["lookback"], sc["long"], cost_mult=a["cost_mult"])["r"])
        ds = stats(book(D, cfg, sc["signal"], sc["lookback"], sc["long"], delist_stress=a["delist_stress"])["r"])
        nb = {str(lb): stats(book(D, cfg, sc["signal"], lb, sc["long"])["r"]) for lb in sc["neighbours"]}
        ph = {str(p): stats(book(D, cfg, sc["signal"], sc["lookback"], sc["long"], phase=p)["r"]) for p in range(7)}
        trials += 2 + len(nb) + 7
        wr = _weekly(r)
        cb = float(wr.corr(_weekly(btc.reindex(r.index).fillna(0)))) if btc is not None else None
        cbot = float(wr.corr(_weekly(bot.reindex(r.index).fillna(0)))) if bot is not None else None
        chk = {
            "sharpe": st.get("sharpe", 0) >= a["min_sharpe"],
            "t_log": st.get("t_log", 0) >= a["min_t"],
            "bear_year": any(st.get("yearly", {}).get(str(y), -1) > 0 for y in a["bear_years"]),
            "cost_2x": c2.get("sharpe", -1) > 0,
            "phases": sum(1 for v in ph.values() if v.get("final_1000", 0) > 1000) >= a["min_phases"],
            "corr_btc": cb is not None and abs(cb) < a["max_corr"],
            "corr_bot": cbot is not None and abs(cbot) < a["max_corr"],
            "neighbours": all(v.get("sharpe", -1) > 0 for v in nb.values()),
            "delist_stress": ds.get("sharpe", -1) > 0,
        }
        res = {"name": sc["signal"], "base": st, "cost_2x": c2, "delist_stress": ds, "neighbours": nb,
               "phases": {k: {"final_1000": v.get("final_1000"), "sharpe": v.get("sharpe")} for k, v in ph.items()},
               "corr_btc": None if cb is None else round(cb, 2), "corr_bot": None if cbot is None else round(cbot, 2),
               "turnover_week": round(base["turnover_week"], 2), "gross": round(base["gross"], 2),
               "funding_ann": round(base["funding_ann"], 4), "checks": chk, "accepted": all(chk.values())}
        if res["accepted"] and bot is not None:
            res["combo"] = combo(bot, r, cfg["combo"])
        out["strategies"][hid] = res
    out["n_trials"] = trials
    return out


def combo(bot: pd.Series, x: pd.Series, cc: dict) -> dict:
    idx = bot.index.intersection(x.index)
    b, m = bot.reindex(idx), (1 - cc["share"]) * bot.reindex(idx) + cc["share"] * x.reindex(idx)
    win, ok_a, ok_b = {}, True, True
    for c in cc["cutoffs"]:
        sb, sm = stats(b[b.index > c]), stats(m[m.index > c])
        win[c] = {"bot": sb.get("final_1000"), "mix": sm.get("final_1000"), "bot_dd": sb.get("max_dd"), "mix_dd": sm.get("max_dd")}
        ok_a &= sm.get("final_1000", 0) >= sb.get("final_1000", 1e9)
        ok_b &= (sm.get("max_dd", -1) - sb.get("max_dd", 0) >= 0.05) and sm.get("final_1000", 0) >= 0.9 * sb.get("final_1000", 1e9)
    return {"bot": stats(b), "mix": stats(m), "windows": win, "accepted": bool(ok_a or ok_b)}


def report(o: dict) -> str:
    L = [f"Piyasa-nötr çalışma · veri sonu {o['data_end']} · {o['n_symbols']} sembol ({o['n_delisted']} delist) · {o['n_trials']} deneme"]
    for h, v in o["strategies"].items():
        b = v["base"]
        L.append(f"{h} {v['name']}: Sharpe {b.get('sharpe')} t {b.get('t_log')} CAGR {b.get('cagr')} DD {b.get('max_dd')} "
                 f"→ {'KABUL' if v['accepted'] else 'RED'} ({', '.join(k for k, x in v['checks'].items() if not x) or 'hepsi geçti'})")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "config" / "xsec.yaml").read_text())
    D = synthetic() if a.synthetic else load(cfg)
    if a.synthetic:
        D["C"] = D["C"].rename(columns={"C0USDT": "BTCUSDT"})
        D["Q"] = D["Q"].rename(columns={"C0USDT": "BTCUSDT"}); D["F"] = D["F"].rename(columns={"C0USDT": "BTCUSDT"})
    o = run(D, cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("synthetic.json" if a.synthetic else "result.json")).write_text(json.dumps(o, indent=1, default=str))
    print(report(o))


if __name__ == "__main__":
    main()
