"""Event-style trade engine for entry/exit rules (bar-by-bar, vectorized across assets).

Execution model (conservative, no look-ahead), for ANY timeframe:
  * Signals are read at the CLOSE of bar t-1 and executed at the OPEN of bar t.
  * Bar t, in order:
      open     : pending exits (signal, time, MA-trail, reversal), then entries
      intrabar : stop first (if stop and target are both touched, the stop wins), then partial
                 take-profit, then full target. Gap through a level fills at the open.
      close    : mark to market, breakeven / trailing / chandelier update, MA-exit and time flags
  * Price limits (BIST +-10%): an order cannot fill at a limit-locked open (entry or exit waits).
  * Liquidity: entries need average traded value >= min_adv (universe setting).
  * Costs: commission + slippage on every traded notional; borrow (shorts) and perp funding
    (all positions) accrue per bar.

Position sizing (SizeCfg):  equal 1/slots | atr_risk (risk X% of equity to the stop) |
                            vol (per-position volatility target);  gross exposure cap.
Exit toolbox (ExitCfg): ATR/%/swing-low stop, ATR/%/R target, partial take-profit + move to
breakeven, breakeven trigger, ATR/% trailing (chandelier), moving-average trailing exit,
max holding bars, rule's own exit signal (on/off).
Every trade records MFE / MAE (best and worst excursion) and the R multiple.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from lab import indicators as I
from lab.engine import Costs, Result
from lab.panel import Panel
from lab.rules import Signals


@dataclass(frozen=True)
class ExitCfg:
    stop_atr: float | None = None
    stop_pct: float | None = None
    stop_swing: int | None = None       # stop below the lowest low of the last N bars
    tp_atr: float | None = None
    tp_pct: float | None = None
    tp_r: float | None = None           # target = R x initial risk
    partial_r: float | None = None      # take part of the position at this R ...
    partial_frac: float = 0.5           # ... this fraction ...
    partial_to_be: bool = True          # ... and move the stop to breakeven
    be_r: float | None = None           # move stop to breakeven once price is +be_r R
    trail_atr: float | None = None      # chandelier: extreme since entry -/+ k ATR
    trail_pct: float | None = None
    ma_exit: int | None = None          # exit when close crosses the EMA(n) against the trade
    max_hold: int | None = None
    atr_n: int = 14
    use_signal_exit: bool = True

    def label(self) -> str:
        d = asdict(self)
        keep = {k: v for k, v in d.items()
                if v is not None and not (k == "atr_n" and v == 14) and not (k == "use_signal_exit" and v)
                and not (k in ("partial_frac", "partial_to_be") and d["partial_r"] is None)}
        return ",".join(f"{k}={v}" for k, v in keep.items()) or "signal_only"


@dataclass(frozen=True)
class SizeCfg:
    mode: str = "equal"          # equal | atr_risk | vol
    risk_pct: float = 0.01       # atr_risk: equity risked to the stop per trade
    vol_target: float = 0.15     # vol: annual vol per position before /slots
    max_w: float = 0.25          # cap per position
    max_gross: float = 1.0       # cap on total exposure (1.0 = no leverage)

    def label(self) -> str:
        if self.mode == "equal":
            return "equal"
        if self.mode == "atr_risk":
            return f"atr_risk{self.risk_pct}"
        return f"vol{self.vol_target}"


E = ExitCfg
EXIT_GRID: list[ExitCfg] = [
    E(),                                                     # 0 rule signal only
    E(stop_atr=1.5), E(stop_atr=2.0), E(stop_atr=3.0),       # 1-3 ATR stops
    E(stop_pct=0.03), E(stop_pct=0.05), E(stop_pct=0.08), E(stop_pct=0.12),   # 4-7 % stops
    E(stop_swing=5), E(stop_swing=10), E(stop_swing=20),     # 8-10 swing-low stops
    E(stop_atr=2.0, tp_r=1.5), E(stop_atr=2.0, tp_r=2.0), E(stop_atr=2.0, tp_r=3.0),  # 11-13 R targets
    E(stop_atr=1.5, tp_atr=3.0), E(stop_atr=2.0, tp_atr=5.0),                          # 14-15 ATR targets
    E(stop_pct=0.05, tp_pct=0.10), E(stop_pct=0.08, tp_pct=0.20),                      # 16-17 % targets
    E(stop_atr=2.0, partial_r=1.0, trail_atr=3.0),           # 18 scale out 50% at 1R, trail rest
    E(stop_atr=2.0, partial_r=2.0, trail_atr=3.0),           # 19
    E(stop_atr=2.0, be_r=1.0), E(stop_atr=2.0, be_r=1.0, tp_r=3.0),                   # 20-21 breakeven
    E(trail_atr=2.0), E(trail_atr=3.0), E(trail_atr=4.0),    # 22-24 chandelier
    E(trail_pct=0.05), E(trail_pct=0.10), E(trail_pct=0.15),  # 25-27 % trailing
    E(stop_atr=2.0, trail_atr=3.0),                          # 28
    E(ma_exit=10), E(ma_exit=20), E(stop_atr=2.0, ma_exit=20),                         # 29-31 MA trailing
    E(max_hold=3), E(max_hold=5), E(max_hold=10), E(max_hold=20), E(max_hold=40),      # 32-36 time exits
    E(stop_atr=2.0, max_hold=10), E(stop_atr=2.0, tp_r=2.0, max_hold=20),              # 37-38
    E(stop_atr=2.0, tp_r=2.0, use_signal_exit=False),        # 39 bracket only
    E(trail_atr=3.0, use_signal_exit=False),                 # 40 trail only
    E(stop_atr=2.0, partial_r=1.0, trail_atr=3.0, use_signal_exit=False),              # 41
    E(max_hold=5, use_signal_exit=False), E(max_hold=10, use_signal_exit=False),       # 42-43 fixed horizon
]

SIZE_GRID: list[SizeCfg] = [SizeCfg(), SizeCfg("atr_risk", 0.005), SizeCfg("atr_risk", 0.01),
                            SizeCfg("atr_risk", 0.02), SizeCfg("vol", vol_target=0.10),
                            SizeCfg("vol", vol_target=0.20)]


def run_trades(p: Panel, sig: Signals, ex: ExitCfg = ExitCfg(), costs: Costs = Costs(),
               side: str = "long", max_positions: int | None = None, size: SizeCfg = SizeCfg(),
               per_asset: bool = False) -> Result:
    """per_asset=True also returns meta["asset_returns"]: each asset's net bar return contribution
    (already net of its own costs and carry). With equal sizing and no slot limit, multiplying by
    the number of assets gives each asset's stand-alone single-asset return series (exact, linear in weight)."""
    idx, cols = p.index, p.columns
    T, N = p.c.shape
    ppy = p.ppy
    c_raw = p.c.to_numpy()
    C = p.c.ffill().to_numpy()
    O = np.where(np.isnan(p.o.to_numpy()), C, p.o.to_numpy())
    H = np.where(np.isnan(p.h.to_numpy()), C, p.h.to_numpy())
    L = np.where(np.isnan(p.l.to_numpy()), C, p.l.to_numpy())
    A = I.atr(p.h, p.l, p.c, ex.atr_n).to_numpy()
    score = (p.c / p.c.shift(63)).to_numpy()
    swing_lo = p.l.rolling(ex.stop_swing, min_periods=1).min().to_numpy() if ex.stop_swing else None
    swing_hi = p.h.rolling(ex.stop_swing, min_periods=1).max().to_numpy() if ex.stop_swing else None
    ma = I.ema(p.c, ex.ma_exit).to_numpy() if ex.ma_exit else None
    vol_a = (p.c.pct_change(fill_method=None).rolling(63, min_periods=20).std() * np.sqrt(ppy)).to_numpy() \
        if size.mode == "vol" else None
    limit = (p.costs_meta or {}).get("price_limit")
    min_adv = (p.costs_meta or {}).get("min_adv")
    adv = (p.c * p.v).rolling(20, min_periods=5).mean().shift(1).to_numpy() if min_adv else None
    member = p.member.reindex(index=idx, columns=cols).fillna(False).to_numpy() if p.member is not None else None

    def arr(x):
        if x is None:
            return np.zeros((T, N), bool)
        return x.reindex(index=idx, columns=cols).fillna(False).to_numpy().astype(bool).copy()

    eL, xL, eS, xS = arr(sig.entry_long), arr(sig.exit_long), arr(sig.entry_short), arr(sig.exit_short)
    if side == "long":
        eS[:] = False
    elif side == "short":
        eL[:] = False
    if member is not None:
        eL &= member; eS &= member

    slots = max_positions or N
    need_atr = bool(ex.stop_atr or ex.tp_atr or ex.trail_atr or
                    (size.mode == "atr_risk" and not (ex.stop_pct or ex.stop_swing)))
    cpt = costs.per_turnover
    carry = (costs.borrow_annual, getattr(costs, "funding_annual", 0.0))

    pos = np.zeros(N); w = np.zeros(N)
    entry_px = np.full(N, np.nan); stop = np.full(N, np.nan); tgt = np.full(N, np.nan)
    tp1 = np.full(N, np.nan); runit = np.full(N, np.nan); ext = np.full(N, np.nan)
    mfe = np.zeros(N); mae = np.zeros(N)
    held = np.zeros(N, int); entry_i = np.zeros(N, int); entry_w = np.zeros(N)
    flag_exit = np.zeros(N, bool); why_exit = np.array([""] * N, dtype=object)
    partial_done = np.zeros(N, bool); realized = np.zeros(N)

    pendL = np.zeros(N, bool); pendS = np.zeros(N, bool)
    port = np.zeros(T); turn = np.zeros(T); wts = np.zeros((T, N))
    aret = np.zeros((T, N)) if per_asset else None
    trades: list[tuple] = []

    def finish(j, i, px, reason):
        tot = realized[j] + (entry_w[j] and w[j] / entry_w[j]) * pos[j] * (px / entry_px[j] - 1)
        r_mult = tot / (runit[j] / entry_px[j]) if runit[j] == runit[j] and runit[j] > 0 else np.nan
        trades.append((idx[entry_i[j]], idx[i], cols[j], int(pos[j]), round(float(entry_w[j]), 4),
                       float(entry_px[j]), float(px), float(tot), float(r_mult), float(mfe[j]), float(mae[j]),
                       int(held[j]), reason))

    for i in range(1, T):
        contrib = np.zeros(N); traded = np.zeros(N)
        start = C[i - 1].copy()
        alive = ~np.isnan(c_raw[i])
        pc = C[i - 1]
        lock_up = (O[i] >= pc * (1 + limit - 0.002)) if limit else np.zeros(N, bool)
        lock_dn = (O[i] <= pc * (1 - limit + 0.002)) if limit else np.zeros(N, bool)

        # ---------------- open: exits decided at close i-1
        want = flag_exit.copy()
        if ex.use_signal_exit:
            sx = ((pos > 0) & xL[i - 1]) | ((pos < 0) & xS[i - 1])
            why_exit[sx & ~want] = "signal"
            want |= sx
        rev = ((pos > 0) & eS[i - 1]) | ((pos < 0) & eL[i - 1])
        why_exit[rev & ~want] = "reversal"
        want |= rev
        can = want & (pos != 0) & alive & ~(((pos > 0) & lock_dn) | ((pos < 0) & lock_up))
        for j in np.nonzero(can)[0]:
            contrib[j] += w[j] * pos[j] * (O[i][j] / start[j] - 1)
            traded[j] += w[j]
            finish(j, i, O[i][j], why_exit[j])
            pos[j] = 0; w[j] = 0
        flag_exit &= ~can

        # ---------------- open: entries decided at close i-1
        ok = alive & (pos == 0)
        if need_atr:
            ok &= ~np.isnan(A[i - 1])
        if adv is not None:
            ok &= np.nan_to_num(adv[i]) >= min_adv
        wantL = (eL[i - 1] | pendL) & ok
        wantS = (eS[i - 1] | pendS) & ok & ~wantL
        pendL = wantL & lock_up          # limit-locked order waits for the next open
        pendS = wantS & lock_dn
        cl = wantL & ~lock_up
        cs = wantS & ~lock_dn
        cand = cl | cs
        if cand.any():
            free = slots - int((pos != 0).sum())
            if free <= 0:
                cand[:] = False
            elif cand.sum() > free:
                sc = np.where(cand, np.nan_to_num(np.where(cl, score[i - 1], -score[i - 1]), nan=-np.inf), -np.inf)
                keep = np.argsort(-sc)[:free]
                m = np.zeros(N, bool); m[keep] = True
                cand &= m
            new_side = np.where(cl & cand, 1.0, np.where(cs & cand, -1.0, 0.0))
            nm = new_side != 0
            if nm.any():
                a = A[i - 1]
                risk = np.full(N, np.nan)
                if ex.stop_atr:
                    risk = ex.stop_atr * a
                elif ex.stop_pct:
                    risk = ex.stop_pct * O[i]
                elif ex.stop_swing:
                    risk = np.where(new_side > 0, O[i] - swing_lo[i - 1], swing_hi[i - 1] - O[i])
                    risk = np.where(risk > 0, risk, np.nan)
                # ---- sizing
                if size.mode == "atr_risk":
                    dist = risk / O[i] if np.isfinite(risk).any() else 2 * a / O[i]
                    dist = np.where(np.isfinite(dist) & (dist > 0), dist, 2 * a / O[i])
                    nw = np.minimum(size.risk_pct / dist, size.max_w)
                elif size.mode == "vol":
                    nw = np.minimum(size.vol_target / np.where(vol_a[i - 1] > 0, vol_a[i - 1], np.nan) / slots, size.max_w)
                else:
                    nw = np.full(N, 1.0 / slots)
                nw = np.where(nm, np.nan_to_num(nw), 0.0)
                room = size.max_gross - w.sum()
                if nw.sum() > room:
                    nw *= max(room, 0) / nw.sum() if nw.sum() > 0 else 0
                nm &= nw > 1e-9
                pos[nm] = new_side[nm]; w[nm] = nw[nm]; entry_w[nm] = nw[nm]
                entry_px[nm] = O[i][nm]; entry_i[nm] = i; held[nm] = 0
                ext[nm] = O[i][nm]; mfe[nm] = 0; mae[nm] = 0
                partial_done[nm] = False; realized[nm] = 0; why_exit[nm] = ""
                runit[nm] = risk[nm]
                stop[nm] = (O[i] - pos * risk)[nm]
                t = np.full(N, np.nan)
                if ex.tp_atr:
                    t = O[i] + pos * ex.tp_atr * a
                elif ex.tp_pct:
                    t = O[i] * (1 + pos * ex.tp_pct)
                elif ex.tp_r:
                    t = O[i] + pos * ex.tp_r * risk
                tgt[nm] = t[nm]
                tp1[nm] = (O[i] + pos * ex.partial_r * risk)[nm] if ex.partial_r else np.nan
                start = np.where(nm, O[i], start)
                traded += np.where(nm, w, 0)

        # ---------------- intrabar: stop -> partial -> target
        live = (pos != 0) & alive
        if live.any():
            lg, sh = live & (pos > 0), live & (pos < 0)
            hit_s = (lg & (L[i] <= stop)) | (sh & (H[i] >= stop))
            for j in np.nonzero(hit_s)[0]:
                fill = stop[j] if entry_i[j] == i else (min(O[i][j], stop[j]) if pos[j] > 0 else max(O[i][j], stop[j]))
                contrib[j] += w[j] * pos[j] * (fill / start[j] - 1)
                traded[j] += w[j]
                finish(j, i, fill, "stop" if not (stop[j] == entry_px[j]) else "breakeven")
                pos[j] = 0; w[j] = 0
            live = (pos != 0) & alive
            if ex.partial_r:
                hp = live & ~partial_done & (((pos > 0) & (H[i] >= tp1)) | ((pos < 0) & (L[i] <= tp1)))
                for j in np.nonzero(hp)[0]:
                    fill = tp1[j] if entry_i[j] == i else (max(O[i][j], tp1[j]) if pos[j] > 0 else min(O[i][j], tp1[j]))
                    part = w[j] * ex.partial_frac
                    contrib[j] += part * pos[j] * (fill / start[j] - 1)
                    realized[j] += (part / entry_w[j]) * pos[j] * (fill / entry_px[j] - 1)
                    traded[j] += part
                    w[j] -= part
                    partial_done[j] = True
                    if ex.partial_to_be:
                        stop[j] = entry_px[j] if np.isnan(stop[j]) else (max(stop[j], entry_px[j]) if pos[j] > 0 else min(stop[j], entry_px[j]))
            ht = live & (((pos > 0) & (H[i] >= tgt)) | ((pos < 0) & (L[i] <= tgt)))
            for j in np.nonzero(ht)[0]:
                fill = tgt[j] if entry_i[j] == i else (max(O[i][j], tgt[j]) if pos[j] > 0 else min(O[i][j], tgt[j]))
                contrib[j] += w[j] * pos[j] * (fill / start[j] - 1)
                traded[j] += w[j]
                finish(j, i, fill, "target")
                pos[j] = 0; w[j] = 0

        # ---------------- close: mark, excursions, stop management, flags
        live = pos != 0
        contrib += np.where(live, w * pos * (C[i] / start - 1), 0.0)
        if live.any():
            held[live] += 1
            ext = np.where(live & (pos > 0), np.fmax(ext, H[i]), np.where(live & (pos < 0), np.fmin(ext, L[i]), ext))
            fav = np.where(pos > 0, H[i] / entry_px - 1, 1 - L[i] / entry_px)
            adv_ = np.where(pos > 0, L[i] / entry_px - 1, 1 - H[i] / entry_px)
            mfe = np.where(live, np.fmax(mfe, fav), mfe)
            mae = np.where(live, np.fmin(mae, adv_), mae)
            if ex.be_r:
                gain = pos * (C[i] - entry_px)
                trig = live & np.isfinite(runit) & (gain >= ex.be_r * runit)
                stop = np.where(trig & (pos > 0), np.fmax(stop, entry_px), np.where(trig & (pos < 0), np.fmin(stop, entry_px), stop))
            trail = None
            if ex.trail_atr:
                trail = ext - pos * ex.trail_atr * A[i]
            elif ex.trail_pct:
                trail = ext * (1 - pos * ex.trail_pct)
            if trail is not None:
                stop = np.where(live & (pos > 0), np.fmax(stop, trail), np.where(live & (pos < 0), np.fmin(stop, trail), stop))
            if ma is not None:
                mx = live & (((pos > 0) & (C[i] < ma[i])) | ((pos < 0) & (C[i] > ma[i])))
                why_exit[mx & ~flag_exit] = "ma_trail"
                flag_exit |= mx
            if ex.max_hold:
                tx = live & (held >= ex.max_hold)
                why_exit[tx & ~flag_exit] = "time"
                flag_exit |= tx

        gross_long = w[pos > 0].sum(); gross_short = w[pos < 0].sum()
        carry_cost = (gross_short * carry[0] + (gross_long + gross_short) * carry[1]) / ppy
        port[i] = contrib.sum() - cpt * traded.sum() - carry_cost
        if aret is not None:
            aret[i] = contrib - cpt * traded - (np.where(pos < 0, w, 0) * carry[0] + np.where(pos != 0, w, 0) * carry[1]) / ppy
        turn[i] = traded.sum()
        wts[i] = pos * w

    ret = pd.Series(port, idx)
    tlog = pd.DataFrame(trades, columns=["entry", "exit", "asset", "side", "weight", "entry_px", "exit_px",
                                         "ret", "r_mult", "mfe", "mae", "bars", "reason"])
    held_w = pd.DataFrame(wts, idx, cols)
    first = held_w.abs().sum(axis=1).gt(0)
    s = first.idxmax() if first.any() else idx[0]
    meta = {"trades": tlog, "exit": ex.label(), "size": size.label(),
            "exposure": float((held_w.abs().sum(axis=1) > 0).loc[s:].mean())}
    if aret is not None:
        meta["asset_returns"] = pd.DataFrame(aret, idx, cols)   # full index (not trimmed)
        meta["held_weights"] = held_w
    return Result(ret.loc[s:], ret.loc[s:], held_w.loc[s:], pd.Series(turn, idx).loc[s:], meta=meta)


