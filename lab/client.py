"""Drop-in client for the trading bots (copy this one file into a bot repo as quant_lab_client.py).

    from quant_lab_client import approved, allocation
    for h in approved(system="bist_orderflow_quant"):
        print(h["id"], h["kind"], h["timeframe"], h["targets"])
    print(allocation("bist_orderflow_quant"))      # {"H001": 0.6, "H013": 0.4}  (HRP across ACCEPT ideas)

    from quant_lab_client import arena_allocation   # regime switcher of the strategy arena
    for x in arena_allocation("4h"):               # [] until the switcher gate passes (backtest + forward)
        print(x["coin"], x["rule"], x["params"], x["weight"], x["position"])

Only verdict == "ACCEPT" is returned (WATCH / REJECT / DEGRADED are ignored).
Fail-safe: if the registry cannot be fetched or is stale, everything returns empty ->
the bot must fall back to its own default (never fail-open).
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

URL = os.environ.get("QUANT_LAB_URL",
                     "https://raw.githubusercontent.com/evsayar33-oss/quant_lab/main/decisions/registry.json")
MAX_AGE_DAYS = 10
_cache: dict = {}


def fetch(url: str = URL, timeout: int = 15) -> dict | None:
    if url in _cache:
        return _cache[url]
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            _cache[url] = json.loads(r.read().decode())
            return _cache[url]
    except Exception as e:  # noqa: BLE001
        print(f"[quant_lab] registry fetch failed: {e}")
        return None


def _fresh(h: dict) -> bool:
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(h["validated_at"])
    except Exception:  # noqa: BLE001
        return False
    return age <= timedelta(days=MAX_AGE_DAYS)


def approved(system: str | None = None, url: str = URL) -> list[dict]:
    reg = fetch(url)
    if not reg:
        return []
    out = []
    for hid, h in reg.get("hypotheses", {}).items():
        if h.get("verdict") != "ACCEPT" or (system and h.get("for_system") != system):
            continue
        if not _fresh(h):
            print(f"[quant_lab] {hid} is stale -> ignored")
            continue
        out.append({"id": hid, **h})
    return out


def allocation(system: str, url: str = URL) -> dict:
    """Capital split across this system's approved hypotheses (only fresh ACCEPT ones)."""
    reg = fetch(url)
    if not reg:
        return {}
    ok = {h["id"] for h in approved(system, url)}
    alloc = {k: v for k, v in reg.get("systems", {}).get(system, {}).get("allocation", {}).items() if k in ok}
    s = sum(alloc.values())
    return {k: round(v / s, 4) for k, v in alloc.items()} if s > 0 else {}


ARENA_URL = os.environ.get("QUANT_LAB_ARENA_URL",
                           "https://raw.githubusercontent.com/evsayar33-oss/quant_lab/main/decisions/arena/{tf}/switcher.json")
ARENA_MAX_AGE_HOURS = 30


def arena_allocation(timeframe: str = "4h", url: str = ARENA_URL) -> list[dict]:
    """Strategies the arena regime switcher holds now, with weights (sum <= 1, the rest is cash).
    Empty (fail-safe) unless: the switcher gate passed (backtest AND forward paper record) and the
    file is fresh. Each item: id, coin, rule, params, exit_id, filter, confirm, side, timeframe, weight,
    position, regime. One arena per timeframe: arena_allocation("4h") or arena_allocation("1d")."""
    sw = fetch(url.format(tf=timeframe))
    if not sw or not sw.get("usable"):
        return []
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(sw["updated_at"])
    except Exception:  # noqa: BLE001
        return []
    if age > timedelta(hours=ARENA_MAX_AGE_HOURS):
        print("[quant_lab] arena switcher is stale -> ignored")
        return []
    return list(sw.get("picks", []))
