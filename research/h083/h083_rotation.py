"""H083 Track B: event-eligible-universe, long-only systematic stock rotation.

These are genuinely different trade styles from event buy-and-hold: repeated
weekly/monthly stock ranking, trend following, mean-reversion, risk-off cash.
All indicators and eligibility as of PRIOR completed close; execution at NEXT open.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

from h083_styles import COMMISSION_USD, SLIP_BPS, SEAL_DATE, CUT_1, CUT_2, _rsi2, _prior_beta, _atr14, bh_q

# No tuning on reported outcomes. Frequency and filters frozen ex ante.
ROTATION_RULES=(
    ('weekly_3m_mom','weekly'),('weekly_trend_50','weekly'),
    ('monthly_6m_mom','monthly'),('monthly_breakout','monthly'),
    ('monthly_pullback','monthly'),('monthly_low_beta','monthly'),
    ('monthly_sector_leader','monthly'),('monthly_vol_squeeze','monthly'),
    ('monthly_risk_on_mom','monthly'),('monthly_market_rs','monthly'),
)


def causal_features(prices:dict[str,pd.DataFrame],spy:pd.DataFrame,
                    earliest_entry:dict[str,pd.Timestamp]) -> dict[str,pd.DataFrame]:
    """Only past close and known event eligible tickers at trading-time."""
    b=spy.Close
    s20=b.pct_change(20,fill_method=None).shift(1)
    out={}
    for ticker,p in prices.items():
        if ticker=='SPY' or ticker not in earliest_entry:
            continue
        c=p.Close
        atr=_atr14(p)/c
        def momentum(n):
            return (c/c.shift(n)-1).shift(1)
        f=pd.DataFrame(index=p.index)
        f['eligible']=f.index>=pd.Timestamp(earliest_entry[ticker]).normalize()
        f['price_ok']=(c.shift(1)>0)&(p.Volume.shift(1)>0)
        f['liq20']=(c*p.Volume).rolling(20,min_periods=20).mean().shift(1)
        f['mom63']=momentum(63)
        f['mom126']=momentum(126)
        f['mom_12_1']=(c.shift(6)/c.shift(126)-1)
        f['trend50']=(c.shift(1)>c.rolling(50,min_periods=50).mean().shift(1))
        f['trend200']=(c.shift(1)>c.rolling(200,min_periods=200).mean().shift(1))
        f['slope50']=(c.rolling(50,min_periods=50).mean().shift(1)>
                      c.rolling(50,min_periods=50).mean().shift(11))
        f['breakout']=(c.shift(1)>p.High.shift(2).rolling(20,min_periods=20).max())
        f['rsi2']=_rsi2(c).shift(1)
        f['beta']=_prior_beta(c,b).shift(1)
        f['atr_ratio']=atr.shift(1)
        f['atr_low']=(atr.shift(1)<atr.shift(1).rolling(126,min_periods=80).quantile(.2))
        f['spy_mom63']=(b/b.shift(63)-1).shift(1)
        f['spy_mom20']=s20
        out[ticker]=f
    return out


def _rank(rule:str,day:pd.Timestamp,features:dict[str,pd.DataFrame],
          prices:dict[str,pd.DataFrame],spy:pd.DataFrame,
          sectors:dict[str,str],slot_count=5)->list[str]:
    c=spy.Close
    day_idx=spy.index.get_loc(day)
    if day_idx<200:
        return []
    spy_trend=c.iloc[day_idx-1]>c.rolling(200,min_periods=200).mean().iloc[day_idx-1]
    if rule=='monthly_risk_on_mom' and not spy_trend:
        return []
    scores=[]
    for ticker,f in features.items():
        if day not in f.index or ticker not in prices:
            continue
        row=f.loc[day]
        if not (bool(row['eligible']) and bool(row['price_ok']) and pd.notna(row['liq20']) and row['liq20']>=5e6):
            continue
        px=prices[ticker]
        if pd.isna(px.loc[day,'Open']) or px.loc[day,'Open']<=0:
            continue
        m63=row.mom63;m126=row.mom126
        if rule in ('weekly_3m_mom','monthly_6m_mom','monthly_risk_on_mom','monthly_market_rs'):
            if not bool(row.trend200) or not (pd.notna(m63) and pd.notna(m126)):
                continue
            if rule=='weekly_3m_mom':score=m63
            elif rule=='monthly_6m_mom':score=row.mom_12_1
            elif rule=='monthly_risk_on_mom':score=row.mom_12_1
            else:score=m63-row.spy_mom63
            if not pd.notna(score) or score<=0:continue
        elif rule=='weekly_trend_50':
            if not (bool(row.trend50) and bool(row.slope50) and pd.notna(m63) and m63>0):continue
            score=m63
        elif rule=='monthly_breakout':
            if not (bool(row.breakout) and bool(row.trend50) and pd.notna(m63)):continue
            score=m63
        elif rule=='monthly_pullback':
            if not (bool(row.trend200) and pd.notna(row.rsi2) and row.rsi2<15):continue
            score=-row.rsi2
        elif rule=='monthly_low_beta':
            if not (bool(row.trend200) and pd.notna(row.beta) and 0<=row.beta<=1 and pd.notna(m63) and m63>0):continue
            score=1-row.beta
        elif rule=='monthly_sector_leader':
            sector=sectors.get(ticker)
            if not sector or sector not in prices:continue
            sec_close=prices[sector].Close
            s=(sec_close/sec_close.shift(20)-1).shift(1).loc[day]
            if not (pd.notna(s) and pd.notna(row.spy_mom20) and s>row.spy_mom20 and bool(row.trend50)):
                continue
            score=m63
        elif rule=='monthly_vol_squeeze':
            if not (bool(row.trend50) and bool(row.atr_low) and pd.notna(m63)):
                continue
            score=m63
        else:raise KeyError(rule)
        if pd.notna(score) and np.isfinite(score):scores.append((float(score),ticker))
    return [ticker for _,ticker in sorted(scores, key=lambda x:(-x[0],x[1]))[:slot_count]]


def _is_rebalance(prev:pd.Timestamp|None,cur:pd.Timestamp,freq:str)->bool:
    if prev is None:return True
    if freq=='monthly':return (cur.year,cur.month)!=(prev.year,prev.month)
    if freq=='weekly':return (cur.isocalendar().year,cur.isocalendar().week)!=(prev.isocalendar().year,prev.isocalendar().week)
    raise KeyError(freq)


def equity_rotation(rule:str,frequency:str,prices:dict[str,pd.DataFrame],
                    spy:pd.DataFrame, features:dict[str,pd.DataFrame],sectors:dict[str,str],
                    initial=10000.,tickets=2000.,slots=5,
                    cost=COMMISSION_USD,slippage=SLIP_BPS,
                    from_date='2023-01-03',thru=SEAL_DATE)->tuple[pd.DataFrame,pd.DataFrame,dict]:
    """Daily mark-to-market, no short/borrow, equal-size lots, costs both sides."""
    idx=spy.index[(spy.index>=pd.Timestamp(from_date))&(spy.index<=pd.Timestamp(thru))]
    if not len(idx):return pd.DataFrame(),pd.DataFrame(),{}
    held={};cash=float(initial);daily=[];trades=[];previous=None;bad_marks=0
    s=slippage/10000.
    for day in idx:
        if _is_rebalance(previous,day,frequency):
            rank=_rank(rule,day,features,prices,spy,sectors,slots)
            # First liquidate non-selected at today's OPEN, before buying new ones.
            for ticker in list(held):
                if ticker not in rank:
                    px=prices[ticker].Open.get(day,np.nan)
                    if not pd.notna(px) or px<=0:
                        bad_marks+=1
                        continue
                    pos=held.pop(ticker)
                    proceeds=pos['shares']*float(px)*(1-s)-cost
                    cash+=proceeds
                    trades.append({'ticker':ticker,'entry_date':pos['entry'],'exit_date':day,
                                   'cost_basis':pos['paid'],'pnl':proceeds-pos['paid'],
                                   'return_net':proceeds/pos['paid']-1})
            for ticker in rank:
                if ticker in held or len(held)>=slots or cash<tickets+cost:
                    continue
                px=prices[ticker].Open.loc[day]
                shares=tickets/(float(px)*(1+s))
                cash -= tickets+cost
                held[ticker]={'shares':shares,'paid':tickets+cost,'entry':day}
        market_value=0.
        for ticker,pos in held.items():
            px=prices[ticker].Close.get(day,np.nan)
            if not pd.notna(px) or px<=0:
                bad_marks+=1
                # Fail closed for valuation; do not invent missing price.
                raise ValueError(f'UNPRICED_OPEN_POSITION {ticker} at {day.date()}')
            market_value+=pos['shares']*float(px)
        daily.append({'date':day,'cash':cash,'positions':len(held),'nav':cash+market_value})
        previous=day
    # Terminal liquidation costs at final CLOSE to avoid comparison with frictionless unsold holdings.
    day=idx[-1]
    for ticker,pos in list(held.items()):
        px=prices[ticker].Close.get(day,np.nan)
        if not pd.notna(px) or px<=0:raise ValueError(f'UNPRICED_TERMINAL_POSITION {ticker}')
        proceeds=pos['shares']*float(px)*(1-s)-cost
        cash+=proceeds
        trades.append({'ticker':ticker,'entry_date':pos['entry'],'exit_date':day,
                       'cost_basis':pos['paid'],'pnl':proceeds-pos['paid'],
                       'return_net':proceeds/pos['paid']-1})
    daily[-1]['cash']=cash;daily[-1]['nav']=cash;daily[-1]['positions']=0
    nav=pd.DataFrame(daily)
    nav['daily_return']=nav.nav.pct_change(fill_method=None).fillna(0)
    drawdown=nav.nav/nav.nav.cummax()-1
    days=(idx[-1]-idx[0]).days
    years=max(days/365.25,1/252)
    r=nav.daily_return
    sharpe=float(np.sqrt(252)*r.mean()/r.std(ddof=1)) if len(r)>10 and r.std(ddof=1)>0 else np.nan
    benchmark_px_open=float(spy.Open.loc[idx[0]])
    benchmark_px_close=float(spy.Close.loc[idx[-1]])
    bench_net=(initial-cost)*(benchmark_px_close*(1-s))/(benchmark_px_open*(1+s))-cost
    bench_ret=bench_net/initial-1
    metrics={'name':rule,'frequency':frequency,'start':str(idx[0].date()),'end':str(idx[-1].date()),
             'trades':len(trades),'initial_usd':initial,'terminal_usd':float(cash),
             'total_return':float(cash/initial-1),
             'spy_buy_hold_return':float(bench_ret),
             'excess_total_vs_spy':float((cash-bench_net)/initial),
             'cagr':float((cash/initial)**(1/years)-1),
             'max_drawdown':float(drawdown.min()),'daily_sharpe':sharpe,'bad_marks':bad_marks,
             'win_rate':float(np.mean([t['pnl']>0 for t in trades])) if trades else np.nan,
             'certified_alpha':False}
    return nav,pd.DataFrame(trades),metrics


def evaluate_rotation(nav:pd.DataFrame,spy:pd.DataFrame)->dict:
    """Equal dates, actual monthly net portfolio returns versus passive SPY.
    Not a sealed holdout: 2026 returns already reported in prior research.
    """
    z=nav.copy()
    z['month']=z.date.dt.to_period('M')
    starts=z.groupby('month').first().nav
    ends=z.groupby('month').last().nav
    pm=ends/starts-1
    # SPY closes here do not include entry/exit commissions every month; gross hurdle.
    spy_starts=spy.Close.reindex(z.date).groupby(z.month.to_numpy()).first()
    spy_ends=spy.Close.reindex(z.date).groupby(z.month.to_numpy()).last()
    bm=spy_ends/spy_starts-1
    diff=(pm-bm).dropna()
    d=diff[diff.index.to_timestamp()<CUT_1]
    v=diff[(diff.index.to_timestamp()>=CUT_1)&(diff.index.to_timestamp()<CUT_2)]
    t=diff[diff.index.to_timestamp()>=CUT_2]
    prior=pd.concat([d,v]);p=float(stats.ttest_1samp(prior,0,alternative='greater').pvalue) if len(prior)>=8 and prior.std(ddof=1)>0 else 1.
    return {'discovery_months':len(d),'validation_months':len(v),'reused_months':len(t),
            'discovery_mean_monthly_excess':float(d.mean()) if len(d) else np.nan,
            'validation_mean_monthly_excess':float(v.mean()) if len(v) else np.nan,
            'reused_mean_monthly_excess':float(t.mean()) if len(t) else np.nan,
            'p_pretest_monthly':p}
