"""Capital protection study: does a protection rule really protect, and what does it cost?

Portfolio under test: equal weight across the ACTIVE arena members of one timeframe, one coin capped at
`max_coin_weight` (the rest stays in cash). Each member's stand-alone 1x bar returns and its signed
exposure come from the frozen arena settings (lab/arena.compute).

Rules (all decided on CLOSED bars, applied from the next bar; changing exposure costs commission + slippage):
  dd_brake (a, b)   : portfolio below its peak by more than a -> half size, by more than b -> flat.
                      Re-entry is decided on the UNPROTECTED (shadow) portfolio, so a flat book can come back:
                      flat until the shadow drawdown is back above -a, half until it is back above -a/2.
  daily_limit x     : after the protected book lost x within one UTC day, no exposure until the next day
                      (on daily bars: sit out the next day).
  crash_guard x     : BTC fell more than x over the last day -> long members are closed, no longs for one day.
  vol_target x      : scale = min(1, x / annualised vol of the last 30 days of the shadow book) - only de-risks
                      (Moreira & Muir 2017; Harvey et al. 2018 "The impact of volatility targeting").
  equity_ma n       : flat while the shadow book's equity is below its n-day moving average
                      (equity-curve trading; the shadow book keeps running so the rule can switch back on).
  catastrophe x     : members whose exit has NO stop get a hard x% stop (members with a stop are unchanged:
                      on bar data a gap through a stop already fills at the open, a second stop adds nothing).

Evidence for every rule is measured, not assumed:
  * full history: CAGR, Sharpe, max drawdown, CVaR95, time in market
  * every real crash window the data covers (config `crises`)
  * Monte Carlo (drawdown brake): block bootstrap of daily portfolio returns -> P(drawdown <= ruin_dd)
  * every neighbouring threshold must pass too (plateau)
Leverage buffer and concentration caps are arithmetic, not hypotheses: shown as tables, always on.
Sources: Kaminski & Lo (2014) "When do stop-loss rules stop losses?"; Grossman & Zhou (1993) drawdown
control; Moreira & Muir (2017) volatility-managed portfolios; Liu & Tsyvinski (2021) crypto momentum.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pandas as pd

from lab import metrics, regime, screen
from lab.engine import Costs
from lab.panel import Panel
from lab.trade_engine import EXIT_GRID


# ------------------------------------------------------------------ portfolio pieces
def base_weights(R: pd.DataFrame, alive: pd.DataFrame, coin_of: dict, max_coin: float) -> pd.DataFrame:
    a = alive.reindex(index=R.index, columns=R.columns).fillna(False)
    n = a.sum(axis=1).replace(0, np.nan)
    W = a.astype(float).div(n, axis=0).fillna(0.0)
    for coin in set(coin_of[c] for c in R.columns):
        cols = [c for c in R.columns if coin_of[c] == coin]
        tot = W[cols].sum(axis=1)
        f = (max_coin / tot).where(tot > max_coin, 1.0)
        W[cols] = W[cols].mul(f, axis=0)
    return W


def book(R, X, W, M, cps) -> pd.Series:
    """Return of the book with member multipliers M (decided at t-1, used at t) and switching costs."""
    Mv = M.to_numpy()
    Wv = W.to_numpy()
    eff = Wv * Mv
    ret = (eff * np.nan_to_num(R.to_numpy())).sum(axis=1)
    dm = np.abs(np.diff(Mv, axis=0, prepend=Mv[:1]))
    cost = (Wv * dm * np.abs(np.nan_to_num(X.shift(1).to_numpy()))).sum(axis=1) * cps
    return pd.Series(ret - cost, R.index)


def dd_brake_scale(shadow: pd.Series, a: float, b: float) -> pd.Series:
    eq = (1 + shadow.fillna(0)).cumprod()
    dd = (eq / eq.cummax() - 1).to_numpy()
    s = np.ones(len(dd))
    cur = 1.0
    for i in range(1, len(dd)):
        d = dd[i - 1]                      # known at the close of i-1
        if d <= -b:
            cur = 0.0
        elif cur == 0.0:
            cur = 0.5 if d > -a else 0.0
        elif d <= -a:
            cur = 0.5
        elif cur == 0.5 and d > -a / 2:
            cur = 1.0
        s[i] = cur
    return pd.Series(s, shadow.index)


def vol_target_scale(shadow: pd.Series, target: float, ppy: float) -> pd.Series:
    look = regime.bars(30, ppy)
    vol = shadow.rolling(look, min_periods=look // 2).std().shift(1) * math.sqrt(ppy)
    return (target / vol).clip(upper=1.0).fillna(1.0)


def equity_ma_scale(shadow: pd.Series, days: int, ppy: float) -> pd.Series:
    eq = (1 + shadow.fillna(0)).cumprod()
    ma = eq.rolling(regime.bars(days, ppy), min_periods=regime.bars(days, ppy) // 2).mean()
    return (eq > ma).astype(float).shift(1).fillna(1.0)


def daily_limit_scale(R, X, W, cps, limit: float, ppy: float) -> pd.Series:
    """Sequential: needs the protected book's own intraday loss."""
    idx = R.index
    Rv, Wv = np.nan_to_num(R.to_numpy()), W.to_numpy()
    Xv = np.abs(np.nan_to_num(X.shift(1).to_numpy()))
    day = idx.normalize()
    daily_bars = ppy < 400
    s = np.ones(len(idx))
    cur, blocked_day, day_pnl, prev_s = 1.0, None, 0.0, 1.0
    for i in range(1, len(idx)):
        if day[i] != day[i - 1]:
            day_pnl = 0.0
        sc = 0.0 if blocked_day is not None and day[i] <= blocked_day else 1.0
        r = sc * float((Wv[i] * Rv[i]).sum()) - abs(sc - prev_s) * float((Wv[i] * Xv[i]).sum()) * cps
        prev_s = sc
        s[i] = sc
        day_pnl = (1 + day_pnl) * (1 + r) - 1
        if day_pnl <= -limit:
            blocked_day = day[i] + (pd.Timedelta(days=1) if daily_bars else pd.Timedelta(0))
    return pd.Series(s, idx)


