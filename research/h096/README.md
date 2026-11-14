# H096 — Real multi-timeframe and entry / risk / target proxy research

**Scope:** real OKX BTC/ETH USDT perpetual closed native 5m, 15m, 1H and 1Dutc candles; strict 4H UTC resampling from complete hourly groups. This is **not** an accepted strategy or executable backtest.

## Causal design

- All event definitions reuse the H095 confirmed-pivot detectors, now supporting 5m, 15m and 1D. Events are timestamped at **bar close**; parent timeframe information is eligible only if its event had already closed, with bounded staleness. Unconfirmed parent signals and future bars are never backfilled.
- Six entry families: LIQ_SWEEP, MSS, BOS, OB_TOUCH, FVG_TOUCH, IFVG_CONFIRMED. Both directions. Compare unfiltered versus same-direction higher-timeframe context (only recent directional parent events).
- Three targets: 1R, 2R and an already-known confirmed opposite pivot. SL risk is at least mean recent high–low range and the entry-to-known-event-zone reference. Entry is **next complete bar open**. Conservative intrabar **stop-first** ordering, adverse stop gaps, favorable target gaps capped at target. Any gap in the intended holding path invalidates the trade; no trades are closed early simply because the dataset ends. One trade at a time **within each tested configuration**, not portfolio-wide.
- Assumed all-in roundtrip 10, 20 and 40 basis points. These are sensitivity assumptions, **not independently measured fees, spreads, funding, slippage or liquidity impact**.
- Fixed chronological 70/30 descriptive split with trades crossing the boundary purged. **Historical holdout is not fresh independent OOS**. No winner selection, no multiple-testing-adjusted significance, no independently verified profitability.
- The matrix is 6 event types × 2 sides × 2 HTF cohorts × 3 targets × 3 cost cases = **216 predeclared comparisons per eligible timeframe and asset**. An unavailable source or too-short series is recorded as NOT_TESTABLE; do not silently fabricate bars.

## Workflow

```bash
python -m unittest discover -s research/h095 -p 'test_*.py' -v
python -m unittest discover -s research/h096 -p 'test_*.py' -v
python research/h096/run.py --pages 12 --out results/h096
```

Actions > **H096 — Real multitimeframe and cost research (read-only)** > Run workflow on `main` after merge. The artifact `h096-multitimeframe-evidence-*` contains per-symbol and per-timeframe source SHA-256, detected event inventories, full proxy performance matrix and `summary.json`. Provider outages produce explicit failed source statuses; no synthetic fallback.

## Research limitations

- OKX native 5m candles are available for only the recent pagination window; a 12-page 5m sample is roughly four days, which is too short to validate robust regime performance. 15m is similarly limited. Daily and 4H coverage may not support robust parent-child overlap across the whole historical period. **No extrapolation.**
- Single historical primary venue, no order-book / bid-ask spread, liquidation data, funding, latency, capacity or broker fills. A price-only stop/target simulator is **not execution evidence**.
- Historical 70/30 is descriptive and can be data-mined. Multiple-comparison corrections, frozen prospective first-seen signals, independent feed replication, realistic funding/fees and portfolio-level concurrent NAV are required before acceptance.
- Technical, PIT fundamental and macro factor fusion remains **not implemented** here; it is H093/H094 follow-on work, not something to label completed.
- H089 30-day observation, main strategy registries, bots and trading decisions are **not changed**.

**Interpretation:** green tests show correct pipeline execution, not positive expectancy. `alpha_accepted=false` by construction.
