"""H089: prospective first-seen paper NAV, explicitly scenario-costed.

Never recompute historic NAV as forward PnL. A position first observed at t0
is priced at the first *later* captured close as baseline; only subsequent
captured closes can generate PnL. Missing days are gaps, never interpolated.
No broker fills, orders or alpha ACCEPT.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"research"/"h088"))
from evidence import append_chain, canonical, stamp, utcnow

WATCH=ROOT/"decisions"/"watch"/"observations.csv"
OUT=ROOT/"decisions"/"evidence"/"h089_forward.jsonl"
SCENARIOS={"optimistic_2bps":2.0,"base_5bps":5.0,"stress_10bps":10.0}
START_NAV=1000.0


def dt(s):
    x=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if x.tzinfo is None:raise ValueError("timestamp must be UTC-aware")
    return x.astimezone(timezone.utc)


def valid_weights(w):
    if not isinstance(w,dict):raise ValueError("positions not dict")
    z={}
    for k,v in w.items():
        if not isinstance(k,str) or not k or not isinstance(v,(int,float)):
            raise ValueError("bad position")
        if not math.isfinite(v) or abs(v)>1:raise ValueError("bad weight")
        if abs(v)>1e-12:z[k]=float(v)
    if sum(abs(v) for v in z.values())>1.000001:raise ValueError("gross leverage >1")
    return z


def first_seen(path=WATCH):
    with Path(path).open(newline="") as f: rows=list(csv.DictReader(f))
    by={}
    for row in rows:
        if row.get("record_type")!="FIRST_SEEN_SNAPSHOT_NOT_FORWARD_PNL":
            continue
        idea=row["idea"]
        seen=dt(row["first_observed_utc"])
        # Freeze first observed decision; later observations are for future rebalances only.
        if idea not in by or seen<by[idea]["seen"]:
            by[idea]={"seen":seen,"positions":valid_weights(json.loads(row["positions"])),
                      "closed_bar":row["latest_closed_bar"]}
    return by


def get_latest_closed(symbol, now=None):
    """Fetch Yahoo daily close with 1-day interval, timestamped on collection.

    Yahoo close is indicative mark, NOT executable futures fill or roll-adjusted PnL.
    """
    import yfinance as yf
    import pandas as pd
    now=now or utcnow()
    data=yf.download(symbol,period="10d",interval="1d",auto_adjust=False,
                     progress=False,threads=False)
    if data is None or data.empty:raise ValueError("no Yahoo daily bars")
    close=data["Close"]
    if hasattr(close,"columns"):close=close.iloc[:,0]
    for index,value in reversed(list(close.dropna().items())):
        date=index.date()
        # Only previous UTC date, conservative: no incomplete current day.
        if date>=now.date():continue
        val=float(value)
        if not math.isfinite(val) or val<=0:continue
        if (now.date()-date).days>5:raise ValueError("stale Yahoo daily close")
        return {"closed_bar_date":date.isoformat(),"close":val,
                "source":"YAHOO_FINANCE_DAILY_CLOSE_NOT_EXECUTABLE",
                "collected_at_utc":stamp(now)}
    raise ValueError("no valid closed daily bar")


def latest_per_idea(records):
    result={}
    for r in records:
        for idea,v in r.get("ideas",{}).items():
            if v.get("status") in ("BASELINE","MARK_TO_MARKET","NO_NEW_CLOSE"):
                result[idea]=v
    return result


def compute_one(idea,initial,prev,prices,now,fee_bps=SCENARIOS):
    positions=initial["positions"]
    seen=initial["seen"]
    if now<=seen:raise ValueError("observation before first seen")
    needed=set(positions)
    if prev and prev.get("status") in ("BASELINE","MARK_TO_MARKET","NO_NEW_CLOSE"):
        needed|=set(prev.get("positions",{}))
    absent=sorted(needed-set(prices))
    if absent:return {"status":"MISSING_PRICE","missing":absent,"forward_pnl_verified":False}
    if any(dt(prices[s]["collected_at_utc"])<seen for s in needed):
        return {"status":"PRICE_NOT_PROSPECTIVELY_OBSERVED","forward_pnl_verified":False}
    if any(prices[s]["closed_bar_date"]<=seen.date().isoformat() for s in needed):
        return {"status":"PRICE_NOT_AFTER_FIRST_SEEN","forward_pnl_verified":False}
    if len({prices[s]["closed_bar_date"] for s in needed})>1:
        return {"status":"NON_SYNCHRONOUS_MARKS","forward_pnl_verified":False}
    if not prev or prev.get("status") not in ("BASELINE","MARK_TO_MARKET","NO_NEW_CLOSE"):
        return {"status":"BASELINE","positions":positions,
                "marks":{s:prices[s] for s in needed},
                "nav_scenarios":{k:START_NAV*(1-sum(abs(v) for v in positions.values())*bps/10000) for k,bps in fee_bps.items()},
                "first_seen_utc":stamp(seen),"forward_pnl_verified":False,
                "note":"first later observed close sets basis; scenario entry fee charged, no pre-baseline gains"}
    old=prev["marks"]
    if any(s not in old for s in needed):
        return {"status":"MISSING_PRIOR_MARK","forward_pnl_verified":False}
    dates={prices[s]["closed_bar_date"] for s in needed}
    if dates and all(prices[s]["closed_bar_date"]==old[s]["closed_bar_date"] for s in needed):
        return {**prev,"status":"NO_NEW_CLOSE","forward_pnl_verified":False}
    if any(prices[s]["closed_bar_date"]<=old[s]["closed_bar_date"] for s in needed):
        return {"status":"STALE_OR_MIXED_BAR","forward_pnl_verified":False}
    # Hold prior weights across observed close-to-close interval. No intra-day fill assumed.
    old_positions=prev["positions"]
    gross=sum(old_positions.get(s,0)*(prices[s]["close"]/old[s]["close"]-1)
              for s in needed)
    if gross<=-1 or not math.isfinite(gross):raise ValueError("invalid return")
    # Positions remain frozen to first-seen snapshot in v1. Subsequent changes
    # are NOT replayed or claimed as executed; a future ledger version must
    # capture and apply each timestamped rebalance prospectively.
    turnover=sum(abs(positions.get(s,0)-old_positions.get(s,0))
                 for s in needed)
    nav={}
    for k,bps in fee_bps.items():
        oldnav=float(prev["nav_scenarios"][k])
        nav[k]=oldnav*(1+gross)*(1-turnover*bps/10000)
    return {"status":"MARK_TO_MARKET","positions":positions,
            "marks":{s:prices[s] for s in needed},"nav_scenarios":nav,
            "gross_return":gross,"turnover_one_way_notional":turnover,
            "forward_pnl_verified":False,
            "note":"scenario-only close marks; no broker fills, futures roll or financing"}


def read_chain(path):
    path=Path(path)
    rows=[];prev="0"*64
    if not path.exists():return rows
    from evidence import sha
    for line in path.read_text().splitlines():
        r=json.loads(line);h=r.pop("entry_sha256")
        if r.get("previous_sha256")!=prev or sha(r)!=h:
            raise ValueError("CHAIN_BROKEN")
        r["entry_sha256"]=h;prev=h;rows.append(r)
    return rows


def collect(now=None,watch=WATCH,out=OUT,price_fetch=get_latest_closed):
    now=now or utcnow()
    first=first_seen(watch)
    if not first:raise ValueError("no real first-seen observations")
    history=read_chain(out)
    prev=latest_per_idea(history)
    symbols=sorted({s for r in first.values() for s in r["positions"]})
    # A zero-position strategy requires no price mark; no fabricated return.
    prices={};errors={}
    for symbol in symbols:
        try:prices[symbol]=price_fetch(symbol,now)
        except Exception as e:errors[symbol]=type(e).__name__+": "+str(e)[:140]
    ideas={}
    for idea,initial in sorted(first.items()):
        ideas[idea]=compute_one(idea,initial,prev.get(idea),prices,now)
    rec={"schema":"H089.forward.v1","collected_at_utc":stamp(now),
         "kind":"SCENARIO_PAPER_NAV_NOT_REALIZED_EXECUTION",
         "first_seen_source_sha256":hashlib.sha256(Path(watch).read_bytes()).hexdigest(),
         "prices":prices,"price_errors":errors,"ideas":ideas,
         "scenario_one_way_bps":SCENARIOS,
         "all_ideas_marked":all(v["status"] in ("BASELINE","MARK_TO_MARKET","NO_NEW_CLOSE") for v in ideas.values()),
         "broker_fills_verified":False,"funding_verified":False,
         "roll_adjusted_futures_returns_verified":False}
    return rec


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--path",default=str(OUT))
    args=ap.parse_args()
    rec=collect(out=Path(args.path))
    digest=append_chain(rec,args.path)
    print(canonical({"hash":digest,"ideas":{k:v["status"] for k,v in rec["ideas"].items()},
                     "errors":rec["price_errors"],"all_ideas_marked":rec["all_ideas_marked"]}))
    if not rec["all_ideas_marked"]:
        raise SystemExit("INCOMPLETE_FORWARD_MARKS: saved gaps, no synthetic returns")


if __name__=="__main__":main()
