"""Read-only post-PR11 diagnostics. No writes to production GitHub branch."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "results/p11_postmerge"
REPORT.mkdir(parents=True, exist_ok=True)


def save(name, payload):
    (REPORT / name).write_text(json.dumps(payload, indent=2, default=str))
    print(json.dumps(payload, indent=2, default=str))


def verify_watch():
    p = ROOT / "decisions/watch"
    obs = p / "observations.csv"
    stfile = p / "state.json"
    hist = p / "history.csv"
    if not all(x.exists() for x in [obs, stfile, hist]):
        raise RuntimeError("Paper Watch did not produce all three audit files")
    st = json.loads(stfile.read_text())
    rows = pd.read_csv(obs, dtype={"run_date": str, "idea": str})
    history = pd.read_csv(hist, dtype={"run_date": str, "idea": str})
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    if st["date"] != today:
        raise RuntimeError("Watch state date does not match this run")
    todays = rows[rows.run_date == today]
    if set(todays.idea) != set(st["ideas"]):
        raise RuntimeError("First-seen snapshot incomplete")
    if rows.duplicated(["run_date", "idea"]).any():
        raise RuntimeError("Repeated first-observed records")
    if history.duplicated(["run_date", "idea"]).any():
        raise RuntimeError("Duplicate reconstructed historical NAV rows")
    stale = {}
    for hid, rec in st["ideas"].items():
        bar = pd.Timestamp(rec["bar"]).date()
        age = (now.date() - bar).days
        stale[hid] = {"bar": str(bar), "age_days": age,
                      "prospective_day_count": rec.get("paper_1x", {}).get("days")}
        if bar < pd.Timestamp(st["start"]).date():
            raise RuntimeError(f"{hid}: no bar after prospective start")
        if age > 7 or age < 0:
            raise RuntimeError(f"{hid}: stale or future source bar {bar}")
    payload = {"status": "WATCH_READONLY_SMOKE_OK", "observation_date": today,
               "observed_ideas": sorted(todays.idea.tolist()),
               "observation_rows": len(rows), "reconstructed_nav_rows": len(history),
               "after_start": stale,
               "warning": "historical NAV remains reconstructed, not genuine forward fill"}
    save("watch_diagnostic.json", payload)


def verify_sources():
    from lab import client, data, funding
    now = datetime.now(timezone.utc)
    registry = client.fetch(client.URL)
    if not registry or "hypotheses" not in registry:
        raise RuntimeError("Cannot fetch primary authoritative registry URL")
    approvals = client.approved()
    universe = ["BTC/USDT", "ETH/USDT"]
    px = data.load_ohlcv(universe, start="2026-11-01", timeframe="1d")
    check = {}
    for symbol in universe:
        d = px.get(symbol)
        if d is None or len(d) < 4:
            raise RuntimeError(f"{symbol}: no sufficient recent exchange data")
        if d[["Open","High","Low","Close","Volume"]].isna().any().any():
            raise RuntimeError(f"{symbol}: missing OHLCV fields")
        if (d[["Open","High","Low","Close"]] <= 0).any().any():
            raise RuntimeError(f"{symbol}: invalid OHLC prices")
        latest = pd.Timestamp(d.index.max())
        if (now.date() - latest.date()).days > 3:
            raise RuntimeError(f"{symbol}: stale last CLOSED daily bar {latest}")
        check[symbol] = {"bars": len(d), "first": str(d.index.min()), "last_closed": str(latest)}
    # A single recent BTC month bounds the funding probe. Missing archive is recorded
    # as a DATA_GAP, not imputed as zero funding.
    f = funding.load("BTCUSDT", start="2026-10")
    gap = bool(f.empty)
    arena = {}
    for key in ["4h", "4h_long", "4h_short", "1d", "1d_long", "1d_short"]:
        base = ROOT / "decisions/arena" / key
        roster = json.loads((base / "roster.json").read_text())
        switch = json.loads((base / "switcher.json").read_text())
        arena[key] = {"active": sum(m.get("status") == "active" for m in roster.get("members", [])),
                      "updated_at": switch.get("updated_at"), "usable": bool(switch.get("usable"))}
    wf = yaml.safe_load((ROOT / ".github/workflows/arena.yml").read_text())
    matrix = wf["jobs"]["arena"]["strategy"]["matrix"]
    if len(matrix["timeframe"]) * len(matrix["side"]) != 6:
        raise RuntimeError("Arena matrix no longer isolates 6 books")
    status = {"status": "SOURCE_READONLY_SMOKE_OK",
              "registry_hypotheses": len(registry["hypotheses"]),
              "current_client_approvals": sorted(x["id"] for x in approvals),
              "crypto_ohlcv": check, "btc_funding_samples": len(f),
              "btc_funding_data_gap": gap,
              "arena_book_status": arena,
              "note": "Successful source checks do not mean Arena end-to-end completed"}
    save("source_diagnostic.json", status)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--mode", choices=["watch", "sources"], required=True)
    q = a.parse_args()
    (verify_watch if q.mode == "watch" else verify_sources)()
