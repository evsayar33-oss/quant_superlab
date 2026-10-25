"""Free market data loader with a local CSV cache. Multi-timeframe.

Sources (all free, no API key):
  - yfinance : BIST (.IS), US stocks/ETFs, FX (USDTRY=X), indices (^VIX, ^IRX, ^TNX, XU100.IS)
               daily history is long; 1h history is limited to ~730 days by Yahoo
  - ccxt     : crypto OHLCV from public endpoints (bitget -> okx -> kucoin), long 1h/4h history

Timeframes: 1h, 4h, 1d, 1w, 1mo
  * 1w / 1mo bars are built from daily bars (W-FRI / month end) so every market is consistent.
  * 4h stock bars are built from 1h bars.
A bar is labelled with its END; signals are read at the bar close and traded at the next bar open.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
MAX_CACHE_AGE_H = float(os.environ.get("LAB_CACHE_HOURS", "20"))
TIMEFRAMES = ("1h", "4h", "1d", "1w", "1mo")
AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


def _is_crypto(t: str) -> bool:
    return "/" in t  # e.g. BTC/USDT


def _cache_path(t: str, field: str) -> Path:
    safe = t.replace("/", "_").replace("^", "IDX_").replace("=", "_")
    return CACHE / f"{safe}__{field}.csv"


def _fresh(p: Path) -> bool:
    return p.exists() and (time.time() - p.stat().st_mtime) < MAX_CACHE_AGE_H * 3600


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    rule = {"1w": "W-FRI", "1mo": "ME", "4h": "4h"}[tf]
    out = df.resample(rule, label="right", closed="right" if tf == "4h" else "right").agg(AGG)
    return out.dropna(subset=["Close"])


def _yf_download(tickers: list[str], start: str, interval: str = "1d") -> dict[str, pd.DataFrame]:
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    if not tickers:
        return out
    kw = {"start": start} if interval == "1d" else {"period": "730d"}
    frames = []
    for i in range(0, len(tickers), 25):            # small batches + retries: Yahoo rate limits
        chunk = tickers[i:i + 25]
        for attempt in range(4):
            try:
                raw = yf.download(chunk, interval=interval, auto_adjust=True, progress=False,
                                  group_by="ticker", threads=True, **kw)
                if raw is not None and len(raw):
                    frames.append((chunk, raw))
                    break
            except Exception as e:  # noqa: BLE001
                print(f"[data] yfinance attempt {attempt + 1} failed: {e}")
            time.sleep(5 * (attempt + 1))
    for chunk, raw in frames:
        out.update(_split(raw, chunk))
    return out


def _split(raw: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            df = df.dropna(how="all")
            if len(df):
                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                out[t] = df
        except KeyError:
            pass
    return out


TF_DELTA = {"1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4), "1d": pd.Timedelta(days=1)}


def _drop_open_bar(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Exchanges also return the bar that is still forming. Drop it: a live signal must use closed bars only.
    ccxt rows are labelled with the bar OPEN time (daily rows normalized to the date)."""
    d = TF_DELTA.get(timeframe)
    if d is None or df is None or not len(df):
        return df
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    return df[df.index + d <= now]


def _ccxt_download(symbol: str, start: str, timeframe: str = "1d", since_ms: int | None = None) -> pd.DataFrame | None:
    import ccxt

    tf = {"1mo": "1M"}.get(timeframe, timeframe)
    since0 = since_ms if since_ms is not None else int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    step = int(TF_DELTA.get(timeframe, pd.Timedelta(days=1)).total_seconds() * 1000) * 200
    now_ms = int(time.time() * 1000)
    for ex_id in ("bitget", "okx", "kucoin"):
        try:
            ex = getattr(ccxt, ex_id)({"enableRateLimit": True})
            rows, since = [], since0
            for _ in range(4000):
                batch = ex.fetch_ohlcv(symbol, tf, since=since, limit=200)
                if not batch:
                    if rows or since + step > now_ms:
                        break
                    since += step          # coin listed after `start`: walk forward to the listing date
                    continue
                rows += batch
                nxt = batch[-1][0] + 1
                if nxt <= since or len(batch) < 2:
                    break
                since = nxt
            if rows:
                df = pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close", "Volume"]).drop_duplicates("ts")
                idx = pd.to_datetime(df["ts"], unit="ms")
                df.index = idx.dt.normalize() if timeframe == "1d" else idx
                return _drop_open_bar(df.drop(columns="ts").sort_index(), timeframe)
        except Exception as e:  # noqa: BLE001 - try next exchange
            print(f"[data] {ex_id} {symbol} {timeframe} failed: {e}")
    return None


