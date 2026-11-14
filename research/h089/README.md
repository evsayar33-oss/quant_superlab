# H089 — Independent venue, cost and prospective paper evidence

**Scope: research-only. No orders, no strategy optimization, no new ACCEPT.**

## What is actually measured

1. Fresh BTCUSDT/ETHUSDT linear perpetual bid/ask from H088's four-venue parser, retained under a separate H089 SHA-256 chain.
2. Official OKX and Bitget contract metadata, current funding snapshots, and up to 100 recent independent historical funding records per venue and symbol. Historical records are aligned by **exact settlement timestamp**. No invented matches or interpolation.
3. A timestamp-matched cost envelope at 1,000 / 10,000 / 100,000 USDT, with *explicitly assumed* 2 / 5 / 10 bps one-way commission. OKX book sizes are converted to base units **only when the public instrument API verifies linear contract type, ctValCcy and ctVal**. Bitget book size units remain unknown and its capacity/cost fields are null.
4. H063–H065 paper portfolio close marks from Yahoo, starting with the **first price observed after the first recorded decision**. The first later price is a basis, not profit. An initial hypothetical entry commission is charged at that basis. Subsequent marks calculate gross returns on **prior** holdings, then apply newly observed decisions for **future** intervals and deduct hypothetical turnover costs. All timestamps, data source labels, gaps and scenario NAVs are chained and committed.
5. The first forward observation in main is 2026-11-14 10:16 UTC. On Saturday 14 November, the last closed futures daily bar is 13 November: **AWAITING_POST_FIRST_SEEN_CLOSE is the correct status**, not a positive return or a data failure. A new bar after the first-seen time is needed before a basis can be set.

## Key limitations — do not call this proven profitability

- Yahoo daily futures close is **not** an actual tradable fill; contract roll adjustments, margin, funding, interest, broker-specific fees, and true execution impact are not independently verified. Futures symbols GC=F, YM=F etc. are Yahoo continuous futures *proxies*; they are not automatically executable contracts.
- OKX and Bitget are independent *exchange feeds*, but BTC and ETH are the same economic underlying. Cross-venue funding overlaps are **not** an independent H056 portfolio backtest. H056 requires the original complete universe, point-in-time listings, funding payment times, executable hedge, financing and survivorship controls, and new data without hypothesis reuse.
- Book top-of-book does not give full depth or realized slippage. A cost number is emitted only when capacity is verifiable; **impact and funding remain unverified**.
- Scenario NAV is **not actual realized forward PnL**. It is a timestamped, cost-scenario, marked paper estimate. The `forward_pnl_verified=false` field is intentional.
- Git hash chains reveal edits in the retained files; Git commit history gives an additional audit trail, but neither establishes external timestamp notarization.
- 30 calendar days of observations do not alone establish statistical alpha. Missing sessions and repeated tests must remain visible.
- No historical performance prior to the first recorded decision is included in the forward NAV.

## Post-merge operation

1. Merge H089 PR into main only after regression, actual venue/funding/price smoke and repository CI all pass.
2. Actions > **H089 — Independent costs and prospective paper NAV** > **Run workflow**. It also runs after successful Paper Watch and on weekday schedule. It **does not modify H088 records**.
3. Verify five hash-linked files in `decisions/evidence/`: `h089_quotes.jsonl`, `h089_venue.jsonl`, `h089_cost.jsonl`, `h089_funding_overlap.jsonl`, `h089_forward.jsonl`.
4. Verify H065 is `AWAITING_POST_FIRST_SEEN_CLOSE` before the first subsequent daily close; do not backfill. Later runs should establish BASELINE then MARK_TO_MARKET.
5. Confirm quote/metadata/funding provenance and the failed-source diagnostics; do not treat a successful workflow as an alpha verdict.
6. For **real execution** cost validation, provide sanitized fills (exchange, instrument, side, order submission/execution UTC, fill price, size, fee amount/currency, funding and position/margin costs). No API keys or account identifiers should be committed.

## Evidence gates

| Gate | H089 outcome |
|---|---|
| Timestamped multi-venue quote | Measured when >=2 reachable |
| OKX multiplier and indicative top-book cost | Conditional on official metadata and capacity |
| Bitget multiplier / depth / true fill | UNKNOWN, not zero |
| Funding cross-venue recent overlap | Diagnostic only |
| H056 independent full strategy replay | NOT COMPLETE |
| H063–H065 cost-scenario paper marks | Starts only after first-seen date and subsequent observed close |
| Realized broker PnL / statistically validated alpha | NOT COMPLETE |

**No production trading files or central strategy decisions are modified.**
