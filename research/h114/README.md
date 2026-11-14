# H114 — NEW signals for gold, silver, SPY, Nasdaq and US stocks

**Purpose:** Not review old H083/H089/H110 results. Form new causal hypotheses and run **new historical strategy simulations**, using market-specific assumed trading costs.

## Pre-registered coverage
- GLD/SLV (gold/silver ETF), SPY/QQQ (S&P 500/Nasdaq 100 ETF)
- GC=F/SI=F (gold/silver futures), ES=F/NQ=F (index futures; Yahoo continuous-contract **research proxies**, not executable individual contracts)
- Thirty US cash stocks, five new cross-sectional long-only allocation models (no unverified short availability)
- Seven distinct single-asset signal grammars: wick reclaim; shock absorption; directional efficiency; compression release; completed-prior-day gap repair; short/long volatility transition; failed breakout. Five fixed ETF combinations.

## Execution and cost model
Daily signals observe **completed t close** and enter at t+1 opening reference, exit/rebalance at the next opening reference. This is causal at a daily resolution, but open auction fill and trade capacity **cannot be independently verified from Yahoo**. Account execution must not be assumed.

ETFs and stocks use indicative **$1.50 per side per $2000 ticket**, plus optimistic/base/stress/double-stress assumed slippage **1/3/8/16 bps per side**. This is a reference ticket and may not reflect the user's broker pricing. Futures use a **$2.50-per-contract per-side proxy** with 1/2/4/8 adverse ticks per side; exchange and broker pass-through, roll gaps, initial/maintenance margin, live bid/ask and per-contract account commission are **unverified**. Contract multipliers/ticks used: GC 100 oz / 0.1, SI 5000 oz / 0.005, ES $50/point / 0.25, NQ $20/point / 0.25. Do not apply futures cost basis to ETF share prices.

Backtests are allocated as next-open-to-next-open returns; initial and terminal turnover costs are included. No index-point data are treated as tradable ETF or futures prices.

## Validation
Three chronological partitions: 2015–2020 discovery, 2021–2023 validation, 2024–13 Nov 2026 historical reused holdout. All historical samples are **already observable**, no truly sealed OOS. Compare every candidate against passive SPY and own buy-and-hold; base fees and stress; reject insufficient active coverage and zero trade, adjust monthly discovery p-values across **all** registered strategies via BH. Positive past returns are *research only*, not alpha ACCEPT.

Outputs: full scenario JSON; all-model split CSV; single strategy daily net return ledger; summary; Turkish committee report; explicit source errors.

## Running after merge
Actions > **H114 — New gold silver SPY NQ US stocks discovery** > Run workflow. The workflow also runs on PR. Review artifact named `h114-new-strategy-research`; **do not merge** unless regression and empirical evidence jobs are green.

No production or H089/H111 forward changes. No orders.
