"""H121: read-only H054-MOM2 and independent Regime Band-30 PAPER intelligence.

CRITICAL: The two books are distinct simulations with different capitals,
inception dates and market models. Their NAV/trades must never be pooled.
H116/H117 historical Binance scores are NOT Bitget PAPER returns.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import math
import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from research import bridge_guard as b

SCHEMA = "QS.h121.h054.paper_intelligence.v1"
SOURCE = "evsayar33-oss/h054_spot_bot"
BOOKS = {"mom2": "main", "band30": "paper/regime-band30-bitget"}
SYMBOLS = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"}
BAR_MS = 14_400_000


def number(x, minimum=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("H121_NONFINITE_PAPER_METRIC")
    if minimum is not None and x < minimum:
        raise ValueError("H121_INVALID_NEGATIVE_PAPER_METRIC")
    return float(x)


def utc_bar(value):
    # Upstream 4h candle IDs are timezone-naive UTC by local bot convention.
    return datetime.fromisoformat(value.replace(" ", "T")).replace(
        tzinfo=timezone.utc) if "T" not in value and "+" not in value else b.utc(value)


def collect(previous, fetch=b.request):
    old = previous.get("sources", {})
    sources, bodies, hashes = {}, {}, {}
    files = {
        "mom2": ("state/state.json", "state/paper.json",
                 "logs/equity.csv", "logs/trades.csv"),
        "band30": ("state.json",),
    }
    for key, ref in BOOKS.items():
        sha = b.get_sha(SOURCE, ref, fetch)
        b.ensure_fast_forward(SOURCE, old.get(key), sha, fetch)
        sources[key] = sha
        for path in files[key]:
            contents, digest = b.pinned(SOURCE, sha, path, fetch)
            bodies[(key, path)] = contents
            hashes[key + ":" + path] = digest
    return sources, bodies, hashes


def parse_mom2(bodies):
    state = json.loads(bodies[("mom2", "state/state.json")])
    paper = json.loads(bodies[("mom2", "state/paper.json")])
    rows = list(csv.DictReader(io.StringIO(bodies[("mom2", "logs/equity.csv")])))
    trades = list(csv.DictReader(io.StringIO(bodies[("mom2", "logs/trades.csv")])))
    if not rows or not all(r.get("time") and r.get("bar") and r.get("mode") for r in rows):
        raise ValueError("H121_MOM2_EQUITY_LOG_EMPTY_OR_BAD")
    if any(r["mode"] != "PAPER" for r in rows):
        raise ValueError("H121_MOM2_LIVE_DATA_MIXED_WITH_PAPER")
    if state.get("why") not in (
        "H054-MOM2 local PAPER_ACCEPT (simulation only)",
        "LIVE_APPROVAL_MISSING", "LOCAL_REGISTRY_SCHEMA",
    ) and state.get("approved") is True:
        raise ValueError("H121_UNKNOWN_APPROVAL_BASIS")
    if state.get("approved") not in (True, False):
        raise ValueError("H121_MOM2_APPROVAL_FLAG_MISSING")
    stamps, values = [], []
    for row in rows:
        stamps.append(b.utc(row["time"]))
        values.append(number(float(row["equity"]), 0))
    if stamps != sorted(stamps):
        raise ValueError("H121_MOM2_EQUITY_HISTORY_REORDERED")
    if any(t.get("mode") != "PAPER" or t.get("ok") not in ("True", "False")
           for t in trades):
        raise ValueError("H121_INVALID_PAPER_TRADE_RECORD")
    last_bar = utc_bar(state["last_bar"])
    updated = b.utc(state["updated_at"])
    if updated < stamps[-1] or last_bar != utc_bar(rows[-1]["bar"]):
        raise ValueError("H121_MOM2_STATE_LEDGER_OUT_OF_SYNC")
    equity = number(state["equity"], 0)
    if abs(equity - values[-1]) > .011:
        raise ValueError("H121_MOM2_EQUITY_NOT_RECONCILED")
    number(paper["fees_paid"], 0)
    for sym in ("BTC/USDT", "ETH/USDT"):
        number(paper["spot"][sym], 0)
        number(paper["perp"][sym]["qty"], 0)
    if len(trades) and max(b.utc(t["time"]) for t in trades) > updated:
        raise ValueError("H121_FUTURE_TRADE_RELATIVE_TO_STATE")
    peak = max(values)
    return {
        "observed_at_utc": updated.isoformat(),
        "latest_4h_bar_utc": last_bar.isoformat(),
        "nav": equity,
        "initial_nominal_usdt": 1000,
        "reported_total_change_pct": round(100*(equity/1000-1), 3),
        "max_recorded_nav": peak,
        "full_log_drawdown_from_peak_pct": round(100*(equity/peak-1), 3),
        "equity_rows": len(rows),
        "paper_order_rows": len(trades),
        "paper_order_errors": sum(t["ok"] == "False" for t in trades),
        "approved_paper": state["approved"],
        "target_weights": state.get("targets", {}),
        "model_revision_segments_not_separated": True,
        "full_history_not_mom2_forward_pnl": True,
        "funding_paid_raw_accounting": number(paper["funding_paid"]),
        "fees_paid_raw_accounting": number(paper["fees_paid"], 0),
        "not_broker_fills": True,
        "execution_price_basis": "LAST_CLOSE_PLUS_ASSUMED_FIXED_SLIPPAGE_AND_FEES",
        "contemporaneous_bid_ask_per_fill_available": False,
        "actual_orderbook_impact_or_queue_position_verified": False,
    }


def parse_band30(bodies):
    state = json.loads(bodies[("band30", "state.json")])
    if state.get("schema") != "h054.regime_band30.bitget.paper.v1":
        raise ValueError("H121_UNEXPECTED_BAND30_SCHEMA")
    ticks = state.get("ticks")
    if not isinstance(ticks, list):
        raise ValueError("H121_MISSING_BAND30_TICKS")
    old = -1
    quoted_spread_bps = []
    book_age_ms = []
    missing_book_size = 0
    for tick in ticks:
        if (not isinstance(tick.get("candle_ms"), int)
                or tick["candle_ms"] <= old or tick["candle_ms"] % BAR_MS != 0):
            raise ValueError("H121_BAD_OR_REORDERED_BAND30_CANDLES")
        old = tick["candle_ms"]
        number(tick["nav"], 0)
        if not isinstance(tick.get("trades"), int) or tick["trades"] < 0:
            raise ValueError("H121_BAD_BAND30_TRADE_COUNT")
        if not isinstance(tick.get("weights"), dict) or not set(tick["weights"]).issubset(SYMBOLS):
            raise ValueError("H121_UNTRUSTED_BAND30_SYMBOLS")
        if sum(number(v, 0) for v in tick["weights"].values()) > 1.0001:
            raise ValueError("H121_EXCESS_BAND30_EXPOSURE")
        if not isinstance(tick.get("quotes"), dict):
            raise ValueError("H121_MISSING_ORDERBOOK_EVIDENCE")
        for sym in tick["weights"]:
            q = tick["quotes"].get(sym, {})
            if not isinstance(q, dict):
                raise ValueError("H121_INVALID_ORDERBOOK_EVIDENCE")
            if "ask" in q and "bid" in q:
                ask, bid = number(q["ask"], 0), number(q["bid"], 0)
                if bid <= 0 or ask < bid:
                    raise ValueError("H121_CROSSED_ORDERBOOK")
                quoted_spread_bps.append(20000.0 * (ask - bid) / (ask + bid))
                if "ts" in q and "received_ms" in q:
                    source_age = int(q["received_ms"]) - int(q["ts"])
                    if source_age < -5000:
                        raise ValueError("H121_QUOTE_FROM_UNRELIABLE_FUTURE")
                    book_age_ms.append(max(0, source_age))
                if "bid_size" not in q or "ask_size" not in q:
                    missing_book_size += 1
    if ticks and old != state.get("last_candle_ms"):
        raise ValueError("H121_BAND30_STATE_TICKS_NOT_ALIGNED")
    gap = state.get("continuity_gaps", [])
    outages = state.get("outages", [])
    if not isinstance(gap, list) or not isinstance(outages, list):
        raise ValueError("H121_BAND30_HISTORY_MISSING")
    for g in gap:
        if not isinstance(g.get("count"), int) or g["count"] < 1:
            raise ValueError("H121_BAD_CANDLE_GAP_COUNT")
    if state.get("finalized") not in (True, False):
        raise ValueError("H121_MISSING_FINALITY")
    last_nav = number(ticks[-1]["nav"], 0) if ticks else number(state.get("cash"), 0)
    return {
        "start_utc": datetime.fromtimestamp(state["start_ms"]/1000, timezone.utc).isoformat(),
        "end_utc": datetime.fromtimestamp(state["end_ms"]/1000, timezone.utc).isoformat(),
        "last_bar_utc": datetime.fromtimestamp(old/1000, timezone.utc).isoformat() if ticks else None,
        "last_observed_utc": datetime.fromtimestamp(ticks[-1]["observed_ms"]/1000, timezone.utc).isoformat() if ticks else None,
        "paper_nav": last_nav, "initial_nominal_usdt": 10000,
        "paper_return_pct": round(100*(last_nav/10000 - 1), 3),
        "observations": len(ticks),
        "trade_count": sum(t["trades"] for t in ticks),
        "gaps": len(gap),
        "missing_candles": sum(g["count"] for g in gap),
        "outages": len(outages),
        "finalized": state["finalized"],
        "uses_observed_bitget_bid_ask": True,
        # Only actual contemporaneous top-of-book quotes are measured.
        # Do NOT claim exchange-realized fill or depth-adjusted impact.
        "execution_quality": {
            "observed_top_of_book_quote_count": len(quoted_spread_bps),
            "observed_median_spread_bps": round(statistics.median(quoted_spread_bps), 3)
                                          if quoted_spread_bps else None,
            "observed_spread_p95_bps": round(sorted(quoted_spread_bps)[
                max(0, math.ceil(.95*len(quoted_spread_bps)) - 1)], 3)
                                          if quoted_spread_bps else None,
            "observed_max_quote_age_ms": max(book_age_ms) if book_age_ms else None,
            "quotes_without_displayed_depth": missing_book_size,
            "full_orderbook_depth_or_queue_position_verified": False,
            "broker_executed_fills_verified": False,
            "order_size_market_impact_calibrated": False,
            "book_spread_is_not_total_fill_cost": True,
        },
        "paper_only": True,
    }


def event(kind, value, message, now):
    return {"lane": "H121", "source_repo": SOURCE, "kind": kind,
            "id": b.hashobj([SCHEMA, kind, value]),
            "observed_at_utc": now.isoformat(), "message": message,
            "official_lab_status": "NOT_RUN", "live_order": False}


def evaluate(mom, band, previous, now):
    if b.utc(mom["observed_at_utc"]) > now or (
        band["last_observed_utc"] and b.utc(band["last_observed_utc"]) > now):
        raise ValueError("H121_FUTURE_REPORTED_OBSERVATION")
    events = []
    if previous:
        old_m, old_b = previous["mom2"], previous["band30"]
        if mom["equity_rows"] < old_m["equity_rows"] or mom["paper_order_rows"] < old_m["paper_order_rows"]:
            raise ValueError("H121_MOM2_RECORDED_HISTORY_DISAPPEARED")
        if band["observations"] < old_b["observations"] or band["gaps"] < old_b["gaps"] or band["outages"] < old_b["outages"]:
            raise ValueError("H121_BAND30_RECORDED_HISTORY_DISAPPEARED")
        if mom["latest_4h_bar_utc"] < old_m["latest_4h_bar_utc"]:
            raise ValueError("H121_MOM2_LAST_BAR_ROLLED_BACK")
        if band["last_bar_utc"] and old_b["last_bar_utc"] and band["last_bar_utc"] < old_b["last_bar_utc"]:
            raise ValueError("H121_BAND30_LAST_BAR_ROLLED_BACK")
        if band["missing_candles"] > old_b["missing_candles"]:
            events.append(event("NEW_UNOBSERVED_CANDLE", str(band["missing_candles"]),
                f"Regime Band-30: kayitli eksik 4s mum sayisi {old_b['missing_candles']} -> {band['missing_candles']}. Geriye donuk doldurma veya varsayimsal fill yok.", now))
        if band["outages"] > old_b["outages"]:
            events.append(event("NEW_PAPER_OUTAGE", str(band["outages"]),
                f"Regime Band-30 yeni kaynak kesintisi: {old_b['outages']} -> {band['outages']}. PAPER sonuclari etkilenebilir.", now))
        if band["trade_count"] > old_b["trade_count"]:
            events.append(event("NEW_BAND30_PAPER_TRADES", str(band["trade_count"]),
                f"Regime Band-30 yeni PAPER simule islem kaydi: {old_b['trade_count']} -> {band['trade_count']}. Karlilik ya da fill dogrulamasi degildir.", now))
        if mom["approved_paper"] is False and old_m["approved_paper"] is True:
            events.append(event("MOM2_PAPER_GATE_REVOKED", mom["latest_4h_bar_utc"],
                "H054-MOM2 yerel PAPER yetkisi kapanmis. LIVE yetkisi verilmez. Orijinal bot kararlarini inceleyin.", now))
        if mom["full_log_drawdown_from_peak_pct"] <= -15 < old_m["full_log_drawdown_from_peak_pct"]:
            events.append(event("MOM2_PAPER_LOSS_THRESHOLD", mom["latest_4h_bar_utc"],
                f"H054 sanal portfoy defterinin kayitli zirveden dususu %{mom['full_log_drawdown_from_peak_pct']}. Defter farkli surumleri icerir; MOM2'ye ozel getiriyi kanitlamaz.", now))
    # Separate stale gate, with a single event keyed by the stale bar itself.
    # Avoid alerting during ordinary pre-close delay or when GitHub cron skips
    # just one candle; both are already tracked by the bot's own cron system.
    completed_start = (int(now.timestamp() * 1000) // BAR_MS - 1)*BAR_MS
    latest_mom = int(b.utc(mom["latest_4h_bar_utc"]).timestamp()*1000)
    last_band = int(b.utc(band["last_bar_utc"]).timestamp()*1000) if band["last_bar_utc"] else 0
    delay_mom = max(0, (completed_start - latest_mom)//BAR_MS)
    delay_band = max(0, (completed_start - last_band)//BAR_MS) if last_band else None
    # Initial bootstrap is quiet; future stale conditions create distinct
    # one-time notices for a *new* stale source bar, not every repeated poll.
    if previous:
        if delay_mom >= 2 and (old_m["latest_4h_bar_utc"] != mom["latest_4h_bar_utc"]
                              or previous.get("mom2_delay_bars", 0) < 2):
            events.append(event("MOM2_CANDLE_STALE", mom["latest_4h_bar_utc"],
                f"H054-MOM2 son 4s mumun gecikmesi {delay_mom} bar (>=2). "
                "Bu test verisi surekliligi riskidir; pozisyon onayi degildir.", now))
        if delay_band is not None and delay_band >= 2 and (
            old_b["last_bar_utc"] != band["last_bar_utc"]
            or previous.get("band30_delay_bars", 0) < 2):
            events.append(event("BAND30_CANDLE_STALE", band["last_bar_utc"],
                f"Regime Band-30 son gozlenen 4s mum {delay_band} bar geride. Eksik mumlara sahte fill yazilmayacak.", now))
    return events, delay_mom, delay_band


def run(state_dir, fetch=b.request, now=None):
    now = now or datetime.now(timezone.utc)
    root = Path(state_dir)
    previous = b.read_manifest(root, SCHEMA)
    sources, bodies, hashes = collect(previous, fetch)
    mom = parse_mom2(bodies)
    band = parse_band30(bodies)
    notices, lag_m, lag_b = evaluate(mom, band, previous, now)
    report = {
        "source_repo": SOURCE, "source_commits": sources, "source_sha256": hashes,
        "mom2": mom, "band30": band, "mom2_delay_bars": lag_m,
        "band30_delay_bars": lag_b,
        "asof_utc": now.isoformat(),
        "book_isolation": "MOM2_MAIN_AND_BAND30_DISTINCT_NO_COMBINED_NAV",
        "strategy_research_links": ["H054-MOM2", "H116", "H117"],
        "h116_h117_not_independent_bitget_pnl": True,
        "not_executable_pnl": True,
        "method_limits": [
            "Full MOM2 main log predates MOM2 revision, hence no isolated MOM2 net return",
            "The Band-30 ledger is 10000 USDT and distinct from 1000-USDT H054",
            "Paper balance and bid/ask references are not broker execution fills",
            "Perpetual funding and hedged cash cannot be inferred from spot-only H116/H117",
            "Missing bars must not be interpolated; absence of trades is not zero alpha",
        ],
    }
    manifest = {
        "sources": sources,
        "mom2": mom, "band30": band,
        "mom2_delay_bars": lag_m, "band30_delay_bars": lag_b,
        "asof_utc": now.isoformat(),
    }
    out = b.record(root, SCHEMA, manifest, report, notices)
    print("H121_PAPER", b.canonical({
        "mom2_nav": mom["nav"], "mom2_log_rows": mom["equity_rows"],
        "band30_nav": band["paper_nav"], "band30_ticks": band["observations"],
        "band30_trades": band["trade_count"],
        "historical_gap_count": band["missing_candles"],
        "new_events": out["events_new"], "alerts_pending": out["alerts_pending"]
    }))
    return out


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--state", required=True)
    args = a.parse_args()
    result = run(args.state)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.getenv("GITHUB_STEP_SUMMARY"), "a") as file:
            file.write("# H121 H054 PAPER Intelligence\n\n")
            file.write("Two independent books; no automatic live approval.\n\n")
            file.write(f"H054 log NAV: {result['mom2']['nav']} USDT "
                       f"({result['mom2']['equity_rows']} log rows, mixed revisions).\n\n")
            file.write(f"Band-30 PAPER NAV: {result['band30']['paper_nav']} USDT, "
                       f"{result['band30']['observations']} ticks, "
                       f"{result['band30']['trade_count']} paper trades, "
                       f"{result['band30']['missing_candles']} missed 4h candles.\n\n")


if __name__ == "__main__":
    main()
