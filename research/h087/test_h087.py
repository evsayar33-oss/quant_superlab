"""H087 synthetic deterministic regression: no future exposure, 2x friction, proper multiplicity."""
import numpy as np
import pandas as pd
import pytest
from crossover import overlay, stationary_max_stat, summarize_model, calc_total
from audit import stationary_ci


def test_overlay_lags_prior_month_and_pays_cost():
    # Weight was already derived from LAST month's close by load_inputs.
    base=np.array([.02,-.05,.10])
    prior=np.array([1.,0.,.5])
    rf=np.array([.001,.001,.001])
    r,t=overlay(base,prior,rf,10)
    assert r[0]==pytest.approx(.02)
    assert r[1]==pytest.approx(.001-.001)
    assert r[2]==pytest.approx(.5*.10+.5*.001-.0005)
    assert t.tolist()==pytest.approx([0.,1.,.5])
    newer=base.copy()
    newer[2]=-.99
    r2,t2=overlay(newer,prior,rf,10)
    assert r2[:2].tolist()==pytest.approx(r[:2])
    assert t2.tolist()==pytest.approx(t.tolist())


def test_extra_cost_does_not_raise_returns():
    rng=np.random.default_rng(2)
    b=rng.normal(.01,.07,48)
    w=np.r_[np.ones(20),np.zeros(9),np.full(19,.5)]
    rf=np.full(48,.002)
    cheap,turn=overlay(b,w,rf,10)
    expensive,_=overlay(b,w,rf,20)
    assert np.all(expensive <= cheap+1e-12)
    assert calc_total(expensive)<=calc_total(cheap)
    assert np.sum(turn)==pytest.approx(1.5)


def test_incomplete_and_leveraged_exposure_fails():
    with pytest.raises(ValueError):
        overlay([.01,.02],[0.5,np.nan],[.001,.002],10)
    with pytest.raises(ValueError):
        overlay([.01],[1.5],[.001],10)


def test_multiple_testing_max_stat_not_naive_winner():
    rng=np.random.default_rng(87031)
    noise=rng.normal(0,.02,(48,70))
    a=stationary_max_stat(noise,reps=300,seed=87031)
    assert a["n_models"]==70 and a["n_months"]==48
    assert 0<=a["familywise_p"]<=1
    assert a==stationary_max_stat(noise,reps=300,seed=87031)
    assert stationary_max_stat(noise[:12],reps=100)["familywise_p"] is None


def test_bootstrap_flags_insufficient_and_is_reproducible():
    assert stationary_ci(np.zeros(20))["p_positive_mean"] is None
    rng=np.random.default_rng(10)
    arr=rng.normal(0,.002,180)
    r=stationary_ci(arr,reps=300,seed=87091)
    assert r==stationary_ci(arr,reps=300,seed=87091)
    assert 0<=r["p_positive_mean"]<=1


def test_best_two_deletion_is_conservative():
    r=np.array([.10,.10,-.04,-.04])
    benchmark=np.zeros(4)
    z=summarize_model(r,benchmark,0,4)
    assert z["active_total_ex_best_two_months"]<0
    assert z["months"]==4