def _ccxt_update(symbol: str, cached: pd.DataFrame, start: str, timeframe: str) -> pd.DataFrame:
    """Incremental refresh: download only the bars after the cached ones (re-fetch the last 3 bars)."""
    if cached is None or len(cached) < 10:
        return _ccxt_download(symbol, start, timeframe)
    d = TF_DELTA.get(timeframe, pd.Timedelta(days=1))
    since = int((cached.index[-1] - 3 * d).tz_localize("UTC").timestamp() * 1000)
    new = _ccxt_download(symbol, start, timeframe, since_ms=since)
    if new is None or not len(new):
        return _drop_open_bar(cached, timeframe)
    out = pd.concat([cached[cached.index < new.index[0]], new]).sort_index()
    return _drop_open_bar(out[~out.index.duplicated(keep="last")], timeframe)


def _binance_backfill(t: str, df: pd.DataFrame | None, start: str, timeframe: str) -> pd.DataFrame | None:
    """Data-source fix (2026-10-24, CHANGELOG): the exchange API often returns a shorter history than the
    coin has (e.g. SOL on Bitget). When the first bar is > 30 days after `start`, the older bars come from
    Binance spot monthly files (data.binance.vision, free). Same coin, same quote currency; only bars BEFORE
    the exchange's first bar are added, so live prices never change source."""
    if timeframe not in ("1h", "4h", "1d"):
        return df
    first = df.index[0] if df is not None and len(df) else None
    if first is not None and first <= pd.Timestamp(start) + pd.Timedelta(days=30):
        return df
    try:
        from lab import assetdata
        bv = assetdata.binance_vision(t.replace("/", ""), timeframe, start=str(pd.Timestamp(start).to_period("M")))
    except Exception as e:  # noqa: BLE001 - backfill is optional
        print(f"[data] binance backfill {t} {timeframe} failed: {e}")
        return df
    if bv is None or not len(bv):
        return df
    if timeframe == "1d":
        bv.index = bv.index.normalize()
    if first is not None:
        bv = bv[bv.index < first]
    out = bv if df is None else pd.concat([bv, df]).sort_index()
    print(f"[data] {t} {timeframe}: {len(bv)} older bars from Binance (from {bv.index[0].date() if len(bv) else '-'})")
    return _drop_open_bar(out[~out.index.duplicated(keep="last")], timeframe)


def _crypto_cached(t: str, p: Path, start: str, timeframe: str) -> pd.DataFrame | None:
    """Crypto cache with incremental refresh. A sidecar file stores the requested start date, so a coin
    listed after `start` is not re-downloaded on every run, and a request for an EARLIER start does a full download."""
    meta = p.with_suffix(".start")
    old, cached_start = None, start
    if p.exists() and meta.exists():
        try:
            cached_start = meta.read_text().strip()
            if pd.Timestamp(cached_start) <= pd.Timestamp(start):
                old = pd.read_csv(p, index_col=0, parse_dates=True)
            else:
                cached_start = start
        except Exception:  # noqa: BLE001
            old, cached_start = None, start
    if old is not None and len(old) and _fresh(p):
        old2 = _binance_backfill(t, old, start, timeframe)
        if old2 is not old:
            old2.to_csv(p)
        return old2[old2.index >= pd.Timestamp(start)]
    df = _ccxt_update(t, old, start, timeframe) if old is not None else _ccxt_download(t, start, timeframe)
    df = _binance_backfill(t, df, start, timeframe)
    if df is None:
        return None if old is None else old[old.index >= pd.Timestamp(start)]
    df.to_csv(p)
    meta.write_text(cached_start)
    return df[df.index >= pd.Timestamp(start)]


