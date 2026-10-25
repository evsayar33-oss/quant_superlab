"""Fundamental (accounting) factor strategies. Need panel.fund (see lab/fundamentals.py).

All inputs are point-in-time: a value appears only after its publication date.
`derive(panel)` adds the ratios below to panel.fund; strategies rank on them.
If coverage is too low, the strategy raises NoData (validation reports NO_DATA, never a fake result).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.engine import rank_top_n, rebalance
from lab.strategies import strategy


class NoData(RuntimeError):
    pass


def _safe_div(a, b):
    return a / b.where(b.abs() > 0)


def derive(p) -> dict:
    f = p.fund
    if not f or "derived" in f:
        return f
    c = p.c
    g = lambda k: f.get(k)  # noqa: E731
    out = {}
    if g("shares") is not None:
        mcap = c * g("shares")
        out["mcap"] = mcap
        out["size"] = np.log(mcap.where(mcap > 0))
        if g("net_income") is not None:
            out["ep"] = _safe_div(g("net_income"), mcap)
        if g("equity") is not None:
            out["bp"] = _safe_div(g("equity"), mcap)
        if g("revenue") is not None:
            out["sp"] = _safe_div(g("revenue"), mcap)
        if g("cfo") is not None:
            out["cfp"] = _safe_div(g("cfo"), mcap)
        if g("op_profit") is not None:
            ev = mcap + (g("fin_debt").fillna(0) if g("fin_debt") is not None else 0)
            out["ebit_ev"] = _safe_div(g("op_profit"), ev)
        if g("shares_1y") is not None:
            out["net_issuance"] = _safe_div(g("shares"), g("shares_1y")) - 1
    if g("net_income") is not None and g("equity") is not None:
        out["roe"] = _safe_div(g("net_income"), g("equity").where(g("equity") > 0))
    if g("total_assets") is not None:
        ta = g("total_assets")
        if g("net_income") is not None:
            out["roa"] = _safe_div(g("net_income"), ta)
        if g("gross_profit") is not None:
            out["gp_assets"] = _safe_div(g("gross_profit"), ta)
        if g("total_assets_1y") is not None:
            out["asset_growth"] = _safe_div(ta, g("total_assets_1y")) - 1
        if g("cfo") is not None and g("net_income") is not None:
            out["accruals"] = _safe_div(g("net_income") - g("cfo"), ta)
        if g("fin_debt") is not None:
            out["leverage"] = _safe_div(g("fin_debt"), ta)
    if g("op_profit") is not None and g("equity") is not None:
        cap = g("equity") + (g("fin_debt").fillna(0) if g("fin_debt") is not None else 0)
        out["roc"] = _safe_div(g("op_profit"), cap.where(cap > 0))
    if g("revenue") is not None and g("revenue_1y") is not None:
        out["rev_growth"] = _safe_div(g("revenue"), g("revenue_1y").abs()) - 1
    if g("net_income") is not None and g("net_income_1y") is not None:
        out["ni_growth"] = _safe_div(g("net_income") - g("net_income_1y"), g("net_income_1y").abs())
    out["fscore"] = _fscore(f, c)
    f.update({k: v.replace([np.inf, -np.inf], np.nan) for k, v in out.items() if v is not None})
    f["derived"] = True
    return f


def _fscore(f, c):
    """Piotroski (2000) F-score from available items (0..9, scaled to the items present)."""
    g = lambda k: f.get(k)  # noqa: E731
    parts = []
    ta, ta1 = g("total_assets"), g("total_assets_1y")
    ni, ni1 = g("net_income"), g("net_income_1y")
    if ni is not None and ta is not None:
        roa = ni / ta
        parts.append((roa > 0).astype(float).where(roa.notna()))
        if ni1 is not None and ta1 is not None:
            parts.append(((roa - ni1 / ta1) > 0).astype(float).where(roa.notna()))
    if g("cfo") is not None:
        parts.append((g("cfo") > 0).astype(float).where(g("cfo").notna()))
        if ni is not None:
            parts.append((g("cfo") > ni).astype(float).where(g("cfo").notna()))
    if g("fin_debt") is not None and g("fin_debt_1y") is not None and ta is not None and ta1 is not None:
        parts.append(((g("fin_debt") / ta) < (g("fin_debt_1y") / ta1)).astype(float).where(ta.notna()))
    if g("cur_assets") is not None and g("cur_liab") is not None and g("cur_assets_1y") is not None:
        cr, cr1 = g("cur_assets") / g("cur_liab"), g("cur_assets_1y") / g("cur_liab_1y")
        parts.append((cr > cr1).astype(float).where(cr.notna()))
    if g("shares") is not None and g("shares_1y") is not None:
        parts.append((g("shares") <= g("shares_1y") * 1.001).astype(float).where(g("shares").notna()))
    if g("gross_profit") is not None and g("revenue") is not None and g("gross_profit_1y") is not None:
        gm, gm1 = g("gross_profit") / g("revenue"), g("gross_profit_1y") / g("revenue_1y")
        parts.append((gm > gm1).astype(float).where(gm.notna()))
    if g("revenue") is not None and ta is not None and g("revenue_1y") is not None and ta1 is not None:
        parts.append(((g("revenue") / ta) > (g("revenue_1y") / ta1)).astype(float).where(ta.notna()))
    if not parts:
        return None
    s = sum(x.fillna(0) for x in parts)
    n = sum(x.notna().astype(float) for x in parts)
    return (9 * s / n.where(n >= 4))


def _need(p, key, min_cov=0.3):
    derive(p)
    x = p.fund.get(key)
    if x is None or x.notna().mean().mean() < min_cov * 0.5:
        raise NoData(f"fundamental field '{key}' unavailable or coverage too low")
    return x


def _rank_strategy(name, key, higher_is_better, source, extra_grid=None):
    grid = {"top_n": [3, 5, 10], "freq": ["ME", "QE"]}
    grid.update(extra_grid or {})

    @strategy(name, grid=grid, defaults={"top_n": 5, "freq": "ME"}, source=source,
              kind="fundamental", needs="panel")
    def _fn(p, top_n, freq, _key=key, _hib=higher_is_better):
        x = _need(p, _key)
        score = x if _hib else -x
        return rebalance(rank_top_n(score.where(p.c.notna()), top_n), freq)
    return _fn


_rank_strategy("value_ep", "ep", True, "Basu (1977) earnings yield")
_rank_strategy("value_bp", "bp", True, "Fama & French (1992) book-to-market")
_rank_strategy("value_sp", "sp", True, "Barbee, Mukherji & Raines (1996) sales-to-price")
_rank_strategy("value_cfp", "cfp", True, "Lakonishok, Shleifer & Vishny (1994) cash-flow yield")
_rank_strategy("value_ebit_ev", "ebit_ev", True, "Loughran & Wellman (2011) EBIT/EV")
_rank_strategy("quality_roe", "roe", True, "Haugen & Baker (1996) profitability")
_rank_strategy("quality_roa", "roa", True, "Return on assets")
_rank_strategy("quality_gp", "gp_assets", True, "Novy-Marx (2013) gross profitability")
_rank_strategy("low_accruals", "accruals", False, "Sloan (1996) accrual anomaly")
_rank_strategy("low_asset_growth", "asset_growth", False, "Cooper, Gulen & Schill (2008) asset growth")
_rank_strategy("low_leverage", "leverage", False, "Low financial leverage")
_rank_strategy("net_buyback", "net_issuance", False, "Pontiff & Woodgate (2008) share issuance")
_rank_strategy("growth_revenue", "rev_growth", True, "Revenue growth")
_rank_strategy("growth_earnings", "ni_growth", True, "Earnings growth")
_rank_strategy("small_size", "size", False, "Banz (1981) size effect")
_rank_strategy("piotroski_f", "fscore", True, "Piotroski (2000) F-score")


@strategy("magic_formula", grid={"top_n": [3, 5, 10], "freq": ["ME", "QE"]},
          defaults={"top_n": 5, "freq": "ME"}, source="Greenblatt (2005) Magic Formula: EBIT/EV + ROC",
          kind="fundamental", needs="panel")
def magic_formula(p, top_n, freq):
    ey, roc = _need(p, "ebit_ev"), _need(p, "roc")
    score = -(ey.rank(axis=1, ascending=False) + roc.rank(axis=1, ascending=False))
    return rebalance(rank_top_n(score.where(p.c.notna() & ey.notna() & roc.notna()), top_n), freq)


@strategy("qvm_composite",
          grid={"top_n": [5, 10], "w_value": [0.2, 0.33, 0.5], "w_mom": [0.2, 0.33, 0.5]},
          defaults={"top_n": 5, "w_value": 0.33, "w_mom": 0.33, "freq": "ME"},
          source="Asness, Moskowitz & Pedersen (2013) Value and Momentum Everywhere; AQR QMJ",
          kind="fundamental", needs="panel")
def qvm_composite(p, top_n, w_value, w_mom, freq):
    derive(p)
    def z(x):
        return x.sub(x.mean(axis=1), axis=0).div(x.std(axis=1), axis=0).clip(-3, 3)
    val_parts = [z(p.fund[k]) for k in ("ep", "bp", "ebit_ev") if k in p.fund]
    qual_parts = [z(p.fund[k]) for k in ("roe", "gp_assets", "roa") if k in p.fund]
    if not val_parts or not qual_parts:
        raise NoData("value/quality fields unavailable")
    val = sum(val_parts) / len(val_parts)
    qual = sum(qual_parts) / len(qual_parts)
    mom = z(p.c.shift(21) / p.c.shift(252) - 1)
    w_q = max(0.0, 1 - w_value - w_mom)
    score = w_value * val + w_q * qual + w_mom * mom
    return rebalance(rank_top_n(score.where(p.c.notna()), top_n), freq)


@strategy("value_momentum",
          grid={"top_n": [5, 10], "value_key": ["ep", "bp", "ebit_ev"]},
          defaults={"top_n": 5, "value_key": "ep", "freq": "ME"},
          source="Value filtered momentum (cheap AND rising)", kind="fundamental", needs="panel")
def value_momentum(p, top_n, value_key, freq):
    v = _need(p, value_key)
    mom = p.c.shift(21) / p.c.shift(252) - 1
    cheap = v.gt(v.median(axis=1), axis=0)
    return rebalance(rank_top_n(mom.where(cheap), top_n), freq)


@strategy("quality_lowvol",
          grid={"top_n": [5, 10]}, defaults={"top_n": 5, "freq": "ME"},
          source="Defensive equity: quality + low volatility", kind="fundamental", needs="panel")
def quality_lowvol(p, top_n, freq):
    q = _need(p, "roe")
    vol = p.c.pct_change(fill_method=None).rolling(252, min_periods=126).std()
    score = q.rank(axis=1, pct=True) - vol.rank(axis=1, pct=True)
    return rebalance(rank_top_n(score.where(p.c.notna()), top_n), freq)
