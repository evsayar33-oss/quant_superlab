"""H088: prospective, immutable-by-hash research evidence (NOT live PnL).

Independent exchange order-book top-of-book snapshots from Binance and Bybit.
A provider is independent of another exchange API, NOT independent of BTC price.
No API keys, orders, model refits or ACCEPT updates. Missing quotes stay missing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"decisions"/"evidence"
SYMBOLS=("BTCUSDT","ETHUSDT")
URLS={
    "binance":"https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol={symbol}",
    "bybit":"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}",
}
MAX_QUOTE_AGE_MS=120_000
MAX_FETCH_SEPARATION_MS=90_000


def utcnow():
    return datetime.now(timezone.utc)


def stamp(dt):
    return dt.isoformat(timespec="milliseconds").replace("+00:00","Z")


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)


def sha(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def parse(provider,symbol,raw,received_ms):
    if provider=="binance":
        if raw.get("symbol")!=symbol:raise ValueError("binance symbol mismatch")
        bid=float(raw["bidPrice"]);ask=float(raw["askPrice"])
        bq=float(raw["bidQty"]);aq=float(raw["askQty"])
        # Binance bookTicker time is not guaranteed on all variants.
        event=raw.get("time") or raw.get("T") or raw.get("E")
    elif provider=="bybit":
        if raw.get("retCode")!=0:raise ValueError("bybit retCode")
        rows=raw["result"]["list"]
        if len(rows)!=1 or rows[0].get("symbol")!=symbol:
            raise ValueError("bybit symbol mismatch")
        row=rows[0];bid=float(row["bid1Price"]);ask=float(row["ask1Price"])
        bq=float(row["bid1Size"]);aq=float(row["ask1Size"])
        event=raw.get("time")
    else:raise ValueError("unknown provider")
    if any(not math.isfinite(v) or v<=0 for v in (bid,ask,bq,aq)) or bid>=ask:
        raise ValueError("invalid/crossed/zero book")
    event=int(event) if event is not None else None
    if event is not None and (event>received_ms+10_000 or received_ms-event>MAX_QUOTE_AGE_MS):
        raise ValueError("stale/future exchange event timestamp")
    mid=(bid+ask)/2
    return {"provider":provider,"symbol":symbol,"received_utc_ms":received_ms,
            "event_utc_ms":event,"bid":bid,"ask":ask,"bid_size":bq,"ask_size":aq,
            "mid":mid,"spread_bps":(ask-bid)/mid*10_000,
            "event_timestamp_verified":event is not None}


def fetch(provider,symbol,timeout=12):
    url=URLS[provider].format(symbol=symbol)
    req=urllib.request.Request(url,headers={"User-Agent":"quant-superlab-h088-research/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        if r.status!=200:raise ValueError("HTTP not 200")
        raw=json.load(r)
    received=int(utcnow().timestamp()*1000)
    return parse(provider,symbol,raw,received)


def executable_proxy(q,notional_usd,fee_bps_per_side=None):
    """Buy marketable top ask, sell marketable top bid.

    Top of book is a bounded-size indicative quote, NOT verified fill/slippage.
    Fee schedule is user-supplied, not automatically observed.
    """
    if notional_usd or notional_usd==0:
        n=float(notional_usd)
    else:raise ValueError("notional required")
    if not math.isfinite(n) or n<=0:raise ValueError("notional invalid")
    bid_capacity=q["bid"]*q["bid_size"]
    ask_capacity=q["ask"]*q["ask_size"]
    within=n<=min(bid_capacity,ask_capacity)
    fee=None
    if fee_bps_per_side is not None:
        fee=float(fee_bps_per_side)
        if not math.isfinite(fee) or fee<0:raise ValueError("fee invalid")
    return {"notional_usd":n,"top_bid_notional_usd":bid_capacity,
            "top_ask_notional_usd":ask_capacity,"top_of_book_covers_notional":within,
            "indicative_roundtrip_spread_bps":q["spread_bps"] if within else None,
            "fee_bps_per_side_user_assumption":fee,
            "indicative_roundtrip_spread_plus_fees_bps":
                (q["spread_bps"]+2*fee if within and fee is not None else None),
            "actual_execution_cost_verified":False,
            "impact_funding_borrow_and_latency_verified":False}


def collect(fetcher=fetch,clock=utcnow,notional=1000.0,fee_bps=None):
    now=clock()
    record={"schema":"H088.v1","collected_at_utc":stamp(now),
            "kind":"PROSPECTIVE_MARKET_OBSERVATION_NOT_EXECUTED_PNL",
            "sources":{},"comparisons":{},"cost_proxies":{},"errors":{}}
    for symbol in SYMBOLS:
        valid={}
        for provider in URLS:
            key=provider+":"+symbol
            try:
                q=fetcher(provider,symbol)
                valid[provider]=q
                record["sources"][key]=q
                record["cost_proxies"][key]=executable_proxy(q,notional,fee_bps)
            except Exception as exc:
                record["errors"][key]=type(exc).__name__+": "+str(exc)[:160]
        if len(valid)==2:
            a,b=valid["binance"],valid["bybit"]
            if abs(a["received_utc_ms"]-b["received_utc_ms"])>MAX_FETCH_SEPARATION_MS:
                record["errors"][symbol]="cross_provider_fetch_times_too_far_apart"
                continue
            denom=(a["mid"]+b["mid"])/2
            record["comparisons"][symbol]={
                "binance_bybit_mid_dislocation_bps":(a["mid"]-b["mid"])/denom*10000,
                "two_independent_exchange_quotes":True,
                "independent_underlying_market":False,
                "cross_venue_arbitrage_executable":False}
    record["complete"]=len(record["sources"])==len(SYMBOLS)*len(URLS) and len(record["comparisons"])==len(SYMBOLS)
    return record


def append_chain(record,path):
    """Hash chain detects accidental edits; git history supplies stronger tamper evidence."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    prev="0"*64;last_ts=None
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():raise ValueError("blank evidence line")
            row=json.loads(line)
            h=row.pop("entry_sha256")
            if row.get("previous_sha256")!=prev or sha(row)!=h:
                raise ValueError("CHAIN_BROKEN: refuse to append")
            if last_ts and row["collected_at_utc"]<=last_ts:
                raise ValueError("CHAIN_TIME_NONMONOTONIC")
            prev=h;last_ts=row["collected_at_utc"]
    if last_ts and record["collected_at_utc"]<=last_ts:
        raise ValueError("OBSERVATION_TIME_NONMONOTONIC")
    new={**record,"previous_sha256":prev}
    new["entry_sha256"]=sha(new)
    with path.open("a") as f:
        f.write(canonical(new)+"\n")
        f.flush();os.fsync(f.fileno())
    return new["entry_sha256"]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--notional",type=float,default=1000)
    p.add_argument("--fee-bps-per-side",type=float,default=None,
                   help="Only an explicit ASSUMPTION, not observed broker tier")
    p.add_argument("--path",default=str(OUT/"quotes.jsonl"))
    args=p.parse_args()
    result=collect(notional=args.notional,fee_bps=args.fee_bps_per_side)
    h=append_chain(result,args.path)
    print(canonical({"complete":result["complete"],"errors":result["errors"],
        "quotes":len(result["sources"]),"hash":h,"costs_are_indicative":True}))
    if not result["complete"]:
        raise SystemExit("INCOMPLETE_PROSPECTIVE_EVIDENCE: partial observation saved; no substitute values")


if __name__=="__main__":main()
