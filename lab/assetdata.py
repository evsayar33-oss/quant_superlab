"""Per-asset OHLCV for the H073 asset book (config/assetbook.yaml). Free sources only.

  yahoo:<ticker>         daily OHLCV from Yahoo (index levels, ETFs)
  binance_vision:<SYM>   Binance spot klines from the free monthly files on data.binance.vision (1d, 4h)

Bars are cached under data/cache/assetbook. The last bar is dropped when it may still be forming.
"""
from __future__ import annotations

import io
import os
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from lab.panel import Panel

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "assetbook"
MAX_AGE_H = float(os.environ.get("LAB_CACHE_HOURS", "20"))
COLS = ["Open", "High", "Low", "Close", "Volume"]


def _fresh(p: Path, offline: bool) -> bool:
    return p.exists() and (offline or time.time() - p.stat().st_mtime < MAX_AGE_H * 3600)


def _get(url: str, p: Path) -> bytes | None:
    import requests
    for i in range(4):
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 quant_lab research"})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            p.write_bytes(r.content)
            return r.content
        except Exception:
            time.sleep(2 ** i)
    return p.read_bytes() if p.exists() else None


def binance_vision(sym: str, tf: str, start: str = "2017-08", offline: bool = False) -> pd.DataFrame:
    """Monthly kline files (complete months) + daily files for the current month."""
    d = CACHE / "bv" / sym / tf
    d.mkdir(parents=True, exist_ok=True)
    out = []
    today = pd.Timestamp.today().normalize()
    for m in pd.period_range(start, today - pd.offsets.MonthBegin(1), freq="M"):
        p = d / f"{sym}-{tf}-{m}.zip"
        if p.exists():
            raw = p.read_bytes()
        elif offline:
            continue
        else:
            raw = _get(f"https://data.binance.vision/data/spot/monthly/klines/{sym}/{tf}/{p.name}", p)
        if raw:
            out.append(_kl(raw))
    for day in pd.date_range(today.replace(day=1), today - pd.Timedelta(days=1)):
        p = d / f"{sym}-{tf}-{day.date()}.zip"
        if p.exists():
            raw = p.read_bytes()
        elif offline:
            continue
        else:
            raw = _get(f"https://data.binance.vision/data/spot/daily/klines/{sym}/{tf}/{p.name}", p)
        if raw:
            out.append(_kl(raw))
    if not out:
        return pd.DataFrame(columns=COLS)
    df = pd.concat(out).sort_index()
    return df[~df.index.duplicated(keep="last")]


def _kl(raw: bytes) -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(raw))
    k = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
    if not str(k.iloc[0, 0]).isdigit():                      # some files carry a header row
        k = k.iloc[1:]
    ts = k[0].astype("int64").to_numpy()
    ts = np.where(ts > 1e14, ts // 1000, ts)                 # files from 2025 use microseconds
    df = pd.DataFrame(k[[1, 2, 3, 4, 5]].astype(float).to_numpy(), columns=COLS,
                      index=pd.to_datetime(ts, unit="ms"))
    return df


def yahoo(ticker: str, start: str, offline: bool = False) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"yahoo_{ticker.replace('^', '_').replace('=', '_')}.csv"
    if _fresh(p, offline):
        return pd.read_csv(p, index_col=0, parse_dates=True)
    import yfinance as yf
    df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[COLS].dropna(subset=["Close"])
    if len(df) and df.index[-1].normalize() >= pd.Timestamp.today().normalize():
        df = df.iloc[:-1]                                     # today's bar may still be forming
    df.to_csv(p)
    return df


def load(source: str, tf: str, start: str, offline: bool = False) -> pd.DataFrame:
    kind, sym = source.split(":", 1)
    if kind == "yahoo":
        if tf != "1d":
            raise ValueError("Yahoo daily only")
        df = yahoo(sym, start, offline)
    elif kind == "binance_vision":
        df = binance_vision(sym, tf, offline=offline)
    else:
        raise ValueError(source)
    return df[df.index >= pd.Timestamp(start)]


def panel(name: str, df: pd.DataFrame, tf: str) -> Panel:
    p = Panel.from_ohlcv({name: df}, name=name)
    p.freq = tf
    return p
