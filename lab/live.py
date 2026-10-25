"""Live (paper) tracking of ACCEPT decisions and automatic demotion on decay.

Every run re-computes each accepted hypothesis with its FROZEN final variant on fresh data
and keeps only the returns after its acceptance date (true out-of-sample, nothing re-fit).
Demotion rules (-> DEGRADED, bots stop using it):
  * live drawdown worse than 1.5x the backtest OOS max drawdown
  * one-sided CUSUM: live mean return falls significantly below the backtest OOS mean
  * live Sharpe after >= 6 months below 0 while backtest OOS Sharpe was > 0.5
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lab import candidates as CD
from lab import data, decision, metrics
from lab.engine import Costs

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT / "decisions" / "live"


def _variant(cand, h):
    return CD.Variant(h["variant"], h["params"])  # frozen at acceptance: nothing is re-fit


def decay_check(live: pd.Series, h: dict) -> tuple[bool, str]:
    n = len(live)
    if n < 20:
        return False, "not enough live bars"
    oos = h.get("oos", {})
    bt_dd = oos.get("max_dd") or -0.2
    dd = metrics.max_drawdown(live)
    if dd < 1.5 * bt_dd:
        return True, f"live drawdown {dd:.1%} beyond 1.5x backtest ({bt_dd:.1%})"
    p = h.get("oos_csv")
    if p and (ROOT / p).exists():
        bt = pd.read_csv(ROOT / p, index_col=0).iloc[:, 0]
        mu, sd = float(bt.mean()), float(bt.std())
        if sd > 0:
            k = 0.5 * sd
            s, worst = 0.0, 0.0
            for x in live.values:
                s = min(0.0, s + (x - mu) + k)
                worst = min(worst, s)
            if worst < -5 * sd * math.sqrt(1):  # ~h=5 sigma CUSUM threshold
                return True, f"CUSUM: live returns persistently below backtest (stat {worst / sd:.1f} sd)"
    if n > metrics.ann() / 2 and metrics.sharpe(live) < 0 and (oos.get("sharpe") or 0) > 0.5:
        return True, f"live Sharpe {metrics.sharpe(live):.2f} < 0 after {n} bars"
    return False, "ok"


def run(hypotheses: list[dict]) -> dict:
    reg = decision.load()
    status = json.loads(decision.LIVE_STATUS.read_text()) if decision.LIVE_STATUS.exists() else {}
    uni = __import__("yaml").safe_load((ROOT / "config/universes.yaml").read_text())
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    for spec in hypotheses:
        hid = spec["id"]
        h = reg["hypotheses"].get(hid)
        if not h or h.get("verdict") not in ("ACCEPT", "DEGRADED") or not h.get("accepted_at"):
            continue
        u = uni[spec["universe"]]
        if spec.get("tickers"):
            u = {**u, "tickers": list(spec["tickers"])}
        acc = pd.Timestamp(h["accepted_at"]).tz_localize(None)
        start = str((acc - timedelta(days=4 * 365)).date())
        try:
            p = data.load_panel(u, start, spec["universe"], timeframe=spec.get("timeframe", "1d"))
            metrics.set_periods(p.ppy)
            cand = CD.from_spec(spec)
            v = _variant(cand, h)
            r = cand.run(p, v, Costs(**u.get("costs", {}))).returns
            live = r[r.index > acc]
            live.rename("live_return").to_csv(LIVE_DIR / f"{hid}.csv")
            bad, why = decay_check(live, h)
            status[hid] = {"live_bars": int(len(live)), "live_return": round(float((1 + live).prod() - 1), 4),
                           "live_sharpe": round(metrics.sharpe(live), 3) if len(live) > 20 else None,
                           "live_max_dd": round(metrics.max_drawdown(live), 4),
                           "degraded": bad, "why": why,
                           "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            print(f"[live] {hid}: {status[hid]}")
        except Exception as e:  # noqa: BLE001
            print(f"[live] {hid} failed: {e}")
    decision.LIVE_STATUS.write_text(json.dumps(status, indent=2))
    decision.merge()
    return status