def crash_guard_mult(X: pd.DataFrame, btc: pd.Series, drop: float, ppy: float) -> pd.DataFrame:
    n = regime.bars(1, ppy) if ppy > 400 else 1
    r1 = btc / btc.shift(n) - 1
    hit = (r1 <= -drop).fillna(False)
    pause = hit.astype(int).rolling(max(n, 1), min_periods=1).max().astype(bool)   # one day after the hit
    longs = X > 1e-9
    M = pd.DataFrame(1.0, index=X.index, columns=X.columns)
    prev_long = longs.shift(1, fill_value=False).astype(bool)
    paused = pause.shift(1, fill_value=False).astype(bool)
    block = prev_long.apply(lambda col: col & paused)
    return M.mask(block, 0.0)


# ------------------------------------------------------------------ measurement
def stats(r: pd.Series, ppy: float) -> dict:
    metrics.set_periods(ppy)
    d = (1 + r).groupby(r.index.normalize()).prod() - 1
    v, cv = metrics.var_cvar(d)
    return {"cagr": round(metrics.cagr(r), 4), "sharpe": round(metrics.sharpe(r), 3),
            "max_dd": round(metrics.max_drawdown(r), 4), "cvar95_day": round(cv, 4),
            "ret": round(float((1 + r).prod() - 1), 4)}


def crisis_table(r: pd.Series, crises: dict) -> dict:
    out = {}
    for k, (a, b) in crises.items():
        x = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b) + pd.Timedelta(days=1))]
        if len(x) < 3:
            continue
        out[k] = {"ret": round(float((1 + x).prod() - 1), 4), "max_dd": round(metrics.max_drawdown(x), 4)}
    return out


