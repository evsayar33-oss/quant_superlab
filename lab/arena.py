"""Strategy arena: ~100 strategies tracked on paper, every closed bar, plus the regime switcher.

Files (all small, on main):
  decisions/arena/<tf>/roster.json   members with FROZEN settings and the date they joined (ids never reused)
  decisions/arena/switcher_gate.json backtest part of the switcher gate (written by the monthly screen)
  decisions/arena/switcher.json      what the switcher holds NOW + regime per coin + gate status (bots read this)
  decisions/arena/state.json         positions at the last run (to report changes once)
  decisions/arena/screen_summary.json last funnel table (dashboard)

Forward (paper) record: every run recomputes each member on fresh data with its frozen settings and
keeps only the bars AFTER it joined. Everything is causal, so this equals trading it live on closed bars.
Members are never re-fit. A member is retired (no longer chosen by the switcher) when:
  * its forward drawdown is worse than dd_mult x its backtest drawdown (any time), or
  * after min_forward_days its forward Sharpe is below min_forward_sharpe.
Retired members keep being tracked (status "retired") so the record stays complete.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from lab import metrics, perp, regime, screen, switcher
from lab.engine import Costs
from lab.panel import Panel
from lab.trade_engine import EXIT_GRID

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "decisions" / "arena"
DIR = BASE / "4h"
ROSTER = STATE = SWITCH = GATE = SUMMARY = DIR


def use(tf: str) -> None:
    """Each timeframe has its own arena: decisions/arena/<tf>/ (own roster, switcher, state)."""
    global DIR, ROSTER, STATE, SWITCH, GATE, SUMMARY
    DIR = BASE / tf
    ROSTER, STATE, SWITCH, GATE, SUMMARY = (DIR / n for n in
                                            ("roster.json", "state.json", "switcher.json", "switcher_gate.json",
                                             "screen_summary.json"))


use("4h")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return default


def _write(p: Path, obj) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=str, ensure_ascii=False))


def _params(d: dict) -> dict:
    """JSON turns tuples into lists; the rule functions expect the original tuples."""
    return {k: tuple(v) if isinstance(v, list) else v for k, v in (d or {}).items()}


def member_key(coin, rule, params: dict, exit_id, side, tf, filt: str = "none", confirm: dict | None = None) -> str:
    k = f"{coin}|{rule}|{screen.fmt(_params(params))}|x={exit_id}|{side}|{tf}"
    if filt and filt != "none":
        k += f"|f={filt}"
    if confirm:
        k += f"|c={confirm['rule']}:{screen.fmt(_params(confirm.get('params') or {}))}:{confirm.get('within', 0)}"
    return k


# ------------------------------------------------------------------ roster
def update_roster(res: dict, cfg: dict) -> tuple[dict, str]:
    """Merge funnel survivors into the roster. Existing members keep their id, settings and join date."""
    from lab import rules as RL
    ac = cfg.get("arena", {})
    cap = int(ac.get("max_members", 100))
    ro = _read(ROSTER, None) or {"universe": cfg["universe"], "timeframe": cfg["timeframe"],
                                 "start": cfg.get("start", "2018-01-01"), "created_at": now_iso(),
                                 "next_id": 1, "members": []}
    if ro.get("universe") != cfg["universe"]:
        for m in ro["members"]:          # config changed: old members stop, record is kept
            if m["status"] != "retired":
                m.update(status="retired", retired_at=now_iso(), why="arena config changed")
        ro.update(universe=cfg["universe"], timeframe=cfg["timeframe"], created_at=now_iso())
    keys = {m["key"]: m for m in ro["members"]}
    ranked = sorted(res["rows"].values(), key=screen.rank_key)
    added, promoted = 0, 0

    def grid_params(row):
        return dict(row["spec"]["params"])

    def n_live():
        return sum(1 for m in ro["members"] if m["status"] in ("active", "control"))

    seen: set = set()      # one variant per (coin, rule) per screen: the best-ranked one
    for want_tier, status in (("ok", "active"), ("near", "control")):
        for row in ranked:
            if (row["coin"], row["rule"]) in seen:
                continue
            is_ok = row["stage"] == "OK"
            if (want_tier == "ok") != is_ok:
                continue
            if want_tier == "near" and (not ac.get("fill_controls", True) or row["stage"] in ("S0", "S1", None)):
                continue
            seen.add((row["coin"], row["rule"]))
            prm = grid_params(row)
            sp = row["spec"]
            k = member_key(row["coin"], row["rule"], prm, sp["exit_id"], cfg["side"], cfg["timeframe"],
                           sp.get("filter", "none"), sp.get("confirm"))
            bt = {"card": row["card"], "sharpe": row["sharpe"], "max_dd": row["max_dd"], "dsr": row.get("dsr"),
                  "stage": row["stage"], "why": row["why"], "tier": row.get("tier"), "screened_at": now_iso()}
            if k in keys:
                m = keys[k]
                m["backtest"] = bt
                if m["status"] == "control" and status == "active":
                    m["status"] = "active"; promoted += 1
                continue
            if n_live() >= cap:
                if status == "active":   # a survivor replaces the weakest control member
                    ctl = [m for m in ro["members"] if m["status"] == "control"]
                    if not ctl:
                        continue
                    weakest = min(ctl, key=lambda m: m["backtest"].get("sharpe") or 0)
                    weakest.update(status="retired", retired_at=now_iso(), why="replaced by a funnel survivor")
                else:
                    continue
            mid = f"A{ro['next_id']:04d}"
            ro["next_id"] += 1
            m = {"id": mid, "key": k, "coin": row["coin"], "rule": row["rule"], "params": prm,
                 "exit_id": sp["exit_id"], "filter": sp.get("filter", "none"), "confirm": sp.get("confirm"),
                 "stage_no": row.get("stage_no", 1), "side": cfg["side"], "timeframe": cfg["timeframe"],
                 "status": status, "added_at": now_iso(), "backtest": bt}
            ro["members"].append(m)
            keys[k] = m
            added += 1
    ro["updated_at"] = now_iso()
    _write(ROSTER, ro)
    act = sum(1 for m in ro["members"] if m["status"] == "active")
    ctl = sum(1 for m in ro["members"] if m["status"] == "control")
    note = (f"Arena: {act} aktif (eleme geçen), {ctl} kontrol (yakın aday, switcher kullanmaz), "
            f"{added} yeni üye, {promoted} kontrolden aktife. Üst sınır {cap}.")
    return ro, note


# ------------------------------------------------------------------ compute
def compute(ro: dict, p: Panel, costs: Costs, members: list[dict] | None = None):
    """Recompute every member with its frozen settings. Returns R (stand-alone 1x returns),
    X (signed exposure), trades per member id."""
    members = members if members is not None else ro["members"]
    groups: dict[tuple, list[dict]] = {}
    for m in members:
        if m["coin"] not in p.columns:
            continue
        spec = {"rule": m["rule"], "params": m["params"], "exit_id": m["exit_id"],
                "filter": m.get("filter", "none"), "confirm": m.get("confirm")}
        groups.setdefault((json.dumps(spec, sort_keys=True, default=str), m["side"]), []).append(m)
    R, X, T = {}, {}, {}
    for (sj, side), ms in groups.items():
        coins = sorted({m["coin"] for m in ms})
        r, x, tr = screen.run_spec(screen.subpanel(p, coins), json.loads(sj), side, costs)
        for m in ms:
            R[m["id"]] = r[m["coin"]]
            X[m["id"]] = x[m["coin"]]
            T[m["id"]] = tr[tr["asset"] == m["coin"]] if len(tr) else tr
    return pd.DataFrame(R), pd.DataFrame(X), T


def member_regimes(reg: pd.DataFrame, ids: list[str], coin_of: dict) -> pd.DataFrame:
    return pd.DataFrame({i: reg[coin_of[i]] for i in ids if coin_of[i] in reg.columns}, index=reg.index)


def regime_sharpe(r: pd.Series, g: pd.Series) -> dict:
    """Sharpe of a member inside each regime (returns of bar t credited to the regime known at t-1)."""
    gp = g.shift(1).reindex(r.index)
    out = {}
    for k in regime.CODES:
        x = r[gp == k].dropna()
        out[regime.NAMES[k]] = round(metrics.sharpe(x), 2) if len(x) > 30 else None
    return out


def _eligible(ro: dict, R: pd.DataFrame, forward: bool) -> pd.DataFrame:
    E = pd.DataFrame(True, index=R.index, columns=R.columns)
    for m in ro["members"]:
        if m["id"] not in E.columns:
            continue
        if m["status"] == "control":
            E[m["id"]] = False
            continue
        if forward:
            a = pd.Timestamp(m["added_at"]).tz_localize(None)
            E.loc[E.index < a, m["id"]] = False
        if m["status"] == "retired" and m.get("retired_at"):
            z = pd.Timestamp(m["retired_at"]).tz_localize(None)
            E.loc[E.index >= z, m["id"]] = False
    return E


def gate_backtest(ro: dict, p: Panel, costs: Costs, cfg: dict) -> dict:
    """Monthly (screen job): switcher grid backtest vs equal weight, plus the cost-stress check."""
    sw = cfg.get("switcher", {})
    pool = [m for m in ro["members"] if m["status"] == "active" or (sw.get("pool") == "all" and m["status"] == "control")]
    if not pool:
        out = {"backtest_pass": False, "reason": "no active members", "checked_at": now_iso()}
        _write(GATE, out)
        return out
    R, X, _ = compute(ro, p, costs, pool)
    st = cfg.get("screen", {}).get("cost_stress", 2.0)
    Rs, _, _ = compute(ro, p, Costs(costs.commission * st, costs.slippage * st, costs.borrow_annual,
                                    costs.funding_annual), pool)
    coin_of = {m["id"]: m["coin"] for m in pool}
    reg = regime.classify(p, cfg.get("regime", {}))
    G = member_regimes(reg, list(R.columns), coin_of)
    alive = pd.DataFrame({i: p.c[coin_of[i]].notna() for i in R.columns})
    ev = switcher.evaluate(R.fillna(0), G, X, coin_of, alive, p.ppy, costs.per_turnover,
                           {**sw, "cost_stress": st}, cfg.get("report_windows_years", [3, 5, 0]), Rs.fillna(0))
    out = {k: v for k, v in ev.items() if k not in ("returns", "equal_weight")}
    out.update(checked_at=now_iso(), pool=len(pool),
               spark=perp.sparkline(ev["returns"]), spark_ew=perp.sparkline(ev["equal_weight"]))
    _write(GATE, out)
    return out


# ------------------------------------------------------------------ the 4-hourly run
def run(p: Panel, costs: Costs, cfg: dict) -> dict:
    ro = _read(ROSTER, None)
    if not ro or not ro.get("members"):
        return {"error": "roster is empty: run the screen first (python run.py --screen)"}
    ppy = p.ppy
    metrics.set_periods(ppy)
    ac, sw = cfg.get("arena", {}), cfg.get("switcher", {})
    R, X, T = compute(ro, p, costs)
    coin_of = {m["id"]: m["coin"] for m in ro["members"]}
    reg = regime.classify(p, cfg.get("regime", {}))
    G = member_regimes(reg, list(R.columns), coin_of)
    end = p.index[-1]
    cps, fund = costs.per_turnover, costs.funding_annual
    windows = cfg.get("report_windows_years", [3, 5, 0])

    # ---- forward record, retirement
    ret_cfg = ac.get("retire", {})
    members_out = []
    changed = False
    for m in ro["members"]:
        i = m["id"]
        if i not in R.columns:
            continue
        r = R[i].dropna()
        a = pd.Timestamp(m["added_at"]).tz_localize(None)
        f = r[r.index > a]
        days = (end - a).days if end > a else 0
        fwd = {"days": int(days), "bars": int(len(f)), "ret": round(float((1 + f).prod() - 1), 4) if len(f) else 0.0,
               "sharpe": round(metrics.sharpe(f), 3) if len(f) > 20 else None,
               "max_dd": round(metrics.max_drawdown(f), 4) if len(f) else 0.0,
               "trades": int((T[i]["entry"] > a).sum()) if len(T[i]) else 0}
        if m["status"] == "active":
            bt_dd = (m.get("backtest") or {}).get("max_dd") or -0.2
            why = None
            if len(f) > 20 and fwd["max_dd"] < ret_cfg.get("dd_mult", 1.5) * bt_dd:
                why = f"ileri düşüş {fwd['max_dd']:.0%} < {ret_cfg.get('dd_mult', 1.5)}× backtest ({bt_dd:.0%})"
            elif days >= ret_cfg.get("min_forward_days", 120) and (fwd["sharpe"] or 0) < ret_cfg.get("min_forward_sharpe", 0.0):
                why = f"{days} gün sonra ileri Sharpe {fwd['sharpe']}"
            if why:
                m.update(status="retired", retired_at=now_iso(), why=why)
                changed = True
                print(f"[arena] retired {i}: {why}")
        x = X[i]
        pos = float(x.iloc[-1]) if len(x) else 0.0
        members_out.append({
            "id": i, "coin": m["coin"], "rule": m["rule"], "params": screen.fmt(_params(m["params"])),
            "exit": EXIT_GRID[m["exit_id"]].label(), "side": m["side"], "status": m["status"],
            "variant": screen.spec_label({"exit_id": m["exit_id"], "filter": m.get("filter", "none"),
                                          "confirm": m.get("confirm")}), "stage_no": m.get("stage_no", 1),
            "tier": (m.get("backtest") or {}).get("tier"), "added_at": m["added_at"][:10], "why": m.get("why", ""),
            "position": "long" if pos > 1e-9 else ("short" if pos < -1e-9 else "flat"), "exposure": round(pos, 3),
            "forward": fwd, "card": perp.card(r, T[i], ppy, windows, cfg.get("account", {}), cps, fund),
            "regime_sharpe": regime_sharpe(r, G[i]) if i in G.columns else {},
            "regime_now": regime.NAMES[int(G[i].iloc[-1])] if i in G.columns else "unknown",
            "spark": perp.sparkline(r), "spark_fwd": perp.sparkline(f, 60),
        })
    if changed:                 # the roster is rewritten only when a member's status changes (small git history)
        ro["updated_at"] = now_iso()
        _write(ROSTER, ro)

    # ---- switcher: current picks (backtest-trained) + forward record (eligibility from join date)
    pool_ids = [m["id"] for m in ro["members"] if m["id"] in R.columns and m["status"] != "control"]
    Rp, Xp, Gp = R[pool_ids].fillna(0), X[pool_ids], G.reindex(columns=pool_ids)
    d = sw.get("default", {"halflife_days": 30, "top_k": 5})
    base = switcher.params_of(sw)
    act = {m["id"] for m in ro["members"] if m["status"] == "active"}
    e_now = pd.DataFrame({i: i in act for i in pool_ids}, index=Rp.index)   # today: only active members
    live_now = switcher.run(Rp, Gp, Xp, coin_of, ppy, cps, **d, **base, eligible=e_now) if pool_ids else None
    fwd_run = switcher.run(Rp, Gp, Xp, coin_of, ppy, cps, **d, **base,
                           eligible=_eligible(ro, Rp, forward=True)) if pool_ids else None
    since = pd.Timestamp(ro.get("created_at")).tz_localize(None)
    alive = pd.DataFrame({i: p.c[coin_of[i]].notna() for i in pool_ids}, index=Rp.index)
    elig_f = _eligible(ro, Rp, forward=True)
    ew_f = switcher.equal_weight(Rp, alive & elig_f) if pool_ids else pd.Series(dtype=float)
    sf = fwd_run["returns"][fwd_run["returns"].index > since] if fwd_run else pd.Series(dtype=float)
    ef = ew_f[ew_f.index > since] if len(ew_f) else ew_f
    gate = _read(GATE, {})
    gcfg = sw.get("gate", {})
    fwd_days = max(0, (end - since).days)
    f_sr, e_sr = (metrics.sharpe(sf) if len(sf) > 20 else None), (metrics.sharpe(ef) if len(ef) > 20 else None)
    checks = {"backtest_gate": bool(gate.get("backtest_pass")),
              "forward_days": fwd_days >= gcfg.get("min_forward_days", 180),
              "forward_beats_equal_weight": f_sr is not None and e_sr is not None and f_sr > e_sr}
    picks = []
    if live_now:
        for i, w in sorted(live_now["current"].items(), key=lambda kv: -kv[1]):
            mo = next(x for x in members_out if x["id"] == i)
            m = next(x for x in ro["members"] if x["id"] == i)
            picks.append({"id": i, "coin": m["coin"], "rule": m["rule"], "params": _params(m["params"]),
                          "exit_id": m["exit_id"], "filter": m.get("filter", "none"), "confirm": m.get("confirm"), "side": m["side"], "timeframe": m["timeframe"],
                          "weight": w, "position": mo["position"], "regime": mo["regime_now"]})
    sw_out = {"updated_at": now_iso(), "data_end": str(end), "universe": ro["universe"], "timeframe": ro["timeframe"],
              "usable": all(checks.values()), "checks": checks, "settings": d,
              "cash": round(1 - sum(x["weight"] for x in picks), 4), "picks": picks,
              "forward": {"since": str(since.date()), "days": fwd_days,
                          "ret": round(float((1 + sf).prod() - 1), 4) if len(sf) else 0.0,
                          "sharpe": round(f_sr, 3) if f_sr is not None else None,
                          "ew_ret": round(float((1 + ef).prod() - 1), 4) if len(ef) else 0.0,
                          "ew_sharpe": round(e_sr, 3) if e_sr is not None else None,
                          "max_dd": round(metrics.max_drawdown(sf), 4) if len(sf) else 0.0},
              "regimes": regime.summary(reg)}
    # write only on a real change, or once a day as a heartbeat (bots need a fresh file) -> few commits
    old = _read(SWITCH, {})
    def core(x):
        return json.dumps({"usable": x.get("usable"), "checks": x.get("checks"), "picks": x.get("picks"),
                           "regimes": {c: v.get("now") for c, v in (x.get("regimes") or {}).items()}},
                          sort_keys=True, default=str)
    if core(old) != core(sw_out) or str(old.get("updated_at", ""))[:10] != now_iso()[:10]:
        _write(SWITCH, sw_out)

    # ---- changes since the last run (for Telegram)
    st = _read(STATE, {})
    prev_pos, prev_w = st.get("positions", {}), st.get("switcher", {})
    events = []
    held = {x["id"] for x in picks} | set(prev_w)
    notify = ac.get("notify", "switcher")
    for mo in members_out:
        old = prev_pos.get(mo["id"], "flat")
        if mo["position"] != old and (notify == "all" or (notify == "switcher" and mo["id"] in held)):
            events.append(f"{mo['id']} {mo['coin']} {mo['rule']}: {old} → {mo['position']}")
    new_w = {x["id"]: x["weight"] for x in picks}
    for i in sorted(set(new_w) | set(prev_w)):
        if abs(new_w.get(i, 0) - prev_w.get(i, 0)) > 1e-6:
            events.append(f"switcher {i}: ağırlık {prev_w.get(i, 0):.0%} → {new_w.get(i, 0):.0%}")
    last_bar = st.get("last_bar")
    new_bar = str(end) != last_bar
    hour = datetime.now(timezone.utc).hour
    today = datetime.now(timezone.utc).date().isoformat()
    summary_due = hour >= ac.get("daily_summary_hour_utc", 20) and st.get("last_summary") != today
    new_st = {"positions": {x["id"]: x["position"] for x in members_out}, "switcher": new_w,
              "last_summary": today if summary_due else st.get("last_summary")}
    if any(new_st[k] != st.get(k) for k in new_st):      # unchanged positions -> no write, no commit
        _write(STATE, {**new_st, "last_bar": str(end), "updated_at": now_iso()})
    books_out = []
    if cfg.get("timeframe") in (cfg.get("books", {}).get("timeframes") or []):
        from lab import books as BK
        try:
            bdata = BK.ensure(DIR / "books.json", ro, cfg)
            books_out = BK.report(bdata, R, X, ro, p, cps, cfg)
        except Exception as e:  # noqa: BLE001 - books are a report; they must not stop the arena
            print(f"[arena] books failed: {e}")
    # ---- H052 manual-trading signal: target share of capital per coin (only on the H052 timeframe)
    h052 = None
    sig_id, sig_cfg = next(iter((cfg.get("signals") or {}).items()), (None, {}))
    if sig_cfg.get("enabled") and cfg.get("timeframe") == sig_cfg.get("timeframe", "4h"):
        try:
            from lab import core as CORE
            import yaml as _y
            ccfg = _y.safe_load((ROOT / "config" / "core.yaml").read_text())
            prm = ccfg["rules"]["dual_trend_vt"]
            assets = [x for x in sig_cfg.get("assets", ["BTC/USDT", "ETH/USDT"]) if x in p.columns]
            band = float(sig_cfg.get("band", 0.0))
            tgt = {x: round(float(CORE.apply_band(CORE.exposure(p.c[x], "dual_trend_vt", prm, ppy), band).iloc[-1]) / len(assets), 3)
                   for x in assets}
            reg = _read(ROOT / "decisions" / "registry.json", {}).get("hypotheses", {}).get(sig_id, {})
            prev = (st.get("h052") or {}) if isinstance(st, dict) else {}
            moves = {x: round(tgt[x] - prev.get(x, 0.0), 3) for x in assets}
            h052 = {"id": sig_id, "targets": tgt, "verdict": reg.get("verdict"), "bar": str(end)}
            if any(abs(v) >= sig_cfg.get("min_change", 0.05) for v in moves.values()):
                txt = ", ".join(f"{x.split('/')[0]} %{tgt[x] * 100:.0f} ({moves[x] * 100:+.0f})" for x in assets)
                events.append(f"🎯 {sig_id} [{reg.get('verdict', '?')}] hedef (kasanın %'si): {txt}; kalan nakit "
                              f"%{(1 - sum(tgt.values())) * 100:.0f}. Bir sonraki bar açılışında uygulanır.")
                stx = _read(STATE, {})
                stx["h052"] = tgt
                _write(STATE, stx)
        except Exception as e:  # noqa: BLE001
            print(f"[arena] H052 signal failed: {e}")
    prev_b = st.get("book_status", {}) if isinstance(st, dict) else {}
    cur_b = {b["id"]: (b.get("band_status") or {}).get("status") for b in books_out}
    for b in books_out:
        if cur_b[b["id"]] == "below" and prev_b.get(b["id"]) != "below":
            events.append(f"⚠️ portföy {b['id']} ({b['name']}) beklenen aralığın altına düştü: {b['forward']['ret']:+.1%}")
    if cur_b != prev_b and books_out:
        stx = _read(STATE, {})
        stx["book_status"] = cur_b
        _write(STATE, stx)
    return {"members": members_out, "switcher": sw_out, "gate": gate, "events": events if new_bar else [],
            "books": books_out, "h052": h052,
            "summary_due": summary_due, "regimes": sw_out["regimes"], "data_end": str(end),
            "spark_switch_fwd": perp.sparkline(sf, 90), "spark_ew_fwd": perp.sparkline(ef, 90)}


def telegram_text(out: dict, summary: bool) -> str:
    sw = out["switcher"]
    L = []
    if out["events"]:
        L.append("🏟️ quant_lab arena — yeni bar " + out["data_end"][:16])
        L += [f"• {e}" for e in out["events"][:25]]
    if summary:
        f = sw["forward"]
        L.append(f"📊 Arena günlük özet ({sw['timeframe']})")
        L.append(f"Switcher {'✅ kullanılabilir' if sw['usable'] else '🧪 paper (kapı geçmedi)'} — "
                 f"ileri {f['ret']:+.1%} (SR {f['sharpe']}) vs eşit ağırlık {f['ew_ret']:+.1%} (SR {f['ew_sharpe']}), "
                 f"{f['days']} gün")
        for x in sw["picks"]:
            L.append(f"  {x['id']} {x['coin']} {x['rule']} {x['weight']:.0%} [{x['regime']}] {x['position']}")
        L.append(f"  nakit {sw['cash']:.0%}")
        if out.get("h052"):
            h = out["h052"]
            L.append(f"🎯 {h.get('id')} hedef: " + ", ".join(f"{k.split('/')[0]} %{v * 100:.0f}" for k, v in h["targets"].items())
                     + f" · nakit %{(1 - sum(h['targets'].values())) * 100:.0f} [{h.get('verdict')}]")
        for b in out.get("books") or []:
            f = b["forward"]
            bs = (b.get("band_status") or {}).get("text", "")
            L.append(f"📒 {b['id']} {b['name']}: ${f['balance_1000']:,.0f} ({f['ret']:+.1%}, düşüş {f['max_dd']:.0%}, {f['days']} gün) — {bs}")
        act = [m for m in out["members"] if m["status"] == "active"]
        top = sorted(act, key=lambda m: -(m["forward"]["ret"]))[:5]
        if top:
            L.append("En iyi ileri kayıt: " + ", ".join(f"{m['id']} {m['coin']} {m['forward']['ret']:+.1%}" for m in top))
    return "\n".join(L)
