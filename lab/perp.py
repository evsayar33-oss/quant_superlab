"""Report card (multi-year windows) and an isolated-margin perpetual-futures simulation.

Report card: the same strategy measured over the LAST 3 years, the last 5 years and the full history
(config `report_windows_years`; 0 = full). A window that the data does not cover is reported as
"no data" and never extrapolated.

Perp simulation (per trade, one position per coin, trades never overlap on one coin):
  margin   = margin_frac x equity at entry
  notional = margin x leverage
  costs    = 2 x (commission + slippage) on the notional + funding x holding time
  liquidation: isolated margin is lost when the adverse move reaches 1/leverage - maintenance margin.
    The adverse move is min(MAE, trade return): MAE does not include the exit bar's wick, the trade
    return does (a stop fill). This is an approximation: exchange mark price and liquidation fees differ.
Leverage does not create an edge. The card shows several leverages side by side so the liquidation
cost of high leverage is visible.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lab import metrics


def _label(years: float) -> str:
    return "full" if not years else f"{int(years)}y"


def window_start(index: pd.DatetimeIndex, years: float, first_valid: pd.Timestamp | None = None):
    """Start of the last `years` years, or None when the data does not cover the window."""
    if not len(index):
        return None
    first = first_valid if first_valid is not None else index[0]
    if not years:
        return first
    st = index[-1] - pd.Timedelta(days=365.25 * years)
    return st if st >= first - pd.Timedelta(days=3) else None


def simulate(trades: pd.DataFrame, ppy: float, cost_per_side: float, funding_annual: float,
             balance: float = 1000.0, margin_frac: float = 0.10, leverage: float = 1.0,
             maint_margin: float = 0.005) -> dict:
    if trades is None or trades.empty:
        return {"final": round(balance, 2), "ret": 0.0, "liquidations": 0, "max_dd": 0.0, "trades": 0}
    t = trades.sort_values("exit")
    liq_dist = max(1.0 / leverage - maint_margin, 1e-6)
    eq, peak, mdd, liq = balance, balance, 0.0, 0
    for ret, mae, bars in zip(t["ret"].to_numpy(), t["mae"].to_numpy(), t["bars"].to_numpy()):
        if eq <= 0:
            break
        margin = margin_frac * eq
        notional = margin * leverage
        adverse = min(float(mae), float(ret))
        if adverse <= -liq_dist:
            pnl = -margin - notional * cost_per_side
            liq += 1
        else:
            pnl = notional * (float(ret) - 2 * cost_per_side - funding_annual * float(bars) / ppy)
            pnl = max(pnl, -margin)            # isolated margin: the loss is capped at the margin
        eq += pnl
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1 if peak > 0 else -1.0)
    eq = max(eq, 0.0)
    return {"final": round(eq, 2), "ret": round(eq / balance - 1, 4), "liquidations": int(liq),
            "max_dd": round(mdd, 4), "trades": int(len(t))}


def trade_stats(tr: pd.DataFrame, cost_per_side: float) -> dict:
    """Net-of-cost trade statistics. Win rate alone says nothing: a system is profitable only when
    win_rate > breakeven_wr = 1 / (1 + payoff), payoff = avg win / |avg loss|. wr_margin is that gap;
    expectancy is the mean net return per trade, expectancy_r the mean R multiple (when stops exist)."""
    if tr is None or tr.empty:
        return {"trades": 0, "win_rate": None, "profit_factor": None, "payoff": None,
                "breakeven_wr": None, "wr_margin": None, "expectancy": None, "expectancy_r": None}
    net = tr["ret"] - 2 * cost_per_side
    w, l = net[net > 0], net[net <= 0]
    gains, losses = w.sum(), -l.sum()
    wr = float((net > 0).mean())
    payoff = float(w.mean() / -l.mean()) if len(w) and len(l) and l.mean() < 0 else None
    be = 1.0 / (1.0 + payoff) if payoff else None
    er = None
    if "r_mult" in tr and tr["r_mult"].notna().any():
        er = round(float(tr["r_mult"].mean()), 3)
    return {"trades": int(len(tr)), "win_rate": round(wr, 3),
            "profit_factor": round(float(gains / losses), 3) if losses > 0 else None,
            "payoff": round(payoff, 3) if payoff else None,
            "breakeven_wr": round(be, 3) if be is not None else None,
            "wr_margin": round(wr - be, 3) if be is not None else None,
            "expectancy": round(float(net.mean()), 4), "expectancy_r": er}


def card(r: pd.Series, trades: pd.DataFrame | None, ppy: float, windows: list, account: dict,
         cost_per_side: float, funding_annual: float, first_valid: pd.Timestamp | None = None) -> dict:
    """Report card of one stand-alone strategy (1x bar returns `r`, its trade log `trades`)."""
    metrics.set_periods(ppy)
    out = {}
    for y in windows:
        st = window_start(r.index, y, first_valid)
        lab = _label(y)
        if st is None:
            out[lab] = {"no_data": True}
            continue
        rr = r[r.index >= st]
        tr = trades[trades["entry"] >= st] if trades is not None and len(trades) else trades
        row = {"start": str(st.date()), "years": round(len(rr) / ppy, 2),
               "ret": round(float((1 + rr).prod() - 1), 4), "cagr": round(metrics.cagr(rr), 4),
               "sharpe": round(metrics.sharpe(rr), 3), "max_dd": round(metrics.max_drawdown(rr), 4)}
        row.update(trade_stats(tr, cost_per_side))
        row["perp"] = {f"{L}x": simulate(tr, ppy, cost_per_side, funding_annual, account.get("balance", 1000),
                                         account.get("margin_frac", 0.1), L, account.get("maint_margin", 0.005))
                       for L in account.get("leverages", [1])}
        out[lab] = row
    return out


def yearly_returns(r: pd.Series) -> dict:
    g = r.groupby(r.index.year)
    return {str(y): round(float((1 + x).prod() - 1), 4) for y, x in g if len(x) > 5}


def pos_year_frac(r: pd.Series, ppy: float) -> float:
    g = [(1 + x).prod() - 1 for _, x in r.groupby(r.index.year) if len(x) > ppy / 4]   # >= a quarter of a year
    return float(np.mean([v > 0 for v in g])) if g else 0.0


def sparkline(r: pd.Series, n: int = 120) -> list[float]:
    """Down-sampled equity curve (1 = start) for the dashboard."""
    if r is None or not len(r):
        return []
    eq = (1 + r.fillna(0)).cumprod()
    step = max(1, math.ceil(len(eq) / n))
    pts = eq.iloc[::step].tolist() + [float(eq.iloc[-1])]
    return [round(float(x), 4) for x in pts]
