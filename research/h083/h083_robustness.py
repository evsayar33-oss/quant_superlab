"""H083 risk/overfit supplementary diagnostics; not future performance certification.

White stationary block Reality Check is computed on synchronized monthly
excess return vectors, CSCV PBO on monthly Sharpe, and an approximate DSR.
"""
from __future__ import annotations
from itertools import combinations
from math import sqrt
import numpy as np
import pandas as pd
from scipy.stats import norm,skew,kurtosis
from h083_styles import COMMISSION_USD,SLIP_BPS


def benchmark_nav(spy: pd.DataFrame,dates:pd.Series|pd.DatetimeIndex,
                  initial:float=10000.,fee:float=COMMISSION_USD,slippage:float=SLIP_BPS)->pd.DataFrame:
    ix=pd.DatetimeIndex(dates).unique().sort_values()
    if not len(ix):return pd.DataFrame(columns=['date','nav'])
    b=spy.reindex(ix)
    if b[['Open','Close']].isna().any().any():
        raise ValueError('Benchmark missing prices')
    s=slippage/10000.
    qty=(initial-fee)/(float(b.Open.iloc[0])*(1+s))
    vals=qty*b.Close.to_numpy(float)
    vals[-1]=vals[-1]*(1-s)-fee
    return pd.DataFrame({'date':ix,'nav':vals})


def monthly_excess(rota_nav:pd.DataFrame,spy_daily:pd.DataFrame)->pd.DataFrame:
    """Monthly returns from previous month-end NAV to current month-end NAV.
    Last-day liquidation and fees are already included in the NAV series.
    """
    source=rota_nav.pivot(index='date',columns='rule',values='nav').sort_index()
    source.index=pd.to_datetime(source.index)
    bench=spy_daily.set_index('date').nav.reindex(source.index)
    month=source.resample('ME').last().pct_change(fill_method=None)
    bmonth=bench.resample('ME').last().pct_change(fill_method=None)
    aligned=month.sub(bmonth,axis=0).dropna(how='any')
    return aligned


def white_reality_check(excess:pd.DataFrame,boot_n=2000,block_mean=3,seed=42)->dict:
    """Maximum mean excess over benchmark, stationary circular block bootstrap.
    One pre-registered 10-rule family. Center each candidate under null.
    """
    a=excess.to_numpy(float)
    n,m=a.shape
    if n<20 or m<2:
        return {'white_rc_p':np.nan,'best_in_sample':'','tested_strategies':m,'months':n}
    means=a.mean(axis=0)
    observed=float(means.max())
    centered=a-means
    rng=np.random.default_rng(seed)
    sims=[]
    for _ in range(boot_n):
        ix=np.empty(n,dtype=int)
        ix[0]=rng.integers(0,n)
        for j in range(1,n):
            ix[j]=(rng.integers(0,n) if rng.random()<1/block_mean else (ix[j-1]+1)%n)
        sims.append(float(centered[ix,:].mean(axis=0).max()))
    p=(1+sum(x>=observed for x in sims))/(1+boot_n)
    return {'white_rc_p':float(p),'best_in_sample':str(excess.columns[int(np.argmax(means))]),
            'max_mean_monthly_excess':observed,'tested_strategies':m,'months':n,'block_mean_months':block_mean}


