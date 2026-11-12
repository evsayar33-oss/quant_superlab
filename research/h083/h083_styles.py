"""H083: explicit daily-bar stock trading styles; source-observable signal and cash costs.

All identifiers and source timestamps are frozen in H081_eligible_snapshot.csv.
Only retrospective research. No trade execution, no automatic deployment.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from scipy import stats

COMMISSION_USD = 1.50
DEFAULT_NOTIONAL = 2000.0
SLIP_BPS = 5.0
SEAL_DATE = pd.Timestamp('2026-11-11')  # full completed session on day research initiated
CUT_1 = pd.Timestamp('2025-07-31')
CUT_2 = pd.Timestamp('2026-06-02')

# All specifications declared before evaluation. Reject future rules not in this registry.
STYLES = tuple((style, hold, exit_rule) for style, holds, exit_rule in [
    ('baseline', (5, 20, 60), 'time'),
    ('delay_3', (5, 20), 'time'),
    ('confirmation', (5, 20), 'time'),
    ('breakout_20', (5, 20), 'time'),
    ('pullback_rsi2', (5, 20), 'time'),
    ('dip_3d', (5, 20), 'time'),
    ('momentum_20', (5, 20), 'time'),
    ('trend_50', (5, 20), 'time'),
    ('low_beta', (5, 20), 'time'),
    ('liquid_5m', (5, 20), 'time'),
    ('risk_on', (5, 20), 'time'),
    ('sector_rs', (5, 20), 'time'),
    ('plant', (5, 20), 'time'),
    ('plant_trend', (5, 20), 'time'),
    ('baseline', (20,), 'atr_bracket'),
    ('baseline', (20,), 'atr_trail'),
    ('breakout_20', (20,), 'atr_bracket'),
    ('pullback_rsi2', (20,), 'atr_bracket'),
    ('risk_on', (20,), 'atr_trail'),
] for hold in holds)


def _normalize_bars(df: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    if not {'Open', 'High', 'Low', 'Close', 'Volume'}.issubset(df.columns):
        raise ValueError('OHLCV columns are required')
    p = df.copy()
    p.index = pd.DatetimeIndex(p.index).tz_localize(None).normalize()
    p = p[~p.index.duplicated(keep='last')].sort_index()
    return p.reindex(calendar).astype(float)


def _index(known_at, event_date, index: pd.DatetimeIndex) -> int | None:
    # Match H078: source UTC before 09:30 NY may enter same session; otherwise next open.
    raw = str(known_at or '').strip()
    ts = pd.to_datetime(raw, utc=True, errors='coerce')
    if pd.notna(ts) and ('T' in raw or ' ' in raw):
        local = ts.tz_convert('America/New_York')
        today = pd.Timestamp(local.date())
        before_open = (local.hour, local.minute, local.second) < (9, 30, 0)
        target = today if before_open else today + pd.Timedelta(days=1)
    else:
        today = pd.to_datetime(event_date, errors='coerce')
        if pd.isna(today):
            return None
        target = today.normalize() + pd.Timedelta(days=1)
    pos = int(index.searchsorted(target, side='left'))
    return pos if pos < len(index) else None


def _prior_beta(prices: pd.Series, spy: pd.Series) -> pd.Series:
    a = prices.pct_change(fill_method=None)
    b = spy.pct_change(fill_method=None)
    # 126 completed sessions min 80; current close is never used at an entry open.
    cov = a.rolling(126, min_periods=80).cov(b)
    var = b.rolling(126, min_periods=80).var()
    return cov / var.replace(0, np.nan)


def _rsi2(close: pd.Series) -> pd.Series:
    d = close.diff()
    gain = d.clip(lower=0).rolling(2, min_periods=2).mean()
    loss = -d.clip(upper=0).rolling(2, min_periods=2).mean()
    return 100 * gain / (gain + loss).replace(0, np.nan)


def _atr14(b: pd.DataFrame) -> pd.Series:
    prev = b.Close.shift(1)
    tr = pd.concat([(b.High-b.Low).abs(),(b.High-prev).abs(),(b.Low-prev).abs()],axis=1).max(axis=1)
    return tr.rolling(14,min_periods=14).mean()


def _has(*values):
    return all(pd.notna(v) and np.isfinite(float(v)) for v in values)


def entry_signal(style: str, event: dict, k: int, p: pd.DataFrame, spy: pd.DataFrame,
                 sector: pd.DataFrame | None = None) -> tuple[int | None, str]:
    """Return order open index; features at close t only permit execution >=t+1."""
    if k < 2 or k >= len(p):
        return None, 'OUTSIDE_PRICE_WINDOW'
    c=p.Close; b=spy.Close; prev=k-1
    if not _has(c.iloc[prev],p.Open.iloc[k]):
        return None,'PRICE_MISSING'
    if style in ('baseline','plant'):
        if style=='plant' and event.get('category')!='plant':
            return None,'STYLE_FILTER'
        return k,'NEXT_OPEN'
    if style=='delay_3':
        return (k+3,'DELAY_3') if k+3 < len(p) else (None,'UNMATURED')
    if style == 'confirmation':
        return (k+1, 'FIRST_SESSION_CONFIRM') if (k+1 < len(p) and _has(c.iloc[k],p.Open.iloc[k])
            and c.iloc[k]>p.Open.iloc[k] and c.iloc[k]>c.iloc[prev]) else (None,'NO_CONFIRMATION')
    if style in ('trend_50','plant_trend'):
        if style=='plant_trend' and event.get('category')!='plant':
            return None,'STYLE_FILTER'
        s=c.rolling(50,min_periods=50).mean()
        return (k,'TREND') if prev>=59 and _has(s.iloc[prev],s.iloc[prev-10]) and c.iloc[prev]>s.iloc[prev]>s.iloc[prev-10] else (None,'NO_TREND')
    if style=='momentum_20':
        return (k,'MOMENTUM') if prev>=20 and _has(c.iloc[prev],c.iloc[prev-20]) and c.iloc[prev]>c.iloc[prev-20] else (None,'NO_MOMENTUM')
    if style=='low_beta':
        beta=_prior_beta(c,b).iloc[prev]
        return (k,'LOW_BETA') if _has(beta) and 0 <= beta <= 1 else (None,'NOT_LOW_BETA')
    if style=='liquid_5m':
        # Approximation because Yahoo split-adjustment/volume adjustment may differ; audited separately.
        v=(c*p.Volume).rolling(20,min_periods=20).mean().iloc[prev]
        return (k,'LIQUIDITY') if _has(v) and v >= 5e6 else (None,'LOW_OR_MISSING_LIQUIDITY')
    if style=='risk_on':
        sma=b.rolling(200,min_periods=200).mean().iloc[prev]
        return (k,'RISK_ON') if _has(sma,b.iloc[prev]) and b.iloc[prev]>sma else (None,'RISK_OFF_OR_UNKNOWN')
    if style=='sector_rs':
        if sector is None:
            return None,'SECTOR_DATA_MISSING'
        sec=sector.Close
        if prev<20 or not _has(sec.iloc[prev],sec.iloc[prev-20],b.iloc[prev],b.iloc[prev-20]):
            return None,'SECTOR_WINDOW_MISSING'
        rel=sec.iloc[prev]/sec.iloc[prev-20] - b.iloc[prev]/b.iloc[prev-20]
        return (k,'SECTOR_RELATIVE_STRENGTH') if rel>0 else (None,'WEAK_SECTOR')
    if style in ('breakout_20','pullback_rsi2','dip_3d'):
        rsi = _rsi2(c) if style=='pullback_rsi2' else None
        for day in range(k,min(k+10,len(p)-1)):
            if not _has(c.iloc[day]):
                continue
            if style=='breakout_20':
                hi=p.High.iloc[max(0,day-20):day].max()
                signal=(day>=20 and _has(hi) and c.iloc[day]>hi)
            elif style=='pullback_rsi2':
                signal=_has(rsi.iloc[day]) and rsi.iloc[day]<10
            else:
                signal=(day>=3 and _has(c.iloc[day-3]) and c.iloc[day]/c.iloc[day-3]-1<-.04)
            if signal and _has(p.Open.iloc[day+1]):
                return day+1,style.upper()
        return None,'NO_TRIGGER'
    raise KeyError(f'Unsupported style: {style}')


def exit_fill(p: pd.DataFrame, k: int, hold: int, exit_rule: str) -> tuple[int | None,float,str]:
    """Exit daily-bar long; gaps through stops get unfavorable opening price;
    if stop and target occur on same bar, stop goes first (conservative).
    """
    last=k+hold-1
    if k<1 or last>=len(p):
        return None,np.nan,'UNMATURED'
    if exit_rule=='time':
        if p.iloc[k:last+1][['Open','Close']].isna().any().any():
            return None,np.nan,'PRICE_GAP'
        return (last,float(p.Close.iloc[last]),'TIME')
    atr=_atr14(p).iloc[k-1]
    op=p.Open.iloc[k]
    if not _has(atr,op) or atr <=0:
        return None,np.nan,'ATR_UNAVAILABLE'
    stop=float(op-2*atr)
    tp=float(op+3*atr)
    if stop<=0:
        return None,np.nan,'STOP_INVALID'
    for j in range(k,last+1):
        row=p.iloc[j]
        if not _has(row.Open,row.High,row.Low,row.Close):
            return None,np.nan,'PRICE_GAP'
        if row.Open<=stop:
            return j,float(row.Open),'GAP_STOP'
        if row.Low<=stop:
            return j,stop,'STOP'  # stop has priority over target on the same bar
        if exit_rule=='atr_bracket':
            if row.Open>=tp:
                return j,tp,'GAP_TARGET_CAPPED'
            if row.High>=tp:
                return j,tp,'TARGET'
        elif exit_rule=='atr_trail':
            # Close-based adjustment applies only to NEXT session.
            stop=max(stop,float(row.Close-2*atr))
        else:
            raise KeyError(exit_rule)
    return last,float(p.Close.iloc[last]),'TIME'


def _return(entry_px:float,exit_px:float,notional:float,slippage_bps:float,fee:float=COMMISSION_USD)->float:
    s=slippage_bps/10000
    return (exit_px*(1-s))/(entry_px*(1+s))-1-2*fee/notional


def evaluate(event:dict, price:pd.DataFrame, spy:pd.DataFrame, sector:pd.DataFrame|None,
             style:str, hold:int, exit_rule:str='time',
             notional:float=DEFAULT_NOTIONAL,slippage_bps:float=SLIP_BPS)->dict:
    if notional<=0 or slippage_bps<0 or slippage_bps>=10000:
        raise ValueError('Invalid cost inputs')
    idx=price.index
    k=_index(event.get('known_at'),event.get('event_date'),idx)
    if k is None:
        return {'status':'NO_ENTRY_DATE'}
    j,why=entry_signal(style,event,k,price,spy,sector)
    if j is None:
        return {'status':why}
    if j>=len(idx) or not _has(price.Open.iloc[j],spy.Open.iloc[j]) or price.Open.iloc[j]<=0:
        return {'status':'ENTRY_PRICE_GAP'}
    exit_idx,exit_price,reason=exit_fill(price,j,hold,exit_rule)
    if exit_idx is None:
        return {'status':reason}
    if idx[exit_idx]>SEAL_DATE:
        return {'status':'UNMATURED'}
    if not _has(spy.Close.iloc[exit_idx]) or spy.Open.iloc[j]<=0:
        return {'status':'SPY_PRICE_MISSING'}
    r=_return(price.Open.iloc[j],exit_price,notional,slippage_bps)
    market_r=_return(spy.Open.iloc[j],spy.Close.iloc[exit_idx],notional,slippage_bps)
    return {'status':'MEASURED','reason':reason,
        'entry_date':idx[j], 'exit_date':idx[exit_idx],
        'entry_open':float(price.Open.iloc[j]),'exit_price':float(exit_price),
        'midas_net':float(r),'spy_midas_net':float(market_r),
        'excess_vs_spy':float(r-market_r),'holding_sessions':exit_idx-j+1}


def time_split(df:pd.DataFrame) ->pd.DataFrame:
    """Common calendar boundaries across styles, purged by actual exit session."""
    d=df.copy()
    d['split']='REUSED_TEST'
    d.loc[d.entry_date<CUT_1,'split']='PURGED'
    d.loc[(d.entry_date<CUT_1)&(d.exit_date<CUT_1),'split']='DISCOVERY'
    d.loc[(d.entry_date>=CUT_1)&(d.entry_date<CUT_2),'split']='PURGED'
    d.loc[(d.entry_date>=CUT_1)&(d.entry_date<CUT_2)&(d.exit_date<CUT_2),'split']='VALIDATION'
    return d


def bh_q(ps):
    p=np.asarray(ps,float);order=np.argsort(p);q=np.empty(len(p));v=1.
    for rank in range(len(p),0,-1):
        ix=order[rank-1];v=min(v,p[ix]*len(p)/rank);q[ix]=v
    return q


def summary(df:pd.DataFrame, specs=STYLES)->pd.DataFrame:
    """Calendar-month clustered comparison vs SPY, correct across ALL tested specifications."""
    records=[]
    for style,hold,ex in specs:
        x=df[(df['style']==style)&(df['hold']==hold)&(df['exit_rule']==ex)]
        z={'style':style,'hold':hold,'exit_rule':ex,'name':f'{style}/{hold}/{ex}'}
        for label,code in [('DISCOVERY','d'),('VALIDATION','v'),('REUSED_TEST','t')]:
            r=x[x.split==label]
            z[f'{code}_n']=int(len(r));z[f'{code}_tickers']=int(r.ticker.nunique())
            z[f'{code}_net_mean']=float(r.midas_net.mean()) if len(r) else np.nan
            z[f'{code}_excess_mean']=float(r.excess_vs_spy.mean()) if len(r) else np.nan
            z[f'{code}_win_rate']=float((r.midas_net>0).mean()) if len(r) else np.nan
            z[f'{code}_months']=int(r.entry_date.dt.to_period('M').nunique()) if len(r) else 0
        prior=x[x.split.isin(['DISCOVERY','VALIDATION'])].copy()
        monthly=prior.groupby(pd.to_datetime(prior.entry_date).dt.to_period('M'))['excess_vs_spy'].mean()
        z['pre_n']=int(len(prior));z['pre_months']=int(len(monthly))
        z['p_monthly']=float(stats.ttest_1samp(monthly.values,0,alternative='greater').pvalue) if len(monthly)>=6 and monthly.std(ddof=1)>0 else 1.
        z['cost_roundtrip_usd']=2*COMMISSION_USD
        records.append(z)
    result=pd.DataFrame(records)
    result['q_monthly_bh']=bh_q(result.p_monthly.values)
    enough=(result.d_n>=20)&(result.v_n>=10)&(result.t_n>=10)&(result.pre_months>=8)
    positive=(result.d_excess_mean>0)&(result.v_excess_mean>0)&(result.d_net_mean>0)&(result.v_net_mean>0)
    result['status']=np.select([~enough,~positive,result.q_monthly_bh>0.10],
        ['LOW_SAMPLE','UNSTABLE_PRETEST','NO_SIGNIFICANCE'],default='PAPER_WATCH')
    result['certified_alpha']=False  # ALL historical outcomes reused from earlier reports
    return result.sort_values(['status','q_monthly_bh','pre_n'],ascending=[True,True,False]).reset_index(drop=True)


def month_bootstrap_ci(g:pd.DataFrame, seed=67, n=2000)->tuple[float,float]:
    x=g.groupby(g.entry_date.dt.to_period('M'))['excess_vs_spy'].mean().values
    if len(x)<6:
        return np.nan,np.nan
    rng=np.random.default_rng(seed)
    sampled=rng.choice(x,size=(n,len(x)),replace=True).mean(axis=1)
    return tuple(np.quantile(sampled,[.025,.975]))


def cash_nav_replay(trades:pd.DataFrame, prices:dict[str,pd.DataFrame], spy:pd.DataFrame,
                    cash_initial=10000.,ticket=2000.,slots=5,fee=COMMISSION_USD,
                    slippage_bps=SLIP_BPS)->tuple[pd.DataFrame,pd.DataFrame,dict]:
    """Daily marked cash + equity portfolio, no leverage, one ticker at a time.

    Trades already possess causal entries/exits. Trades that share day are
    selected by stable event_id/ticker ordering, not future profitability.
    """
    t=trades.sort_values(['entry_date','event_id','ticker']).drop_duplicates(['event_id','ticker'])
    cal=spy.index[spy.index<=SEAL_DATE]
    if t.empty:
        return pd.DataFrame(),pd.DataFrame(),{'trades':0}
    start=t.entry_date.min();end=t.exit_date.max()
    cal=cal[(cal>=start)&(cal<=end)]
    cash=float(cash_initial);active={};daily=[];ledger=[];rejected=0
    for day in cal:
        # Process existing exits before new entries, at close, not earlier intraday cash.
        opened=t[t.entry_date==day]
        for row in opened.to_dict('records'):
            ticker=row['ticker']
            if len(active)>=slots or ticker in active or cash<ticket+fee:
                rejected+=1;continue
            # buy at open; pay extra fee in cash.
            raw=float(row['entry_open']);s=slippage_bps/10000.
            qty=ticket/(raw*(1+s))
            cash -= ticket+fee
            active[ticker]={'qty':qty,'entry':day,'exit':row['exit_date'],'exit_px':row['exit_price'],
                            'cost':ticket+fee,'event_id':row['event_id'],'rule':row['name']}
        to_close=[]
        for ticker,pos in active.items():
            if pos['exit']==day:
                proceeds=pos['qty']*pos['exit_px']*(1-slippage_bps/10000.)-fee
                cash+=proceeds
                ledger.append({'event_id':pos['event_id'],'ticker':ticker,'entry_date':pos['entry'],
                               'exit_date':day,'profit_usd':proceeds-pos['cost'],'return_net':(proceeds-pos['cost'])/pos['cost']})
                to_close.append(ticker)
        for ticker in to_close: del active[ticker]
        mtm=0.
        for ticker,pos in active.items():
            mark=prices[ticker].Close.get(day,np.nan)
            if not pd.notna(mark):
                raise ValueError(f'No mark for open {ticker} on {day}')
            mtm+=pos['qty']*float(mark)
        daily.append({'date':day,'nav':cash+mtm,'cash':cash,'positions':len(active)})
    nav=pd.DataFrame(daily)
    nav['daily_return']=nav.nav.pct_change(fill_method=None).fillna(0)
    dd=nav.nav/nav.nav.cummax()-1
    days=(nav.date.iloc[-1]-nav.date.iloc[0]).days
    years=max(days/365.25,1/252)
    r=nav.daily_return
    sharpe=float(np.sqrt(252)*r.mean()/r.std(ddof=1)) if len(r)>2 and r.std(ddof=1)>0 else np.nan
    stats_={'signals':len(t),'executed':len(ledger),'rejected_cash_or_capacity':rejected,
            'nav_start':cash_initial,'nav_end':float(nav.nav.iloc[-1]),
            'total_return':float(nav.nav.iloc[-1]/cash_initial-1),
            'cagr':float((nav.nav.iloc[-1]/cash_initial)**(1/years)-1),
            'max_drawdown':float(dd.min()),'daily_sharpe':sharpe,'calendar_days':days,
            'warning':'Retrospective, reused historical sample, not independently validated.'}
    return nav,pd.DataFrame(ledger),stats_
