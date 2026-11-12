#!/usr/bin/env python3
"""H080 runner: reuse H079 outputs, audit all categories and PIT inputs."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lab.event_study_h080 import (timestamp_audit, enrich_with_verified_fundamentals,
                                  attach_prior_regimes, regime_diagnostics, report)
from scripts.run_event_study import DEFAULT_FEED, load_feed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2019-01-01")
    p.add_argument("--max-tickers", type=int, default=600)
    p.add_argument("--feed-file", default="")
    p.add_argument("--pit-market-cap-file", default="")
    p.add_argument("--regime-file", default="")
    p.add_argument("--output", default="results/h080")
    args = p.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(ROOT / "scripts/run_h079.py"), "--start", args.start,
               "--max-tickers", str(args.max_tickers), "--output", str(out / "h079")]
    if args.feed_file:
        command += ["--feed-file", args.feed_file]
    subprocess.run(command, cwd=ROOT, check=True)

    feed = load_feed(DEFAULT_FEED, args.feed_file or None)
    feed["event_date"] = pd.to_datetime(feed["event_date"], errors="coerce")
    feed = feed[feed["event_date"] >= pd.Timestamp(args.start)].copy()
    returns = pd.read_csv(out / "h079" / "event_returns_enriched.csv")
    pit = pd.read_csv(args.pit_market_cap_file) if args.pit_market_cap_file else None
    regimes = pd.read_csv(args.regime_file) if args.regime_file else None
    enriched = attach_prior_regimes(enrich_with_verified_fundamentals(returns, pit), regimes)
    audit = timestamp_audit(feed, returns)
    groups = regime_diagnostics(enriched)
    audit.to_csv(out / "all_family_timestamp_audit.csv", index=False)
    enriched.to_csv(out / "event_returns_pit_regimes.csv", index=False)
    groups.to_csv(out / "all_sector_regime_diagnostics.csv", index=False)
    (out / "H080_REPORT.md").write_text(report(audit, groups, pit is not None, regimes is not None), encoding="utf-8")
    print((out / "H080_REPORT.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
