"""CFTC Commitments of Traders (free, public Socrata API) -> point-in-time positioning.

Legacy "Futures Only" report. Positions are as of Tuesday and published on Friday afternoon
(US time); we make a report visible from the following Monday (Tuesday + 6 days), so a
backtest never trades on positioning before it was public.

Output per asset (wide frames aligned to the bar index):
  cot_spec_net  non-commercial (speculators) net position as % of open interest
  cot_comm_net  commercial (hedgers) net position as % of open interest
Universe config maps tickers to CFTC contract codes, e.g.
  cot: {GC=F: "088691", GLD: "088691", SI=F: "084691", SLV: "084691", HG=F: "085692", CPER: "085692"}
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
API = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
PUBLISH_LAG_DAYS = 6


def _fetch(code: str) -> pd.DataFrame:
    p = CACHE / f"cot_{code}.csv"
    if p.exists() and time.time() - p.stat().st_mtime < 3 * 86400:
        return pd.read_csv(p, parse_dates=["date"])
    q = urllib.parse.urlencode({
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd",
        "$limit": "10000",
        "$select": "report_date_as_yyyy_mm_dd,open_interest_all,noncomm_positions_long_all,"
                   "noncomm_positions_short_all,comm_positions_long_all,comm_positions_short_all",
    })
    with urllib.request.urlopen(urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "quant_lab"}), timeout=60) as r:
        rows = json.loads(r.read().decode())
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError(f"no COT rows for {code}")
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None)
    for c in df.columns:
        if c.endswith("_all"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    oi = df["open_interest_all"]
    df["spec_net"] = (df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]) / oi
    df["comm_net"] = (df["comm_positions_long_all"] - df["comm_positions_short_all"]) / oi
    df = df[["date", "spec_net", "comm_net"]].dropna().drop_duplicates("date").sort_values("date")
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return df


def load(mapping: dict, index: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    spec, comm = {}, {}
    for ticker, code in mapping.items():
        try:
            df = _fetch(str(code))
        except Exception as e:  # noqa: BLE001 - positioning is optional
            print(f"[cot] {ticker} ({code}) unavailable: {e}")
            continue
        avail = df["date"] + pd.Timedelta(days=PUBLISH_LAG_DAYS)
        for out, col in ((spec, "spec_net"), (comm, "comm_net")):
            s = pd.Series(df[col].values, index=avail)
            out[ticker] = s.reindex(s.index.union(index)).sort_index().ffill().reindex(index)
    res = {}
    if spec:
        res["cot_spec_net"] = pd.DataFrame(spec)
        res["cot_comm_net"] = pd.DataFrame(comm)
        print(f"[cot] loaded {list(spec)}")
    return res
