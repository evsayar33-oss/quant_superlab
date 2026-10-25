"""Core3 bot: BTC, ETH, SOL on Bitget SPOT, one third of capital each, H054 core rule on closed 4h bars.

  python -m bot.run            # dry run (default): prints the plan, sends nothing
  LIVE=1 python -m bot.run     # live: places market orders (needs BITGET_KEY / BITGET_SECRET / BITGET_PASSPHRASE)

Safety: dry run unless LIVE=1; only spot (no leverage, no shorts); trades only when the target moves more than
the band; skips orders below the exchange minimum; a kill switch file state/STOP stops all trading.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd
import yaml

from bot.signal import BAND, apply_band, exposure

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
STATE = ROOT / "state" / "state.json"


def exchange(live: bool):
    kw = {"enableRateLimit": True, "timeout": 30000, "options": {"defaultType": "spot"}}
    if live:
        kw.update(apiKey=os.environ["BITGET_KEY"], secret=os.environ["BITGET_SECRET"], password=os.environ["BITGET_PASSPHRASE"])
    ex = ccxt.bitget(kw)
    ex.has["fetchCurrencies"] = False      # skip the 2.4 MB coin list; markets are enough
    return ex


def closes(sym: str, n_bars: int = 1600) -> pd.Series:
    """Closed 4h spot bars from Bitget's public REST API (no key). The still-forming bar is dropped."""
    import requests
    url = "https://api.bitget.com/api/v2/spot/market/history-candles"
    rows, end = [], int(pd.Timestamp.utcnow().timestamp() * 1000)
    while len(rows) < n_bars:
        r = requests.get(url, params={"symbol": sym, "granularity": "4h", "endTime": end, "limit": 200}, timeout=30)
        r.raise_for_status()
        d = r.json().get("data") or []
        if not d:
            break
        rows += d
        end = min(int(x[0]) for x in d) - 1
    df = pd.DataFrame([(int(x[0]), float(x[4])) for x in rows], columns=["t", "c"]).drop_duplicates("t").sort_values("t")
    s = pd.Series(df["c"].to_numpy(), index=pd.to_datetime(df["t"], unit="ms"))
    if len(s) and s.index[-1] + pd.Timedelta(hours=4) > pd.Timestamp.utcnow().tz_localize(None):
        s = s.iloc[:-1]
    return s


def execute(ex, sym: str, side: str, qty: float) -> None:
    """Limit order at the best bid (buy) / best ask (sell): no spread paid, no slippage. Price is capped at
    max_slippage from the mid. Unfilled after wait_seconds -> cancel, retry once at the new best price,
    then the rest goes as a market order so the position never lags the signal."""
    import time
    for attempt in range(2):
        ob = ex.fetch_order_book(sym, limit=5)
        bid, ask = ob["bids"][0][0], ob["asks"][0][0]
        mid = (bid + ask) / 2
        price = min(bid, mid * (1 + CFG["max_slippage"])) if side == "buy" else max(ask, mid * (1 - CFG["max_slippage"]))
        amt = float(ex.amount_to_precision(sym, qty))
        if amt * mid < CFG["min_order_usdt"]:
            return
        o = ex.create_order(sym, "limit", side, amt, float(ex.price_to_precision(sym, price)))
        time.sleep(CFG["wait_seconds"])
        o = ex.fetch_order(o["id"], sym)
        filled = float(o.get("filled") or 0)
        if o.get("status") != "closed":
            try:
                ex.cancel_order(o["id"], sym)
            except Exception:
                pass
            o = ex.fetch_order(o["id"], sym)
            filled = float(o.get("filled") or 0)
        qty -= filled
        if qty * mid < CFG["min_order_usdt"]:
            return
    amt = float(ex.amount_to_precision(sym, qty))
    if side == "buy":                                   # Bitget spot market buy is sized in USDT
        ex.create_order(sym, "market", side, amt, None, {"createMarketBuyOrderRequiresPrice": False, "cost": amt * mid})
    else:
        ex.create_order(sym, "market", side, amt)


def main() -> None:
    live = os.environ.get("LIVE") == "1"
    if (ROOT / "state" / "STOP").exists():
        print("STOP file present: no trading"); return
    ex = exchange(live) if live else None
    ppy = 6 * 365.25
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    bal = ex.fetch_balance() if live else {"total": {"USDT": CFG["paper_capital_usdt"]}}
    px, tgt = {}, {}
    for a in CFG["assets"]:
        sym = f"{a}/USDT"
        c = closes(f"{a}USDT")
        e = apply_band(exposure(c, ppy), BAND)
        tgt[a] = float(e.iloc[-1])
        px[a] = float(c.iloc[-1])
    equity = float(bal["total"].get("USDT", 0)) + sum(float(bal["total"].get(a, 0)) * px[a] for a in CFG["assets"])
    share = 1.0 / len(CFG["assets"])
    plan = []
    for a in CFG["assets"]:
        held = float(bal["total"].get(a, 0)) * px[a]
        want = tgt[a] * share * equity
        diff = want - held
        if abs(diff) < max(CFG["min_order_usdt"], BAND * share * equity * 0.5):
            continue
        plan.append({"asset": a, "side": "buy" if diff > 0 else "sell", "usdt": round(abs(diff), 2), "target": round(tgt[a], 3)})
    print(json.dumps({"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "live": live,
                      "equity_usdt": round(equity, 2), "targets": tgt, "plan": plan}, indent=1))
    if live:
        for p in sorted(plan, key=lambda x: x["side"] == "buy"):        # sells first, then buys
            execute(ex, f"{p['asset']}/USDT", p["side"], p["usdt"] / px[p["asset"]])
    state.update({"last_run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "targets": tgt, "equity": equity})
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))


if __name__ == "__main__":
    sys.exit(main())
