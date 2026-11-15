"""H118: 90-day prospective comparison of three frozen H117 signal families.

Read-only OKX spot market observations. No API keys, orders or backfilled paper
fills. Historical bars are ONLY for causal indicator warmup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.h117 import research as h117

SCHEMA = "h118.prospective_spot.v1"
MARKET = "okx"
SYMBOLS = h117.h116.SYMBOLS
MODELS = ("mom2_baseline", "regime_band30", "regime_7d_band20")
CAPITAL = 10000.0
FEE_BPS = 15.0
DAYS = 90
MAX_QUOTE_AGE_MS = 600000
MAX_CANDLE_AGE_MS = 8 * 3600000
ANCHOR_MS = int(pd.Timestamp("2025-11-01", tz="UTC").timestamp() * 1000)
BAR_MS = 4 * 3600000


def seed(now_ms: int) -> dict:
    return {"schema": SCHEMA, "started_ms": now_ms,
            "ends_ms": now_ms + DAYS * 86400000,
            "market": MARKET, "models": list(MODELS),
            "asset_symbols": list(SYMBOLS), "fee_bps_per_side": FEE_BPS,
            "cash_initial": CAPITAL, "last_candle_ms": None,
            "last_tick_ms": None, "finalized": False,
            "accounts": {m: {"cash": CAPITAL, "qty": {s: 0. for s in SYMBOLS},
                             "nav": CAPITAL, "trades": 0, "turnover_usdt": 0.}
                         for m in MODELS},
            "ticks": [], "outages": []}


def validate(state: dict) -> None:
    if (state.get("schema") != SCHEMA or state.get("market") != MARKET
        or state.get("models") != list(MODELS) or
        state.get("asset_symbols") != list(SYMBOLS) or
        state.get("fee_bps_per_side") != FEE_BPS):
        raise ValueError("UNRECOGNIZED_OR_MUTATED_STUDY")
    if state.get("finalized") and not state.get("ticks"):
        raise ValueError("FINALIZED_WITH_NO_OBSERVATIONS")


def market_snapshot(now_ms: int) -> dict:
    """Fetch a fixed-anchor native 4h candle tape plus contemporaneous bid/ask."""
    import ccxt
    ex = ccxt.okx({"enableRateLimit": True, "timeout": 20000})
    frames, quotes, source_sha = {}, {}, {}
    for symbol in SYMBOLS:
        pair = symbol.replace("USDT", "/USDT")
        bars = []
        cursor = ANCHOR_MS
        for _ in range(90):
            rows = ex.fetch_ohlcv(pair, timeframe="4h", since=cursor, limit=300)
            if not rows:
                break
            newer = [x for x in rows if int(x[0]) >= cursor]
            if not newer:
                raise ValueError("NON_PROGRESSING_PAGINATION:" + symbol)
            bars.extend(newer)
            cursor = int(newer[-1][0]) + BAR_MS
            if cursor > now_ms - BAR_MS:
                break
        else:
            raise ValueError("PAGE_LIMIT:" + symbol)
        data = pd.DataFrame(bars, columns=["ts", "Open", "High", "Low", "Close", "Volume"])
        if data.empty:
            raise ValueError("NO_NATIVE_BARS:" + symbol)
        if data["ts"].duplicated().any():
            raise ValueError("DUPLICATE_BARS:" + symbol)
        data = data.loc[data["ts"] + BAR_MS <= now_ms].copy()
        if len(data) < 1250:
            raise ValueError("TOO_FEW_CLOSED_BARS:" + symbol)
        ts = data.ts.to_numpy(np.int64)
        if np.any(np.diff(ts) != BAR_MS):
            raise ValueError("GAP_IN_SOURCE:" + symbol)
        if not np.isfinite(data[["Open", "High", "Low", "Close", "Volume"]].to_numpy(float)).all():
            raise ValueError("NONFINITE_SOURCE:" + symbol)
        if (data[["Open", "High", "Low", "Close"]] <= 0).any().any():
            raise ValueError("INVALID_OHLC:" + symbol)
        data.index = pd.to_datetime(data.pop("ts").astype("int64"), unit="ms", utc=True).dt.tz_localize(None)
        frames[symbol] = data
        quote = ex.fetch_ticker(pair)
        quote_ms = quote.get("timestamp")
        bid, ask = quote.get("bid"), quote.get("ask")
        if (quote_ms is None or now_ms - int(quote_ms) > MAX_QUOTE_AGE_MS
                or int(quote_ms) > now_ms + 60000 or
                bid is None or ask is None or not (0 < float(bid) <= float(ask))):
            raise ValueError("STALE_OR_INVALID_BID_ASK:" + symbol)
        quotes[symbol] = {"bid": float(bid), "ask": float(ask),
                          "quote_ms": int(quote_ms)}
        encoded = data.to_csv(float_format="%.12f", date_format="%Y-%m-%dT%H:%M:%S",
                              lineterminator="\n").encode("utf-8")
        source_sha[symbol] = hashlib.sha256(encoded).hexdigest()
    if not all(frames[s].index.equals(frames[SYMBOLS[0]].index) for s in SYMBOLS):
        raise ValueError("CROSS_ASSET_BAR_MISALIGNMENT")
    last = int(frames[SYMBOLS[0]].index[-1].tz_localize("UTC").timestamp() * 1000)
    if now_ms - (last + BAR_MS) > MAX_CANDLE_AGE_MS:
        raise ValueError("STALE_CLOSED_CANDLE")
    closes = pd.DataFrame({s: frames[s]["Close"] for s in SYMBOLS})
    research_weights = h117.build(closes)
    return {"last_candle_ms": last, "quotes": quotes,
            "target_weights": {model: {s: float(research_weights[model].iloc[-1][s])
                                       for s in SYMBOLS} for model in MODELS},
            "candle_sha256": source_sha, "venue": MARKET}


def execute(account: dict, targets: dict, quotes: dict, fee_bps: float) -> dict:
    """Observed spread plus assumed one-way fee/slippage per filled notional.

    Pure, deterministic in-memory paper bookkeeping; exits before entries.
    """
    acc = {"cash": float(account["cash"]),
           "qty": {s: float(account["qty"][s]) for s in SYMBOLS},
           "nav": float(account["nav"]),
           "trades": int(account["trades"]),
           "turnover_usdt": float(account["turnover_usdt"])}
    bids = {s: float(quotes[s]["bid"]) for s in SYMBOLS}
    asks = {s: float(quotes[s]["ask"]) for s in SYMBOLS}
    pre_nav = acc["cash"] + sum(acc["qty"][s] * bids[s] for s in SYMBOLS)
    if not math.isfinite(pre_nav) or pre_nav <= 0:
        raise ValueError("INVALID_NAV")
    if any(not math.isfinite(float(targets[s])) or float(targets[s]) < 0 for s in SYMBOLS):
        raise ValueError("INVALID_TARGET")
    if sum(targets.values()) > 1 + 1e-9:
        raise ValueError("TARGET_LEVERAGE")
    target_usdt = {s: pre_nav * float(targets[s]) for s in SYMBOLS}
    changes = []
    cost = fee_bps / 10000
    # Exit/trim at observed bid, then use spendable USDT to buy at observed ask.
    for s in SYMBOLS:
        value = acc["qty"][s] * bids[s]
        if value > target_usdt[s] + 1e-8:
            amount = (value - target_usdt[s]) / bids[s]
            acc["qty"][s] -= amount
            proceeds = amount * bids[s]
            acc["cash"] += proceeds * (1 - cost)
            acc["trades"] += 1
            acc["turnover_usdt"] += proceeds
            changes.append({"asset": s, "side": "SELL", "qty": amount,
                            "price": bids[s], "notional": proceeds})
    for s in SYMBOLS:
        value = acc["qty"][s] * bids[s]
        need = max(0, target_usdt[s] - value)
        spend = min(need, acc["cash"] / (1 + cost))
        if spend > 1e-8:
            bought = spend / asks[s]
            acc["qty"][s] += bought
            acc["cash"] -= spend * (1 + cost)
            acc["trades"] += 1
            acc["turnover_usdt"] += spend
            changes.append({"asset": s, "side": "BUY", "qty": bought,
                            "price": asks[s], "notional": spend})
    acc["nav"] = acc["cash"] + sum(acc["qty"][s] * bids[s] for s in SYMBOLS)
    if acc["cash"] < -1e-6 or acc["nav"] <= 0:
        raise ValueError("PAPER_ACCOUNT_NEGATIVE_CASH_OR_NAV")
    return {"account": acc, "fills": changes}


def apply(state: dict, now_ms: int, snapshot: dict) -> bool:
    validate(state)
    if state["finalized"]:
        return False
    if state["last_tick_ms"] is not None and now_ms <= state["last_tick_ms"]:
        raise ValueError("NON_MONOTONIC_OBSERVATION")
    candle = int(snapshot["last_candle_ms"])
    if candle + BAR_MS > now_ms:
        raise ValueError("FUTURE_OR_UNCLOSED_BAR")
    if state["last_candle_ms"] is not None and candle <= state["last_candle_ms"]:
        return False  # Retried schedule run; no retroactive execution.
    before = len(state["ticks"])
    next_accounts, fills = {}, {}
    for model in MODELS:
        result = execute(state["accounts"][model],
                         snapshot["target_weights"][model],
                         snapshot["quotes"], state["fee_bps_per_side"])
        next_accounts[model] = result["account"]
        fills[model] = result["fills"]
    entry = {"observed_ms": now_ms, "candle_ms": candle, "venue": snapshot["venue"],
             "quote_snapshots": snapshot["quotes"],
             "candle_sha256": snapshot["candle_sha256"],
             "target_weights": snapshot["target_weights"], "paper_fills": fills,
             "nav": {m: next_accounts[m]["nav"] for m in MODELS}}
    # Atomic state update: do not persist partial fills from a failed model.
    state["accounts"] = next_accounts
    state["last_tick_ms"] = now_ms
    state["last_candle_ms"] = candle
    state["ticks"].append(entry)
    if now_ms >= state["ends_ms"]:
        state["finalized"] = True
        state["finished_ms"] = now_ms
    return len(state["ticks"]) == before + 1


def report(state: dict) -> dict:
    n = len(state["ticks"])
    coverage = max(1, math.ceil((min(int(time.time()*1000), state["ends_ms"]) -
                                 state["started_ms"]) / BAR_MS))
    return {"schema": SCHEMA, "status": "FINALIZED" if state["finalized"] else "ACTIVE",
            "start_utc": datetime.fromtimestamp(state["started_ms"]/1000, timezone.utc).isoformat(),
            "end_utc": datetime.fromtimestamp(state["ends_ms"]/1000, timezone.utc).isoformat(),
            "observations": n, "outages": len(state["outages"]),
            "expected_4h_observations_approx": coverage,
            "coverage_ratio_approx": round(n/coverage, 4),
            "investable_market": "OKX SPOT (paper only)", "real_fills": False,
            "venue_independence_from_historical_binance": True,
            "funding_modeled": False,
            "strategies": {m: {"paper_nav": round(state["accounts"][m]["nav"], 5),
                             "return_pct": round(100*(state["accounts"][m]["nav"]/CAPITAL-1), 4),
                             "trades": state["accounts"][m]["trades"],
                             "turnover_usdt": round(state["accounts"][m]["turnover_usdt"], 3)}
                           for m in MODELS},
            "limitations": ["No real orders, realized fills or live broker account.",
                            "Snapshot-only spread + assumed trading fees; no impact/taxes.",
                            "Missed four-hour intervals are NEVER backfilled.",
                            "90 calendar days do not guarantee statistical significance."]}


def run(mode: str, state_path: Path, out: Path, now_ms: int | None = None,
        snapshot_fn=market_snapshot) -> dict | None:
    now = int(time.time()*1000) if now_ms is None else int(now_ms)
    if mode == "start":
        if state_path.exists():
            raise ValueError("ALREADY_STARTED_STATE_IMMUTABLE")
        state = seed(now)
    elif mode == "tick":
        if not state_path.exists():
            print("NO_ACTIVE_STUDY; scheduled job intentionally skipped")
            return None
        state = json.loads(state_path.read_text())
    else:
        raise ValueError("INVALID_MODE")
    validate(state)
    if state["finalized"]:
        print("ALREADY_FINALIZED; nothing executed")
        return state
    try:
        snap = snapshot_fn(now)
        apply(state, now, snap)
    except Exception as exc:
        state["outages"].append({"observed_ms": now, "type": type(exc).__name__,
                                 "message": str(exc)[:160]})
        print(f"FAIL_CLOSED_PAPER_OUTAGE:{type(exc).__name__}:{exc}", file=sys.stderr)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True, allow_nan=False)+"\n")
    (out/"summary.json").write_text(json.dumps(report(state), indent=2, sort_keys=True)+"\n")
    (out/"state.json").write_text(state_path.read_text())
    print(json.dumps({"observations": len(state["ticks"]), "outages": len(state["outages"]),
                      "finalized": state["finalized"]}))
    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("start", "tick"), required=True)
    parser.add_argument("--state", default="results/h118/state.json")
    parser.add_argument("--out", default="results/h118/report")
    args = parser.parse_args()
    run(args.mode, Path(args.state), Path(args.out))
