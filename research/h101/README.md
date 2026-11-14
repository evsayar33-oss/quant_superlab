# H101 — Trade-level cost stress and sample-coverage diagnosis

## Why
H100 on `main` (run 43594999433) completed successfully, evaluating 96 configuration cells: 91 lacked three-venue supporting samples, 5 showed mixed/negative performance, and **none** cleared a consistent-positive descriptive screen. There was no accepted alpha. H099 did not preserve the initial risk/entry price needed to convert additional assumed execution basis points into R.

## What H101 measures
- Fetches genuine read-only OKX, Gate, Bitget and MEXC perpetual BTC/ETH 15m + 1H candles. Derives complete 4H higher-timeframe bars exclusively from complete 1H groups.
- Reuses H095/H096 detector, parent-context, next-open entry, stop-first candle simulation, 1R target and 24-bar max hold. **Does not alter** H096's documented parent-event requirement for the `all` cohort, and does not search new parameter combinations.
- Preserves per-venue, per-configuration **trade ledgers** with entry/exit timestamps, entry price, initial price risk, and assumed net R at fixed **20, 40, 80 bps** round-trip costs. Cost conversion is `delta_bps / 10000 * entry_price / initial_risk`. These are *scenarios*, not measured fills/spread/slippage/impact/funding.
- Splits each venue's own available history at a fixed chronological 70% threshold. The final 30% is labeled **historical tail**, **not untouched prospective OOS**. Different venue coverage windows can differ; source manifests expose range, gaps and hashes.
- Reports whether all 3 reachable independent venues have >=30 trades for each configuration, and whether the means remain positive at 80bps. A separate flag requires at least 30 trades in *each* venue's historical tail. Data access failures and inadequacy remain visible. 96 fixed scope configurations are evaluated with no winner optimization.

## Deliberate proof limitations
- No alpha can be accepted, even when three venues are positive: overlapping crypto markets and familywise multiple testing make these results dependent and exploratory.
- 20/40/80 bps are **assumed** all-in round-trip costs; no real execution, bid/ask order books, position sizing, funding settlement or portfolio NAV verification is claimed.
- The same frozen historical dataset used repeatedly for study is **not** independent prospective evidence.
- H096's `all` cohort requires a parent event, and therefore is not truly unconditional; corrected signal semantics belong to a separately versioned methodology.
- More historical trade opportunities and reliable prospective, realistic execution evidence are required before any strategy approval.

## Run
```bash
python -m unittest discover -s research/h101 -p 'test_*.py' -v
python research/h101/run.py --pages 8 --out results/h101
```

After green PR checks, merge and run Actions → **H101 — Trade-level costs and sample diagnostics (read-only)** on `main`. Review 90-day `results/h101/summary.json` and `trade_ledgers/`. No H089 or production changes, no automatic daily scan added.
