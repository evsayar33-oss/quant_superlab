"""H088: collect independent, same-underlying USDT linear perpetual bid/ask observations.

Provider availability is *measured*, never presumed. 2/4 venues required for
each symbol; no venue substitution presented as an identical exchange quote.
This is a timestamped market-data experiment, NOT observed executions or alpha.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"decisions"/"evidence"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
URLS = {
    "binance": "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol={symbol}",
    "bybit": "https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}",
    "okx": "https://www.okx.com/api/v5/market/ticker?instId={base}-USDT-SWAP",
    "bitget": "https://api.bitget.com/api/v2/mix/market/ticker?symbol={symbol}&productType=USDT-FUTURES",
}
MAX_QUOTE_AGE_MS = 120_000
MAX_FETCH_SEPARATION_MS = 90_000
MIN_VENUES_PER_SYMBOL = 2


def utcnow():
    return datetime.now(timezone.utc)


def stamp(dt):
    return dt.isoformat(timespec="milliseconds").replace("+00:00","Z")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",",":"), allow_nan=False)


def sha(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def parse(provider, symbol, raw, received_ms):
    base = symbol.replace("USDT","")
    if provider == "binance":
        if raw.get("symbol") != symbol: raise ValueError("binance symbol mismatch")
        bid, ask = float(raw["bidPrice"]), float(raw["askPrice"])
        bq, aq = float(raw["bidQty"]), float(raw["askQty"])
        event = raw.get("time") or raw.get("T") or raw.get("E")
        size_verified = True   # Binance USDT-M bookTicker qty is base contract units.
        instrument = symbol
    elif provider == "bybit":
        if raw.get("retCode") != 0: raise ValueError("bybit retCode")
        rows = raw["result"]["list"]
        if len(rows) != 1 or rows[0].get("symbol") != symbol:
            raise ValueError("bybit symbol mismatch")
        row = rows[0]
        bid, ask = float(row["bid1Price"]), float(row["ask1Price"])
        bq, aq = float(row["bid1Size"]), float(row["ask1Size"])
        event = raw.get("time")
        size_verified = True   # Linear USDT perp contract quantity in base units.
        instrument = symbol
    elif provider == "okx":
        if str(raw.get("code")) != "0": raise ValueError("okx code")
        rows = raw["data"]
        instrument = f"{base}-USDT-SWAP"
        if len(rows) != 1 or rows[0].get("instId") != instrument:
            raise ValueError("okx instId mismatch")
        row = rows[0]
        bid, ask = float(row["bidPx"]), float(row["askPx"])
        bq, aq = float(row["bidSz"]), float(row["askSz"])
        event = row.get("ts")
        # OKX swaps report sizes in contracts; ctVal was not requested.
        size_verified = False
    elif provider == "bitget":
        if str(raw.get("code")) != "00000": raise ValueError("bitget code")
        rows = raw["data"]
        if len(rows) != 1 or rows[0].get("symbol") != symbol:
            raise ValueError("bitget symbol mismatch")
        row = rows[0]
        bid, ask = float(row["bidPr"]), float(row["askPr"])
        bq, aq = float(row["bidSz"]), float(row["askSz"])
        event = row.get("ts")
        size_verified = False   # No verified contract multiplier yet.
        instrument = symbol
    else:
        raise ValueError("unsupported venue")
    if any(not math.isfinite(v) or v <= 0 for v in (bid,ask,bq,aq)) or bid >= ask:
        raise ValueError("invalid/crossed/zero quote")
    event = int(event) if event is not None else None
    if event is not None and (event > received_ms+10000 or received_ms-event > MAX_QUOTE_AGE_MS):
        raise ValueError("stale/future event time")
    mid=(bid+ask)/2
    return {
        "provider":provider, "symbol":symbol, "instrument":instrument,
        "instrument_class":"USDT_LINEAR_PERPETUAL", "quote_currency":"USDT",
        "received_utc_ms":received_ms,"event_utc_ms":event,
        "bid":bid,"ask":ask,"bid_size":bq,"ask_size":aq,
        "size_in_base_units_verified":size_verified,
        "mid":mid,"spread_bps":(ask-bid)/mid*10000,
        "event_timestamp_verified":event is not None,
    }


def fetch(provider, symbol, timeout=12):
    if provider not in URLS or symbol not in SYMBOLS:raise ValueError("unregistered venue/symbol")
    url=URLS[provider].format(symbol=symbol,base=symbol.replace("USDT",""))
    req=urllib.request.Request(url,headers={"User-Agent":"quant-superlab-H088/2.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        if resp.status!=200:raise ValueError("HTTP not 200")
        raw=json.load(resp)
    return parse(provider,symbol,raw,int(utcnow().timestamp()*1000))


def executable_proxy(q, notional_usd, fee_bps_per_side=None):
    """Indicative spread, NOT a fill; unknown multiplier => capacity UNKNOWN."""
    n=float(notional_usd)
    if not math.isfinite(n) or n<=0:raise ValueError("notional invalid")
    fee=None
    if fee_bps_per_side is not None:
        fee=float(fee_bps_per_side)
        if not math.isfinite(fee) or fee<0:raise ValueError("fee invalid")
    verified=bool(q.get("size_in_base_units_verified",True))  # backward-compatible tests
    bid_cap=q["bid"]*q["bid_size"] if verified else None
    ask_cap=q["ask"]*q["ask_size"] if verified else None
    within=(n<=min(bid_cap,ask_cap)) if verified else None
    return {
        "notional_usd":n,
        "top_bid_notional_usd":bid_cap,"top_ask_notional_usd":ask_cap,
        "top_of_book_covers_notional":within,
        "size_unit_verified":verified,
        "indicative_roundtrip_spread_bps":q["spread_bps"] if within is True else None,
        "fee_bps_per_side_user_assumption":fee,
        "indicative_roundtrip_spread_plus_fees_bps":
            q["spread_bps"]+2*fee if within is True and fee is not None else None,
        "actual_execution_cost_verified":False,
        "impact_funding_borrow_and_latency_verified":False,
    }


def collect(fetcher=fetch, clock=utcnow, notional=1000., fee_bps=None):
    rec={"schema":"H088.v2","collected_at_utc":stamp(clock()),
         "kind":"PROSPECTIVE_MARKET_OBSERVATION_NOT_EXECUTED_PNL",
         "sources":{},"comparisons":{},"cost_proxies":{},"errors":{},
         "provider_attempted":list(URLS),
         "provider_minimum_per_symbol":MIN_VENUES_PER_SYMBOL,
         "completeness_by_symbol":{}}
    for symbol in SYMBOLS:
        good={}
        for provider in URLS:
            key=provider+":"+symbol
            try:
                q=fetcher(provider,symbol)
                if q.get("provider") != provider or q.get("symbol") != symbol or q.get("instrument_class") != "USDT_LINEAR_PERPETUAL":
                    raise ValueError("provider/asset/class label inconsistent")
                good[provider]=q
                rec["sources"][key]=q
                rec["cost_proxies"][key]=executable_proxy(q,notional,fee_bps)
            except Exception as exc:
                rec["errors"][key]=type(exc).__name__+": "+str(exc)[:160]
        pairs=[]
        venues=sorted(good)
        for ia,a in enumerate(venues):
            for b in venues[ia+1:]:
                qa,qb=good[a],good[b]
                if abs(qa["received_utc_ms"]-qb["received_utc_ms"])>MAX_FETCH_SEPARATION_MS:
                    rec["errors"][symbol+":"+a+"-"+b]="cross_venue_timestamp_gap"
                    continue
                denom=(qa["mid"]+qb["mid"])/2
                pairs.append({
                    "venues":[a,b],
                    "mid_dislocation_bps":(qa["mid"]-qb["mid"])/denom*10000,
                    "same_usdt_linear_perp_class":True,
                    "independent_exchange_quotes":True,
                    "independent_underlying_market":False,
                    "cross_venue_arbitrage_executable":False,
                })
        rec["comparisons"][symbol]=pairs
        rec["completeness_by_symbol"][symbol]=len(venues)>=MIN_VENUES_PER_SYMBOL and len(pairs)>0
    rec["complete"]=all(rec["completeness_by_symbol"].values())
    return rec


def append_chain(record,path):
    """Hash-chain continuity; immutable evidence strengthened by Git history."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    prev="0"*64;last_ts=None
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():raise ValueError("blank evidence line")
            row=json.loads(line)
            h=row.pop("entry_sha256")
            if row.get("previous_sha256")!=prev or sha(row)!=h:
                raise ValueError("CHAIN_BROKEN: refuse append")
            if last_ts and row["collected_at_utc"]<=last_ts:
                raise ValueError("CHAIN_TIME_NONMONOTONIC")
            prev=h;last_ts=row["collected_at_utc"]
    if last_ts and record["collected_at_utc"]<=last_ts:
        raise ValueError("OBSERVATION_TIME_NONMONOTONIC")
    new={**record,"previous_sha256":prev};new["entry_sha256"]=sha(new)
    with path.open("a") as out:
        out.write(canonical(new)+"\n")
        out.flush();os.fsync(out.fileno())
    return new["entry_sha256"]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--notional",type=float,default=1000)
    parser.add_argument("--fee-bps-per-side",type=float,default=None)
    parser.add_argument("--path",default=str(OUT/"quotes.jsonl"))
    args=parser.parse_args()
    observation=collect(notional=args.notional,fee_bps=args.fee_bps_per_side)
    h=append_chain(observation,args.path)
    print(canonical({"complete":observation["complete"],
        "by_symbol":observation["completeness_by_symbol"],
        "errors":observation["errors"],"source_count":len(observation["sources"]),
        "hash":h,"actual_execution_cost_verified":False}))
    if not observation["complete"]:
        raise SystemExit("INCOMPLETE_PROSPECTIVE_EVIDENCE: source gaps persisted, no synthetic quote")


if __name__=="__main__":main()
