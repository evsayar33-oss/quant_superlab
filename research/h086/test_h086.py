"""H086 offline causality, math, source-format and release-gate unit tests."""
from __future__ import annotations

import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from h086_run import (
    parse_ff_daily, parse_cboe_vix, signal_weights, daily_book, summarize,
    evaluate_period, bootstrap_p, holm_adjust, join_sources,
)


def example_panel(n=550):
    rng = np.random.default_rng(86014)
    dates = pd.bdate_range("1999-01-01", periods=n)
    return pd.DataFrame({
        "rf": np.repeat(.0001, n),
        "mkt_excess": rng.normal(.0002, .012, n),
        "vix": np.clip(20 + rng.normal(0, 6, n), 8, 50),
    }, index=dates)


def test_all_five_models_only_use_prior_closes():
    p = example_panel()
    w = signal_weights(p)
    assert set(w) == {"H086A", "H086B", "H086C", "H086D", "H086E"}
    # Alter the day's CLOSE, its return and VIX, but not any earlier observation.
    for i in (270, 400):
        corrupted = p.copy()
        corrupted.iloc[i, corrupted.columns.get_loc("vix")] = 95.
        corrupted.iloc[i, corrupted.columns.get_loc("mkt_excess")] = -.25
        w2 = signal_weights(corrupted)
        for k in w:
            assert w[k].iloc[i] == pytest.approx(w2[k].iloc[i]), (i, k)
    for key, weights in w.items():
        assert weights.notna().all() and weights.between(0., 1.).all(), key


def test_fixed_cost_stress_never_increases_period_wealth():
    p = example_panel()
    w = signal_weights(p)["H086C"]
    a = daily_book(p, w, 10)
    b = daily_book(p, w, 20)
    assert (b.ret <= a.ret + 1e-12).all()
    assert np.prod(1+b.ret) <= np.prod(1+a.ret)
    assert summarize(a)["sessions"] == len(p)
    assert (a.cost >= 0).all()


def test_market_proxy_plus_cash_consistent():
    p = example_panel(300)
    s = pd.Series(1.0, index=p.index)
    r = daily_book(p, s, 10)
    assert r.ret.iloc[0] == pytest.approx(p.mkt_excess.iloc[0] + p.rf.iloc[0] - .001)
    assert r.ret.iloc[1] == pytest.approx(p.mkt_excess.iloc[1] + p.rf.iloc[1])
    cash = daily_book(p, pd.Series(0., index=p.index), 20)
    assert np.allclose(cash.ret, p.rf)


def test_source_aligner_fails_instead_of_imputing_missing_days():
    p=example_panel(300)
    cfg={"data":{"start":"1999-01-01","end":"2001-01-01",
                 "maximum_vix_missing_fraction":.01,
                 "forward_fill_trading_days":1,"min_overlap":100}}
    v=p.vix.copy()
    v.iloc[10:30]=np.nan
    with pytest.raises(ValueError, match="missing fraction"):
        join_sources(p[["rf","mkt_excess"]], v, cfg)


def test_french_daily_csv_percentage_and_archive_structure():
    dates=pd.bdate_range("1980-01-01", periods=6015)
    lines=["F-F French daily file",",Mkt-RF,SMB,HML,RF"]
    for d in dates:
        lines.append(f"{d:%Y%m%d},1.00,0.0,0.0,0.01")
    lines.extend(["", "Annual factors", "2024,42.1,1.0,2.0,0.2"])
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,"w") as z:
        z.writestr("F-F_Research_Data_Factors_daily.CSV", "\n".join(lines))
    df=parse_ff_daily(mem.getvalue())
    assert len(df)==6015
    assert df.iloc[0].mkt_excess==pytest.approx(.01)
    assert df.iloc[0].rf==pytest.approx(.0001)


def test_vix_csv_duplicate_fails_closed():
    csv=b"DATE,OPEN,HIGH,LOW,CLOSE\n01/02/1990,20,21,19,20\n01/02/1990,20,21,19,21\n"
    with pytest.raises(ValueError):
        parse_cboe_vix(csv)


def test_multiple_testing_adjustment_controls_family():
    ps=holm_adjust({"A":.001,"B":.02,"C":.04,"D":.50,"E":.90})
    assert ps["A"]==pytest.approx(.005)
    assert ps["B"]==pytest.approx(.08)
    assert ps["C"]>=ps["B"]
    assert ps["D"]==1.
    assert ps["E"]==1.
    assert holm_adjust({"A":None,"B":.001})["B"] == pytest.approx(.002)


def test_block_bootstrap_deterministic_and_non_significant_on_flat_excess():
    months=pd.date_range("2019-01-31",periods=96,freq="ME")
    x=pd.Series(np.zeros(96),index=months)
    p=bootstrap_p(x,n=500,seed=42)
    assert p["p"]>=.95
    assert p["months"]==96
    assert bootstrap_p(x,n=500,seed=42)["p"]==p["p"]
