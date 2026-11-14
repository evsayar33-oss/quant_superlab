"""H089 independent venue metadata and funding snapshots, not H056 backtest.

Official public exchange endpoints, fail closed. OKX ctVal converts contracts
to base units only when ctValCcy equals base and ctType=linear.
Bitget contract size unit must be verified separately; never assume.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import urllib.request
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"research"/"h088"))
from evidence import append_chain,canonical,stamp,utcnow

OUT=ROOT/"decisions"/"evidence"/"h089_venue.jsonl"
SYMBOLS=("BTCUSDT","ETHUSDT")


def get(url,timeout=12):
    req=urllib.request.Request(url,headers={"User-Agent":"quant-superlab-h089/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if response.status!=200:raise ValueError("HTTP status")
        return json.load(response)


def positive(x):
    v=float(x)
    if not math.isfinite(v) or v<=0:raise ValueError("non-positive contract size")
    return v


def okx_meta(symbol,fetch=get):
    base=symbol.removesuffix("USDT")
    instrument=base+"-USDT-SWAP"
    x=fetch("https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId="+instrument)
    if str(x.get("code"))!="0":raise ValueError("OKX instruments API error")
    rows=x.get("data",[])
    if len(rows)!=1:raise ValueError("OKX instrument not unique")
    r=rows[0]
    if r.get("instId")!=instrument or r.get("ctType")!="linear" or r.get("ctValCcy")!=base:
        raise ValueError("OKX multiplier unit not independently verified")
    return {"venue":"okx","symbol":symbol,"instrument":instrument,
            "base_units_per_contract":positive(r["ctVal"]),
            "multiplier_verified_from_public_metadata":True,
            "source":"OKX_PUBLIC_INSTRUMENTS"}


def bitget_meta(symbol,fetch=get):
    x=fetch("https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES&symbol="+symbol)
    if str(x.get("code"))!="00000":raise ValueError("Bitget contracts API error")
    rows=x.get("data",[])
    if len(rows)!=1 or rows[0].get("symbol")!=symbol:
        raise ValueError("Bitget instrument not unique")
    r=rows[0]
    # Public metadata contains volumePlace/sizeMultiplier but not a
    # reliable explicit book-size unit across versions. Do not infer.
    return {"venue":"bitget","symbol":symbol,
            "instrument":symbol,"raw_size_multiplier":r.get("sizeMultiplier"),
            "raw_volume_place":r.get("volumePlace"),
            "base_units_per_contract":None,
            "multiplier_verified_from_public_metadata":False,
            "source":"BITGET_PUBLIC_CONTRACTS_UNIT_UNRESOLVED"}


def funding(venue,symbol,fetch=get):
    base=symbol.removesuffix("USDT")
    if venue=="okx":
        x=fetch("https://www.okx.com/api/v5/public/funding-rate?instId="+base+"-USDT-SWAP")
        if str(x.get("code"))!="0" or len(x.get("data",[]))!=1:raise ValueError("OKX funding API error")
        r=x["data"][0]
        rate=float(r["fundingRate"])
        t=r.get("fundingTime")
    elif venue=="bitget":
        x=fetch("https://api.bitget.com/api/v2/mix/market/current-fund-rate?symbol="+symbol+"&productType=USDT-FUTURES")
        if str(x.get("code"))!="00000" or len(x.get("data",[]))!=1:raise ValueError("Bitget funding API error")
        r=x["data"][0]
        rate=float(r["fundingRate"])
        t=r.get("nextUpdate") or r.get("nextFundingTime")
    else:raise ValueError("unsupported funding venue")
    if not math.isfinite(rate) or abs(rate)>0.1:raise ValueError("invalid funding rate")
    return {"venue":venue,"symbol":symbol,"reported_funding_rate":rate,
            "funding_time_exchange_ms":int(t) if t else None,
            "funding_rate_is_observed_payment":False,
            "historical_H056_strategy_replayed":False}


def collect(fetch=get,now=None):
    now=now or utcnow()
    rec={"schema":"H089.venue.v1","collected_at_utc":stamp(now),
         "kind":"PUBLIC_CONTRACT_METADATA_AND_FUNDING_SNAPSHOT_NOT_FILLS",
         "instruments":{},"funding":{},"errors":{},
         "historical_independent_H056_backtest_verified":False}
    for symbol in SYMBOLS:
        for venue,fn in (("okx",okx_meta),("bitget",bitget_meta)):
            k=venue+":"+symbol
            try:rec["instruments"][k]=fn(symbol,fetch)
            except Exception as e:rec["errors"]["meta:"+k]=type(e).__name__+": "+str(e)[:150]
            try:rec["funding"][k]=funding(venue,symbol,fetch)
            except Exception as e:rec["errors"]["funding:"+k]=type(e).__name__+": "+str(e)[:150]
    rec["at_least_one_verified_multiplier"]=any(x["multiplier_verified_from_public_metadata"] for x in rec["instruments"].values())
    rec["two_venue_funding_per_symbol"]=all(
        "okx:"+s in rec["funding"] and "bitget:"+s in rec["funding"] for s in SYMBOLS)
    return rec


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--path",default=str(OUT))
    args=p.parse_args()
    r=collect()
    h=append_chain(r,args.path)
    print(canonical({"hash":h,"meta":len(r["instruments"]),"funding":len(r["funding"]),
                     "errors":r["errors"],"two_venue_funding":r["two_venue_funding_per_symbol"]}))
    if not r["two_venue_funding_per_symbol"] or not r["at_least_one_verified_multiplier"]:
        raise SystemExit("INCOMPLETE_VENUE_EVIDENCE: persisted; not independently validated")


if __name__=="__main__":main()
