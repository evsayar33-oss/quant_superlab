# H091–H094 — Real Market Research, Step 1 (research-only)

This PR implements a **real-input exploratory discovery pipeline** and explicit incomplete gates for the four-stage plan. It does not claim the complete plan is finished.

## Status and public sources

- H091: OKX official **BTC-USDT-SWAP and ETH-USDT-SWAP** public 1H history-candles, paginated backwards with complete-bar (`confirm=1`), timestamp, OHLC, duplicate, pagination, expiry and gap validation. Up to 12×100 bars per instrument by default. Independent overlap diagnostic using Bitget official USDT-FUTURES 1H history-candles, last ~100 bars. Bitget is not an identical exchange or an independently established economic market; both contracts refer to the same underlying.
- H092: Enumerates **LIQ sweep/reclaim, range-break with contrary-body OB proxy and 3-candle FVG** independently across 1H and complete 4H bars. Long and short separately, fixed 1R/2R and historic structural range reference targets, 10 bps assumed round-trip cost with additional 2× cost sensitivity, no overlapping trades **within** each rule. In addition a separate 3-model event-order **proxy** experiment tests LIQ→range break, LIQ→range break→FVG and certified unswept→range break→FVG. **These are not confirmed MSS, true OB retests, full iFVG or execution at a structural block**; the report says so.
- H093: Implements release-availability-ordered, symbol-specific **as-of** factor joins with explicit staleness limits and identical-cohort ablation guards. Actual fundamental/macro factors for the required BTC/ETH historical timestamps are **not** acquired in this PR; all model-specific uplift claims remain NOT_TESTABLE. The equity SEC PIT integration is a separate workstream.
- H094: Research evidence gate records OOS validity, independent venues, funding/slippage/fills, PIT ablation, multiple-testing, nonoverlap portfolio and first-seen prospective sample requirements; no `ACCEPT`, no live execution or bot changes. A historical 70/30 descriptive split here **is not a new untouched holdout**; already-viewed dates cannot be recycled as independent evidence.

### Tests & workflows

```bash
python -m unittest discover -s research/h091 -p 'test_*.py' -v
python research/h091/run.py --symbols BTC ETH --pages 12 --out results/h091_h094
```

Actions > **H091-H094 — Real market entry research (read-only)** > Run workflow. The regression step runs without the network. The real-source smoke (OKX primary, Bitget cross-check) returns downloadable `results/h091_h094` in a job artifact; no changes are pushed to `decisions/` and no private token is used.

The ordinary repo CI includes H091-H094 contract tests. The new standalone workflow is read-only on PR and manual triggers; it does **not** commit research results to `main`, create bots or alter current H089/H088 prospective evidence.

### Mandatory caveats and research debt

1. Only BTC and ETH USDT perpetual markets, only 1H and resampled 4H. NQ/SPX/XAU/XAG and M15/M5, daily/weekly/monthly technical entries remain **NOT_TESTABLE** until separately verifiable data is acquired.
2. Multi-venue **price overlap** is a data quality check, not independent portfolio alpha replication.
3. Known historic OHLC (a single venue for the backtest), synthetic proxy next-open fills and assumed 10bps cost do **not** verify true order queue, spread, market depth, funding, roll, liquidation or broker fills. No executable capacity inference.
4. Test multiple comparisons, data snooping and strategy overlap remain serious risks. Descriptive t-statistics and wins are **not** selection gates. A true fresh holdout, purged walk-forward, multiplicity correction, negative controls and cost stress beyond simple 2× must precede an acceptance decision.
5. A real H093 fundamental/macro fusion requires immutable release timestamps (SEC filing, official economic print, verified historical funding / on-chain), instrument semantics, survivorship control and identical-cohort ablations. **Unobserved values must remain unknown.**
6. H094 forward tracking requires **new** frozen prospective signals first seen after a pre-specified recipe freeze, and many future outcome observations. There are no H091-H094 prospective trading outcomes yet.
7. Every strategy family missing from the H090 catalog is still an open research requirement. A CI pass means the plumbing works, not that the research is comprehensive.

**Next empirical milestones:** expand instrument/timeframe coverage (respect licensing and data continuity), implement the complete point-in-time LIQ/MSS/OB/FVG detectors and entry-type structural target matching, historical finance/macro joins, then separately freeze and start H094 first-seen-only prospective capture. Do not loosen existing registry gates or turn these exploratory observations into ACCEPT.

**Production isolation:** Neither the active H089 30-day observation nor any production rule, live bot or acceptance gate is modified.
