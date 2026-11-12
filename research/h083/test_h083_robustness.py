import numpy as np
import pandas as pd
import pytest
from h083_robustness import (benchmark_nav,monthly_excess,white_reality_check,cscv_pbo,
                              deflated_sharpe_approx,friction_stress,winner_concentration)


def test_reality_check_noise_rarely_certain():
    r=np.random.default_rng(87)
    df=pd.DataFrame(r.normal(0,.03,size=(48,10)),columns=[str(i) for i in range(10)])
    x=white_reality_check(df,boot_n=400,seed=17)
    assert 0<=x['white_rc_p']<=1
    assert x['tested_strategies']==10
    y=cscv_pbo(df)
    assert y['partitions']==70
    assert 0<=y['pbo']<=1


def test_dsr_cannot_be_read_as_certification():
    rng=np.random.default_rng(41)
    x=pd.DataFrame(rng.normal(0,.01,(48,10)),columns=[str(i) for i in range(10)])
    z=deflated_sharpe_approx(x)
    assert z['number_rules']==10
    assert 0<=z['approx_dsr_probability']<=1


def test_spy_benchmark_fee_reduces_return():
    dates=pd.bdate_range('2024-01-01',periods=70)
    frame=pd.DataFrame({'Open':np.linspace(100,120,70),'Close':np.linspace(100,120,70)},index=dates)
    z=benchmark_nav(frame,dates,slippage=5)
    assert len(z)==70
    assert z.nav.iloc[-1]>z.nav.iloc[0]
    assert z.nav.iloc[-1]<12000


def test_friction_stress_more_slippage_reduces_pnl():
    l=pd.DataFrame([{'rule':'x','ticker':'A','pnl':150,'cost_basis':2001.5},
                    {'rule':'x','ticker':'B','pnl':-45,'cost_basis':2001.5}])
    s=friction_stress(l)
    assert s.terminal_pnl_usd_fixed_ledger.is_monotonic_decreasing
    w=winner_concentration(l)
    assert w.top_1_ticker.iloc[0]=='A'
    assert w.top_2_fraction_of_net_pnl.iloc[0]==pytest.approx(1)


def test_monthly_excess_uses_actual_monthend_dates():
    dates=pd.bdate_range('2024-01-01',periods=75)
    frames=[]
    for rule in ['a','b']:
        frames.append(pd.DataFrame({'date':dates,'rule':rule,
                                    'nav':10000*np.exp(np.arange(len(dates))*(.0002 if rule=='a' else .0005))}))
    nav=pd.concat(frames,ignore_index=True)
    bench=pd.DataFrame({'date':dates,'nav':10000*np.exp(np.arange(len(dates))*.0003)})
    x=monthly_excess(nav,bench)
    assert isinstance(x.index,pd.DatetimeIndex)
    assert x.shape[1]==2
    assert x.index.max().day>=28
