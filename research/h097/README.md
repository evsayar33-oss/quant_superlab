# H097 — Independent evidence gates (research-only)

This is the next **validation** layer for H095/H096. It does not authorize a strategy, change H089, modify the production registry or claim profitability.

## Implemented

1. Re-fetches native real OKX BTC/ETH 5m, 15m, 1H, 1Dutc closed bars; derives only complete 4H UTC candles. Source artifacts have SHA-256.
2. Reuses H095's closed-bar causal event detection and H096's stop-first, next-bar-open, no-gap, fully observed holding-period proxy.
3. Expanding anchored chronological walk-forward windows: first 100 bars training history, 24-bar embargo, then nonoverlapping 60-bar tests; expands by 60 bars. **No model is selected using the test data**. Fold statistics are descriptive, not independent new data.
4. All 216 prespecified family × side × parent-alignment × target × assumed-cost configurations are retained, including those with zero trades. Reports one-sided Bonferroni-corrected **normal-tail heuristic** for each configuration; these values are **not valid serial-dependence-robust p-values** and cannot certify alpha. Minimum 20 trades per fold, three usable folds and 100 trades overall are *descriptive sufficiency screens*, not statistical significance or a release gate.
5. Simple trailing-candle volatility regime breakdown, using only prior bars for the label.
6. Requests public **historical OKX funding-rate observations** for each instrument and saves raw observations with hash. No funding cost is applied to the strategy: exact settlement coverage, position notional and fills are not verified. Provider failure is explicitly recorded as NOT_VERIFIED, never replaced with a fabricated cost.
7. All outputs explicitly declare `alpha_accepted=false`, `research_complete=false`, `fresh_oos_verified=false`, `independent_venue_verified=false`, `prospective_verified=false`.

## Run

```bash
python -m unittest discover -s research/h097 -p 'test_*.py' -v
python research/h097/run.py --pages 12 --out results/h097
```

After merging, use Actions → **H097 — Walk-forward evidence and funding audit (read-only)** → Run workflow on `main`. Download `h097-independent-evidence-*` and inspect `summary.json`, per-timeframe walk-forward matrices and funding observation records.

## Critical limitations

- OKX pagination yields limited short-timeframe history; many walk-forward folds are sparse. Sparse evidence must be reported, not silently treated as failure or success of the underlying strategy.
- **Actual execution costs are not yet integrated.** OHLC alone cannot measure bid/ask spread, fill slippage, market impact, liquidation risk or latency. Funding-rate observations alone do not establish exact trade funding costs.
- **This is not untouched independent out-of-sample validation.** The family definitions were already explored in H091–H096. Reusing the same vendor data with embargoed folds is useful for diagnostics but does not reset the research discovery clock.
- Bonferroni heuristic does not correct trade dependence, changing volatility, overlapping signals across configurations, optional stopping or post-selection bias. Use dependence-aware bootstrap / White reality check or SPA with genuinely untouched samples for subsequent work.
- **No independent second venue replication or frozen first-seen prospective record** yet. No live fills or portfolio-level capital NAV.
- This phase intentionally does **not** implement H093 point-in-time macro/fundamental data; that remains a distinct unresolved gate.

No code under H089, bots, active production strategy registries or trading execution is changed.
