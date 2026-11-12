#!/usr/bin/env python3
"""H081: re-run H080, audit source evidence, compute SPY regimes, apply fixed gates."""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import data
from lab.event_study_h081 import (source_evidence_audit, evidence_override,
                                  spy_prior_regimes, final_decisions, evidence_report)
from lab.event_study_h080 import (enrich_with_verified_fundamentals,
                                  attach_prior_regimes, regime_diagnostics)
from scripts.run_event_study import DEFAULT_FEED, load_feed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--max-tickers", type=int, default=600)
    ap.add_argument("--feed-file", default="")
    ap.add_argument("--evidence-file", default="")
    ap.add_argument("--pit-market-cap-file", default="")
    ap.add_argument("--output", default="results/h081")
    a = ap.parse_args()
    out = ROOT / a.output
    out.mkdir(parents=True, exist_ok=True)
    feed = load_feed(DEFAULT_FEED, a.feed_file or None)
    feed["event_date"] = pd.to_datetime(feed["event_date"], errors="coerce")
    feed = feed[feed["event_date"] >= pd.Timestamp(a.start)].copy()
    evidence = pd.read_csv(a.evidence_file) if a.evidence_file else None
    upgraded, decisions = evidence_override(feed, evidence)
    audit = source_evidence_audit(upgraded)
    decisions.to_csv(out / "source_evidence_decisions.csv", index=False)
    audit.to_csv(out / "all_sector_evidence_audit.csv", index=False)
    upgraded.to_csv(out / "feed_evidence_snapshot.csv", index=False)
    feed_path = out / "feed_evidence_snapshot.csv"
    command = [sys.executable, str(ROOT / "scripts/run_h080.py"), "--start", a.start,
               "--max-tickers", str(a.max_tickers), "--feed-file", str(feed_path),
               "--output", str(out / "h080")]
    subprocess.run(command, cwd=ROOT, check=True)
    ret = pd.read_csv(out / "h080" / "h079" / "h078" / "event_returns.csv")
    if ret.empty:
        ret = pd.DataFrame(columns=["event_id", "ticker", "event_date", "amount_usd"])
    pit = pd.read_csv(a.pit_market_cap_file) if a.pit_market_cap_file else None
    ret = enrich_with_verified_fundamentals(ret, pit)
    # Reproducible regime: SPY 200-session SMA using only past completed sessions.
    start = (pd.to_datetime(a.start) - pd.Timedelta(days=500)).date().isoformat()
    raw = data.load_ohlcv(["SPY"], start, "1d")
    if "SPY" not in raw or raw["SPY"].empty:
        raise RuntimeError("SPY history missing: cannot compute historical regimes")
    regimes = spy_prior_regimes(raw["SPY"]["Close"])
    regimes.to_csv(out / "spy_prior_regimes.csv", index=False)
    ret = attach_prior_regimes(ret, regimes)
    ret.to_csv(out / "event_returns_final.csv", index=False)
    regime_diagnostics(ret).to_csv(out / "sector_regime_diagnostics.csv", index=False)
    cfg = yaml.safe_load((ROOT / "config/event_study.yaml").read_text())
    gate = cfg["gate"]
    result = final_decisions(ret, min_events=int(gate["min_events"]),
                             min_split=int(gate["min_split"]),
                             min_holdout_hit=float(gate["min_holdout_hit"]),
                             q_limit=float(gate["q_limit"]),
                             bootstrap_n=int(cfg["bootstrap_n"]), seed=int(cfg["seed"]))
    result.to_csv(out / "statistical_final_decisions.csv", index=False)
    pit_n = int(ret["pit_market_cap_usd"].notna().sum())
    regime_n = int(ret["prior_regime"].ne("UNAVAILABLE").sum())
    (out / "H081_REPORT.md").write_text(evidence_report(audit, result, decisions, pit_n, regime_n), encoding="utf-8")
    print((out / "H081_REPORT.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
