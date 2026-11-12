#!/usr/bin/env python3
"""Fetch the public Radar event feed and run H078 on free daily OHLCV data."""
from __future__ import annotations

import argparse
import hashlib
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab import data  # noqa: E402
from lab.event_study import (BENCHMARK, partition_event_timestamps, markdown_report,
                             measure_events, summarize)  # noqa: E402
from lab.panel import Panel  # noqa: E402

DEFAULT_FEED = (
    "https://raw.githubusercontent.com/evsayar33-oss/federal-incentive-radar/"
    "data/event_trade_feed.csv"
)


def load_feed(url: str, local_path: str | None = None) -> pd.DataFrame:
    if local_path:
        return pd.read_csv(local_path)
    request = urllib.request.Request(url, headers={"User-Agent": "quant-superlab-event-study/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return pd.read_csv(io.BytesIO(response.read()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed-url", default=DEFAULT_FEED)
    ap.add_argument("--feed-file", default="")
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--max-tickers", type=int, default=600)
    ap.add_argument("--output", default="results/event_study")
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config/event_study.yaml").read_text())
    feed = load_feed(args.feed_url, args.feed_file or None)
    if feed.empty:
        raise SystemExit("Event feed is empty; no study was run.")
    feed["event_date"] = pd.to_datetime(feed["event_date"], errors="coerce")
    feed = feed.dropna(subset=["event_date"])
    feed = feed[feed["event_date"] >= pd.Timestamp(args.start)].copy()
    feed_rows = len(feed)
    historical_feed, forward_only_feed, excluded_feed = partition_event_timestamps(feed)
    quality = feed["timestamp_quality"].fillna("unknown").astype(str).str.lower()
    exact_rows = int(quality.eq("exact_utc").sum())
    date_only_rows = int(quality.eq("date_only").sum())
    forward_only_rows = len(forward_only_feed)
    excluded_unverified = len(excluded_feed)
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    forward_only_feed.to_csv(out / "forward_only_events.csv", index=False)
    feed = historical_feed
    if feed.empty:
        empty_returns = pd.DataFrame()
        empty_summary = pd.DataFrame()
        empty_returns.to_csv(out / "event_returns.csv", index=False)
        empty_summary.to_csv(out / "event_summary.csv", index=False)
        (out / "event_study.md").write_text(
            markdown_report(empty_summary, empty_returns, feed_rows, 0, 0, args.start,
                            excluded_unverified_timestamps=excluded_unverified,
                            forward_only_observations=forward_only_rows,
                            exact_timestamp_rows=exact_rows,
                            date_only_rows=date_only_rows),
            encoding="utf-8",
        )
        print((out / "event_study.md").read_text(encoding="utf-8"))
        return 0
    feed["ticker"] = feed["ticker"].astype(str).str.strip().str.upper()
    feed = feed[feed["ticker"].ne("") & feed["ticker"].ne("NAN")]
    if feed.empty:
        raise SystemExit("No events remain after the requested start-date filter.")

    counts = feed["ticker"].value_counts()
    # A deterministic hash sample avoids selecting tickers because they have more
    # historical Radar events (which would overweight repeat-news issuers).
    all_tickers = counts.index.astype(str).tolist()
    selected = sorted(all_tickers, key=lambda ticker: hashlib.sha256(ticker.encode()).hexdigest())[:max(1, args.max_tickers)]
    excluded = max(0, len(all_tickers) - len(selected))
    feed = feed[feed["ticker"].isin(selected)].copy()
    sector_etfs = sorted(set(feed.get("sector_etf", pd.Series(dtype=str)).dropna().astype(str)) - {""})
    tickers = sorted(set(selected + [BENCHMARK] + sector_etfs))
    price_start = (feed["event_date"].min() - pd.Timedelta(days=430)).date().isoformat()
    raw = data.load_ohlcv(tickers, price_start, "1d")
    if BENCHMARK not in raw:
        raise SystemExit("SPY OHLCV is unavailable; event study cannot be market-adjusted.")
    usable = {t: frame for t, frame in raw.items() if frame is not None and not frame.empty}
    if BENCHMARK not in usable:
        raise SystemExit("SPY OHLCV is unavailable after filtering.")
    panel = Panel.from_ohlcv(usable, bench=usable[BENCHMARK]["Close"], name="federal_event_study")
    panel.freq = "1d"
    costs = cfg["costs"]
    per_side_cost = float(costs["commission"]) + float(costs["slippage"])
    returns = measure_events(
        feed, panel, per_side_cost=per_side_cost,
        horizons=tuple(cfg["horizons"]), benchmark=BENCHMARK,
        cooldown_days=int(cfg["cooldown_days"]),
    )
    summary = summarize(
        returns, min_events=int(cfg["gate"]["min_events"]),
        min_split=int(cfg["gate"]["min_split"]),
        min_holdout_hit=float(cfg["gate"]["min_holdout_hit"]),
        q_limit=float(cfg["gate"]["q_limit"]),
        bootstrap_n=int(cfg["bootstrap_n"]), seed=int(cfg["seed"]),
    )
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    returns.to_csv(out / "event_returns.csv", index=False)
    summary.to_csv(out / "event_summary.csv", index=False)
    (out / "event_study.md").write_text(
        markdown_report(summary, returns, feed_rows, len(set(usable) & set(selected)), excluded, price_start,
                        excluded_unverified_timestamps=excluded_unverified,
                        forward_only_observations=forward_only_rows,
                        exact_timestamp_rows=exact_rows,
                        date_only_rows=date_only_rows),
        encoding="utf-8",
    )
    print((out / "event_study.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
