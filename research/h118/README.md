# H118 — Three-strategy, 90-day prospective PAPER verification

H116/H117 discovered higher historical returns; they did **not** prove prospective alpha. This study freezes exactly three models at inception:

1. H054-MOM2 — BTC/ETH baseline
2. H117 Regime Band-30 — four-asset top-two rotation with BTC regime and 30% band
3. H117 Weekly Band-20 — seven-day rebalance and 20% band

The models use the already-merged H117 research signal definitions. **No modifications to h054_spot_bot, no real exchange orders, no secrets and no automatic production promotion.**

## After merge

In quant_superlab, open Actions → H118 — 90-day three-strategy prospective PAPER → Run workflow. Choose main and mode start **once**. This initializes three independent virtual 10,000-USDT accounts. The first successful execution starts the 90-calendar-day timestamp; subsequent automated runs at UTC 00:20, 04:20, 08:20, 12:20, 16:20 and 20:20 use mode tick.

Permanent, append-only observation records (except naturally growing JSON state) are kept on a separate state-only orphan branch: paper/h118-90d, state.json. Do not delete, reset or force-push it. A second start is rejected. Every run publishes a report artifact named h118-paper-observation-<run-id> containing summary.json and state.json. On PR the workflow runs only offline regression tests; it cannot start the forward study.

## Data integrity and accounting

The prospective venue is **OKX spot**, different from historical Binance. Native closed 4h OHLCV from a fixed 2025-11-01 indicator anchor warms up the unchanged H117 causal signals; prices from before actual observations **never** become historical paper fills. A fresh public bid/ask snapshot is collected at the actual observation time. Paper sells occur at the observed bid and buys at the observed ask, plus assumed 15bp fee/slippage per traded side. Cash, spot quantity, every notional, tick NAV and observations are recorded. No margin, borrow, funding, shorts, broker API keys or transactions. Historical returns are not spliced into forward NAV.

If price series are missing, quotes stale, API unavailable, source timestamps inconsistent, or one asset has invalid data, the system records an outage with no trades and no synthetic replacement. Each closed candle may be acted on only once. If GitHub Actions skips an interval, missing observations stay missing; an observed later candle does not create intermediate fills.

At 30, 60 and 90 elapsed days, compare cumulative NAV, model-by-model drawdown, turnover, trade frequency, cost assumptions and missed-tick coverage. These interim checkpoints are informational. A final 90-day report does not imply statistical significance or verified executable alpha.

## Operational constraints

- The schedule belongs to the default branch only, so the forward study is inactive before merge + manual start.
- Repository Actions permissions must allow the workflow to create and push paper/h118-90d. If blocked, **do not** claim observations persist.
- No pre-start synthetic holdings or retrospective profit counting.
- The requested strategy, Regime Band-30, remains a research comparator and is **not** installed as the actual h054_spot_bot trading strategy.
