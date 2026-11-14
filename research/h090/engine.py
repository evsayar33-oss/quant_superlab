"""H090 deterministic *research-only* causal event-grammar prototype.

This module DOES NOT detect events, execute orders, fit parameters or calculate
alpha. It receives already observed events and checks chronology, source
availability, context, the entry family and a *previously known* target level.
Any missing evidence is a rejected candidate, not a guessed indicator.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

EVENT_KINDS = frozenset({
    "FIB_POSITION", "LIQ_SWEEP", "LIQ_NOT_TAKEN", "STRUCTURE_BREAK",
    "MSS_CONFIRM", "OB_TOUCH", "FVG_TOUCH", "IFVG_CONFIRM", "BB_TOUCH",
    "MB_TOUCH", "TREND_BREAK", "BLOCK_TARGET", "LIQ_TARGET", "FVG_TARGET",
    "FUNDAMENTAL_AVAILABLE", "MACRO_AVAILABLE", "RISK_REGIME"
})
TIMEFRAMES = frozenset({"M", "W", "D", "H4", "H1", "M15", "M5"})
TARGET_FOR_ENTRY = {
    "OB_TOUCH": "BLOCK_TARGET",
    "BB_TOUCH": "BLOCK_TARGET",
    "MB_TOUCH": "BLOCK_TARGET",
    "LIQ_SWEEP": "LIQ_TARGET",
    "FVG_TOUCH": "FVG_TARGET",
    "IFVG_CONFIRM": "FVG_TARGET",
}
RECIPE_KINDS = frozenset({"technical", "technical_fundamental", "technical_macro",
                         "technical_fundamental_macro"})


def utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp string required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return result.astimezone(timezone.utc)


def number(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not price")
    try:
        f = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("finite numeric value required") from exc
    if not math.isfinite(f):
        raise ValueError("non-finite numeric value")
    return f


@dataclass(frozen=True)
class Event:
    event_id: str
    symbol: str
    kind: str
    timeframe: str
    side: str
    occurred_at: str
    observed_at: str
    source: str
    attrs: dict

    @classmethod
    def parse(cls, raw: dict) -> "Event":
        if not isinstance(raw, dict):
            raise ValueError("event must be object")
        e = cls(**raw)
        if not e.event_id or not e.symbol or not e.source:
            raise ValueError("event id, symbol and provenance required")
        if e.kind not in EVENT_KINDS or e.timeframe not in TIMEFRAMES:
            raise ValueError("unregistered event kind/timeframe")
        if e.side not in ("long", "short", "both"):
            raise ValueError("unsupported side")
        if not isinstance(e.attrs, dict):
            raise ValueError("event attrs must be mapping")
        if utc(e.occurred_at) > utc(e.observed_at):
            raise ValueError("future event observed before occurrence")
        if e.kind == "LIQ_NOT_TAKEN":
            start = utc(e.attrs["window_start"])
            end = utc(e.attrs["window_end"])
            if start >= end or end > utc(e.occurred_at):
                raise ValueError("noncausal no-sweep observation window")
        return e

    @property
    def seen(self) -> datetime:
        return utc(self.observed_at)


def validate_recipe(r: dict) -> None:
    if not isinstance(r, dict) or not r.get("id"):
        raise ValueError("recipe id required")
    if r.get("kind") not in RECIPE_KINDS:
        raise ValueError("recipe kind invalid")
    if r.get("side") not in ("long", "short"):
        raise ValueError("recipe must declare one direction")
    steps = r.get("sequence")
    if not isinstance(steps, list) or not steps:
        raise ValueError("non-empty ordered sequence required")
    if any(not isinstance(step, dict) or step.get("kind") not in EVENT_KINDS or
           step.get("timeframe") not in TIMEFRAMES for step in steps):
        raise ValueError("invalid sequence step")
    if steps[-1]["kind"] not in TARGET_FOR_ENTRY:
        raise ValueError("last event must be registered entry family")
    if not isinstance(r.get("max_hours_between"), (int, float)) or not 0 < r["max_hours_between"] <= 720:
        raise ValueError("bounded event lifetime required")
    allowed = r.get("fib_alignment", {})
    if not isinstance(allowed, dict) or any(k not in TIMEFRAMES or v not in
            ("above_05", "below_05") for k, v in allowed.items()):
        raise ValueError("invalid Fibonacci alignment")
    target = r.get("target_event")
    if target is not None and target not in ("BLOCK_TARGET", "LIQ_TARGET", "FVG_TARGET"):
        raise ValueError("unregistered target family")
    for key in ("fundamental", "macro"):
        obj = r.get(key)
        if obj is not None and (not isinstance(obj, dict) or not obj.get("field")
                                or obj.get("equals") is None):
            raise ValueError("explicit context field and value required")
    if "fundamental" in r["kind"] and not r.get("fundamental"):
        raise ValueError("missing required fundamental context")
    if "macro" in r["kind"] and not r.get("macro"):
        raise ValueError("missing required macro context")


def _latest(events: list[Event], kind: str, timeframe: str | None,
            symbol: str, at: datetime, side: str | None = None) -> Event | None:
    pool = [e for e in events if e.kind == kind and e.symbol == symbol and
            (timeframe is None or e.timeframe == timeframe) and e.seen <= at and
            (side is None or e.side in (side, "both"))]
    return max(pool, key=lambda e: (e.seen, e.event_id), default=None)


def _context_matches(events: list[Event], recipe: dict, symbol: str, at: datetime) -> bool:
    for tf, want in recipe.get("fib_alignment", {}).items():
        latest = _latest(events, "FIB_POSITION", tf, symbol, at, recipe["side"])
        if latest is None or latest.attrs.get("position") != want:
            return False
        if not latest.attrs.get("range_anchored_asof"):
            return False
    for typ, kind in (("fundamental", "FUNDAMENTAL_AVAILABLE"),
                      ("macro", "MACRO_AVAILABLE")):
        condition = recipe.get(typ)
        if condition:
            latest = _latest(events, kind, condition.get("timeframe"), symbol, at)
            if latest is None or (latest.attrs.get("field") != condition["field"]
                                  or latest.attrs.get("value") != condition["equals"]):
                return False
            # Publication/availability time is the observation timestamp.
            max_age = condition.get("max_age_hours", 24 * 90)
            if not isinstance(max_age, (int, float)) or max_age <= 0:
                raise ValueError("invalid max_age_hours")
            if at - latest.seen > timedelta(hours=max_age):
                return False
    return True


def _target(events: list[Event], symbol: str, side: str,
            at: datetime, entry_price: float, kind: str) -> Event | None:
    matches = []
    for e in events:
        if e.kind != kind or e.symbol != symbol or e.seen > at:
            continue
        if e.side not in (side, "both"):
            continue
        if "price" not in e.attrs:
            continue
        price = number(e.attrs["price"])
        if (side == "long" and price > entry_price) or (side == "short" and price < entry_price):
            matches.append((abs(price - entry_price), e.event_id, e))
    return min(matches, default=(None, None, None))[2]


def _sequence(candidates: list[Event], recipe: dict) -> list[Event] | None:
    """Strictly increasing *known* times: repeated same-bar confirmation is rejected."""
    result = []
    for step in recipe["sequence"]:
        pool = [e for e in candidates if e.kind == step["kind"] and
                e.timeframe == step["timeframe"] and e.side in (recipe["side"], "both") and
                (not result or 0 < (e.seen - result[-1].seen).total_seconds() <=
                 recipe["max_hours_between"] * 3600)]
        if not pool:
            return None
        # Select earliest valid transition, not the hindsight-best outcome.
        result.append(min(pool, key=lambda x: (x.seen, x.event_id)))
    return result


def evaluate_recipe(raw_events: list[dict], recipe: dict, *, asof: str) -> list[dict]:
    """Return source-traceable research signals, with no simulated fills/PnL.

    One pass per symbol, only information observed no later than asof.
    """
    validate_recipe(recipe)
    cutoff = utc(asof)
    parsed = [Event.parse(raw) for raw in raw_events]
    ids = [e.event_id for e in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate event IDs")
    visible = [e for e in parsed if e.seen <= cutoff]
    result = []
    for symbol in sorted({e.symbol for e in visible}):
        es = [e for e in visible if e.symbol == symbol]
        chain = _sequence(es, recipe)
        if chain is None:
            continue
        entry = chain[-1]
        # Not-taken is a positive certified observation of a complete window,
        # NEVER inferred simply because a sweep event was not collected.
        for e in chain:
            if e.kind == "LIQ_NOT_TAKEN":
                a = utc(e.attrs["window_start"])
                b = utc(e.attrs["window_end"])
                if any(x.kind == "LIQ_SWEEP" and x.timeframe == e.timeframe and
                       a <= utc(x.occurred_at) <= b for x in es):
                    chain = None
                    break
        if chain is None or not _context_matches(es, recipe, symbol, entry.seen):
            continue
        if "price" not in entry.attrs:
            continue
        entry_price = number(entry.attrs["price"])
        if entry_price <= 0:
            continue
        target_kind = recipe.get("target_event") or TARGET_FOR_ENTRY[entry.kind]
        target = _target(es, symbol, recipe["side"], entry.seen, entry_price, target_kind)
        if target is None:
            continue  # Explicitly no trade without a known valid target.
        target_price = number(target.attrs["price"])
        result.append({
            "recipe_id": recipe["id"], "symbol": symbol, "side": recipe["side"],
            "entry_family": entry.kind, "entry_at_utc": entry.observed_at,
            "entry_reference_price": entry_price, "target_family": target_kind,
            "target_reference_price": target_price,
            "event_ids": [e.event_id for e in chain], "target_event_id": target.event_id,
            "kind": "RESEARCH_SIGNAL_NOT_ORDER_NOT_BACKTEST",
            "execution_verified": False, "profitability_verified": False,
        })
    return result


def load_recipes(path: str | Path | None = None) -> list[dict]:
    src = Path(path) if path is not None else Path(__file__).with_name("recipes.json")
    obj = json.loads(src.read_text())
    if obj.get("schema") != "H090.recipes.v1":
        raise ValueError("recipe schema mismatch")
    recipes = obj["recipes"]
    if len({r["id"] for r in recipes}) != len(recipes):
        raise ValueError("duplicate recipe ID")
    for recipe in recipes:
        validate_recipe(recipe)
    return recipes