def cscv_pbo(excess:pd.DataFrame,blocks=8)->dict:
    """Combinatorial symmetric cross validation diagnostics, NOT chronological OOS.
    8 consecutive blocks, 4-in/4-out across 70 combinations.
    In-sample Sharpe ranks are evaluated out of sample.
    """
    x=excess.to_numpy(float);n,m=x.shape
    if n<blocks*3 or m<3:
        return {'pbo':np.nan,'partitions':0}
    partitions=np.array_split(np.arange(n),blocks)
    vals=[];winner_counts=np.zeros(m,dtype=int)
    for chosen in combinations(range(blocks),blocks//2):
        tr=np.concatenate([partitions[k] for k in chosen])
        te=np.concatenate([partitions[k] for k in range(blocks) if k not in chosen])
        trr=x[tr];ter=x[te]
        in_s=trr.mean(axis=0)/np.maximum(trr.std(axis=0,ddof=1),1e-9)
        out_s=ter.mean(axis=0)/np.maximum(ter.std(axis=0,ddof=1),1e-9)
        w=int(np.argmax(in_s));winner_counts[w]+=1
        rank=(np.sum(out_s<out_s[w])+0.5*np.sum(out_s==out_s[w]))/m
        vals.append(rank<.5)
    return {'pbo':float(np.mean(vals)),'partitions':len(vals),
            'most_selected_in_sample':str(excess.columns[int(np.argmax(winner_counts))]),
            'most_selected_count':int(winner_counts.max())}


def deflated_sharpe_approx(excess:pd.DataFrame)->dict:
    """Approximate DSR against 10-strategy selection, based on monthly net SPY-excess.

    Effective independent N is unknown. This is a sensitivity diagnostic;
    overlapping correlated models violate an exact independent-trial formula.
    """
    a=excess.to_numpy(float)
    n,m=a.shape
    srs=a.mean(axis=0)/np.maximum(a.std(axis=0,ddof=1),1e-9)
    best=int(np.argmax(srs));sr=float(srs[best])
    gamma=0.5772156649015329
    # Conservative dispersion of measured cross-strategy Sharpe ratios.
    dispersion=max(float(np.std(srs,ddof=1)),1/sqrt(n))
    expectation=dispersion*((1-gamma)*norm.ppf(1-1/m)+gamma*norm.ppf(1-1/(m*np.e)))
    selected=a[:,best]
    sk=float(skew(selected,bias=False));ku=float(kurtosis(selected,fisher=False,bias=False))
    v=max(1-sk*sr+(ku-1)*sr*sr/4,1e-8)
    probability=float(norm.cdf((sr-expectation)*sqrt(n-1)/sqrt(v)))
    return {'approx_dsr_probability':probability,'best_sharpe_rule':str(excess.columns[best]),
            'best_monthly_excess_sr':sr,'expected_max_sr':float(expectation),
            'number_rules':m,'months':n,
            'interpretation':'Exploratory approximation, correlated models and reused test; never certification.'}


def friction_stress(ledger:pd.DataFrame,base_bps=SLIP_BPS,levels=(0.,5.,15.,30.))->pd.DataFrame:
    """Fixed realized trade list and quantities recalculated for execution bps.
    NOT an exact portfolio rerun: at extreme costs selection/cash may change.
    """
    data=[]
    for rule,g in ledger.groupby('rule'):
        paid=g.cost_basis.to_numpy(float)
        pnl=g.pnl.to_numpy(float)
        ticket=paid-COMMISSION_USD
        raw_exit_factor=(paid+pnl+COMMISSION_USD)/ticket * (1+base_bps/10000)/(1-base_bps/10000)
        for slip in levels:
            adjusted_pnl=ticket*(raw_exit_factor*(1-slip/10000)/(1+slip/10000)-1)-2*COMMISSION_USD
            data.append({'name':rule,'slippage_bps_per_side':slip,'completed_trades':len(g),
                         'terminal_pnl_usd_fixed_ledger':float(adjusted_pnl.sum()),
                         'source_pnl_usd':float(pnl.sum())})
    return pd.DataFrame(data)


def winner_concentration(ledger:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for name,group in ledger.groupby('rule'):
        sums=group.groupby('ticker').pnl.sum().sort_values(ascending=False)
        total=float(sums.sum())
        rows.append({'name':name,'total_pnl':total,'tickers':len(sums),
                     'top_1_ticker':str(sums.index[0]) if len(sums) else '',
                     'top_1_pnl':float(sums.iloc[0]) if len(sums) else np.nan,
                     'top_2_pnl':float(sums.head(2).sum()),
                     'top_2_fraction_of_net_pnl':float(sums.head(2).sum()/total) if total>0 else np.nan,
                     'loss_if_top_1_removed_ledger_only':total-float(sums.iloc[0]) if len(sums) else np.nan})
    return pd.DataFrame(rows)
