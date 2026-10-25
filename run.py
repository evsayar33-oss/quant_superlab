"""quant_lab command line.

  python run.py --list                          catalog: strategies, rules, filters, exits, universes, hypotheses
  python run.py --hypothesis H001               validate one registered hypothesis (writes the decision)
  python run.py --all                           validate every active hypothesis
  python run.py --strategy xs_momentum --universe bist30           ad-hoc weight strategy (no decision)
  python run.py --rule rsi_reversal --universe bist30 [--filters all] [--exits all] [--side both]
                                                ad-hoc entry/exit rule (no decision)
  python run.py --scan --universe bist30 [--families all|rules|strategies|factors] [--filters none,trend_sma200]
                                                try everything, rank honestly, suggest hypotheses
  python run.py --synthetic [--rule NAME | --strategy NAME]        offline smoke test
  python run.py --screen [--telegram]           arena screening funnel (config/arena.yaml): roster + switcher gate
  python run.py --arena [--site site] [--telegram]
                                                arena paper run on the latest closed bar + switcher + dashboard
Options: --start YYYY-MM-DD  --telegram (needs TELEGRAM_TOKEN, CHAT_ID)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import yaml

from lab import data, decision, rules, validation
from lab.engine import Costs
from lab.panel import Panel
from lab.strategies import REGISTRY
from lab.trade_engine import EXIT_GRID

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
ICON = {"ACCEPT": "✅", "WATCH": "🟡", "REJECT": "❌", "NO_DATA": "⚪", "ERROR": "⚠️", "DEGRADED": "🔻"}


def load_yaml(p: str):
    return yaml.safe_load((ROOT / p).read_text())


def universe(name: str) -> dict:
    u = load_yaml("config/universes.yaml")
    if name not in u:
        sys.exit(f"Unknown universe '{name}'. Known: {sorted(u)}")
    return u[name]


def get_panel(spec: dict, synthetic: bool) -> tuple[Panel, Costs]:
    if synthetic:
        return Panel.from_close(data.synthetic_prices(15, 2600, seed=11)), Costs()
    u = universe(spec["universe"])
    if spec.get("tickers"):          # a hypothesis may test a subset of a universe (e.g. one coin)
        u = {**u, "tickers": list(spec["tickers"])}
    tf = spec.get("timeframe", "1d")
    p = data.load_panel(u, spec.get("start", "2012-01-01"), spec["universe"], timeframe=tf)
    return p, Costs(**u.get("costs", {}))


def _fmt_dict(d) -> str:
    return json.dumps(d, default=str, ensure_ascii=False)


def report_md(hid: str, spec: dict, rep: dict, charts: dict) -> str:
    o, b = rep["oos"], rep["benchmark"]
    what = spec.get("rule") or spec.get("strategy")
    L = [
        f"# {hid} — {what} on {spec.get('universe', 'synthetic')} [{rep['timeframe']}]  {ICON[rep['verdict']]} {rep['verdict']}",
        "",
        f"- Kind: {rep['kind']} · Source: {rep['source']}",
        f"- For system: `{spec.get('for_system', '-')}`",
        f"- Data: {rep['data_start']} → {rep['data_end']} · {rep['n_assets']} assets · {rep['bars_per_year']} bars/year"
        f" · survivorship mask: {rep['survivorship_mask']}",
        f"- Costs: {rep['costs']}",
        f"- Variants tried (DSR trials): {rep['n_trials']} (failed: {rep['failed_variants']})",
        f"- Final variant: `{rep['final_variant']}`",
        "",
        "## Verdict reasons", *[f"- {r}" for r in rep["reasons"]],
        "",
        "## Walk-forward out-of-sample",
    ]
    if charts.get("equity"):
        L += [f"![equity](charts/{charts['equity']})", ""]
    L += ["| Metric | Strategy | Equal-weight benchmark |", "|---|---|---|",
          *[f"| {k} | {o.get(k)} | {b.get(k)} |" for k in
            ["years", "cagr", "vol", "sharpe", "sharpe_excess_rf", "sortino", "max_dd", "max_dd_bars", "calmar",
             "ulcer", "var95", "cvar95", "omega", "tail_ratio", "skew", "kurtosis", "hit_rate", "turnover_ann"]],
          "",
          f"- **Gate Sharpe ({rep['gate_sharpe_basis']}): {rep['gate_sharpe']}**",
          f"- Deflated Sharpe: **{rep['dsr']}** · PBO: **{rep['pbo']}** · Reality Check p: **{rep['reality_check_p']}**",
          f"- PSR {o.get('psr')} · Info ratio {o.get('info_ratio')} · Beta {o.get('beta')} · Up/Down capture {o.get('up_capture')}/{o.get('down_capture')}",
          f"- Sharpe with 2× costs: {rep['stress_2x_cost']['sharpe']} · Walk-forward efficiency: {rep['wf_efficiency']}",
          f"- Bootstrap: {rep['bootstrap']}",
          f"- Yearly OOS Sharpe: {rep['yearly_sharpe']}"]
    if rep.get("oos_usd"):
        u = rep["oos_usd"]
        L.append(f"- In USD: CAGR {u['cagr']} · Sharpe {u['sharpe']} · excess-rf Sharpe {u['sharpe_excess_rf']} · MaxDD {u['max_dd']}")
    if charts.get("monthly"):
        L += ["", f"![monthly](charts/{charts['monthly']})"]
    L += ["", "## Regimes (where does it work?)", f"`{_fmt_dict(rep['regimes'])}`",
          "", "## Calendar profile (weekday / month / hour)", f"`{_fmt_dict(rep['calendar'])}`"]
    if rep.get("trade_stats"):
        L += ["", "## Trades (OOS)", f"`{_fmt_dict(rep['trade_stats'])}`"]
    if rep.get("robustness"):
        L += ["", "## Robustness"] + [f"- **{k}**: `{_fmt_dict(v)}`" for k, v in rep["robustness"].items()]
    st = rep.get("studies") or {}
    if st:
        L += ["", "## Timing, take-profit, stop-loss and profit studies (in-sample diagnostics)"]
        if "event_study_long" in st:
            L.append(f"- Event study (forward return by bars held): `{_fmt_dict(st['event_study_long'])}`")
            if charts.get("hold"):
                L.append(f"![hold](charts/{charts['hold']})")
        if "event_study_short" in st:
            L.append(f"- Event study short: `{_fmt_dict(st['event_study_short'])}`")
        if "exit_grid_long" in st:
            L.append(f"- Best stop / target / max-hold combinations: `{_fmt_dict(st['exit_grid_long'].get('top', [])[:5])}`")
            if charts.get("exit"):
                L.append(f"![exit](charts/{charts['exit']})")
        if "overlays" in st:
            L.append(f"- Portfolio overlays (vol target, drawdown brake, equity-curve filter): `{_fmt_dict(st['overlays'])}`")
        L.append("> Studies are in-sample diagnostics. To use a better exit, register it (exits: [...]) and let the gate judge it.")
    if rep.get("protection") and not rep["protection"].get("error"):
        from lab import protect
        L += protect.markdown_series(rep["protection"])
    L += ["", "## Walk-forward windows", *[f"- {w['test_start']} → {w['test_end']}: IS {w['is_sharpe']} / OOS {w['oos_sharpe']} — `{w['variant']}`" for w in rep["walk_forward"][-12:]],
          "", "## Best variants (full sample, reference only)",
          *[f"- {r['variant']}: Sharpe {r['sharpe']}" for r in rep["full_sample_top"][:10]],
          "", "## Current targets / signals", "```json", json.dumps(rep["targets"], indent=1, default=str), "```",
          "", "> Survivorship bias: unless a membership mask is used, universes are today's members (upper-bound results)."]
    return "\n".join(L)


def telegram(text: str) -> None:
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("CHAT_ID")
    if not tok or not chat:
        print("[telegram] TELEGRAM_TOKEN/CHAT_ID not set, skipped")
        return
    for i in range(0, len(text), 3900):
        body = urllib.parse.urlencode({"chat_id": chat, "text": text[i:i + 3900]}).encode()
        try:
            urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", body, timeout=15)
        except Exception as e:  # noqa: BLE001
            print(f"[telegram] failed: {e}")


def make_charts(stem: str, rep: dict) -> dict:
    from lab import charts as CH, metrics
    out = {}
    d = RESULTS / "charts"
    d.mkdir(parents=True, exist_ok=True)
    try:
        r = rep["_oos_returns"]
        if len(r) > 30:
            out["equity"] = CH.equity_dd(r, rep.get("_bench_oos"), d / f"{stem}_equity.png", f"{stem} — OOS equity")
            if rep["timeframe"] in ("1d", "1h", "4h", "1w"):
                out["monthly"] = CH.monthly_heatmap(metrics.monthly_table(r), d / f"{stem}_monthly.png")
        es = (rep.get("studies") or {}).get("event_study_long")
        if es:
            out["hold"] = CH.holding_curve(es, d / f"{stem}_hold.png")
        if rep.get("_exit_table") is not None:
            out["exit"] = CH.exit_heatmap(rep["_exit_table"], d / f"{stem}_exit.png")
    except Exception as e:  # noqa: BLE001 - charts must never break a validation
        print(f"[charts] {e}")
    return {k: v for k, v in out.items() if v}


def run_one(hid: str, spec: dict, write_registry: bool, synthetic: bool = False) -> dict:
    p, costs = get_panel(spec, synthetic)
    p.c = p.c.dropna(axis=1, how="all")
    if p.c.shape[1] == 0 or len(p.c) < 600:
        print(f"[{hid}] not enough data ({p.c.shape}) — skipped")
        return {"verdict": "NO_DATA", "reasons": ["not enough price history"]}
    rep = validation.validate(spec, p, costs, float(spec.get("train_years", 3)), int(spec.get("test_months", 6)))
    RESULTS.mkdir(exist_ok=True)
    stem = f"{hid}_{spec.get('rule') or spec.get('strategy')}_{spec.get('universe', 'synthetic')}_{spec.get('timeframe', '1d')}"
    charts = make_charts(stem, rep)
    (RESULTS / f"{stem}.md").write_text(report_md(hid, spec, rep, charts))
    rep["_oos_returns"].rename("oos_return").to_csv(RESULTS / f"{stem}_oos.csv")
    clean = {k: v for k, v in rep.items() if not k.startswith("_")}
    (RESULTS / f"{stem}.json").write_text(json.dumps(clean, indent=2, default=str))
    if write_registry:
        decision.record(hid, spec, rep, rep["targets"], oos_csv=f"results/{stem}_oos.csv")
        (RESULTS / f"{hid}_ERROR.txt").unlink(missing_ok=True)
    o = rep["oos"]
    print(f"[{hid}] {rep['verdict']}  OOS Sharpe={o.get('sharpe')} CAGR={o.get('cagr')} MaxDD={o.get('max_dd')} "
          f"DSR={rep['dsr']} PBO={rep['pbo']} trials={rep['n_trials']}")
    return rep


def summary_text(reg: dict) -> str:
    lines = ["🧭 quant_lab decisions"]
    for hid, h in sorted(reg["hypotheses"].items()):
        lines.append(f"{ICON.get(h['verdict'], '🔻')} {hid} {h['strategy']} {h['universe']}/{h.get('timeframe')} "
                     f"SR {h.get('gate_sharpe')} DSR {h.get('dsr')} → {h.get('for_system')}")
    for s, v in reg.get("systems", {}).items():
        lines.append(f"🤖 {s}: {v['allocation']} ({v['method']})")
    return "\n".join(lines)


def do_scan(a) -> None:
    from lab import scanner
    filters = [f for f in a.filters.split(",") if f] if a.filters != "all" else list(rules.FILTERS)
    spec = {"universe": a.universe or "synthetic", "start": a.start, "timeframe": a.timeframe}
    p, costs = get_panel(spec, a.synthetic)
    names = a.rules.split(",") if a.rules else None
    res = scanner.scan(p, costs, a.families, filters, a.side, names)
    RESULTS.mkdir(exist_ok=True)
    stem = f"scan_{spec['universe']}_{a.timeframe}_{a.families}"
    warn = ("\n\n> ⚠️ **Zaman makinesi kontrolü önerilir.** Bir tarama sonucu karar değil, adaydır; birçok varyant "
            "arasından seçilen sonuçlar ileride çökebilir. Önce `run.py --hypothesis` kapısı, seçim süreci için "
            "`Time machine test`. Kural: CLAUDE.md / AGENTS.md.\n")
    (RESULTS / f"{stem}.md").write_text(scanner.to_markdown(res) + warn + "\n\n```yaml\n" +
                                        scanner.suggest_yaml(res, spec["universe"]) + "\n```\n")
    res["board"].to_csv(RESULTS / f"{stem}.csv", index=False)
    res["variants"].to_csv(RESULTS / f"{stem}_variants.csv", index=False)
    print(scanner.to_markdown(res, top=15))
    if a.telegram:
        top = res["board"].head(10)
        msg = [f"🔎 Scan {spec['universe']} — {res['n_trials']} variants, PBO {res['global_pbo']}, "
               f"bench SR {res['benchmark_sharpe']}"]
        msg += [f"{i}. {r.family} OOS SR {r.wf_oos_sharpe} DD {r.wf_oos_maxdd}" for i, r in enumerate(top.itertuples(), 1)]
        msg.append("⚠️ Tarama sonucu adaydır, karar değil. Kapı (--hypothesis) ve zaman makinesi kontrolü önerilir.")
        telegram("\n".join(msg))


def arena_cfgs(a) -> list[dict]:
    """One config per timeframe. --timeframe runs a single one; --stage2 on|off overrides the config."""
    base = load_yaml("config/arena.yaml")
    if a.universe:
        base["universe"] = a.universe
    tfs = base.get("timeframes") or [base.get("timeframe", "4h")]
    if "--timeframe" in sys.argv:
        tfs = [a.timeframe]
    if a.stage2 in ("on", "off"):
        base.setdefault("stage2", {})["enabled"] = a.stage2 == "on"
    # sides: "both" (one book trades long AND short), "long" only, "short" only. Each side has its own
    # arena folder: decisions/arena/<tf> for both, decisions/arena/<tf>_long, <tf>_short for the others.
    sides = [a.side] if "--side" in sys.argv else (base.get("sides") or [base.get("side", "both")])
    out = []
    for tf in tfs:
        for side in sides:
            c = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
            for k, v in (base.get("by_timeframe", {}).get(tf) or {}).items():
                c[k] = {**(c.get(k) or {}), **v} if isinstance(v, dict) else v
            c["timeframe"] = tf
            c["side"] = side
            c["key"] = tf if side == "both" else f"{tf}_{side}"
            out.append(c)
    return out


def arena_panel(cfg: dict, synthetic: bool) -> tuple[Panel, Costs]:
    if synthetic:   # offline: random walks on a 4h-like calendar (no edge by construction)
        import numpy as np
        import pandas as pd
        rng = np.random.default_rng(5)
        idx = pd.date_range("2019-01-01", periods=int(6.2 * 2190), freq="4h")
        cols = [f"C{i}/USDT" for i in range(8)]
        rets = rng.normal(0.0001, 0.012, (len(idx), len(cols)))
        c = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=idx, columns=cols)
        c.iloc[: 2190 * 4, -1] = np.nan          # one "late listing" coin with < 3 years of data
        p = Panel.from_close(c.ffill().bfill(), seed=5)
        p.c = c
        p.o, p.h, p.l, p.v = (x.where(c.notna()) for x in (p.o, p.h, p.l, p.v))
        p.freq, p.market = "4h", "crypto"
        return p, Costs(0.0006, 0.0005, 0.0, 0.08)
    u = universe(cfg["universe"])
    p = data.load_panel(u, cfg.get("start", "2018-01-01"), cfg["universe"], with_fundamentals=False,
                        timeframe=cfg["timeframe"])
    return p, Costs(**u.get("costs", {}))


def do_arena(a, hyps) -> None:
    from lab import arena
    built = []
    for cfg in arena_cfgs(a):
        arena.use(cfg["key"])
        if a.arena and not a.screen and cfg["side"] != "both" and not arena.ROSTER.exists():
            print(f"[arena] {cfg['key']}: no roster yet (run the screen with --side {cfg['side']} first)")
            continue
        print(f"===== arena {cfg['universe']} {cfg['key']} =====")
        try:
            out = _arena_one(a, hyps, cfg)
        except Exception as e:  # noqa: BLE001 - one timeframe must not stop the other
            import traceback
            traceback.print_exc()
            if a.telegram:
                telegram(f"⚠️ arena {cfg['timeframe']} hata: {e}")
            continue
        if out:
            built.append(cfg["key"])
    if a.site and built:
        from lab import dashboard
        dashboard.write_index(a.site, built)


def _arena_one(a, hyps, cfg) -> dict | None:
    from lab import arena, dashboard, screen
    p, costs = arena_panel(cfg, a.synthetic)
    tag = f"{cfg['universe']}_{cfg['key']}"
    if a.timemachine:
        from lab import timemachine
        o = timemachine.run(p, costs, cfg, a.timemachine)
        if o.get("error"):
            print(o["error"]); return None
        md = timemachine.markdown(o)
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / f"timemachine_{a.timemachine}_{tag}.md").write_text(md)
        print(md)
        if a.telegram:
            f = lambda v: "–" if v is None else f"{v:+.0%}"   # noqa: E731
            telegram(f"⏳ zaman makinesi {cfg['timeframe']} (kesim {o['cutoff']} → bugün)\n" + "\n".join(
                f"{b['id']} {b['name']}: $1000 → {b['forward'].get('final_1000', 0):,.0f} "
                f"(yıllık {f(b['forward'].get('cagr'))}, düşüş {f(b['forward'].get('max_dd'))}) — {(b.get('band_status') or {}).get('text', '')}"
                for b in o["books"]) + "\n" + "\n".join(
                f"{g}: $1000 → {s_.get('final_1000', 0):,.0f}, SR {s_.get('sharpe')}" for g, s_ in o["groups"].items()))
        return None
    if a.protect:
        from lab import protect
        ro = arena._read(arena.ROSTER, None)
        act = [m for m in (ro or {}).get("members", []) if m["status"] == "active"]
        if not act:
            print("[protect] no active members")
            return None
        R, X, _ = arena.compute(ro, p, costs, act)
        res = protect.run(p, costs, cfg, R, X, act)
        md = protect.markdown(res, cfg)
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / f"protection_{tag}.md").write_text(md)
        arena._write(arena.DIR / "protection.json", {"date": date.today().isoformat(), **protect.summary_json(res)})
        print(md)
        if a.telegram:
            telegram(f"🛡️ kasa koruma testi {cfg['timeframe']} ({res['members']} üye)\n" + "\n".join(
                f"{'✅' if v['pass'] else '❌'} {protect.NAMES_TR.get(k, k)}" for k, v in res["tests"].items()) +
                f"\nkaldıraç tavanı: {res['leverage']['max_leverage']}x")
        return None
    if a.screen:
        res = screen.run(p, costs, cfg)
        if res.get("error"):
            print(res["error"])
            if a.telegram:
                telegram(f"🏟️ arena screen: {res['error']}")
            return None
        ro, note = arena.update_roster(res, cfg)
        gate = arena.gate_backtest(ro, p, costs, cfg)
        RESULTS.mkdir(exist_ok=True)
        md = screen.markdown(res, cfg, note)
        ids = [int(h["id"][1:]) for h in hyps if str(h.get("id", "")).startswith("H") and h["id"][1:].isdigit()]
        yml = screen.suggested_yaml(res, cfg, (max(ids) + 1) if ids else 1)
        if yml:
            md += "\n\n## Önerilen hipotezler (tier A — kapıya gönder)\n\n```yaml\n" + yml + "```\n"
        md += ("\n\n## Switcher backtest kapısı\n\n" +
               f"Geçti: **{gate.get('backtest_pass')}** — kontroller: `{_fmt_dict(gate.get('checks', {}))}`\n\n" +
               f"Pencereler: `{_fmt_dict(gate.get('windows', {}))}`\n")
        (RESULTS / f"arena_screen_{tag}.md").write_text(md)
        screen.to_frame(res).to_csv(RESULTS / f"arena_screen_{tag}.csv", index=False)
        ok = sorted([r for r in res["rows"].values() if r["stage"] == "OK"], key=screen.rank_key)
        surv = []
        for r in ok[:100]:
            d = {"coin": r["coin"], "rule": r["rule"], "params": r["params"], "tier": r.get("tier"),
                 "sharpe": r["sharpe"], "dsr": r.get("dsr")}
            for w, v in r["card"].items():
                d[f"ret_{w}"] = None if v.get("no_data") else v["ret"]
            d["variant"] = r["variant"]
            d["stage_no"] = r["stage_no"]
            surv.append(d)
        arena._write(arena.SUMMARY, {"date": date.today().isoformat(), "universe": cfg["universe"],
                                     "funnel2": res.get("funnel2"), "stage2": res.get("stage2"),
                                     "timeframe": cfg["timeframe"], "n_trials": res["n_trials"],
                                     "n_variant_runs": res["n_variant_runs"], "coins_ok": len(res["coins"]),
                                     "coins_total": len(res["years"]), "funnel": res["funnel"], "survivors": surv,
                                     "note": note})
        print(md)
        if a.telegram:
            f = res["funnel"]
            telegram("🏟️ arena eleme motoru " + tag + f"\n{res['n_trials']} deneme, {len(res['coins'])} coin\n" +
                     "\n".join(f"{x['stage']} {x['label']}: -{x['eliminated']} → {x['remaining']}" for x in f) +
                     (f"\n2. aşama: {res['stage2']['candidates']} aday, {res['stage2']['trials']} ek deneme → "
                      f"{sum(1 for r in res['rows'].values() if r['stage_no'] == 2 and r['stage'] == 'OK')} geçti"
                      if res.get('stage2', {}).get('enabled') else "") +
                     f"\n{note}\nSwitcher backtest kapısı: {'✅' if gate.get('backtest_pass') else '❌'} {gate.get('checks', {})}"
                     "\n⚠️ Zaman makinesi kontrolü önerilir: bu adaylar binlerce deneme arasından seçildi. "
                     "Gerçek paradan önce 'Time machine test' workflow'unu aynı yön ve zaman dilimiyle çalıştırın.")
        return None
    out = arena.run(p, costs, cfg)
    if out.get("error"):
        print(out["error"])
        return None
    if a.site:
        print(f"[arena] dashboard -> {dashboard.build(out, cfg, a.site)}")
    sw = out["switcher"]
    print(json.dumps({"usable": sw["usable"], "checks": sw["checks"], "cash": sw["cash"],
                      "picks": [(x["id"], x["coin"], x["weight"]) for x in sw["picks"]], "events": out["events"]},
                     ensure_ascii=False, indent=1))
    if a.telegram:
        txt = arena.telegram_text(out, out["summary_due"])
        if txt:
            telegram(f"[{cfg['timeframe']}] " + txt)
    return out


def _core_panel_loader(cfg: dict, synthetic: bool):
    cache: dict = {}

    def get(tf: str, assets: list[str]):
        allx = sorted({x for v in [cfg["variants"]["baseline"], *cfg["variants"]["list"]] for x in v["assets"]})
        if tf not in cache:
            if synthetic:
                import numpy as np
                import pandas as pd
                per = {"1h": 24 * 365, "4h": 2190, "1d": 365}[tf]
                n = per * 6
                idx = pd.date_range("2019-01-01", periods=n, freq={"1h": "h", "4h": "4h", "1d": "D"}[tf])
                rng = np.random.default_rng(4)
                c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.02 / np.sqrt(per / 365), (n, len(allx))), axis=0)),
                                 idx, allx)
                p = Panel.from_close(c, seed=4); p.freq = tf
            else:
                u = {"tickers": allx, "benchmark": "BTC/USDT", "market": "crypto", "risk_free": None, "macro": []}
                p = data.load_panel(u, cfg.get("start", "2018-01-01"), "core", with_fundamentals=False, timeframe=tf)
            cache[tf] = p
        return cache[tf]
    return get


def do_core(a) -> None:
    from lab import core
    cfg = load_yaml("config/core.yaml")
    tfs = [a.timeframe] if "--timeframe" in sys.argv else cfg.get("timeframes", ["1d"])
    out_dir = ROOT / "decisions" / "core"
    out_dir.mkdir(parents=True, exist_ok=True)
    for tf in tfs:
        if a.synthetic:
            import numpy as np
            import pandas as pd
            n = 2190 * 7 if tf == "4h" else 365 * 7
            idx = pd.date_range("2018-01-01", periods=n, freq="4h" if tf == "4h" else "D")
            rng = np.random.default_rng(3)
            c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, (n, 2)), axis=0)), idx, cfg["universe_assets"])
            p = Panel.from_close(c, seed=3); p.freq = tf
        else:
            u = {"tickers": cfg["universe_assets"], "benchmark": cfg["universe_assets"][0], "market": "crypto",
                 "risk_free": None, "macro": []}
            p = data.load_panel(u, cfg.get("start", "2018-01-01"), "core", with_fundamentals=False, timeframe=tf)
        o = core.run(p, cfg)
        md = core.markdown(o, cfg)
        if cfg.get("variants") and tf == cfg["variants"]["baseline"]["timeframe"]:
            vo = core.run_variants(cfg, _core_panel_loader(cfg, a.synthetic))
            o["variants"] = vo
            md += "\n" + core.markdown_variants(vo, cfg)
            if cfg.get("risk_levels") or cfg.get("funding_arb"):
                rl = core.run_risk_levels(cfg, _core_panel_loader(cfg, a.synthetic))
                base = rl["series"].get(0.40)
                h054_d = (1 + base).groupby(base.index.normalize()).prod() - 1 if base is not None else None
                fu = core.run_funding(cfg, h054_d) if not a.synthetic else {"error": "synthetic run"}
                o["risk_levels"] = {k: v for k, v in rl.items() if k != "series"}
                o["funding_arb"] = fu
                md += "\n" + core.markdown_risk_funding(rl, fu, cfg)
                if cfg.get("idle_arb") and not a.synthetic:
                    ia = core.run_idle_arb(cfg, _core_panel_loader(cfg, a.synthetic))
                    o["idle_arb"] = ia
                    md += "\n" + core.markdown_idle(ia, cfg)
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / f"core_{tf}.md").write_text(md)
        slim = {**o, "spark": {}}
        (out_dir / f"{tf}.json").write_text(json.dumps(slim, indent=1, default=str, ensure_ascii=False))
        print(md)
        if a.telegram:
            ok = [r for r in o["rows"] if r.get("approved")]
            telegram(f"🧱 çekirdek çalışma {tf}: {len(ok)} kural onaylandı\n" + "\n".join(
                f"{'✅' if r.get('approved') else ('▫️' if r['approved'] is None else '❌')} {r['book']} {core.NAMES.get(r['rule'], r['rule'])}: "
                f"$1000→{r['full'].get('final_1000', 0):,.0f}, DD {r['full'].get('max_dd', 0):.0%}" for r in o["rows"])
                + ("\n\nH052 varyantları:\n" + "\n".join(
                    f"{'✅' if v.get('approved') else '❌'} {v['name']}: SR {(v.get('variant') or {}).get('full', {}).get('sharpe')} "
                    f"vs temel {(v.get('baseline') or {}).get('full', {}).get('sharpe')}" for v in o["variants"]["rows"])
                   if o.get("variants") else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--hypothesis")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--strategy")
    ap.add_argument("--rule")
    ap.add_argument("--universe")
    ap.add_argument("--start", default="2012-01-01")
    ap.add_argument("--timeframe", default="1d", help="1h | 4h | 1d | 1w | 1mo")
    ap.add_argument("--filters", default="none")
    ap.add_argument("--exits", default="")
    ap.add_argument("--overlays", default="", help="opt-in portfolio overlays: all | vt15,dd20")
    ap.add_argument("--side", default="long", help="scan: long|short|both; arena/screen/time machine: both|long|short (default there: config/arena.yaml sides)")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--families", default="all")
    ap.add_argument("--rules", default="")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--telegram", action="store_true")
    ap.add_argument("--ids", action="store_true", help="print active hypothesis ids as JSON (workflow matrix)")
    ap.add_argument("--merge", action="store_true", help="rebuild decisions/registry.json from parts")
    ap.add_argument("--live", action="store_true", help="paper-track ACCEPT decisions, demote on decay")
    ap.add_argument("--calibrate", action="store_true", help="reproduce known results on real data")
    ap.add_argument("--screen", action="store_true", help="arena screening funnel (monthly)")
    ap.add_argument("--arena", action="store_true", help="arena paper run + regime switcher (every closed bar)")
    ap.add_argument("--core", action="store_true", help="core study: simple fixed rules on BTC/ETH (config/core.yaml)")
    ap.add_argument("--timemachine", default="", help="cutoff date YYYY-MM-DD: replay the arena as if today were then")
    ap.add_argument("--protect", action="store_true", help="capital protection study on the active arena members")
    ap.add_argument("--stage2", default="", help="with --screen: on | off (default: config/arena.yaml)")
    ap.add_argument("--site", default="", help="with --arena: write the dashboard (index.html + data.json) here")
    ap.add_argument("--prefetch", action="store_true",
                    help="download & cache all data needed by active hypotheses (or --universe/--timeframe)")
    a = ap.parse_args()

    hyps = load_yaml("hypotheses/registry.yaml") or []
    if a.core:
        return do_core(a)
    if a.screen or a.arena or a.protect or a.timemachine:
        return do_arena(a, hyps)
    if a.ids:
        print(json.dumps([h["id"] for h in hyps if h.get("status") == "active"]))
        return
    if a.calibrate:
        from lab import calibration
        rows = []
        try:
            rows = calibration.run()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            rows = [{"id": "C0", "check": "calibration crashed", "pass": False, "result": str(e)[:300], "expected": "no crash"}]
        md = calibration.markdown(rows)
        RESULTS.mkdir(exist_ok=True)
        (RESULTS / "calibration.md").write_text(md)
        print(md)
        if a.telegram:
            telegram("🧪 " + md.splitlines()[0][2:] + "\n" + "\n".join(
                f"{'✅' if r['pass'] else '❌'} {r['id']} {r['check']}: {r['result']}" for r in rows))
        return
    if a.prefetch:
        want = [(a.universe, a.timeframe, a.start)] if a.universe else sorted(
            {(h["universe"], h.get("timeframe", "1d"), h.get("start", "2012-01-01")) for h in hyps
             if h.get("status") == "active" and (not a.hypothesis or h["id"] in a.hypothesis.split(","))})
        for uni, tf, st in want:
            try:
                p = data.load_panel(universe(uni), st, uni, timeframe=tf)
                print(f"[prefetch] {uni} {tf}: {p.c.shape} fund={len(p.fund)} macro={list(p.macro)}")
            except Exception as e:  # noqa: BLE001
                print(f"[prefetch] {uni} {tf} failed: {e}")
        return
    if a.merge:
        reg = decision.merge()
        print(json.dumps({k: v["verdict"] for k, v in reg["hypotheses"].items()}, indent=1))
        print(json.dumps(reg["systems"], indent=1, default=str))
        if a.telegram:
            telegram(summary_text(reg))
        return
    if a.live:
        from lab import live
        st = live.run([h for h in hyps if h.get("status") == "active"])
        if a.telegram and st:
            telegram("📡 quant_lab live tracking\n" + "\n".join(
                f"{'🔻' if v['degraded'] else '🟢'} {k} live {v['live_return']:+.1%} SR {v['live_sharpe']} — {v['why']}"
                for k, v in st.items()))
        return
    if a.list:
        print(f"Weight strategies ({len(REGISTRY)}):")
        for n, s in sorted(REGISTRY.items()):
            print(f"  {n:24s} [{s.kind}] grid={s.grid}  — {s.source}")
        print(f"\nEntry/exit rules ({len(rules.RULES)}, {rules.n_variants()} parameter variants):")
        for n, r in sorted(rules.RULES.items()):
            print(f"  {n:22s} [{r.family}] grid={r.grid}  — {r.source}")
        print(f"\nFilters: {', '.join(rules.FILTERS)}")
        print("Exit configs:")
        for i, e in enumerate(EXIT_GRID):
            print(f"  {i:2d} {e.label()}")
        print("\nUniverses:", ", ".join(load_yaml("config/universes.yaml")))
        print("Hypotheses:")
        for h in hyps:
            print(f"  {h['id']} {h.get('rule') or h.get('strategy')} / {h['universe']} -> {h.get('for_system')} [{h['status']}]")
        return

    if a.scan:
        if not (a.universe or a.synthetic):
            sys.exit("--scan needs --universe")
        return do_scan(a)

    results = {}
    if a.synthetic or (a.universe and (a.strategy or a.rule)):
        spec = {"universe": a.universe or "synthetic", "start": a.start, "timeframe": a.timeframe}
        if a.rule:
            spec.update({"rule": a.rule, "side": a.side,
                         "filters": "all" if a.filters == "all" else a.filters.split(","),
                         "exits": "all" if a.exits == "all" else ([int(x) for x in a.exits.split(",")] if a.exits else None)})
        else:
            spec["strategy"] = a.strategy or "xs_momentum"
        if a.overlays:
            spec["overlays"] = "all" if a.overlays == "all" else a.overlays.split(",")
        hid = "SYN" if a.synthetic else f"ADHOC_{date.today():%Y%m%d}"
        results[hid] = run_one(hid, spec, write_registry=False, synthetic=a.synthetic)
    else:
        todo = [h for h in hyps if h.get("status") == "active"]
        if a.hypothesis:
            todo = [h for h in hyps if h["id"] == a.hypothesis]
            if not todo:
                sys.exit(f"Unknown hypothesis {a.hypothesis}")
        elif not a.all:
            ap.print_help()
            return
        for h in todo:
            try:
                results[h["id"]] = run_one(h["id"], h, write_registry=True)
            except Exception as e:  # noqa: BLE001 - one bad hypothesis must not stop the batch
                import traceback
                tb = traceback.format_exc()
                print(tb)
                print(f"[{h['id']}] ERROR {e}")
                RESULTS.mkdir(exist_ok=True)
                (RESULTS / f"{h['id']}_ERROR.txt").write_text(tb)   # published with the reports
                results[h["id"]] = {"verdict": "ERROR", "reasons": [str(e)]}
        decision.merge()

    if a.telegram and results:
        msg = ["🧪 quant_lab validation"]
        for hid, r in results.items():
            o = r.get("oos", {})
            msg.append(f"{ICON.get(r.get('verdict'), '⚠️')} {hid} {r.get('name', '')} "
                       f"SR={o.get('sharpe')} DD={o.get('max_dd')} DSR={r.get('dsr')} PBO={r.get('pbo')}")
        telegram("\n".join(msg))


if __name__ == "__main__":
    main()
