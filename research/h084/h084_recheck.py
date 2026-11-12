"""H084 independent verification of the frozen H083 winner-memory research.

Recomputes the 14 cash-veto rotation variants and six event-history variants.
No future outcomes are used to determine entry-time eligibility.
Results are retrospective; no trade authorization or statistically proven alpha.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np

ROT_RULES = ("monthly_low_beta", "monthly_vol_squeeze")
ROT_FILTERS = ("all","consensus_2","consensus_3","last_same_rule_win",
               "last_any_rule_win","two_prior_same_wins","consensus2_prior_win")
EVENT_FILTERS = ("all","prior_ticker_win","prior_ticker_excess",
                 "prior_sector_winrate","prior_category_winrate","prior_ticker_sector")


def rotation_recheck(frame):
    d = frame.copy()
    for c in ("entry_date","exit_date"):
        d[c] = pd.to_datetime(d[c],errors="raise")
    if (d.exit_date < d.entry_date).any():
        raise ValueError("Future exit before entry")
    if d[["pnl","cost_basis","return_net"]].isna().any().any():
        raise ValueError("Missing PnL")
    if (d.cost_basis <= 0).any():
        raise ValueError("Invalid position value")
    rows=[]
    audit=[]
    for r in d[d.rule.isin(ROT_RULES)].itertuples(index=False):
        past = d[(d.ticker == r.ticker) & (d.exit_date < r.entry_date)]
        same = past[past.rule == r.rule].sort_values("exit_date")
        last_same = len(same)>0 and float(same.iloc[-1].pnl)>0
        same_days = same.groupby("exit_date").pnl.mean().sort_index()
        two_same = len(same_days)>=2 and bool((same_days.iloc[-2:]>0).all())
        all_days = past.groupby("exit_date").pnl.mean().sort_index()
        last_any = len(all_days)>=2 and float(all_days.iloc[-1])>0
        # Concurrent model entry is determined at the preceding close.
        other = d[(d.ticker == r.ticker)&(d.rule != r.rule)&
                  (d.entry_date <= r.entry_date)&(d.exit_date > r.entry_date)]
        consensus = int(other.rule.nunique())
        values = {
            "all":True,"consensus_2":consensus>=2,"consensus_3":consensus>=3,
            "last_same_rule_win":last_same,"last_any_rule_win":last_any,
            "two_prior_same_wins":two_same,
            "consensus2_prior_win":consensus>=2 and last_any,
        }
        audit.append({"ticker":r.ticker,"rule":r.rule,"entry_date":r.entry_date,
                      "exit_date":r.exit_date,"pnl":float(r.pnl),**values})
    a=pd.DataFrame(audit)
    for rule in ROT_RULES:
        sub=a[a.rule==rule]
        base=float(sub.pnl.sum())
        for choice in ROT_FILTERS:
            picked=sub[sub[choice]]
            pnl=float(picked.pnl.sum())
            rows.append({"rule":rule,"selector":choice,"trades":int(len(picked)),
                         "win_rate":float((picked.pnl>0).mean()) if len(picked) else None,
                         "net_profit_usd":pnl,"delta_vs_baseline_usd":pnl-base,
                         "terminal_cash_usd":10000+pnl,
                         "validated_alpha":False,"evaluation":"REUSED_TEST",
                         "method":"CASH_VETO_NO_REPLACEMENT"})
    return pd.DataFrame(rows),a


def event_recheck(frame):
    required={"name","ticker","event_id","entry_date","exit_date","sector_etf",
              "category","midas_net","excess_vs_spy","split"}
    if required-set(frame):
        raise ValueError("Missing event fields: "+str(required-set(frame)))
    d=frame[(frame.name=="baseline/20/time") & (frame.split!="PURGED")].copy()
    d.entry_date=pd.to_datetime(d.entry_date,errors="raise")
    d.exit_date=pd.to_datetime(d.exit_date,errors="raise")
    d["sector_etf"]=d.sector_etf.fillna("UNKNOWN").replace("NAN","UNKNOWN")
    d=d.sort_values(["entry_date","ticker","event_id"]).reset_index(drop=True)
    audit=[]
    for r in d.itertuples(index=False):
        past=d[d.exit_date<r.entry_date]
        ticker=past[past.ticker==r.ticker].sort_values("exit_date")
        sector=past[(past.sector_etf==r.sector_etf)&(past.ticker!=r.ticker)]
        category=past[(past.category==r.category)&(past.ticker!=r.ticker)]
        prior_win=len(ticker)>0 and ticker.iloc[-1].midas_net>0
        prior_excess=len(ticker)>0 and ticker.iloc[-1].excess_vs_spy>0
        sector_win=len(sector)>=8 and (sector.excess_vs_spy>0).mean()>0.55
        category_win=len(category)>=8 and (category.excess_vs_spy>0).mean()>0.55
        audit.append({"event_id":r.event_id,"ticker":r.ticker,
                      "entry_date":r.entry_date,"midas_net":float(r.midas_net),
                      "excess_vs_spy":float(r.excess_vs_spy),
                      "all":True,"prior_ticker_win":prior_win,
                      "prior_ticker_excess":prior_excess,
                      "prior_sector_winrate":sector_win,
                      "prior_category_winrate":category_win,
                      "prior_ticker_sector":prior_win and sector_win})
    a=pd.DataFrame(audit)
    rows=[]
    for name in EVENT_FILTERS:
        p=a[a[name]]
        rows.append({"selector":name,"events":len(p),
                     "win_rate":float((p.midas_net>0).mean()) if len(p) else None,
                     "mean_midas_net":float(p.midas_net.mean()) if len(p) else None,
                     "mean_excess_vs_spy":float(p.excess_vs_spy.mean()) if len(p) else None,
                     "validated_alpha":False,"evaluation":"REUSED_TEST"})
    return pd.DataFrame(rows),a


def run(source,output):
    source,output=Path(source),Path(output)
    ledger=pd.read_csv(source/"rotation_trade_ledger.csv")
    events=pd.read_csv(source/"all_style_trades.csv")
    rotation,rotation_audit=rotation_recheck(ledger)
    event,event_audit=event_recheck(events)
    assert len(rotation)==14 and len(event)==6
    assert len(rotation_audit)==244 and len(event_audit)==196
    # Independent golden-reference checks against frozen H084 published report.
    expected={
        ("monthly_low_beta","all"):(103,6009),
        ("monthly_low_beta","last_same_rule_win"):(31,-694),
        ("monthly_vol_squeeze","all"):(141,5175),
        ("monthly_vol_squeeze","last_same_rule_win"):(44,2670),
        ("monthly_vol_squeeze","consensus_2"):(68,4478),
        ("monthly_vol_squeeze","consensus2_prior_win"):(30,4116),
    }
    for (rule,selector),(count,approx_pnl) in expected.items():
        row=rotation[(rotation.rule==rule)&(rotation.selector==selector)].iloc[0]
        assert int(row.trades)==count,(rule,selector,row.trades,count)
        assert abs(float(row.net_profit_usd)-approx_pnl)<2,(rule,selector,row.net_profit_usd)
    event_expected={"all":196,"prior_ticker_win":52,"prior_ticker_excess":49,
                    "prior_sector_winrate":27,"prior_category_winrate":65,
                    "prior_ticker_sector":4}
    for selector,count in event_expected.items():
        row=event[event.selector==selector].iloc[0]
        assert int(row.events)==count,(selector,row.events,count)
    output.mkdir(parents=True,exist_ok=True)
    rotation.to_csv(output/"winner_rotation_independent_recheck.csv",index=False)
    event.to_csv(output/"winner_event_independent_recheck.csv",index=False)
    rotation_audit.to_csv(output/"rotation_causal_audit.csv",index=False)
    event_audit.to_csv(output/"event_causal_audit.csv",index=False)
    summary={"verification":"PASS","rotation_variants":len(rotation),
             "event_variants":len(event),"total_variants":20,
             "rotation_trades":len(rotation_audit),"event_trades":len(event_audit),
             "new_approved_alpha":0,"historical_holdout":"REUSED_TEST",
             "cost_model":"H083 PnL includes $1.50 buy + $1.50 sell and 5bp/side; no double-charge"}
    (output/"H084_INDEPENDENT_VERIFICATION.json").write_text(
        json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--h083-results",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    run(args.h083_results,args.output)
