"""One invocation: deterministic historical hypothesis matrix and committee report."""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path
from campaign_core import (HOUR,VENUES,SYMBOLS,TIMEFRAMES,SIDES,FAMILIES,COSTS,
                           validate,aggregate,btc_regime,evaluate)
from campaign_stats import metrics,time_splits,weekly_bootstrap,weekly_signflip,bh,pair_decision

SCHEMA="h109.one_shot_campaign.v1"

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def load(source):
    h104=json.loads((source/"summary.json").read_text())
    if h104.get("schema")!="h104.long_history.v1":raise ValueError("INVALID_H104_SCHEMA")
    series={};meta={}
    for venue in VENUES:
        for symbol in SYMBOLS:
            key=f"{symbol}_{venue}"
            src=h104["sources"][key]
            path=source/"bars"/f"{key}.json"
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=src["bars_sha256"]:
                raise ValueError("H104_SHA256_MISMATCH:"+key)
            bars=validate(json.loads(raw))
            gaps=sum(b["ts"]-a["ts"]!=HOUR for a,b in zip(bars,bars[1:]))
            if gaps!=src["gap_count"]:raise ValueError("H104_GAP_METADATA_MISMATCH")
            if gaps:raise ValueError("SOURCE_GAPS_FAIL_CLOSED:"+key)
            series[key]=bars
            meta[key]={"bars_sha256":src["bars_sha256"],"source_bars":len(bars),
                       "first_ms":bars[0]["ts"],"last_ms":bars[-1]["ts"]}
    start=max(b[0]["ts"] for b in series.values())
    end=min(b[-1]["ts"] for b in series.values())
    if end-start<90*24*HOUR:raise ValueError("PAIRED_HISTORY_LESS_THAN_90_DAYS")
    # Exactly the same UTC span across all symbols and venues. No interpolation.
    cut={key:[b for b in bars if start<=b["ts"]<=end] for key,bars in series.items()}
    if len({len(b) for b in cut.values()})!=1:raise ValueError("COMMON_WINDOW_MISSING_BARS")
    return cut,{"source_sha256":meta,"start_ms":start,"end_ms":end,
                "common_hours":(end-start)//HOUR+1}

def candidate_rows(bars,out):
    series={}
    for venue in VENUES:
        for symbol in SYMBOLS:
            hourly=bars[f"{symbol}_{venue}"]
            series[(venue,symbol,"1H")]=hourly
            series[(venue,symbol,"4H")]=aggregate(hourly)
    if min(len(v) for v in series.values())<100:raise ValueError("SHORT_AGGREGATED_SERIES")
    candidates=[];windows={}
    for tf in TIMEFRAMES:
        step=HOUR if tf=="1H" else 4*HOUR
        common=set.intersection(*(set(x["ts"] for x in series[(venue,symbol,tf)])
                                 for venue in VENUES for symbol in SYMBOLS))
        common=sorted(common)
        if len(common)<100:raise ValueError("NO_COMMON_TIMEFRAME")
        train_end=common[int(len(common)*.5)]
        val_end=common[int(len(common)*.75)]
        windows[tf]={"first_ms":common[0],"last_ms":common[-1],
                     "common_bars":len(common),"train_end_ms":train_end,
                     "historical_tail_start_ms":val_end}
        for venue in VENUES:
            context=btc_regime(series[(venue,"BTC",tf)],step)
            for symbol in SYMBOLS:
                data=series[(venue,symbol,tf)]
                for fam in FAMILIES:
                    for side in SIDES:
                        key=f"{venue}_{symbol}_{tf}_{fam}_{side}"
                        trades=evaluate(data,step,fam,side,context)
                        sha=save(out/"ledgers"/(key+".json"),trades)
                        full=metrics(trades)
                        splits=time_splits(trades,train_end,val_end)
                        regimes={name:metrics([t for t in trades if t["btc_regime"]==name])
                                 for name in ("risk_on","risk_off")}
                        regimes.update({name:metrics([t for t in trades if t["vol_regime"]==name])
                                        for name in ("high_vol","low_vol")})
                        candidates.append({"id":key,"pair_id":f"{symbol}_{tf}_{fam}_{side}",
                                           "venue":venue,"symbol":symbol,"timeframe":tf,
                                           "family":fam,"side":side,"control":fam=="calendar_control",
                                           "ledger_sha256":sha,"full":full,"split":splits,
                                           "regimes":regimes,
                                           "week_boot40":weekly_bootstrap(trades),
                                           "week_signflip_p40":weekly_signflip(trades)})
    return candidates,windows

def report(candidates):
    q=bh([(x["id"],x["week_signflip_p40"] if not x["control"] else None) for x in candidates])
    for c in candidates:c["bh_q40"]=q[c["id"]]
    index={c["id"]:c for c in candidates}
    pairs=[]
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            for fam in FAMILIES:
                for side in SIDES:
                    pair_id=f"{symbol}_{tf}_{fam}_{side}"
                    v={venue:index[f"{venue}_{pair_id}"] for venue in VENUES}
                    entries=list(v.values())
                    all_stats=[x["full"] for x in entries]
                    tails=[x["split"]["historical_tail"] for x in entries]
                    row={"id":pair_id,"control":fam=="calendar_control",
                         "paired_n30_and_tail10":all(x["n"]>=30 for x in all_stats)
                                                and all(x["n"]>=10 for x in tails),
                         "positive40_both":all(x["net_mean_r"]["40"] is not None and x["net_mean_r"]["40"]>0 for x in all_stats),
                         "positive80_both":all(x["net_mean_r"]["80"] is not None and x["net_mean_r"]["80"]>0 for x in all_stats),
                         "positive_tail40_both":all(x["net_mean_r"]["40"] is not None and x["net_mean_r"]["40"]>0 for x in tails),
                         "weekly_bootstrap_lower_positive_both":all(x["week_boot40"]["ci95"] is not None
                             and x["week_boot40"]["ci95"][0]>0 for x in entries),
                         "bh_q_under005_both":all(x["bh_q40"] is not None and x["bh_q40"]<.05 for x in entries),
                         "venues":{venue:{"n":x["full"]["n"],"tail_n":x["split"]["historical_tail"]["n"],
                            "net40_r":x["full"]["net_mean_r"]["40"],
                            "net80_r":x["full"]["net_mean_r"]["80"],
                            "tail_net40_r":x["split"]["historical_tail"]["net_mean_r"]["40"],
                            "bh_q":x["bh_q40"]} for venue,x in v.items()}}
                    row["decision"]=pair_decision(row)
                    pairs.append(row)
    return pairs

def run(source,out):
    bars,provenance=load(source)
    candidates,windows=candidate_rows(bars,out)
    pairs=report(candidates)
    manifest={"schema":SCHEMA,"provenance":provenance,"timeframes":list(TIMEFRAMES),
        "symbols":list(SYMBOLS),"venues":list(VENUES),"families":list(FAMILIES),
        "sides":list(SIDES),"cost_scenarios_roundtrip_bps":list(COSTS),
        "signal_parameters":"fixed causal 24/72-bar, z=1.8, RSI2 15/85, momentum 3%, compression 0.8",
        "execution":"next-open, 2x range ATR stop, 3x range ATR target, 48h max, stop-first",
        "splits":"fixed shared UTC 50/25/25 chronological; purge crossing train/validation/tail",
        "regimes":"BTC 72-bar return sign and trailing 24/72 volatility ratio, as-of signal",
        "inference":"1000 fixed-seed weekly-cluster bootstrap and signflip; pooled BH q values across non-control eligible venue tests",
        "gates":"paired n>=30 and historical-tail>=10; net40 positive, net80 positive, tail40 positive, weekly lower95 positive and both q<.05",
        "time_windows":windows,"no_parameter_search":True}
    manifest_hash=save(out/"manifest.json",manifest)
    statuses=dict(Counter(x["decision"] for x in pairs))
    summary={"schema":SCHEMA,"manifest_sha256":manifest_hash,
         "venue_level_trials":len(candidates),"paired_candidates":len(pairs),
         "non_control_pairs":sum(not p["control"] for p in pairs),
         "decision_counts":statuses,"paired":pairs,
         "data_not_testable":{
            "funding_cash_flows":"NO_VERIFIED_HISTORICAL_FUNDING",
            "orderbook_slippage_and_realized_fills":"NO_REPLAYABLE_L2_OR_ORDER_LOG",
            "options_implied_volatility":"NO_OPTIONS_HISTORY",
            "open_interest_and_liquidations":"NO_VERIFIED_TIMESERIES",
            "macro_cross_asset":"NO_TIMESTAMP_ALIGNED_EXTERNAL_SERIES",
            "low_timeframes_5m_15m":"NO_NATIVE_COMMON_180D_SOURCE",
            "independent_venue_replication":"VENUES_CORRELATED",
            "30_day_forward_paper":"CANNOT_REPLACE_FUTURE_TIME_WITH_BACKTEST"},
         "alpha_accepted":False,"prospective_oos_verified":False,
         "real_execution_verified":False,"portfolio_nav_verified":False,
         "funding_verified":False,"research_only":True,
         "statistical_tests_only_descriptive":True,
         "limitations":["Finite predefined grid does not encompass all imaginable strategies",
            "Old market periods and previous research reuse invalidate untouched prospective claims",
            "Two crypto venues and BTC/ETH share market exposures",
            "Weekly bootstrap/BH are descriptive; market nonstationarity may invalidate inference",
            "Historical OHLC stop-first execution proxy omits funding, impact, fees realized and net NAV",
            "No candidate can be promoted without future independent paper evidence"]}
    save(out/"trials.json",candidates)
    save(out/"summary.json",summary)
    out.mkdir(parents=True,exist_ok=True)
    with (out/"matrix.csv").open("w",newline="") as fp:
        w=csv.writer(fp);w.writerow(["pair_id","decision","okx_n","gate_n","okx_net40_r",
            "gate_net40_r","okx_net80_r","gate_net80_r","okx_tail_n","gate_tail_n","okx_q","gate_q"])
        for x in pairs:
            a,b=(x["venues"][v] for v in VENUES)
            w.writerow([x["id"],x["decision"],a["n"],b["n"],a["net40_r"],b["net40_r"],
                a["net80_r"],b["net80_r"],a["tail_n"],b["tail_n"],a["bh_q"],b["bh_q"]])
    (out/"committee.md").write_text("# Consolidated historical research committee\n\n"
        +f"Venue trials: {len(candidates)}. Paired candidates: {len(pairs)}.\n\n"
        +"## Decision breakdown\n"
        +"".join("- "+name+": "+str(n)+"\n" for name,n in sorted(statuses.items()))
        +"\nNo alpha accepted. This is historical replay only; external execution and forward data absent.\n")
    print(json.dumps({"schema":SCHEMA,"trials":len(candidates),"pairs":len(pairs),
                      "decision_counts":statuses,"alpha_accepted":False},sort_keys=True))
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",default="results/h104")
    p.add_argument("--out",default="results/h109/campaign")
    x=p.parse_args();run(Path(x.source),Path(x.out))
