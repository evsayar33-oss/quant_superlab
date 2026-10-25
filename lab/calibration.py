"""Calibration: does the engine reproduce results that are KNOWN from the literature and from
plain arithmetic, on real data? If a check fails, the machine (data, engine or metrics) is
suspect and no verdict should be trusted until it is fixed.

Checks (each with the reason the expected range is what it is):
  C1 identity      SPY buy&hold through the weight engine == SPY's own return series
  C2 faber         SPY close>SMA200 timing (Faber 2007): much smaller drawdown than buy&hold
                   (2008 crash avoided), Sharpe in the same neighbourhood
  C3 tsmom         12-month time-series momentum on a cross-asset ETF set (Moskowitz, Ooi &
                   Pedersen 2012): positive Sharpe, shallower drawdown than equal weight
  C4 low_vol       lowest-volatility large caps have lower volatility than equal weight
                   (Ang et al. 2006; Baker et al. 2011) - a property, not a return claim
  C5 gold          GLD buy&hold CAGR 2005->today inside the known range (data sanity)
  C6 lira          USDTRY rose by more than 10x since 2010 (FX series sanity)
  C7 lookahead     a "cheating" signal built from today's return makes money only without
                   the execution lag; with the engine's lag it must not
  C8 trade_engine  price>SMA200 via the TRADE engine agrees with the weight engine (C2)
"""
from __future__ import annotations

import pandas as pd

from lab import data, engine, metrics
from lab.engine import Costs
from lab.panel import Panel
from lab.rules import RULES, Signals
from lab.strategies import REGISTRY
from lab.trade_engine import ExitCfg, run_trades


def _row(cid, name, ok, detail, expect):
    return {"id": cid, "check": name, "pass": bool(ok), "result": detail, "expected": expect}


def run() -> list[dict]:
    metrics.set_periods(252)
    out = []
    spy_d = data.load_ohlcv(["SPY"], "2000-01-01")["SPY"]
    spy = spy_d[["Close"]].rename(columns={"Close": "SPY"})
    bh = engine.run(spy, pd.DataFrame(1.0, index=spy.index, columns=["SPY"]), Costs(0, 0)).returns
    raw = spy["SPY"].pct_change(fill_method=None).reindex(bh.index).fillna(0)
    diff = float((bh - raw).iloc[2:].abs().max())
    out.append(_row("C1", "identity: engine buy&hold == raw returns", diff < 1e-10, f"max abs diff {diff:.2e}", "< 1e-10"))

    on = (spy["SPY"] > spy["SPY"].rolling(200).mean()).astype(float).to_frame("SPY")
    fab = engine.run(spy, on, Costs(0.0002, 0.0003)).returns
    s_bh, s_f = metrics.summary(bh.loc[fab.index]), metrics.summary(fab)
    ok = s_f["max_dd"] > s_bh["max_dd"] + 0.15 and abs(s_f["sharpe"] - s_bh["sharpe"]) < 0.4
    out.append(_row("C2", "Faber SMA200 timing on SPY (2000+)", ok,
                    f"timing SR {s_f['sharpe']} DD {s_f['max_dd']} | buy&hold SR {s_bh['sharpe']} DD {s_bh['max_dd']}",
                    "timing DD at least 15 pts shallower, Sharpe within +-0.4"))

    ga = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"]
    px = data.load_prices(ga, "2006-01-01")
    w = REGISTRY["ts_momentum"](px, lookback=252, vol_target=0.15, long_only=True, freq="ME")
    ts = engine.run(px, w, Costs(0.0002, 0.0003)).returns
    ew = engine.run(px, REGISTRY["equal_weight"](px), Costs(0.0002, 0.0003)).returns.loc[ts.index]
    s_ts, s_ew = metrics.summary(ts), metrics.summary(ew)
    ok = s_ts["sharpe"] > 0.1 and s_ts["max_dd"] > s_ew["max_dd"]
    out.append(_row("C3", "TSMOM 12m cross-asset (2006+)", ok,
                    f"TSMOM SR {s_ts['sharpe']} DD {s_ts['max_dd']} | EW SR {s_ew['sharpe']} DD {s_ew['max_dd']}",
                    "Sharpe > 0.1 and drawdown shallower than equal weight"))

    lc = ["AAPL", "MSFT", "JNJ", "PG", "KO", "PEP", "WMT", "XOM", "JPM", "NVDA", "AMZN", "META", "MRK",
          "HD", "MCD", "VZ", "T", "INTC", "CSCO", "ORCL", "DUK", "SO", "CL", "MMM", "CAT"]
    pl = data.load_prices(lc, "2010-01-01")
    lv = engine.run(pl, REGISTRY["low_vol"](pl, lookback=252, top_n=8, freq="ME"), Costs()).returns
    ewl = engine.run(pl, REGISTRY["equal_weight"](pl), Costs()).returns.loc[lv.index]
    ratio = metrics.summary(lv)["vol"] / metrics.summary(ewl)["vol"]
    out.append(_row("C4", "low-vol portfolio volatility vs equal weight", ratio < 0.92, f"vol ratio {ratio:.2f}", "< 0.92"))

    gld = data.load_prices(["GLD"], "2005-01-01")["GLD"].dropna()
    c = metrics.cagr(gld.pct_change(fill_method=None).dropna())
    out.append(_row("C5", "GLD buy&hold CAGR 2005+ (data sanity)", 0.05 < c < 0.14, f"CAGR {c:.3f}", "5%..14%"))

    fx = data.load_series("USDTRY=X", "2010-01-01").dropna()
    mult = float(fx.iloc[-1] / fx.iloc[:20].mean())
    out.append(_row("C6", "USDTRY rise since 2010 (FX sanity)", mult > 10, f"x{mult:.1f}", "> x10"))

    sec = data.load_prices(["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB"], "2005-01-01")
    cheat = engine.rank_top_n(sec.pct_change(fill_method=None), 2)
    lagged = metrics.sharpe(engine.run(sec, cheat, Costs(0, 0)).returns)
    nolag = metrics.sharpe(engine.run(sec, cheat, Costs(0, 0), lag=0).returns)
    out.append(_row("C7", "look-ahead canary (today's return as signal)", lagged < 1.5 and nolag > 5,
                    f"with lag SR {lagged:.2f} | without lag SR {nolag:.2f}", "lag < 1.5, no-lag > 5"))

    p = Panel.from_ohlcv({"SPY": spy_d})
    s = RULES["price_ma"].fn(p, kind="sma", n=200)
    te = run_trades(p, s, ExitCfg(), Costs(0.0002, 0.0003)).returns
    sr_te = metrics.sharpe(te)
    ok = abs(sr_te - s_f["sharpe"]) < 0.25
    out.append(_row("C8", "trade engine vs weight engine (same SMA200 idea)", ok,
                    f"trade engine SR {sr_te:.3f} | weight engine SR {s_f['sharpe']}",
                    "within +-0.25 (fills differ: next open vs close)"))
    return out


def markdown(rows: list[dict]) -> str:
    n_ok = sum(r["pass"] for r in rows)
    L = [f"# Calibration — {n_ok}/{len(rows)} passed", "",
         "If any check fails, verdicts are not trustworthy until it is fixed.", "",
         "| id | check | pass | result | expected |", "|---|---|---|---|---|"]
    L += [f"| {r['id']} | {r['check']} | {'✅' if r['pass'] else '❌'} | {r['result']} | {r['expected']} |" for r in rows]
    return "\n".join(L)
