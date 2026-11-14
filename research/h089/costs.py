"""H089 cost envelope from already captured real H088 quote + official metadata.

NOT actual fills. No implicit zero funding/impact. Unknown contract units yield
UNKNOWN capacity, not a fabricated execution cost.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"research"/"h088"))
from evidence import append_chain,canonical,stamp,utcnow
sys.path.insert(0,str(HERE))
from forward import read_chain

EVID=ROOT/"decisions"/"evidence"
OUT=EVID/"h089_cost.jsonl"
NOTIONALS=(1000.,10000.,100000.)
FEE_BPS=(2.,5.,10.)


def calculate(q,metadata,notional,fee_bps):
    n=float(notional);fee=float(fee_bps)
    if n<=0 or fee<0 or not math.isfinite(n+fee):raise ValueError("invalid cost inputs")
    base_per_contract=metadata.get("base_units_per_contract")
    verified=metadata.get("multiplier_verified_from_public_metadata") is True
    if verified:
        unit=float(base_per_contract)
        if unit<=0 or not math.isfinite(unit):raise ValueError("bad contract unit")
    else:unit=None
    # H088 bid_size/ask_size are contract counts on OKX, but their size
    # unit remains UNKNOWN for Bitget until verified by a separate source.
    bidcap=q["bid"]*q["bid_size"]*unit if unit is not None else None
    askcap=q["ask"]*q["ask_size"]*unit if unit is not None else None
    enough=(n<=min(bidcap,askcap)) if unit is not None else None
    spread=float(q["spread_bps"])
    if spread<0 or not math.isfinite(spread):raise ValueError("invalid spread")
    return {"notional_usdt":n,"fee_bps_per_side_assumed":fee,
            "bid_top_notional_usdt":bidcap,"ask_top_notional_usdt":askcap,
            "top_level_capacity_sufficient":enough,
            "observed_spread_bps":spread,
            "indicative_roundtrip_spread_plus_fees_bps":
                spread+2*fee if enough is True else None,
            "real_fill_cost_verified":False,
            "impact_beyond_top_level_verified":False,
            "funding_and_borrow_included":False,
            "scenario_complete_realistic_execution":False}


def collect(quote_file=EVID/"quotes.jsonl",meta_file=EVID/"h089_venue.jsonl",now=None):
    now=now or utcnow()
    quotes=read_chain(quote_file);metas=read_chain(meta_file)
    if not quotes or not metas:raise ValueError("no persisted market observations")
    q=quotes[-1];m=metas[-1]
    qts=q["collected_at_utc"];mts=m["collected_at_utc"]
    from forward import dt
    if abs((dt(qts)-dt(mts)).total_seconds())>900:
        raise ValueError("quote and metadata snapshots more than 15min apart")
    rec={"schema":"H089.cost.v1","collected_at_utc":stamp(now),
         "kind":"INDICATIVE_TOP_OF_BOOK_COST_SCENARIOS_NOT_REAL_FILLS",
         "quote_sha256":q["entry_sha256"],"venue_sha256":m["entry_sha256"],
         "quote_time":qts,"venue_time":mts,"costs":{},"unknown":{}}
    for k,book in q.get("sources",{}).items():
        metadata=m.get("instruments",{}).get(k)
        if not metadata:
            rec["unknown"][k]="NO_MATCHED_VERIFIED_CONTRACT_METADATA"
            continue
        rec["costs"][k]=[
            calculate(book,metadata,n,fee)
            for n in NOTIONALS for fee in FEE_BPS]
    rec["real_execution_verified"]=False
    return rec


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--path",default=str(OUT))
    args=ap.parse_args()
    r=collect()
    h=append_chain(r,args.path)
    print(canonical({"hash":h,"venues":list(r["costs"]),"unknown":r["unknown"],
                     "real_execution_verified":False}))


if __name__=="__main__":main()
