"""H097 independent OKX historical funding observations; never invent missing data.

Funding is a distinct public observation, not executable total trading costs.
Funding application requires position interval, side and notional; unavailable
observations make exact historical funding NOT_VERIFIED.
"""
from __future__ import annotations
from urllib.parse import urlencode
from datetime import datetime,timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"h096"))
from market import get_json,SYMBOLS

URL="https://www.okx.com/api/v5/public/funding-rate-history"


def parse(payload):
    if str(payload.get("code"))!="0" or not isinstance(payload.get("data"),list):
        raise ValueError("FUNDING_PROVIDER_ERROR")
    rows=[]
    for x in payload["data"]:
        t=int(x["fundingTime"])
        rate=float(x.get("realizedRate") or x.get("fundingRate"))
        if not (-1<rate<1):raise ValueError("INVALID_FUNDING_RATE")
        rows.append({"funding_time_ms":t,"realized_rate":rate,
                     "rate_field":"realizedRate" if x.get("realizedRate") not in (None,"")
                     else "fundingRate"})
    if len({r["funding_time_ms"] for r in rows})!=len(rows):
        raise ValueError("DUPLICATE_FUNDING_PAGE")
    return rows


def fetch(symbol,pages=4,get=get_json):
    if symbol not in SYMBOLS or not 1<=pages<=10:raise ValueError("INVALID_FUNDING_ARGS")
    cursor=None;found={};seen=set()
    for _ in range(pages):
        params={"instId":SYMBOLS[symbol],"limit":"100"}
        if cursor is not None:params["after"]=str(cursor)
        data=parse(get(URL+"?"+urlencode(params)))
        if not data:break
        oldest=min(r["funding_time_ms"] for r in data)
        if cursor is not None and oldest>=cursor:raise ValueError("FUNDING_PAGINATION_STALLED")
        if oldest in seen:raise ValueError("FUNDING_PAGINATION_LOOP")
        seen.add(oldest)
        for x in data:
            if x["funding_time_ms"] in found and found[x["funding_time_ms"]]!=x:
                raise ValueError("FUNDING_CONFLICT")
            found[x["funding_time_ms"]]=x
        cursor=oldest
        if len(data)<80:break
    rows=sorted(found.values(),key=lambda x:x["funding_time_ms"])
    if not rows:raise ValueError("FUNDING_EMPTY")
    return {"schema":"H097.funding_observations.v1","symbol":symbol,
            "instrument":SYMBOLS[symbol],"source":URL,"observations":rows,
            "count":len(rows),"verified_fills":False,
            "exact_trade_funding_costs_verified":False}


def funding_for_trade(trade,observations):
    """Only return exact *observed* settlement sum if interval coverage can be
    independently established. No assumed schedule interpolation."""
    return {"status":"NOT_VERIFIED_SETTLEMENT_COVERAGE",
            "observed_settlements_in_interval":sum(
                trade["entry_ms"]<r["funding_time_ms"]<=trade["exit_ms"]
                for r in observations),
            "applied_cost":None}
