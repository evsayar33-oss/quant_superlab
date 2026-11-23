"""Tiny, reproducible historical-data source probes.

NO bulk mining: one archived Binance day and one community BIST membership
CSV pinned to an immutable code commit. Raw vendor data are NOT redistributed,
pushed into the user's repos, or authorized for strategy backtests.

HTTP failures produce explicit UNKNOWN rather than synthetic success.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import urllib.error
import urllib.request
import zipfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

BINANCE_ZIP=("https://data.binance.vision/data/spot/daily/klines/"
             "BTCUSDT/1h/BTCUSDT-1h-2021-01-01.zip")
BIST_REPO_SHA="21baf355201841f03b2be49e25fc4f51e5c63e06"
BIST_CSV=("https://raw.githubusercontent.com/GocmenCo/"
          "bist-constituents/"+BIST_REPO_SHA+
          "/data/bist_constituents.csv")
MAX_ZIP=1250000
MAX_BIST=8000000


def get(url,limit):
    with urllib.request.urlopen(
            urllib.request.Request(url,headers={
                "User-Agent":"quant-superlab-free-history-diligence/1.0",
                "Accept":"application/octet-stream"}),timeout=18) as r:
        data=r.read(limit+1)
    if len(data)>limit:
        raise ValueError("HISTORICAL_SOURCE_TOO_LARGE")
    return data


def parse_binance(blob,checksum,now=None):
    """No strategy labels from historical data; OHLC with true taker volume."""
    if len(blob)>MAX_ZIP:
        raise ValueError("OVERSIZED_ARCHIVE")
    actual=hashlib.sha256(blob).hexdigest()
    text=checksum.decode("utf-8-sig").strip().split()
    if not text or len(text[0])!=64 or text[0].lower()!=actual:
        raise ValueError("BINANCE_CHECKSUM_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names=[i for i in z.infolist() if i.filename.endswith(".csv")]
        if len(names)!=1 or names[0].file_size>2000000:
            raise ValueError("UNSAFE_BINANCE_ZIP")
        rows=list(csv.reader(io.StringIO(z.read(names[0]).decode("utf-8-sig"))))
    good=0
    observed=[]
    for row in rows:
        if len(row)<11:
            continue
        try:
            ts=float(row[0])
            o,h,l,c=map(float,row[1:5])
            volume=float(row[7])
            taker_buy=float(row[10])
            t=datetime.fromtimestamp(ts / (1e6 if ts>=1e15 else 1000),timezone.utc)
        except (TypeError,ValueError,OverflowError,OSError):
            continue
        if (t.date().isoformat()!="2021-01-01" or not
            (o>0 and h>=max(o,c) and l<=min(o,c) and volume>=0
             and 0<=taker_buy<=volume)):
            raise ValueError("BINANCE_INVALID_SOURCE_ROWS")
        observed.append((t,volume,taker_buy))
        good+=1
    if good<12 or len({v[0] for v in observed})!=good:
        raise ValueError("NOT_ENOUGH_UNIQUE_CLOSED_HOURLY_ROWS")
    return {
        "status":"ARCHIVED_HOURLY_BARS_CHECKSUM_VALID",
        "source":"BINANCE_SPOT_BTCUSDT_2021-01-01",
        "observations":good,"raw_sha256":actual,
        "first_bar":min(x[0] for x in observed).isoformat(),
        "last_bar":max(x[0] for x in observed).isoformat(),
        "has_taker_buy_quote_volume":True,
        "historically_asof_trade_executability_verified":False,
        "validated_alpha":False,"paper_approved":False,
    }


def parse_bist(blob):
    """Community reconstructed BIST index universe is not historical prices."""
    if len(blob)>MAX_BIST:
        raise ValueError("OVERSIZED_BIST_MEMBERSHIP")
    try:
        reader=csv.DictReader(io.StringIO(blob.decode("utf-8-sig")))
        required={"year","snapshot_date","ticker","index"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("BIST_EXPECTED_COLUMN_MISSING")
        members,dates=defaultdict(Counter),set()
        tickers=set()
        n=0
        for row in reader:
            date=row.get("snapshot_date","")
            ticker=row.get("ticker","")
            tier=row.get("index","").upper().strip()
            if not ticker or len(ticker)>24:
                raise ValueError("BIST_BAD_TICKER")
            if len(date)!=10 or date[4]!="-" or date[7]!="-":
                raise ValueError("BIST_BAD_SNAPSHOT_DATE")
            if tier not in ("","XU030","XU050","XU100"):
                raise ValueError("BIST_UNEXPECTED_INDEX_TIER")
            dates.add(date);tickers.add(ticker);members[date][tier]+=1;n+=1
    except UnicodeError as exc:
        raise ValueError("BIST_INVALID_CSV_ENCODING") from exc
    if n<20000 or len(dates)<100 or len(tickers)<500:
        raise ValueError("BIST_PIT_DATASET_COVERAGE_TOO_SMALL")
    actual_quarters=sum(
        1 for row in members.values()
        if row["XU030"]==30 and row["XU050"]==20 and row["XU100"]==50)
    if actual_quarters<50:
        raise ValueError("BIST_INDEX_MEMBERSHIP_TIERS_INCONSISTENT")
    return {
        "status":"COMMUNITY_PIT_MEMBERSHIP_DATASET_FORMAT_AND_TIERS_VERIFIED",
        "source":"GocmenCo/bist-constituents",
        "pinned_git_commit":BIST_REPO_SHA,
        "raw_sha256":hashlib.sha256(blob).hexdigest(),
        "membership_rows":n,
        "distinct_tickers":len(tickers),
        "historical_review_dates":len(dates),
        "first_snapshot":min(dates),"last_snapshot":max(dates),
        "complete_30_20_50_tier_snapshots":actual_quarters,
        "contains_delisted_member_prices":False,
        "commercial_data_rights_checked":False,
        "official_vintage_crosscheck_completed":False,
        "independent_alpha_validated":False,
    }


def probe():
    captured=datetime.now(timezone.utc).isoformat()
    z={"schema":"QS.source_probe.v1","collector_utc":captured,
       "results":{},"any_strategy_promoted":False,
       "source_is_historically_asof_verified":False}
    for label,call in [
        ("BINANCE_2021_SPOT_TAKER",lambda:parse_binance(
             get(BINANCE_ZIP,MAX_ZIP),get(BINANCE_ZIP+".CHECKSUM",5000))),
        ("BIST_2000_2026_MEMBERSHIP",lambda:parse_bist(
             get(BIST_CSV,MAX_BIST)))]:
        try:
            z["results"][label]=call()
        except (urllib.error.URLError,urllib.error.HTTPError,ValueError,
                UnicodeError,RuntimeError,TimeoutError,zipfile.BadZipFile,
                OSError) as ex:
            z["results"][label]={"status":"DATASET_PROBE_UNAVAILABLE_OR_REJECTED",
                                  "exception_type":type(ex).__name__,
                                  "validated_alpha":False}
    return z


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="out/free_history_atlas")
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    report=probe()
    (out/"actual_archive_probes.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("TWO_FREE_HISTORY_SOURCE_PROBES",
          {k:v["status"] for k,v in report["results"].items()})
    # Do not synthesize a successful historical source if unavailable;
    # reports remain explicit and source-specific for subsequent research.


if __name__=="__main__":
    main()
