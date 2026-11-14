# H090 — Institutional Research Architecture (Foundation PR)

**Status: research architecture + deterministic causal-protocol tests only. No discovered edge, no production authorization, no new historical or prospective trading result.**

## Why

Existing code already has ICT technical zones `ict/ictlab`, point-in-time fundamental factors `lab/fundamentals.py`, portfolio macro synthesis `lab/synthesis.py`, and trade execution simulations `lab/trade_engine.py`. None of those alone demonstrates that causal ICT sequence x multi-timeframe x point-in-time fundamentals x macro x target family x portfolio conflict has been tested as an integrated strategy. This PR creates a **durable cross-family research inventory**, exposes gaps and prototypes a deterministic event grammar before expensive historical replay.

## Components

| Component | Contract |
|---|---|
| `catalog.json` | Versioned 12 research families, timeframes and event types; auditable source marker checks; explicit untested experiment matrix, missing capabilities and mandatory research protocol |
| `engine.py` | Read-only chronological event chain matcher with observed-at timestamps, explicit NO-SWEEP windows, 0.5 Fibonacci context, fundamental/macro as-of gating and known directional target family; **no actual detectors/price fill simulation** |
| `recipes.json` | Six explicitly distinct prototype recipes: swept LIQ→MSS→OB, no-sweep→OB→FVG, iFVG after structure, equity technical+PIT accounting, metals technical+macro and crypto technical+onchain+macro |
| `orchestrator.py` | Deterministic research signal conflict abstention and bounded risk intents for multi-strategy candidates; no live orders, ranking or fills |
| `audit.py` | Source hash inventory, required research experiment statuses, unscoped strategy families and immutable evidence gate; Markdown + JSON reports. **Missing remains UNTESTED**, file existence ≠ semantic implementation |
| `test_h090.py` | Synthetic deterministic chronology, no-lookahead, branch absence, target, fundamental/macro availability, conflict, risk and tamper checks |
| `.github/workflows/h090.yml` | Standalone read-only offline regression and research coverage audit; produces downloadable Actions artifacts; existing CI also enforces regressions |

## Operating instructions

After merging, **no immediate manual Actions run is necessary**: the existing CI runs H090 tests on PR and future pushes. For a manual coverage snapshot, choose Actions > `H090 — Research architecture and coverage audit` > Run workflow on main. The run creates downloadable `coverage.json` and `coverage.md` **only as workflow artifacts**, not as new production decisions. Offline command:

```bash
python -m unittest discover -s research/h090 -p 'test_*.py' -v
python research/h090/audit.py --output-dir results/h090_audit
```

`audit.py --require-complete` should **fail at this foundation stage**: there is no verified end-to-end OOS or prospective research evidence. No one should "fix" this by relabeling UNTESTED as verified.

## Formal event contract — what each future detector must produce

Every evidence event requires `event_id, symbol, kind, timeframe, side, occurred_at, observed_at, source, attrs`. `occurred_at` must not be later than `observed_at`, both need timezone. Observed is **when that data was actually usable** (closed swing confirmed, news published, financial filing public). Missing values fail closed. For a defensible no-liquidity-sweep branch, a certified observation covering a specific completed `window_start/window_end` is mandatory; the absence of a collected sweep alone is **not proof of no sweep**. Real rule data producers must also document exchange holidays, revised bars, price adjustment, contract calendar and time zone.

A strategy contains a strictly timestamp-ordered `sequence`, bounded gap, optional as-of Fibonacci range filters and point-in-time factor or macro checks, and an explicit, *already available* Block/LIQ/FVG target. If a valid target is missing, no candidate is returned. A candle's target is never resolved from the future. The prototype reports reference entry/target prices only; it **does not assert an executable stop, fill, R, TP touch or net profitability**.

### H090 decision pipeline

1. **Technical and contextual sources:** Separate raw technical zones from financial filings, onchain metrics, macro rates/FX, scheduled events and cross-asset regimes. Tag availability, revision history and instrument identity.
2. **Event/state grammar:** Turn confirmed observations into independently timestamped events. Test sweep vs certified non-sweep, after-sweep MSB/MSS, iFVG, OB + FVG inside block, daily block priority, multi-TF dealing-range 0.5 by well-defined anchor.
3. **Baseline families first:** Compare OB, liquidity, FVG and variants separately at all supported timeframes; report no-history / no-trades as NOT_TESTABLE, not zero cost or zero returns. Avoid universal 5m/15m claims with incomplete data.
4. **Factor and macro ablations:** Same instrument, timestamps and costs for technical alone / fundamental alone / macro alone / technical+fundamental / technical+macro / combined; nested training-only feature selection. Avoid equity accounting factors being silently treated as BTC or gold fundamentals.
5. **Entry-family exit experiments:** Block entry→Block target, LIQ entry→LIQ target, FVG entry→FVG target **and cross-family controls** compared with fixed R and tested structural stop and invalidation rules; choose only what persists out-of-sample.
6. **Portfolio combinations:** When simultaneous long/short candidates contradict, abstain or apply a pre-registered priority. Enforce per-symbol, sector/underlying and total gross/risk limits; do not double count common exposure.
7. **Independent validation:** Purged walk-forward by maximum holding horizon, untouched true holdout (prior viewed periods are NOT fresh), multiple trials accounted for, cross-asset/source/regime testing, 2x costs, block bootstrap and time-machine tests. Only first-seen after freeze can become new forward evidence.
8. **Decision registry:** Separate research audit results from `hypotheses/registry.yaml` and `decisions/registry.json`. Only the pre-existing validation/ACCEPT gate can authorize a strategy.

### What remains incomplete after this PR

The catalog intentionally reports missing: real multi-timeframe detector integration (including 5m/15m source coverage), complete Fibonacci range anchors and point-in-time iFVG/MSS, verified own-family target execution including stop/partial fills, financial+technical and macro+technical production-grade joins, real multi-strategy backtest/exposure management, independently sourced out-of-sample results and forward H090 trades. The live order book, brokerage fills, roll/funding and impact are also **not** verified by these synthetic tests.

**H089:** Existing H063–H065 30-day prospective watch and the H088/H089 Actions and evidence files are intentionally untouched. H090 uses no H089 historical data to assert new alpha. This is a research foundation, not a substitute for the later empirical study.
