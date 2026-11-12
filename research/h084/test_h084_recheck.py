"""H084 independent verification invariants."""
import pandas as pd
import pytest
from h084_recheck import rotation_recheck, event_recheck

def sample_ledger():
    return pd.DataFrame([
        dict(ticker="A",rule="monthly_low_beta",entry_date="2025-01-01",
             exit_date="2025-01-10",pnl=100,cost_basis=2000,return_net=.05),
        dict(ticker="A",rule="monthly_low_beta",entry_date="2025-02-01",
             exit_date="2025-02-10",pnl=-30,cost_basis=2000,return_net=-.015),
        dict(ticker="A",rule="monthly_vol_squeeze",entry_date="2025-02-01",
             exit_date="2025-02-10",pnl=40,cost_basis=2000,return_net=.02),
    ])

def test_previous_closed_win_can_be_used():
    r,a=rotation_recheck(sample_ledger())
    feb=a[(a.rule=="monthly_low_beta")&(a.entry_date==pd.Timestamp("2025-02-01"))].iloc[0]
    assert bool(feb.last_same_rule_win)

def test_current_trade_outcome_is_not_a_prior_win():
    d=sample_ledger()
    d.loc[d.entry_date=="2025-01-01","exit_date"]="2025-02-10"
    _,a=rotation_recheck(d)
    feb=a[(a.rule=="monthly_low_beta")&(a.entry_date==pd.Timestamp("2025-02-01"))].iloc[0]
    assert not bool(feb.last_same_rule_win)

def test_same_day_exit_not_known_at_open():
    d=sample_ledger()
    d.loc[d.entry_date=="2025-01-01","exit_date"]="2025-02-01"
    _,a=rotation_recheck(d)
    feb=a[(a.rule=="monthly_low_beta")&(a.entry_date==pd.Timestamp("2025-02-01"))].iloc[0]
    assert not bool(feb.last_same_rule_win)

def test_cash_veto_does_not_invent_replacement():
    r,_=rotation_recheck(sample_ledger())
    row=r[(r.rule=="monthly_low_beta")&(r.selector=="last_same_rule_win")].iloc[0]
    assert row.trades==1 and row.net_profit_usd==-30

def test_reject_bad_cost_basis():
    d=sample_ledger()
    d.loc[0,"cost_basis"]=0
    with pytest.raises(ValueError):rotation_recheck(d)

def test_reject_reverse_dates():
    d=sample_ledger()
    d.loc[0,"exit_date"]="2024-12-01"
    with pytest.raises(ValueError):rotation_recheck(d)

def test_missing_event_fields_fails_closed():
    with pytest.raises(ValueError):event_recheck(pd.DataFrame({"ticker":["A"]}))
