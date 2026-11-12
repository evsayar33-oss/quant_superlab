#!/usr/bin/env python3
"""Reproducible H083 multi-style event-aligned daily OHLCV research runner.

Snapshot 619 source-time-eligible events from H081, not the 217 measured subset.
No intervention in production or external broker account.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2] if 'research' in Path(__file__).parts else Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from lab import data
from lab.event_study import thin_events
from h083_styles import (SEAL_DATE,STYLES,COMMISSION_USD,SLIP_BPS,DEFAULT_NOTIONAL,
                          _normalize_bars,evaluate,time_split,summary,
                          month_bootstrap_ci,cash_nav_replay,_index)
from h083_rotation import (ROTATION_RULES,causal_features,equity_rotation,evaluate_rotation)
from h083_robustness import (benchmark_nav, monthly_excess, white_reality_check,
                              cscv_pbo, deflated_sharpe_approx, friction_stress,
                              winner_concentration)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--events',default='research/h083/H081_eligible_snapshot.csv')
    ap.add_argument('--output',default='results/h083')
    ap.add_argument('--limit',type=int,default=0,help='TEST ONLY; default full universe')
    ap.add_argument('--price-start',default='2020-01-01')
    args=ap.parse_args()
    source=Path(args.events)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    events=pd.read_csv(source,dtype={'event_id':str,'ticker':str,'known_at':str,'timestamp_quality':str})
    if not {'event_id','event_date','known_at','ticker','timestamp_quality','category','event_family','sector_etf'}.issubset(events):
        raise ValueError('Event source schema incomplete')
    if len(events)!=619 and not args.limit:
        raise ValueError(f'Frozen H081 universe changed: {len(events)} != 619')
    events=events[events.timestamp_quality.isin(['exact_utc','date_only'])].copy()
    events['ticker']=events.ticker.astype(str).str.strip().str.upper()
    events=events[events.ticker.notna() & events.ticker.ne('') & events.ticker.ne('NAN')]
    # H078-derived 60-calendar-day deoverlap performed BEFORE price lookup/selection.
    chosen=thin_events(events,60)
    if args.limit:
        chosen=chosen.head(args.limit)
    all_tickers=sorted(set(chosen.ticker)|{'SPY'}|set(chosen.sector_etf.dropna().astype(str))-{''})
    print(f'[H083] eligible={len(events)}, first_nonoverlap={len(chosen)}, ticker+ETF={len(all_tickers)}',flush=True)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    raw=data.load_ohlcv(all_tickers,args.price_start,'1d')
    if 'SPY' not in raw or raw['SPY'] is None or len(raw['SPY'])<300:
        raise RuntimeError('SPY history unavailable/too short; no results certified')
    calendar=pd.DatetimeIndex(raw['SPY'].index).tz_localize(None).normalize()
    calendar=calendar[calendar<=SEAL_DATE].unique().sort_values()
    spy=_normalize_bars(raw['SPY'],calendar)
    prices={s:_normalize_bars(p,calendar) for s,p in raw.items() if p is not None and not p.empty}
    available=sum(t in prices for t in set(chosen.ticker))
    coverage={'raw_events':len(events),'chosen_after_cooldown':len(chosen),
              'unique_source_tickers':int(chosen.ticker.nunique()),
              'price_tickers_loaded':available,'missing_tickers':sorted(set(chosen.ticker)-set(prices)),
              'data_start':str(calendar.min().date()),'seal_date':str(SEAL_DATE.date()),
              'event_snapshot_sha256':source_hash,'styles':len(STYLES),
              'requested_tickers_plus_etfs':len(all_tickers)}
    (out/'coverage.json').write_text(json.dumps(coverage,indent=2,ensure_ascii=False),encoding='utf-8')
    print('[H083] price coverage:',available,'/',chosen.ticker.nunique(),flush=True)
    candidates=[];failures=[]
    for ev in chosen.to_dict('records'):
        ticker=ev['ticker']
        if ticker not in prices:
            for style,hold,exit_rule in STYLES:
                failures.append({'event_id':ev['event_id'],'ticker':ticker,'style':style,
                                 'hold':hold,'exit_rule':exit_rule,'reason':'TICKER_PRICE_MISSING'})
            continue
        price=prices[ticker]
        sec_key=str(ev.get('sector_etf') or '').strip().upper()
        sec=prices.get(sec_key)
        for style,hold,exit_rule in STYLES:
            res=evaluate(ev,price,spy,sec,style,hold,exit_rule)
            if res['status']!='MEASURED':
                failures.append({'event_id':ev['event_id'],'ticker':ticker,'style':style,
                                 'hold':hold,'exit_rule':exit_rule,'reason':res['status']})
                continue
            candidates.append({'event_id':ev['event_id'],'ticker':ticker,
                'event_date':ev['event_date'],'category':ev.get('category'),
                'event_family':ev.get('event_family'),'sector_etf':sec_key,
                'style':style,'hold':hold,'exit_rule':exit_rule,
                'name':f'{style}/{hold}/{exit_rule}',**res})
    fails=pd.DataFrame(failures)
    if len(fails):fails.groupby(['style','hold','exit_rule','reason'],dropna=False).size().rename('n').reset_index().to_csv(out/'exclusion_reasons.csv',index=False)
    if not candidates:
        raise RuntimeError('No complete measured trades; examine coverage and exclusions.')
    d=time_split(pd.DataFrame(candidates))
    d.to_csv(out/'all_style_trades.csv',index=False)
    summ=summary(d)
    summ.to_csv(out/'style_statistical_gates.csv',index=False)
    ci=[]
    for _,r in summ.iterrows():
        subset=d[(d.name==r['name'])&d.split.isin(['DISCOVERY','VALIDATION'])]
        a,b=month_bootstrap_ci(subset)
        ci.append({'name':r['name'],'pre_month_cluster_ci95_lo':a,'pre_month_cluster_ci95_hi':b})
    pd.DataFrame(ci).to_csv(out/'month_bootstrap_intervals.csv',index=False)
    nav_rows=[];ledgers=[];daily_nav=[]
    # Portfolios listed ex ante, not chosen from retrospective return rankings.
    selected=['baseline/20/time','trend_50/20/time','breakout_20/20/time',
              'pullback_rsi2/5/time','low_beta/20/time','risk_on/20/time']
    for spec in selected:
        for seg in ('DISCOVERY','VALIDATION','REUSED_TEST'):
            ts=d[(d.name==spec)&(d.split==seg)]
            if ts.empty:
                continue
            nav,ledger,metrics=cash_nav_replay(ts,prices,spy)
            nav['spec']=spec;nav['split']=seg
            ledger['spec']=spec;ledger['split']=seg
            nav_rows.append({'name':spec,'split':seg,**metrics})
            daily_nav.append(nav);ledgers.append(ledger)
    pd.DataFrame(nav_rows).to_csv(out/'portfolio_metrics.csv',index=False)
    if daily_nav:pd.concat(daily_nav,ignore_index=True).to_csv(out/'daily_portfolio_nav.csv',index=False)
    if ledgers:pd.concat(ledgers,ignore_index=True).to_csv(out/'portfolio_trade_ledger.csv',index=False)
    # Track B: repeatable weekly/monthly stock rotation, independent of holding a
    # single event for an arbitrary horizon. Membership only after first verified event.
    eligible_from={}
    sector_map={}
    for ev in chosen.sort_values('event_date').to_dict('records'):
        ticker=ev['ticker']
        pos=_index(ev.get('known_at'),ev.get('event_date'),calendar)
        if pos is None:continue
        day=calendar[pos]
        if ticker not in eligible_from or day<eligible_from[ticker]:
            eligible_from[ticker]=day
            sec=str(ev.get('sector_etf') or '').strip().upper()
            if sec in prices:sector_map[ticker]=sec
    features=causal_features(prices,spy,eligible_from)
    rotation=[];rot_nav=[];rot_trades=[];rot_invalid=[]
    for rule,freq in ROTATION_RULES:
        try:
            nav, ledger, result=equity_rotation(rule,freq,prices,spy,features,sector_map)
            if nav.empty:
                rot_invalid.append({'name':rule,'reason':'EMPTY_NAV'})
                continue
            result.update(evaluate_rotation(nav,spy))
            nav['rule']=rule;ledger['rule']=rule
            rot_nav.append(nav);rot_trades.append(ledger);rotation.append(result)
        except Exception as err:
            # Fail a strategy closed; never invent a missing delisted-stock price.
            rot_invalid.append({'name':rule,'reason':str(err)[:400]})
    if rotation:
        rot=pd.DataFrame(rotation)
        rot['q_pretest_monthly_bh']=__import__('h083_styles').bh_q(rot.p_pretest_monthly.values)
        rot['status']=np.select([
            (rot.trades<30)|(rot.validation_months<5)|(rot.reused_months<4),
            (rot.discovery_mean_monthly_excess<=0)|(rot.validation_mean_monthly_excess<=0),
            rot.q_pretest_monthly_bh>0.10],
            ['LOW_SAMPLE','UNSTABLE_PRETEST','NO_SIGNIFICANCE'],default='PAPER_WATCH')
        rot['certified_alpha']=False
        rot.to_csv(out/'rotation_strategy_summary.csv',index=False)
        combined_nav=pd.concat(rot_nav,ignore_index=True)
        combined_ledger=pd.concat(rot_trades,ignore_index=True)
        combined_nav.to_csv(out/'rotation_daily_nav.csv',index=False)
        combined_ledger.to_csv(out/'rotation_trade_ledger.csv',index=False)
        bench=benchmark_nav(spy,combined_nav[combined_nav.rule==rotation[0]['name']].date)
        bench.to_csv(out/'benchmark_spy_daily_nav.csv',index=False)
        r=bench.nav.pct_change(fill_method=None).fillna(0)
        benchmark_stats={'spy_total_return':float(bench.nav.iloc[-1]/10000-1),
                         'spy_max_drawdown':float((bench.nav/bench.nav.cummax()-1).min()),
                         'spy_daily_sharpe':float(np.sqrt(252)*r.mean()/r.std(ddof=1)) if r.std(ddof=1)>0 else None,
                         'start':str(bench.date.iloc[0].date()),'end':str(bench.date.iloc[-1].date())}
        (out/'benchmark_spy_metrics.json').write_text(json.dumps(benchmark_stats,indent=2),encoding='utf-8')
        ex=monthly_excess(combined_nav,bench)
        ex.to_csv(out/'rotation_monthly_excess_vs_spy.csv')
        from h083_styles import CUT_2
        pre=ex.loc[ex.index<CUT_2]
        robustness={**white_reality_check(pre),**cscv_pbo(pre),**deflated_sharpe_approx(pre),
                    'family':'10 predeclared rotation strategies',
                    'data_reused':True,'no_production_approval':True}
        (out/'multiple_testing_robustness.json').write_text(json.dumps(robustness,indent=2),encoding='utf-8')
        friction_stress(combined_ledger).to_csv(out/'fixed_ledger_execution_stress.csv',index=False)
        winner_concentration(combined_ledger).to_csv(out/'rotation_winner_concentration.csv',index=False)
    else:
        rot=pd.DataFrame();benchmark_stats={};robustness={}
    if rot_invalid:pd.DataFrame(rot_invalid).to_csv(out/'rotation_invalid.csv',index=False)
    # Portfolio comparisons are descriptive, not sealed OOS; don't deploy.
    statuses=summ.status.value_counts().to_dict()
    lines=['# H083 — Multi-style Midas fixed-fee US stock event research','',
        '**Retrospective research only; no production authorization or validated alpha.**','',
        f'- Frozen event snapshot SHA256: `{source_hash}`',
        f'- H081 source-time-eligible events: {len(events)}; after 60d ticker cooldown: {len(chosen)}.',
        f'- Price-covered tickers: {available}/{chosen.ticker.nunique()}; incomplete market-data observations excluded.',
        f'- Tested ex-ante-defined styles: {len(STYLES)}; measured style-trade rows: {len(d)}.',
        f'- Costs: $1.50 buy + $1.50 sell, ${DEFAULT_NOTIONAL:.0f} ticket, {SLIP_BPS:.0f}bp price impact each side.',
        '- Benchmark: SPY bought at same entry open and sold at matching exit close, with the same $3 fees and 5 bp each side.',
        '- Date splits: before 2025-07-31 discovery, 2025-07-31 to 2026-06-01 validation, from 2026-06-02 reused_test.',
        '- Date boundary crossing trades are PURGED from earlier splits.',
        '- End date: 2026-11-11, only matured positions counted.',
        '- Reused historical outcomes were exposed in H078-H082: NO genuinely untouched holdout exists.',
        '- Price provider: Yahoo/yfinance auto-adjusted prices; future corporate-action adjustment and missing/delisted ticker risks require vendor-level PIT audit.',
        '- Ex-post strategy ranking is not a forecast. Production requires independent prospective sealed validation.',
        '- Statistics: preperiod calendar-month clustered one-tailed t test of net returns over equivalent SPY trade, BH-adjusted across all specifications.',
        '- Decision gates: >=20 discovery, >=10 validation, >=10 reused-test, >=8 independent months, positive preperiod excess and q<=0.1.',
        f'- Gate statuses: {json.dumps(statuses,sort_keys=True)}. Certified: 0.',
        '', '## All strategy gate table',summ.to_markdown(index=False,floatfmt='.4f'),
        '', '## Portfolio samples (realized cash, daily mark-to-market)',
        pd.DataFrame(nav_rows).to_markdown(index=False,floatfmt='.4f') if nav_rows else 'No portfolio samples.',
        '', '## Rotating (no fixed event horizon) stock portfolio strategies',
        rot.to_markdown(index=False,floatfmt='.4f') if not rot.empty else 'No valid rotation NAV results.',
        '', '## SPY buy-and-hold full-account comparator',
        json.dumps(benchmark_stats,indent=2),
        '', '## Multiple selection and overfitting audit',
        json.dumps(robustness,indent=2),
        '', '## Crucial gaps',
        'No complete Midas tradability audit, split/delist PIT pricing, earnings fundamental archive, or truly unseen evaluation sample.',
        'Sector strength requires the sector ETF series. Missing sector data is not forward-filled.',
        'RSI pullbacks, breakouts and confirmation entries always occur at NEXT open after the signal close.',
        'Stop execution is conservative: adverse open gaps fill at the opening price, competing stop/target first fill stop.',
        'Dollar-volume filter uses price*volume proxy, subject to Yahoo split-adjustment distortions.',
        'Recompute and verify independently before any deployment.\n']
    (out/'H083_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('[H083] done:', statuses, 'portfolio rows:',len(nav_rows), 'rotation strategies:',len(rotation), 'rotation invalid:',len(rot_invalid),flush=True)

if __name__=='__main__':main()