def load_ohlcv(tickers: list[str], start: str = "2010-01-01", timeframe: str = "1d") -> dict[str, pd.DataFrame]:
    """Return {ticker: OHLCV DataFrame} for the timeframe. Uses cache when fresh."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"timeframe must be one of {TIMEFRAMES}")
    if timeframe in ("1w", "1mo"):
        daily = load_ohlcv(tickers, start, "1d")
        return {t: resample(d, timeframe) for t, d in daily.items()}
    result: dict[str, pd.DataFrame] = {}
    need_yf: list[str] = []
    for t in tickers:
        p = _cache_path(t, f"ohlcv_{timeframe}")
        if _is_crypto(t):
            got = _crypto_cached(t, p, start, timeframe)
            if got is not None:
                result[t] = got
            continue
        if _fresh(p):
            df = pd.read_csv(p, index_col=0, parse_dates=True)
            if len(df) and (timeframe != "1d" or df.index[0] <= pd.Timestamp(start) + pd.Timedelta(days=10)):
                result[t] = df
                continue
        need_yf.append(t)
    yf_iv = "1h" if timeframe in ("1h", "4h") else "1d"
    for t, df in _yf_download(need_yf, start, yf_iv).items():
        if timeframe == "4h":
            df = resample(df, "4h")
        df.to_csv(_cache_path(t, f"ohlcv_{timeframe}"))
        result[t] = df
    missing = [t for t in tickers if t not in result]
    if missing:
        print(f"[data] WARNING no {timeframe} data for: {missing}")
    return result


def load_prices(tickers: list[str], start: str = "2010-01-01", field: str = "Close", timeframe: str = "1d") -> pd.DataFrame:
    data = load_ohlcv(tickers, start, timeframe)
    px = pd.DataFrame({t: d[field] for t, d in data.items()}).sort_index()
    px = px[px.index >= pd.Timestamp(start)]
    return px.where(px > 0).ffill(limit=5)


def load_series(ticker: str, start: str = "2005-01-01") -> pd.Series | None:
    """Daily close of a macro / FX / rate series (e.g. ^VIX, USDTRY=X, ^IRX)."""
    d = load_ohlcv([ticker], start, "1d").get(ticker)
    return None if d is None else d["Close"].where(d["Close"] > 0).ffill()


def synthetic_prices(n_assets: int = 10, n_days: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Random-walk prices for offline tests (no edge by construction)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-01", periods=n_days)
    rets = rng.normal(0.0003, 0.02, size=(n_days, n_assets))
    return pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx,
                        columns=[f"A{i}" for i in range(n_assets)])


def _align(s: pd.Series | None, index: pd.DatetimeIndex) -> pd.Series | None:
    """Align a DAILY series to the bar index without look-ahead.
    On intraday bars a daily close is only known after that day ends -> available next day."""
    if s is None:
        return None
    s = s.copy()
    if len(index) > 1 and (index[1:] - index[:-1]).min() < pd.Timedelta(hours=20):
        s.index = s.index.normalize() + pd.Timedelta(days=1)
    return s.reindex(s.index.union(index)).sort_index().ffill().reindex(index)


def load_panel(universe: dict, start: str, name: str = "", with_fundamentals: bool = True,
               timeframe: str = "1d"):
    """Everything a strategy may need, aligned on the universe's bar index:
    OHLCV, benchmark, risk-free, FX (to report in USD), macro series, membership mask, fundamentals."""
    from lab import fundamentals, membership
    from lab.panel import Panel

    tickers = universe["tickers"]
    bench_t = universe.get("benchmark")
    ohlcv = load_ohlcv(tickers + ([bench_t] if bench_t and bench_t not in tickers else []), start, timeframe)
    bench = ohlcv[bench_t]["Close"] if bench_t in ohlcv else None
    data = {t: d[d.index >= pd.Timestamp(start)] for t, d in ohlcv.items() if t in tickers}
    if not data:
        raise RuntimeError("no price data")
    p = Panel.from_ohlcv(data, bench, name)
    p.freq = timeframe
    p.market = universe.get("market", "")
    p.costs_meta = {"price_limit": universe.get("price_limit"), "min_adv": universe.get("min_adv")}

    # Risk-free (annual %, daily series) -> per-bar return. ^IRX = US 13-week T-bill.
    rf_t = universe.get("risk_free", "^IRX")
    rf = load_series(rf_t, "2000-01-01") if rf_t else None
    if rf is not None:
        p.rf_annual = (_align(rf, p.index) / 100.0).fillna(0.0)
    fx_t = universe.get("fx")  # e.g. USDTRY=X : price of 1 USD in local currency
    if fx_t:
        p.fx = _align(load_series(fx_t, "2000-01-01"), p.index)
    for m in universe.get("macro", ["^VIX", "^TNX", "^IRX", "USDTRY=X"]):
        try:
            s = load_series(m, "2000-01-01")
            if s is not None:
                p.macro[m] = _align(s, p.index)
        except Exception as e:  # noqa: BLE001 - macro is optional
            print(f"[data] macro {m}: {e}")
    if universe.get("cot"):
        from lab import cot
        p.extra.update(cot.load(universe["cot"], p.index if timeframe == "1d" else p.index))
    if universe.get("funding"):
        from lab import funding as _fu
        p.extra["funding_daily"] = _fu.panel_frame(list(p.columns), p.index, str(universe["funding"]) if universe["funding"] is not True else "2019-09")
    if universe.get("membership"):
        p.member = membership.mask(universe["membership"], p.index, list(p.columns))
    if with_fundamentals and universe.get("market") in ("bist", "us"):
        daily_idx = p.index if timeframe == "1d" else pd.DatetimeIndex(p.index.normalize().unique())
        f = fundamentals.load(list(p.columns), daily_idx, universe["market"])
        p.fund = {k: _align_frame(v, p.index) for k, v in f.items()}
    return p


def _align_frame(f: pd.DataFrame, index: pd.DatetimeIndex) -> pd.DataFrame:
    return f.reindex(f.index.union(index)).sort_index().ffill().reindex(index)
