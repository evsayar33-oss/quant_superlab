"""Historical index membership (survivorship-bias control).

A universe may declare `membership:` in config/universes.yaml:
  membership: sp500                     # free history from github.com/fja05680/sp500
  membership: data/membership/x.csv     # your own file: columns date,tickers ("AAA,BBB,...")

mask() returns a bool frame (bars x assets): True only while the asset was a member.
Strategies cannot select a stock before it joined the index or after it left.
Limitation: prices of companies that were delisted are not in free sources, so the
universe can still miss dead stocks; the mask removes the look-ahead of using today's list.
"""
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"


def _fetch_sp500() -> pd.DataFrame:
    p = CACHE / "sp500_membership.csv"
    if p.exists():
        return pd.read_csv(p)
    api = "https://api.github.com/repos/fja05680/sp500/contents"
    with urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": "quant_lab"}), timeout=30) as r:
        files = json.loads(r.read().decode())
    cands = sorted(f["name"] for f in files if f["name"].startswith("S&P 500 Historical Components") and f["name"].endswith(".csv"))
    if not cands:
        raise RuntimeError("sp500 membership file not found")
    url = next(f["download_url"] for f in files if f["name"] == cands[-1])
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "quant_lab"}), timeout=60) as r:
        df = pd.read_csv(io.StringIO(r.read().decode()))
    df.to_csv(p, index=False)
    return df


def load(spec: str) -> pd.DataFrame:
    df = _fetch_sp500() if spec == "sp500" else pd.read_csv(ROOT / spec)
    df.columns = [c.lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def mask(spec: str, index: pd.DatetimeIndex, tickers: list[str]) -> pd.DataFrame | None:
    try:
        df = load(spec)
    except Exception as e:  # noqa: BLE001 - membership is a safety layer, never a hard failure
        print(f"[membership] unavailable ({e}); using today's list (survivorship bias remains)")
        return None
    norm = lambda t: t.upper().replace(".", "-").replace(".IS", "")  # noqa: E731
    rows = {d: set(norm(x) for x in str(s).split(",")) for d, s in zip(df["date"], df["tickers"])}
    dates = sorted(rows)
    out = pd.DataFrame(False, index=index, columns=tickers)
    pos = pd.Series(dates).searchsorted(index.normalize(), side="right") - 1
    keys = [norm(t) for t in tickers]
    for i, k in enumerate(pos):
        if k >= 0:
            mem = rows[dates[k]]
            out.iloc[i] = [kk in mem for kk in keys]
    cov = float(out.values.mean())
    print(f"[membership] {spec}: avg member share {cov:.2f}")
    return out
