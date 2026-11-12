#!/usr/bin/env python3
"""Run H078 without modification, then publish all-family H079 diagnostics."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab.event_study import partition_event_timestamps  # noqa: E402
from lab.event_study_h079 import (attach_point_in_time_cap, coverage_table,
                                  diagnostics, report)  # noqa: E402
from scripts.run_event_study import DEFAULT_FEED, load_feed  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--max-tickers", type=int, default=600)
    ap.add_argument("--feed-file", default="")
    ap.add_argument("--pit-market-cap-file", default="")
    ap.add_argument("--output", default="results/h079")
    args = ap.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)

    command = [sys.executable, str(ROOT / "scripts/run_event_study.py"),
               "--start", args.start, "--max-tickers", str(args.max_tickers),
               "--output", str(out / "h078")]
    if args.feed_file:
        command.extend(["--feed-file", args.feed_file])
    subprocess.run(command, check=True, cwd=ROOT)

    feed = load_feed(DEFAULT_FEED, args.feed_file or None)
    feed["event_date"] = pd.to_datetime(feed["event_date"], errors="coerce")
    feed = feed[feed["event_date"] >= pd.Timestamp(args.start)].copy()
    historical, forward_only, excluded = partition_event_timestamps(feed)
    historical.to_csv(out / "historical_eligible_events.csv", index=False)
    forward_only.to_csv(out / "forward_only_events.csv", index=False)
    excluded.to_csv(out / "excluded_events.csv", index=False)

    returns_path = out / "h078" / "event_returns.csv"
    try:
        returns = pd.read_csv(returns_path)
    except pd.errors.EmptyDataError:
        returns = pd.DataFrame()
    if returns.empty:
        returns = pd.DataFrame(columns=[
            "event_id", "ticker", "event_date", "event_family", "category",
            "sector_etf", "horizon", "amount_usd", "net_stock_return_2x",
            "net_spy_excess_2x",
        ])
    caps = pd.read_csv(args.pit_market_cap_file) if args.pit_market_cap_file else None
    enriched = attach_point_in_time_cap(returns, caps)
    enriched.to_csv(out / "event_returns_enriched.csv", index=False)
    coverage = coverage_table(feed, returns)
    stats = diagnostics(enriched)
    coverage.to_csv(out / "all_category_coverage.csv", index=False)
    stats.to_csv(out / "sector_category_diagnostics.csv", index=False)
    (out / "H079_REPORT.md").write_text(report(coverage, stats, caps is not None), encoding="utf-8")
    print((out / "H079_REPORT.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