def trade_stats(tlog: pd.DataFrame, years: float | None = None) -> dict:
    if tlog is None or tlog.empty:
        return {"n_trades": 0}
    r = tlog["ret"]
    wins, losses = r[r > 0], r[r <= 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else None
    wr = float((r > 0).mean())
    payoff = float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) and losses.mean() else None
    kelly = (wr - (1 - wr) / payoff) if payoff else None
    streak = mx = 0
    for x in r.values:
        streak = streak + 1 if x <= 0 else 0
        mx = max(mx, streak)
    out = {
        "n_trades": int(len(r)),
        "trades_per_year": round(len(r) / years, 1) if years else None,
        "win_rate": round(wr, 3),
        "avg_trade": round(float(r.mean()), 4),
        "median_trade": round(float(r.median()), 4),
        "avg_win": round(float(wins.mean()), 4) if len(wins) else None,
        "avg_loss": round(float(losses.mean()), 4) if len(losses) else None,
        "profit_factor": round(float(pf), 3) if pf is not None else None,
        "payoff": round(payoff, 3) if payoff else None,
        "expectancy_r": round(float(tlog["r_mult"].mean()), 3) if tlog["r_mult"].notna().any() else None,
        "sqn": round(float(tlog["r_mult"].mean() / tlog["r_mult"].std() * np.sqrt(min(len(r), 100))), 2)
        if tlog["r_mult"].notna().sum() > 5 and tlog["r_mult"].std() > 0 else None,
        "kelly_fraction": round(float(kelly), 3) if kelly is not None else None,
        "max_consec_losses": int(mx),
        "avg_bars": round(float(tlog["bars"].mean()), 1),
        "avg_bars_win": round(float(tlog.loc[r > 0, "bars"].mean()), 1) if len(wins) else None,
        "avg_bars_loss": round(float(tlog.loc[r <= 0, "bars"].mean()), 1) if len(losses) else None,
        "avg_mfe": round(float(tlog["mfe"].mean()), 4),
        "avg_mae": round(float(tlog["mae"].mean()), 4),
        "edge_ratio": round(float(tlog["mfe"].mean() / abs(tlog["mae"].mean())), 3) if tlog["mae"].mean() < 0 else None,
        "exit_reasons": tlog["reason"].value_counts().to_dict(),
        "long_short": tlog.groupby("side")["ret"].agg(["count", "mean"]).round(4).to_dict("index"),
    }
    return out
