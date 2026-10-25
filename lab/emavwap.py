"""H078 9 EMA x session VWAP cross, intraday (config/emavwap.yaml, pre-registered).

Signals at bar close t, fill at open t+1, flat at the last bar of each session. Output is a lead, never a decision.
    python -m lab.emavwap            -> results/h078_emavwap.json + .md
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from lab import assetdata
from lab.indicators import ema, session_vwap

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config/emavwap.yaml").read_text())
RULE = {"min": "min", "3m": "3min", "5m": "5min", "15m": "15min", "60m": "60min"}


def _ohlc(df: pd.DataFrame, tf: str, origin) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return df.resample(RULE[tf], origin=origin, label="left", closed="left").agg(agg).dropna(subset=["close"])


def stock_bars(t: str, tf: str) -> pd.DataFrame:
    import yfinance as yf
    if tf == "3m":   # yahoo serves 1m for the last ~30 days only, 7 days per request
        end = pd.Timestamp.now(tz="UTC").normalize() + pd.Timedelta(days=1)
        parts = [yf.download(t, interval="1m", start=(end - pd.Timedelta(days=7 * (i + 1))).date(),
                             end=(end - pd.Timedelta(days=7 * i)).date(), progress=False, auto_adjust=False)
                 for i in range(4)]
        raw = pd.concat([p for p in parts if len(p)])
    else:
        raw = yf.download(t, interval=tf, period="730d" if tf == "60m" else "60d", progress=False, auto_adjust=False)
    raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
    raw = raw[~raw.index.duplicated()].sort_index()
    raw.index = raw.index.tz_convert("America/New_York")
    raw = raw.between_time("09:30", "15:59")
    if tf == "3m":
        raw = pd.concat([_ohlc(g, "3m", "start_day") for _, g in raw.groupby(raw.index.date)])
    return raw[["open", "high", "low", "close", "volume"]]


def crypto_bars(sym: str, tf: str) -> pd.DataFrame:
    df = assetdata.binance_vision(sym, "3m", start=CFG["crypto_start"])
    df = df[~df.index.duplicated()].sort_index().rename(columns=str.lower)
    return df if tf == "3m" else _ohlc(df, tf, "start_day")


def trades(df: pd.DataFrame, n: int, exit_: str, side: str) -> pd.DataFrame:
    """One position at a time; returns gross per-trade log-free simple returns with entry time."""
    day = pd.Series(df.index.date, index=df.index)
    e = ema(df["close"], n)      # EMA runs across sessions, as on the chart
    vw = session_vwap(df["high"], df["low"], df["close"], df["volume"], day)
    above = (e > vw).astype(int)
    up = (above.diff() == 1) & (day == day.shift(1))     # no cross from the previous session's VWAP
    dn = (above.diff() == -1) & (day == day.shift(1))
    last = day != day.shift(-1)
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    up, dn, last, ev = up.to_numpy(), dn.to_numpy(), last.to_numpy(), e.to_numpy()
    out, pos, px, t0 = [], 0, 0.0, None
    for i in range(len(df) - 1):
        if pos:
            stop = (dn[i] if pos > 0 else up[i]) if exit_ == "cross" else (c[i] < ev[i] if pos > 0 else c[i] > ev[i])
            if last[i]:
                out.append((t0, pos * (c[i] / px - 1))); pos = 0
            elif stop:
                out.append((t0, pos * (o[i + 1] / px - 1))); pos = 0
        if not pos and not last[i]:
            if up[i]:
                pos, px, t0 = 1, o[i + 1], df.index[i + 1]
            elif dn[i] and side == "both":
                pos, px, t0 = -1, o[i + 1], df.index[i + 1]
    return pd.DataFrame(out, columns=["t", "r"])


def stats(tr: pd.DataFrame, cost: float) -> dict:
    if not len(tr):
        return {"n": 0}
    r = tr["r"] - 2 * cost
    g, ls = r[r > 0].sum(), -r[r < 0].sum()
    h = len(r) // 2
    eq = (1 + r).cumprod()
    return {"n": int(len(r)), "mean_bps": round(r.mean() * 1e4, 2), "win": round((r > 0).mean(), 3),
            "pf": round(g / ls, 3) if ls else None, "total_pct": round((eq.iloc[-1] - 1) * 100, 2),
            "maxdd_pct": round((eq / eq.cummax() - 1).min() * 100, 2),
            "h1_bps": round(r.iloc[:h].mean() * 1e4, 2), "h2_bps": round(r.iloc[h:].mean() * 1e4, 2)}


def run() -> dict:
    g, acc = CFG["grid"], CFG["acceptance"]
    jobs = [(t, tf, "stock") for t in CFG["stocks"] for tf in CFG["stock_tfs"]] + \
           [(t, tf, "crypto") for t in CFG["crypto"] for tf in CFG["crypto_tfs"]]
    res = []
    for t, tf, kind in jobs:
        try:
            df = stock_bars(t, tf) if kind == "stock" else crypto_bars(t, tf)
        except Exception as ex:
            print(f"[h078] {t} {tf} data failed: {ex}"); continue
        cost = CFG["cost_bps_side"][kind] / 1e4
        cell = {"market": t, "tf": tf, "bars": len(df), "from": str(df.index[0])[:10], "to": str(df.index[-1])[:10],
                "settings": {}}
        for n in g["ema"]:
            for ex in g["exit"]:
                for sd in g["side"]:
                    tr = trades(df, n, ex, sd)
                    cell["settings"][f"ema{n}_{ex}_{sd}"] = {"1x": stats(tr, cost), "2x": stats(tr, 2 * cost)}
        v, s = cell["settings"], cell["settings"]["ema9_cross_long"]
        checks = {"min_trades": s["1x"]["n"] >= acc["min_trades"],
                  "pf_1x": (s["1x"].get("pf") or 0) >= acc["pf_1x_min"],
                  "mean_2x_pos": s["2x"].get("mean_bps", -1) > 0,
                  "both_halves": min(s["1x"].get("h1_bps", -1), s["1x"].get("h2_bps", -1)) > 0,
                  "neighbours": all(v[f"ema{k}_cross_long"]["1x"].get("mean_bps", -1) > 0 for k in (7, 12))}
        checks = {k: bool(x) for k, x in checks.items()}
        cell["checks"], cell["pass"] = checks, all(checks.values())
        res.append(cell)
        print(f"[h078] {t:8s} {tf:4s} n={s['1x']['n']:5d} mean1x={s['1x'].get('mean_bps')} "
              f"pf={s['1x'].get('pf')} 2x={s['2x'].get('mean_bps')} pass={cell['pass']}")
    out = {"hypothesis": "H078", "trials": len(res) * 12, "cells": res}
    (ROOT / "results/h078_emavwap.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    run()