def monte_carlo(r: pd.Series, mc: dict, brake: tuple | None, seed: int = 11) -> dict:
    d = ((1 + r).groupby(r.index.normalize()).prod() - 1).to_numpy()
    if len(d) < 200:
        return {}
    rng = np.random.default_rng(seed)
    n, blk, P = int(365 * mc.get("years", 1)), int(mc.get("block_days", 10)), int(mc.get("paths", 3000))
    ruin = mc.get("ruin_dd", -0.5)
    hits, finals = 0, []
    for _ in range(P):
        starts = rng.integers(0, len(d) - blk, size=n // blk + 1)
        path = np.concatenate([d[s:s + blk] for s in starts])[:n]
        if brake:
            sh = pd.Series(path, pd.RangeIndex(n))
            sc = dd_brake_scale(sh, *brake).to_numpy()
            path = path * sc
        eq = np.cumprod(1 + path)
        mdd = float((eq / np.maximum.accumulate(eq) - 1).min())
        hits += mdd <= ruin
        finals.append(eq[-1])
    return {"p_ruin": round(hits / P, 4), "median_1y": round(float(np.median(finals)) - 1, 4),
            "p5_1y": round(float(np.percentile(finals, 5)) - 1, 4)}


def leverage_table(cat: float, mult: float, mmr: float = 0.005) -> dict:
    """Max leverage so that the liquidation distance is >= mult x the catastrophe stop distance."""
    lmax = 1.0 / (mult * cat + mmr)
    rows = {}
    for L in (1, 2, 3, 5, 10, 20):
        liq = 1.0 / L - mmr
        rows[f"{L}x"] = {"liq_distance": round(liq, 4), "ok": liq >= mult * cat,
                         "survives_gap_30pct": liq > 0.30}
    return {"max_leverage": round(lmax, 2), "table": rows}


# ------------------------------------------------------------------ the study
def _growth_row(name: str, r: pd.Series, ppy: float, crises: dict, note: str = "") -> dict:
    r = r.dropna()
    first = r[r.ne(0)].index.min() if r.ne(0).any() else r.index[0]
    r = r[r.index >= first]
    metrics.set_periods(ppy)
    eq = (1 + r).cumprod()
    yr = (1 + r).groupby(r.index.year).prod() - 1
    end = r.index[-1]

    def last(y):
        x = r[r.index > end - pd.Timedelta(days=365.25 * y)]
        return round(float((1 + x).prod() - 1), 4) if (end - first).days >= 365.25 * y - 3 else None
    cr = crisis_table(r, crises)
    return {"name": name, "note": note, "start": str(first.date()), "end": str(end.date()),
            "final_1000": round(1000 * float(eq.iloc[-1]), 0), "total": round(float(eq.iloc[-1] - 1), 4),
            "cagr": round(metrics.cagr(r), 4), "sharpe": round(metrics.sharpe(r), 2),
            "max_dd": round(metrics.max_drawdown(r), 4), "worst_year": round(float(yr.min()), 4) if len(yr) else None,
            "worst_year_name": str(yr.idxmin()) if len(yr) else None, "ret_3y": last(3), "ret_5y": last(5),
            "worst_crisis_dd": round(min((v["max_dd"] for v in cr.values()), default=0.0), 4),
            "yearly": {str(k): round(float(v), 4) for k, v in yr.items()}}


def portfolio_options(p, R, X, W, members, cols, coin_of, alive, cps, ppy, crises, btc) -> list[dict]:
    """Candidate bot books side by side: how many strategies, how much leverage, which protection.
    Top-N = highest backtest Sharpe, one strategy per coin (no single-coin book). Leverage multiplies
    returns AND costs/funding; with a 2 ATR stop and <= 4x leverage a stop fires before liquidation."""
    sharpe = {m["id"]: ((m.get("backtest") or {}).get("sharpe") or 0) for m in members if m["id"] in cols}
    ranked, seen = [], set()
    for i in sorted(sharpe, key=lambda k: -sharpe[k]):
        if coin_of[i] not in seen:
            ranked.append(i); seen.add(coin_of[i])

    def book_of(ids, lev=1.0):
        sub = [i for i in cols if i in ids]
        Wn = base_weights(R[sub], alive[sub], coin_of, 1.0)
        ones = pd.DataFrame(1.0, index=R.index, columns=sub)
        return book(R[sub] * lev, X[sub], Wn, ones, cps * lev)

    rows = []
    all_ew = book(R, X, W, pd.DataFrame(1.0, index=R.index, columns=cols), cps)
    rows.append(_growth_row(f"Hepsi eşit ağırlık ({len(cols)} strateji), 1x", all_ew, ppy, crises, "şu anki test portföyü"))
    for n in (10, 5):
        if len(ranked) >= n:
            for lev in ((1.0, 2.0, 3.0) if n == 5 else (1.0,)):
                rows.append(_growth_row(f"En iyi {n} (farklı coin), {lev:.0f}x", book_of(ranked[:n], lev), ppy, crises))
    if len(ranked) >= 5:
        b3 = book_of(ranked[:5], 3.0)
        rows.append(_growth_row("En iyi 5, 3x + düşüş sigortası (−%10 yarım / −%20 nakit)",
                                b3 * dd_brake_scale(b3, 0.10, 0.20) - dd_brake_scale(b3, 0.10, 0.20).diff().abs().fillna(0) * cps * 3,
                                ppy, crises))
        vt = vol_target_scale(b3, 0.35, ppy)
        rows.append(_growth_row("En iyi 5, 3x + volatilite hedefi %35", b3 * vt - vt.diff().abs().fillna(0) * cps * 3,
                                ppy, crises))
    # ---- weighting methods on the same top-10 / top-5 (DeMiguel et al. 2009: 1/N is hard to beat;
    # inverse volatility and HRP (Lopez de Prado 2016) are the usual challengers). Weights use ONLY past
    # returns (trailing 90 days, rebalanced monthly), so there is no look-ahead.
    for n in (10, 5):
        if len(ranked) >= n:
            for meth in ("invvol", "hrp"):
                rows.append(_growth_row(f"En iyi {n}, {'ters volatilite' if meth == 'invvol' else 'HRP'} ağırlık, 1x",
                                        weighted_book(R, X, alive, ranked[:n], meth, cps, ppy), ppy, crises))
    # ---- selection-luck test: random books of 5 strategies (one per coin) vs the top 5
    if len(ranked) >= 6:
        rows.append(random_books(R, X, alive, cols, coin_of, cps, ppy, crises, ranked[:5]))
    if btc is not None:
        b = btc.reindex(R.index).ffill().pct_change(fill_method=None).fillna(0)
        rows.append(_growth_row("Karşılaştırma: BTC al-tut", b, ppy, crises))
    return rows


def weighted_book(R, X, alive, ids, method, cps, ppy) -> pd.Series:
    sub = list(ids)
    look = regime.bars(90, ppy)
    r = R[sub].fillna(0.0)
    months = r.index.to_period("M")
    W = pd.DataFrame(0.0, index=r.index, columns=sub)
    last_w = pd.Series(1.0 / len(sub), index=sub)
    for i, (m, idx) in enumerate(pd.Series(r.index, index=r.index).groupby(months)):
        start = idx.iloc[0]
        hist = r[r.index < start].tail(look)
        if len(hist) > look // 3:
            if method == "invvol":
                v = hist.std().replace(0, np.nan)
                w = (1 / v).fillna(0)
            else:
                w = _hrp(hist)
            if w.sum() > 0:
                last_w = w / w.sum()
        W.loc[idx.values] = last_w.values
    W = W.where(alive[sub].reindex(W.index).fillna(False), 0.0)
    ones = pd.DataFrame(1.0, index=R.index, columns=sub)
    return book(R[sub], X[sub], W, ones, cps)


def _hrp(hist: pd.DataFrame) -> pd.Series:
    """Hierarchical risk parity (Lopez de Prado 2016): cluster by correlation, split risk top-down."""
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
    cov, corr = hist.cov(), hist.corr().fillna(0)
    d = np.sqrt(np.clip((1 - corr.values) / 2, 0, None))
    np.fill_diagonal(d, 0)
    order = [hist.columns[i] for i in leaves_list(linkage(squareform(d, checks=False), "single"))]
    w = pd.Series(1.0, index=order)
    clusters = [order]
    while clusters:
        clusters = [c[j:k] for c in clusters for j, k in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for a, b in zip(clusters[::2], clusters[1::2]):
            va = _cvar(cov.loc[a, a]); vb = _cvar(cov.loc[b, b])
            al = 1 - va / (va + vb) if va + vb > 0 else 0.5
            w[a] *= al; w[b] *= 1 - al
    return w.reindex(hist.columns).fillna(0)


def _cvar(c: pd.DataFrame) -> float:
    iv = 1 / np.diag(c.values).clip(min=1e-18)
    iv /= iv.sum()
    return float(iv @ c.values @ iv)


def random_books(R, X, alive, cols, coin_of, cps, ppy, crises, top_ids, n_books: int = 300, k: int = 5) -> dict:
    """Pick k strategies at random (one per coin) many times. Where does the top-k book rank?"""
    rng = np.random.default_rng(17)
    by_coin: dict[str, list] = {}
    for i in cols:
        by_coin.setdefault(coin_of[i], []).append(i)
    coins = list(by_coin)
    finals, dds, sharpes = [], [], []
    metrics.set_periods(ppy)

    def ew(ids):
        Wn = base_weights(R[ids], alive[ids], coin_of, 1.0)
        return book(R[ids], X[ids], Wn, pd.DataFrame(1.0, index=R.index, columns=ids), cps)
    for _ in range(n_books):
        pick = [by_coin[c][rng.integers(len(by_coin[c]))] for c in rng.choice(coins, size=min(k, len(coins)), replace=False)]
        r = ew(pick)
        r = r[r.ne(0).cummax()]
        finals.append(float((1 + r).prod())); dds.append(metrics.max_drawdown(r)); sharpes.append(metrics.sharpe(r))
    rt = ew(list(top_ids)); rt = rt[rt.ne(0).cummax()]
    top_sr = metrics.sharpe(rt)
    row = _growth_row(f"Rastgele {k} strateji (medyan of {n_books}), 1x", rt * 0, ppy, crises)
    row.update({"name": f"Rastgele {k} strateji ({n_books} deneme), 1x — medyan",
                "random": True, "final_1000": round(1000 * float(np.median(finals)), 0),
                "sharpe": round(float(np.median(sharpes)), 2), "max_dd": round(float(np.median(dds)), 4),
                "sharpe_p10_p90": [round(float(np.percentile(sharpes, 10)), 2), round(float(np.percentile(sharpes, 90)), 2)],
                "top_sharpe": round(top_sr, 2), "top_sharpe_percentile": round(float(np.mean(np.array(sharpes) < top_sr)), 3),
                "cagr": None, "worst_year": None, "ret_3y": None, "ret_5y": None, "worst_crisis_dd": 0.0})
    return row


def run(p: Panel, costs: Costs, cfg: dict, R: pd.DataFrame, X: pd.DataFrame, members: list[dict]) -> dict:
    pc = cfg.get("protection", {})
    ppy = p.ppy
    cps = costs.per_turnover
    coin_of = {m["id"]: m["coin"] for m in members}
    cols = [m["id"] for m in members if m["id"] in R.columns]
    R, X = R[cols], X[cols].fillna(0.0)
    alive = pd.DataFrame({i: p.c[coin_of[i]].notna() for i in cols}, index=R.index)
    W = base_weights(R, alive, coin_of, pc.get("max_coin_weight", 0.2))
    W_eq = base_weights(R, alive, coin_of, 1.0)
    ones = pd.DataFrame(1.0, index=R.index, columns=cols)
    base = book(R, X, W, ones, cps)
    uncapped = book(R, X, W_eq, ones, cps)
    btc = p.c.get("BTC/USDT") if "BTC/USDT" in p.columns else p.bench
    crises = pc.get("crises", {})
    tests = pc.get("tests", {})
    acc = pc.get("accept", {})
    mc = pc.get("monte_carlo", {})

    def evaluate(r):
        return {"full": stats(r, ppy), "crises": crisis_table(r, crises)}

    res = {"base": evaluate(base), "uncapped": evaluate(uncapped)}
    res["base"]["mc"] = monte_carlo(base, mc, None)

    variants: dict[str, list[tuple]] = {}
    for a, b in tests.get("dd_brake", []):
        sc = dd_brake_scale(base, a, b)
        variants.setdefault("dd_brake", []).append(((a, b), book(R, X, W, ones.mul(sc, axis=0), cps)))
    for x in tests.get("vol_target", []):
        sc = vol_target_scale(base, x, ppy)
        variants.setdefault("vol_target", []).append((x, book(R, X, W, ones.mul(sc, axis=0), cps)))
    for n in tests.get("equity_ma", []):
        sc = equity_ma_scale(base, n, ppy)
        variants.setdefault("equity_ma", []).append((n, book(R, X, W, ones.mul(sc, axis=0), cps)))
    for x in tests.get("daily_limit", []):
        sc = daily_limit_scale(R, X, W, cps, x, ppy)
        variants.setdefault("daily_limit", []).append((x, book(R, X, W, ones.mul(sc, axis=0), cps)))
    if btc is not None:
        for x in tests.get("crash_guard", []):
            M = crash_guard_mult(X, btc.reindex(R.index).ffill(), x, ppy)
            variants.setdefault("crash_guard", []).append((x, book(R, X, W, M, cps)))
    nostop = [m for m in members if m["id"] in cols and not (
        EXIT_GRID[m["exit_id"]].stop_atr or EXIT_GRID[m["exit_id"]].stop_pct or EXIT_GRID[m["exit_id"]].stop_swing)]
    res["catastrophe_members"] = len(nostop)
    if nostop:
        for x in tests.get("catastrophe_stop", []):
            Rc = R.copy()
            for m in nostop:
                spec = {"rule": m["rule"], "params": m["params"], "exit_id": m["exit_id"],
                        "filter": m.get("filter", "none"), "confirm": m.get("confirm")}
                ex = replace(EXIT_GRID[m["exit_id"]], stop_pct=x)
                r, _, _ = screen.run_spec(screen.subpanel(p, [m["coin"]]), spec, m["side"], costs, exit_cfg=ex)
                Rc[m["id"]] = r[m["coin"]]
            variants.setdefault("catastrophe_stop", []).append((x, book(Rc, X, W, ones, cps)))

    b_full, b_cr = res["base"]["full"], res["base"]["crises"]
    verdicts = {}
    for name, lst in variants.items():
        rows, all_pass = [], True
        for thr, r in lst:
            ev = evaluate(r)
            f, cr = ev["full"], ev["crises"]
            common = [k for k in cr if k in b_cr]
            better = [k for k in common if cr[k]["max_dd"] > b_cr[k]["max_dd"] + 1e-6]
            frac = len(better) / len(common) if common else 0.0
            chk = {
                "crises_better": f"{len(better)}/{len(common)}",
                "crises_ok": bool(common) and frac >= acc.get("min_crises_better_frac", 0.67),
                "full_dd_ok": (f["max_dd"] > b_full["max_dd"]) if acc.get("must_lower_full_dd", True) else True,
                "sharpe_ok": f["sharpe"] >= b_full["sharpe"] * (1 - acc.get("max_sharpe_drop", 0.10)) if b_full["sharpe"] > 0
                else f["sharpe"] >= b_full["sharpe"],
                "cagr_ok": f["cagr"] >= b_full["cagr"] * (1 - acc.get("max_cagr_drop", 0.25)) if b_full["cagr"] > 0
                else f["cagr"] >= b_full["cagr"],
            }
            ok = all(v for k, v in chk.items() if k.endswith("_ok"))
            all_pass &= ok
            row = {"threshold": thr, **ev, "checks": chk, "pass": ok}
            if name == "dd_brake":
                row["mc"] = monte_carlo(base, mc, thr)
            rows.append(row)
        verdicts[name] = {"pass": bool(rows) and all_pass, "rows": rows}
    res["tests"] = verdicts
    cat_mid = (tests.get("catastrophe_stop") or [0.12])[len(tests.get("catastrophe_stop") or [0.12]) // 2]
    res["leverage"] = leverage_table(cat_mid, pc.get("leverage_buffer_mult", 2.0))
    res["members"] = len(cols)
    res["options"] = portfolio_options(p, R, X, W, members, cols, coin_of, alive, cps, ppy, crises, btc)
    res["series"] = {"base": base, **{f"{n}:{lst[len(lst) // 2][0]}": lst[len(lst) // 2][1]
                                      for n, lst in variants.items() if lst}}
    return res


NAMES_TR = {"dd_brake": "Kasa düşüş sigortası", "daily_limit": "Günlük kayıp limiti",
            "crash_guard": "BTC çöküş bekçisi", "catastrophe_stop": "Felaket stopu",
            "vol_target": "Volatilite hedefi", "equity_ma": "Kasa eğrisi filtresi"}


def markdown(res: dict, cfg: dict) -> str:
    tf = cfg.get("timeframe")
    b = res["base"]
    L = [f"# Kasa koruma testi — {cfg.get('universe')} {tf}", "",
         f"Portföy: arenadaki **{res['members']} aktif üye**, eşit ağırlık, coin başı en fazla "
         f"%{cfg['protection'].get('max_coin_weight', 0.2) * 100:.0f}. Kabul kuralları sonuçlardan önce yazıldı "
         "(`config/arena.yaml` → `protection.accept`). Bir koruma sadece **komşu eşiklerin hepsinde** ve "
         "**her zaman diliminde** geçerse açılır.", "",
         "## Korumasız portföy", "",
         f"Tüm geçmiş: CAGR {b['full']['cagr']:+.1%}, Sharpe {b['full']['sharpe']}, maks. düşüş {b['full']['max_dd']:.1%}, "
         f"günlük CVaR95 {b['full']['cvar95_day']:.1%}. Coin sınırı olmadan: maks. düşüş {res['uncapped']['full']['max_dd']:.1%}.", ""]
    if b.get("mc"):
        L.append(f"Monte Carlo (1 yıl): P(düşüş ≤ −%50) = {b['mc']['p_ruin']:.1%}, medyan {b['mc']['median_1y']:+.0%}, "
                 f"kötü %5 {b['mc']['p5_1y']:+.0%}.")
    L += ["", "| Kriz | Getiri | Maks. düşüş |", "|---|---|---|"]
    for k, v in b["crises"].items():
        L.append(f"| {k} | {v['ret']:+.1%} | {v['max_dd']:.1%} |")
    for name, v in res["tests"].items():
        L += ["", f"## {NAMES_TR.get(name, name)} — {'✅ GEÇTİ' if v['pass'] else '❌ GEÇMEDİ'}", "",
              "| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |",
              "|---|---|---|---|---|---|---|"]
        for r in v["rows"]:
            c = r["checks"]
            flags = "".join("✓" if c[k] else "✗" for k in ("crises_ok", "full_dd_ok", "sharpe_ok", "cagr_ok"))
            L.append(f"| {r['threshold']} | {r['full']['cagr']:+.1%} | {r['full']['sharpe']} | {r['full']['max_dd']:.1%} | "
                     f"{c['crises_better']} | {flags} | {'geçti' if r['pass'] else 'kaldı'} |")
            if r.get("mc"):
                L.append(f"|  | MC P(≤−%50): {r['mc']['p_ruin']:.1%} (korumasız {b['mc'].get('p_ruin', 0):.1%}) |  |  |  |  |  |")
    if res.get("catastrophe_members", 0) == 0:
        L += ["", "## Felaket stopu", "", "Test edilmedi: aktif üyelerin hepsinin çıkışında zaten bir stop var. "
              "Bar verisinde gap, stopu açılıştan doldurur; ikinci bir stop bir şey değiştirmez."]
    if res.get("options"):
        L += ["", "## Portföy seçenekleri ($1000 ile başlangıç, maliyet ve funding dahil)", "",
              "| Portföy | Başlangıç | Bugün ($) | Yıllık | Sharpe | Maks. düşüş | En kötü yıl | Son 3y | Son 5y | En kötü kriz |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        f = lambda v: "–" if v is None else f"{v:+.0%}"   # noqa: E731
        for o in res["options"]:
            if o.get("random"):
                L.append(f"| {o['name']} | – | {o['final_1000']:,.0f} | – | {o['sharpe']} (p10–p90: {o['sharpe_p10_p90'][0]}–{o['sharpe_p10_p90'][1]}) | "
                         f"{o['max_dd']:.0%} | – | – | – | – |")
                L.append(f"|  | En iyi 5'in Sharpe'ı {o['top_sharpe']}: rastgele portföylerin %{o['top_sharpe_percentile'] * 100:.0f}'inden iyi |  |  |  |  |  |  |  |  |")
                continue
            L.append(f"| {o['name']} | {o['start']} | {o['final_1000']:,.0f} | {f(o['cagr'])} | {o['sharpe']} | "
                     f"{o['max_dd']:.0%} | {f(o['worst_year'])} ({o['worst_year_name']}) | {f(o['ret_3y'])} | {f(o['ret_5y'])} | "
                     f"{o['worst_crisis_dd']:.0%} |")
    lv = res["leverage"]
    L += ["", "## Likidasyon tamponu (matematik, test gerekmez)", "",
          f"Kural: likidasyon mesafesi ≥ {cfg['protection'].get('leverage_buffer_mult', 2.0)} × felaket stop mesafesi → "
          f"**en fazla {lv['max_leverage']}x**.", "", "| Kaldıraç | Likidasyon mesafesi | Kurala uygun | −%30 gap'te hayatta |", "|---|---|---|---|"]
    for k, v in lv["table"].items():
        L.append(f"| {k} | %{v['liq_distance'] * 100:.1f} | {'✓' if v['ok'] else '✗'} | {'✓' if v['survives_gap_30pct'] else '✗'} |")
    L += ["", "## Zayıf yönler", "",
          "- Portföy, aynı geçmişte seçilmiş üyelerden oluşur; korumasız sonuç iyimserdir. Korumanın **farkı** daha güvenilirdir.",
          "- Bar verisi kullanılır: bar içindeki ani iğneler (wick) ve borsa kesintileri modellenmez.",
          "- Kriz sayısı az (en fazla 6). 'Krizlerin 2/3'ü' kuralı küçük örneklemle çalışır.",
          "- Monte Carlo blokları geçmişten alınır; geçmişte hiç olmamış bir şok kapsanmaz."]
    return "\n".join(L)


def summary_json(res: dict) -> dict:
    return {"members": res["members"], "base": res["base"], "leverage": res["leverage"],
            "options": res.get("options", []),
            "catastrophe_members": res.get("catastrophe_members", 0),
            "tests": {k: {"pass": v["pass"], "rows": [{kk: vv for kk, vv in r.items()} for r in v["rows"]]}
                      for k, v in res["tests"].items()}}


__all__ = ["run", "markdown", "summary_json", "math"]


# ================================================================== any strategy, any market (hypothesis reports)
def load_cfg(market: str) -> dict:
    import yaml
    from pathlib import Path
    c = yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "protection.yaml").read_text())
    tests = {**c.get("tests", {}), **(c.get("by_market", {}).get(market) or {})}
    crises = c.get("crises", {}).get(market) or c.get("crises", {}).get("multi", {})
    return {"tests": tests, "accept": c.get("accept", {}), "monte_carlo": c.get("monte_carlo", {}), "crises": crises}


def _judge(b_full, b_cr, ev, acc) -> tuple[bool, dict]:
    f, cr = ev["full"], ev["crises"]
    common = [k for k in cr if k in b_cr]
    better = [k for k in common if cr[k]["max_dd"] > b_cr[k]["max_dd"] + 1e-6]
    frac = len(better) / len(common) if common else 0.0
    chk = {
        "crises_better": f"{len(better)}/{len(common)}",
        "crises_ok": bool(common) and frac >= acc.get("min_crises_better_frac", 0.67),
        "full_dd_ok": (f["max_dd"] > b_full["max_dd"]) if acc.get("must_lower_full_dd", True) else True,
        "sharpe_ok": f["sharpe"] >= b_full["sharpe"] * (1 - acc.get("max_sharpe_drop", 0.10)) if b_full["sharpe"] > 0
        else f["sharpe"] >= b_full["sharpe"],
        "cagr_ok": f["cagr"] >= b_full["cagr"] * (1 - acc.get("max_cagr_drop", 0.25)) if b_full["cagr"] > 0
        else f["cagr"] >= b_full["cagr"],
    }
    return all(v for k, v in chk.items() if k.endswith("_ok")), chk


def _daily_limit_series(r: pd.Series, limit: float, ppy: float) -> pd.Series:
    day = r.index.normalize()
    daily_bars = ppy < 400
    s = np.ones(len(r))
    blocked, pnl = None, 0.0
    rv = r.fillna(0).to_numpy()
    for i in range(1, len(r)):
        if day[i] != day[i - 1]:
            pnl = 0.0
        sc = 0.0 if blocked is not None and day[i] <= blocked else 1.0
        s[i] = sc
        pnl = (1 + pnl) * (1 + sc * rv[i]) - 1
        if pnl <= -limit:
            blocked = day[i] + (pd.Timedelta(days=1) if daily_bars else pd.Timedelta(0))
    return pd.Series(s, r.index)


def _market_guard_series(r: pd.Series, bench: pd.Series | None, drop: float, ppy: float) -> pd.Series | None:
    if bench is None:
        return None
    b = bench.reindex(r.index).ffill()
    n = regime.bars(1, ppy) if ppy > 400 else 1
    hit = (b / b.shift(n) - 1 <= -drop).fillna(False)
    pause = hit.astype(int).rolling(max(n, 1), min_periods=1).max().astype(bool)
    return (~pause.shift(1, fill_value=False).astype(bool)).astype(float)


def study_series(r: pd.Series, bench: pd.Series | None, ppy: float, cps: float, market: str) -> dict:
    """Capital-protection diagnostic for ONE strategy's return series (any market).
    Switching cost assumes full exposure (conservative): |change in scale| x (commission + slippage)."""
    c = load_cfg(market or "multi")
    tests, acc, crises, mc = c["tests"], c["accept"], c["crises"], c["monte_carlo"]
    r = r.dropna()
    metrics.set_periods(ppy)

    def ev(x):
        return {"full": stats(x, ppy), "crises": crisis_table(x, crises)}

    def apply(sc):
        sc = sc.reindex(r.index).fillna(1.0)
        return r * sc - sc.diff().abs().fillna(0) * cps

    base = ev(r)
    base["mc"] = monte_carlo(r, mc, None)
    variants: dict[str, list] = {}
    for a, b in tests.get("dd_brake", []):
        variants.setdefault("dd_brake", []).append(((a, b), apply(dd_brake_scale(r, a, b))))
    for x in tests.get("vol_target", []):
        variants.setdefault("vol_target", []).append((x, apply(vol_target_scale(r, x, ppy))))
    for n in tests.get("equity_ma", []):
        variants.setdefault("equity_ma", []).append((n, apply(equity_ma_scale(r, n, ppy))))
    for x in tests.get("daily_limit", []):
        variants.setdefault("daily_limit", []).append((x, apply(_daily_limit_series(r, x, ppy))))
    for x in tests.get("market_guard", []):
        sc = _market_guard_series(r, bench, x, ppy)
        if sc is not None:
            variants.setdefault("market_guard", []).append((x, apply(sc)))
    out = {"market": market, "crises_covered": list(base["crises"]), "base": base, "tests": {}}
    for name, lst in variants.items():
        rows, ok_all = [], True
        for thr, x in lst:
            e = ev(x)
            ok, chk = _judge(base["full"], base["crises"], e, acc)
            ok_all &= ok
            row = {"threshold": thr, **e, "checks": chk, "pass": ok}
            if name == "dd_brake":
                row["mc"] = monte_carlo(r, mc, thr)
            rows.append(row)
        out["tests"][name] = {"pass": bool(rows) and ok_all, "rows": rows}
    return out


NAMES_TR.update({"market_guard": "Piyasa çöküş bekçisi"})


def markdown_series(st: dict) -> list[str]:
    """Report section for a hypothesis (Turkish, phone-friendly)."""
    b = st["base"]
    L = ["", "## Kasa koruma (kriz testi, teşhis)", "",
         f"Piyasa: **{st['market']}**. Kapsanan krizler: {', '.join(st['crises_covered']) or 'yok (veri kısa)'}. "
         "Eşikler ve kabul kuralları `config/protection.yaml` içinde, sonuçlardan önce yazıldı. "
         "Bu bölüm stratejiyi DEĞİŞTİRMEZ. Bir kuralı kullanmak için hipoteze `overlays:` olarak ekleyin.", "",
         f"Korumasız (tüm geçmiş): CAGR {b['full']['cagr']:+.1%}, Sharpe {b['full']['sharpe']}, "
         f"maks. düşüş {b['full']['max_dd']:.1%}" + (f", MC P(≤−%50) {b['mc']['p_ruin']:.1%}" if b.get("mc") else ""), "",
         "| Kriz | Getiri | Maks. düşüş |", "|---|---|---|"]
    for k, v in b["crises"].items():
        L.append(f"| {k} | {v['ret']:+.1%} | {v['max_dd']:.1%} |")
    L += ["", "| Kural | Sonuç (tüm eşikler) | Eşik: krizlerde daha iyi · Sharpe · maks. düşüş |", "|---|---|---|"]
    for name, v in st["tests"].items():
        det = " / ".join(f"{r['threshold']}: {r['checks']['crises_better']} · {r['full']['sharpe']} · {r['full']['max_dd']:.0%}"
                         for r in v["rows"])
        L.append(f"| {NAMES_TR.get(name, name)} | {'✅ geçti' if v['pass'] else '❌ geçmedi'} | {det} |")
    return L
