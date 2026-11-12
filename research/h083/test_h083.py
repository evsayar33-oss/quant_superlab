from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from h083_styles import (STYLES,SEAL_DATE,_rsi2,_prior_beta,entry_signal,
                         exit_fill,evaluate,time_split,summary,cash_nav_replay,_return)


def market(n=280):
    idx=pd.bdate_range('2024-01-01',periods=n)
    close=np.linspace(100,140,n)
    op=close*.999
    return pd.DataFrame({'Open':op,'High':close*1.01,'Low':close*.99,
                         'Close':close,'Volume':np.full(n,2e6)},index=idx)


def event(p):
    return {'event_id':'e1','ticker':'TEST','event_family':'corporate_capex',
            'category':'plant','known_at':p.index[220].date().isoformat(),
            'event_date':p.index[220].date().isoformat()}


def test_styles_count_and_uniqueness():
    assert len(STYLES) >= 30
    assert len(set(STYLES))==len(STYLES)


def test_date_only_enters_next_session():
    p=market()
    r=evaluate(event(p),p,p,None,'baseline',5)
    assert r['status']=='MEASURED'
    assert r['entry_date']==p.index[221]
    assert r['exit_date']==p.index[225]


def test_confirmation_uses_first_session_close():
    p=market();ev=event(p)
    r=evaluate(ev,p,p,None,'confirmation',5)
    assert r['status']=='MEASURED'
    assert r['entry_date']==p.index[222]
    assert r['entry_date']>p.index[221]


def test_breakout_cannot_fill_same_close():
    p=market();ev=event(p)
    p.loc[p.index[221],'Close']=200
    p.loc[p.index[221],'High']=201
    j,why=entry_signal('breakout_20',ev,221,p,p)
    assert j == 222  # signal at prior day close, entry following open


def test_no_current_close_used_for_entry_time_filter():
    p=market();ev=event(p)
    k=221
    p2=p.copy();p2.loc[p2.index[k],'Close']=0.01
    j1,_=entry_signal('momentum_20',ev,k,p,p)
    j2,_=entry_signal('momentum_20',ev,k,p2,p)
    assert j1==j2==k


def test_midas_fixed_commission_dollar_not_pct():
    a=_return(100,110,1000,0)
    b=_return(100,110,5000,0)
    assert a == pytest.approx(.097)
    assert b == pytest.approx(.0994)


def test_adverse_gap_through_stop_not_filled_at_stop():
    p=market();j=221
    p.loc[p.index[j],'Open']=80
    p.loc[p.index[j],'High']=140
    p.loc[p.index[j],'Low']=75
    # ATR and stop computed from prior data, gap from prior price to 80 => stop immediately
    last,px,why=exit_fill(p,j,20,'atr_bracket')
    # entry at 80, day itself may trigger target; but no same-bar stop because initial stop below 80
    assert last is not None and px > 0
    q=market();
    # Entry at normal 221, then gap below prior fixed stop on 222
    q.loc[q.index[j+1],['Open','High','Low','Close']]=[80,86,74,81]
    last,px,why=exit_fill(q,j,20,'atr_bracket')
    assert last==j+1 and px==80 and why=='GAP_STOP'


def test_stop_target_same_bar_stop_first():
    p=market();j=221
    p.loc[p.index[j],['High','Low']]=[200,50]
    last,px,why=exit_fill(p,j,20,'atr_bracket')
    assert last==j and why=='STOP'


def test_never_infers_future_exit():
    p=market();ev=event(p)
    r=evaluate(ev,p,p,None,'delay_3',100)
    assert r['status']=='UNMATURED'


def test_purge_label_over_boundary():
    d=pd.DataFrame({'entry_date':pd.to_datetime(['2025-07-28','2025-07-29','2025-08-01','2026-06-03']),
                    'exit_date':pd.to_datetime(['2025-07-30','2025-08-12','2025-08-11','2026-06-12'])})
    assert time_split(d)['split'].to_list()==['DISCOVERY','PURGED','VALIDATION','REUSED_TEST']


def test_every_hypothesis_remains_unapproved():
    d=pd.DataFrame(columns=['style','hold','exit_rule','split','ticker','entry_date','midas_net','excess_vs_spy'])
    res=summary(d)
    assert len(res)==len(STYLES)
    assert res.certified_alpha.eq(False).all()
    assert res.status.eq('LOW_SAMPLE').all()


def test_cash_nav_mark_to_market():
    p=market()
    dates=p.index
    t=pd.DataFrame([{'name':'baseline/5/time','ticker':'TEST','event_id':'x',
        'entry_date':dates[221],'exit_date':dates[225],
        'entry_open':float(p.Open.iloc[221]),'exit_price':float(p.Close.iloc[225])}])
    nav,ledger,metrics=cash_nav_replay(t,{'TEST':p},p)
    assert len(ledger)==1
    assert metrics['executed']==1
    assert metrics['nav_end']>metrics['nav_start']
    assert (nav.positions<=1).all()
    assert nav.iloc[-1].cash==pytest.approx(nav.iloc[-1].nav)


def test_future_session_never_counted():
    p=market(300)
    p.index=pd.bdate_range('2026-01-01',periods=300)
    ev=event(p)
    r=evaluate(ev,p,p,None,'baseline',20)
    assert r['status']=='UNMATURED'

from h083_rotation import causal_features,equity_rotation,evaluate_rotation,ROTATION_RULES,_rank


def test_rotation_uses_prior_close_and_first_event_eligibility():
    p=market(550)
    p2=p.copy();p2['Close']=p2.Close*1.03;p2['Open']=p2.Open*1.03
    bars={'AAA':p,'BBB':p2,'SPY':p}
    eligible={'AAA':p.index[220],'BBB':p.index[240]}
    feat=causal_features(bars,p,eligible)
    assert bool(feat['AAA'].loc[p.index[219],'eligible']) is False
    assert bool(feat['AAA'].loc[p.index[220],'eligible']) is True
    # changing the current close must not change today's pre-open feature.
    p3=p.copy();p3.loc[p.index[260],'Close']=999
    alt=causal_features({'AAA':p3,'SPY':p},p,{'AAA':p.index[220]})
    assert alt['AAA'].loc[p.index[260],'mom63']==pytest.approx(feat['AAA'].loc[p.index[260],'mom63'])


def test_rotation_portfolio_is_cash_only():
    p=market(550);p2=p.copy();p2['Close']=p.Close*.97;p2['Open']=p.Open*.97
    bars={'AAA':p,'BBB':p2,'SPY':p}
    feat=causal_features(bars,p,{'AAA':p.index[220],'BBB':p.index[220]})
    nav,ledger,metrics=equity_rotation('weekly_3m_mom','weekly',bars,p,feat,{},from_date='2024-12-01')
    assert len(nav)>30
    assert metrics['terminal_usd']>0
    assert (nav.cash>=-1e-9).all()
    assert (nav.positions<=5).all()
    assert nav.iloc[-1].positions==0
    result=evaluate_rotation(nav,p)
    assert 'p_pretest_monthly' in result
    assert all(not m['certified_alpha'] for m in [metrics])
