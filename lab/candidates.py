"""Candidate = a family of tradeable variants the validator can sweep.

Two kinds:
  * StrategyCandidate : weight-based strategy from lab.strategies (factor / rotation / timing)
  * RuleCandidate     : entry/exit rule from lab.rules + filters + exit configs, run through
                        the trade engine (stops, targets, trailing, time exits)

Every variant is computed ONCE on the full history. All computations are causal, so slicing
a full-history return series is identical to re-running on truncated data; the walk-forward
therefore selects among precomputed series (fast and exact).
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import pandas as pd

from lab import engine, overlays, rules
from lab.engine import Costs, Result
from lab.panel import Panel
from lab.strategies import get as get_strategy
from lab.trade_engine import EXIT_GRID, SIZE_GRID, ExitCfg, run_trades

_G: dict = {}  # worker globals (fork start method shares the panel without pickling)


@dataclass
class Variant:
    key: str
    params: dict


class StrategyCandidate:
    def __init__(self, name: str, overlays=None):
        self.strat = get_strategy(name)
        self.name = name
        self.source = self.strat.source
        self.overlays = list(overlays or [])

    def variants(self) -> list[Variant]:
        pts = rules.grid_points(self.strat.grid)
        return [Variant(f"{self.name}|{_fmt(p)}", p) for p in pts]

    def run(self, p: Panel, v: Variant, costs: Costs) -> Result:
        prm = {k: x for k, x in v.params.items() if not k.startswith("_")}
        res = engine.run(p.c, self.strat(p, **prm), costs, ppy=p.ppy, member=p.member)
        return overlays.apply(res, v.params["_overlay"], p.ppy, costs) if v.params.get("_overlay") else res

    def overlay_variants(self, seeds: list[Variant]) -> list[Variant]:
        return _overlay_variants(seeds, self.overlays)

    def targets(self, p: Panel, v: Variant) -> dict:
        w = self.strat(p, **{k: x for k, x in v.params.items() if not k.startswith("_")}).iloc[-1]
        if v.params.get("_overlay"):
            sc = overlays.scale_series(self.run(p, Variant(v.key, {**v.params, "_overlay": None}), Costs()).returns,
                                       v.params["_overlay"], p.ppy)
            w = w * float(sc.iloc[-1])
        return {k: round(float(x), 4) for k, x in w[w.abs() > 1e-6].sort_values(ascending=False).items()}


class RuleCandidate:
    """rule x rule-grid x filters x exits. `staged=True` sweeps exits only on the best stage-1 variants."""

    def __init__(self, rule: str, filters=("none",), exits=None, side: str = "long",
                 max_positions: int | None = None, staged: bool = True, stage2_top: int = 3,
                 sizes=None, confirm: str | None = None, confirm_within=(0, 3), confirm_params=None, overlays=None):
        self.rule = rules.RULES[rule]
        self.name = rule
        self.source = self.rule.source
        self.filters = list(filters)
        self.exits = list(exits) if exits is not None else None
        self.side = side
        self.max_positions = max_positions
        self.staged = staged
        self.stage2_top = stage2_top
        self.sizes = list(sizes) if sizes is not None else list(range(len(SIZE_GRID)))
        self.max_variants = 1500
        self.overlays = list(overlays or [])
        self.confirm = rules.RULES[confirm] if confirm else None
        self.confirm_within = list(confirm_within) if isinstance(confirm_within, (list, tuple)) else [confirm_within]
        # confirmation rule: its own grid is swept unless fixed params are given
        self.confirm_points = [confirm_params] if confirm_params else (
            rules.grid_points(self.confirm.grid) if self.confirm else [None])
        if self.confirm:
            self.name = f"{rule}+{confirm}"

    def variants(self, stage: int = 1, seeds: list[Variant] | None = None) -> list[Variant]:
        out = []
        if stage == 1:
            ex_list = (self.exits or [0])[:1] if self.staged else (self.exits or [0])
            for gp in rules.grid_points(self.rule.grid):
                for f in self.filters:
                    for e in ex_list:
                        for cp in self.confirm_points:
                            for cw in (self.confirm_within if self.confirm else [None]):
                                prm = {**gp, "_filter": f, "_exit": e, "_size": 0}
                                if self.confirm:
                                    prm.update({"_cparams": cp, "_cwithin": cw})
                                out.append(Variant(self._key(gp, f, e, 0, prm), prm))
            if len(out) > self.max_variants:   # very large spaces (e.g. combos): seeded random search
                import random
                rnd = random.Random(42)
                out = rnd.sample(out, self.max_variants)
        elif stage == 3:  # position-sizing study on the best exits
            for s in seeds or []:
                for z in self.sizes:
                    if z == s.params.get("_size", 0):
                        continue
                    p = {**s.params, "_size": z}
                    gp = {k: v for k, v in p.items() if not k.startswith("_")}
                    out.append(Variant(self._key(gp, p["_filter"], p["_exit"], z, p), p))
        else:
            ex_list = self.exits if self.exits is not None else list(range(len(EXIT_GRID)))
            for s in seeds or []:
                for e in ex_list:
                    if e == s.params["_exit"]:
                        continue
                    p = {**s.params, "_exit": e}
                    gp = {k: v for k, v in p.items() if not k.startswith("_")}
                    out.append(Variant(self._key(gp, p["_filter"], e, p.get("_size", 0), p), p))
        return out

    def _key(self, gp, f, e, z, prm=None):
        k = f"{self.name}|{_fmt(gp)}|f={f}|x={EXIT_GRID[e].label()}"
        if prm and prm.get("_cparams") is not None:
            k += f"|confirm={_fmt(prm['_cparams'])},within={prm['_cwithin']}"
        return k if not z else k + f"|size={SIZE_GRID[z].label()}"

    def _signals(self, p: Panel, v: Variant):
        gp = {k: x for k, x in v.params.items() if not k.startswith("_")}
        sig = self.rule.fn(p, **gp)
        if self.confirm is not None:
            sig = rules.confirm(sig, self.confirm.fn(p, **(v.params.get("_cparams") or {})),
                                v.params.get("_cwithin") or 0)
        return rules.apply_filter(sig, p, v.params["_filter"])

    def run(self, p: Panel, v: Variant, costs: Costs) -> Result:
        res = run_trades(p, self._signals(p, v), EXIT_GRID[v.params["_exit"]], costs,
                         self.side, self.max_positions, SIZE_GRID[v.params.get("_size", 0)])
        return overlays.apply(res, v.params["_overlay"], p.ppy, costs) if v.params.get("_overlay") else res

    def overlay_variants(self, seeds: list[Variant]) -> list[Variant]:
        return _overlay_variants(seeds, self.overlays)

    def targets(self, p: Panel, v: Variant) -> dict:
        res = self.run(p, v, Costs())
        w = res.weights.iloc[-1]   # already scaled by the overlay when one is used
        s = self._signals(p, v)
        last = p.index[-1]
        return {
            "positions": {k: round(float(x), 4) for k, x in w[w.abs() > 1e-6].items()},
            "entry_long_next_open": [c for c in p.columns if bool(s.entry_long.loc[last, c])],
            "exit_long_next_open": [c for c in p.columns if bool(s.exit_long.loc[last, c])],
            "entry_short_next_open": [] if s.entry_short is None or self.side == "long"
            else [c for c in p.columns if bool(s.entry_short.loc[last, c])],
        }


def _overlay_variants(seeds: list[Variant], kinds: list[str]) -> list[Variant]:
    """Stage 4: the chosen portfolio overlays on top of the best variants (counted as trials).
    OPT-IN: a hypothesis lists them (`overlays: all` or `[vt15, dd20]`); none by default."""
    out = []
    for sd in seeds:
        if sd.params.get("_overlay"):
            continue
        for k in kinds:
            out.append(Variant(f"{sd.key}|overlay={k}", {**sd.params, "_overlay": k}))
    return out


def _fmt(d: dict) -> str:
    return ",".join(f"{k}={v}" for k, v in d.items() if not str(k).startswith("_"))


def _work(args):
    cand, v, costs = args
    p = _G["panel"]
    try:
        r = cand.run(p, v, costs)
        return v.key, r.returns, r.turnover, r.meta.get("trades")
    except Exception as e:  # noqa: BLE001
        return v.key, None, None, str(e)


def run_all(cand, p: Panel, variants: list[Variant], costs: Costs, workers: int | None = None):
    """Run variants (in parallel where possible). Returns {key: (returns, turnover, trades)}."""
    workers = workers or int(os.environ.get("LAB_WORKERS", os.cpu_count() or 1))
    _G["panel"] = p
    jobs = [(cand, v, costs) for v in variants]
    out, errors = {}, {}
    if workers > 1 and len(jobs) > 4:
        import multiprocessing as mp
        try:
            ctx = mp.get_context("fork")
            with ProcessPoolExecutor(workers, mp_context=ctx) as ex:
                res = list(ex.map(_work, jobs, chunksize=max(1, len(jobs) // (workers * 4))))
        except Exception:  # noqa: BLE001 - fall back to serial
            res = [_work(j) for j in jobs]
    else:
        res = [_work(j) for j in jobs]
    for key, r, t, tr in res:
        if r is None:
            errors[key] = tr
        else:
            out[key] = (r, t, tr)
    return out, errors


def _overlay_list(spec: dict) -> list[str]:
    o = spec.get("overlays")
    if o in (None, "", "none", []):
        return []
    if o == "all":
        return list(overlays.KINDS)
    bad = [k for k in o if k not in overlays.KINDS]
    if bad:
        raise ValueError(f"unknown overlays {bad}; known: {overlays.KINDS}")
    return list(o)


def from_spec(spec: dict):
    """Build a candidate from a hypotheses/registry.yaml entry.
    Exits and overlays are OPT-IN: without `exits:` only the rule's own exit (#0) is used; without
    `overlays:` no overlay is tried. `exits: all` / `overlays: all` search every one (all counted as trials)."""
    if "rule" in spec:
        filters = spec.get("filters", ["none"])
        if filters == "all":
            filters = list(rules.FILTERS)
        exits = spec.get("exits")
        if exits == "all":
            exits = list(range(len(EXIT_GRID)))
        elif exits in (None, "", []):
            exits = [0]                       # opt-in: the rule's own exit only
        sizes = spec.get("sizes")
        if sizes == "all":
            sizes = None
        return RuleCandidate(spec["rule"], filters, exits, spec.get("side", "long"),
                             spec.get("max_positions"), spec.get("staged", True), spec.get("stage2_top", 3), sizes,
                             spec.get("confirm"), spec.get("confirm_within", [0, 3]), spec.get("confirm_params"),
                             _overlay_list(spec))
    return StrategyCandidate(spec["strategy"], _overlay_list(spec))


__all__ = ["StrategyCandidate", "RuleCandidate", "Variant", "run_all", "from_spec", "ExitCfg"]
