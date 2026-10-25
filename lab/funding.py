"""Funding-rate arbitrage (cash-and-carry) on free data.

Funding history: Binance USDT-M monthly files (data.binance.vision, free, no key) - the proxy for Bitget,
whose public history endpoint only returns recent months. Cached in data/cache/funding_<SYM>.csv.

Book: long spot + short perp, equal notional = hedge_share x capital. Price moves cancel; the book earns
the funding received by the short (pays it when funding is negative). Costs: 4 legs per round trip.
Honest limits: spot-perp basis moves and exchange differences (Binance vs Bitget) are not modelled; the
short perp needs margin top-ups after big rallies (1x margin is liquidated only after a +100% move).
"""
from __future__ import annotations

import io
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from lab import metrics

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
URL = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip"


def load(symbol: str, start: str = "2020-01") -> pd.Series:
    """Funding rate per settlement (fraction, e.g. 0.0001 = 0.01%), indexed by settlement time (UTC)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"funding_{symbol}.csv"
    have = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0] if path.exists() else pd.Series(dtype=float)
    months = pd.period_range(start, pd.Timestamp.now(tz="UTC").tz_localize(None) - pd.offsets.MonthBegin(1), freq="M")
    got = set(have.index.to_period("M").astype(str)) if len(have) else set()
    parts = [have]
    for m in months:
        ms = str(m)
        if ms in got and ms != str(months[-1]):
            continue
        try:
            with urllib.request.urlopen(URL.format(s=symbol, m=ms), timeout=30) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            df = pd.read_csv(z.open(z.namelist()[0]))
            tcol = next(c for c in df.columns if "time" in c.lower())
            rcol = next(c for c in df.columns if "rate" in c.lower())
            s = pd.Series(df[rcol].astype(float).values, index=pd.to_datetime(df[tcol], unit="ms"))
            parts.append(s)
            time.sleep(0.2)
        except Exception as e:  # noqa: BLE001 - a missing month is skipped, the report shows the data range
            print(f"[funding] {symbol} {ms}: {e}")
    out = pd.concat(parts).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.rename("funding").to_csv(path)
    return out


def daily_funding(rates: pd.Series) -> pd.Series:
    return rates.groupby(rates.index.normalize()).sum()


def book(daily: pd.Series, rule: str, prm: dict, hedge_share: float, cost_per_leg: float) -> pd.Series:
    """Daily return on capital of the hedged book."""
    if rule == "always_on":
        on = pd.Series(1.0, index=daily.index)
    elif rule == "positive_only":
        ann = daily.rolling(prm.get("lookback_days", 3), min_periods=1).mean() * 365
        state, cur = [], 0.0
        for v in ann.to_numpy():
            if cur == 0.0 and v > prm.get("enter_ann", 0.10):
                cur = 1.0
            elif cur == 1.0 and v < prm.get("exit_ann", 0.0):
                cur = 0.0
            state.append(cur)
        on = pd.Series(state, index=daily.index)
    else:
        raise ValueError(rule)
    on = on.shift(1).fillna(0.0)                                  # decided at day close t-1
    cost = on.diff().abs().fillna(on) * 2 * cost_per_leg          # spot + perp legs per switch
    return hedge_share * (on * daily - cost)


def combine(daily_books: list[pd.Series]) -> pd.Series:
    df = pd.concat(daily_books, axis=1).fillna(0.0)
    return df.mean(axis=1)


def stats(r: pd.Series) -> dict:
    metrics.set_periods(365)
    r = r.dropna()
    if len(r) < 30:
        return {}
    return {"start": str(r.index[0].date()), "final_1000": round(1000 * float((1 + r).prod()), 0),
            "cagr": round(metrics.cagr(r), 4), "sharpe": round(metrics.sharpe(r), 2),
            "max_dd": round(metrics.max_drawdown(r), 4),
            "yearly": {str(k): round(float(v), 4) for k, v in ((1 + r).groupby(r.index.year).prod() - 1).items()}}


def to_daily(r: pd.Series) -> pd.Series:
    return (1 + r).groupby(r.index.normalize()).prod() - 1


def panel_frame(columns, index, start: str = "2019-09") -> pd.DataFrame:
    """Daily funding (sum of the day's settlements) per panel column, e.g. 'BTC/USDT' -> BTCUSDT. Missing = NaN.
    Point-in-time: a day's funding is known only after that day, so it is shifted by one bar (used from the next bar)."""
    out = {}
    for c in columns:
        sym = str(c).replace("/", "").replace("-", "").upper()
        if not sym.endswith("USDT"):
            continue
        try:
            out[c] = daily_funding(load(sym, start))
        except Exception as e:  # noqa: BLE001 - a coin without funding history is skipped
            print(f"[funding] {sym}: {e}")
    if not out:
        return pd.DataFrame(index=index, columns=columns, dtype=float)
    df = pd.DataFrame(out).reindex(pd.DatetimeIndex(index).normalize()).shift(1)
    df.index = index
    return df.reindex(columns=columns)
