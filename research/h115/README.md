# H115 — 180-day prospective H114 paper observation, 30/90/180 checkpoints

**Purpose:** Test NEW H114 hypotheses prospectively, not retrospectively re-rank the original 2015–2026 history and not promote BTC H111 or H089. This H115 experiment is a **separate paper-only program**. It submits **no orders** and needs **no brokerage API keys**.

## Pre-committed research arms

Five US30 stock cross-sectional models: residual momentum, volatility calm, defensive efficiency and two negative controls (shock recovery and gap repair). ETF arms: SLV wick reclaim, SPY trend efficiency, GLD vol-state diagnostic, QQQ trend diagnostic, SPY+QQQ equal-sleeve trend, GLD+SLV+SPY+QQQ equal-sleeve trend, GLD+SLV wick. Two futures **diagnostic-only** arms SI=F gap repair and ES=F trend efficiency. **No historical candidate selection or parameter tuning during the study.**

Signals reuse H114 source directly, with the full exact 30-stock membership list (no silently replacing failed tickers). H114 and H115 source SHA-256 values, the list of arms and market list are frozen in the persistent state at study inception.

## Scheduled observations

On merge to main, select **Actions > H115 — 180-day H114 forward paper > Run workflow > start** **once**. The 180 calendar-day clock starts on that dispatch. It does **not** auto-start on the scheduled runs and cannot be restarted without an explicit, separately reviewed experiment. Hourly provider polling is NOT assumed: the workflow schedules twice per NY trading weekday at **16:20 and 17:20 UTC**. Only the first valid observation each US trading date can enter the ledger. GitHub may delay or skip schedules; missing sessions are left missing. Both times occur within daytime US equity-market hours during US standard and daylight time.

Each observation fetches up to the most recent completed prior US equity daily close from Yahoo and separately obtains a **recent Yahoo 5-minute intraday close reference**, with source timestamp. No trade is filled retrospectively at the daily official open. Price-to-price simulated returns only accumulate between **two genuinely observed** snapshots. Newly computed target weights apply *after* the current mark, with round-trip proxy costs charged on turnover. No price interpolation or reconstruction of missing days.

**This is NOT executable bid/ask trading and should not be called realized live execution.** Yahoo data may be 15+ minutes delayed; opening auction, share/contract spread, realized orders, exchange/broker fee invoices, futures roll, split/corporate actions and margin requirements are unverified.

## Costs

Cash ETFs/stocks: historical H114 base proxy 3 bp + $1.50/$2k = **10.5 bp per side**, stress **15.5 bp**, double stress **23.5 bp** per side. Futures: historical H114 assumed per-side 2/4/8 adverse ticks + $2.50 commission per contract per side, converted by GC/SI/ES/NQ contract multipliers. Futures continuous `=F` prices are **non-investable diagnostics**, not a contract-accurate portfolio.

## State and evaluation

Append-only per-session SHA-256-linked snapshots on dedicated **`paper/h115-180d`** branch (state.json), never on main. GitHub Actions concurrency serializes jobs. GitHub history and hash checks detect accidental rewriting; no proof against a malicious administrator with force-push permissions. Secondary reports uploaded per workflow run as GitHub Actions artifacts.

Review dates are automatically derived from first successful `start`: **30, 90, 180 calendar days**. Checkpoints report number of observed sessions, missed observations, NAV (1x unlevered) and SPY passive benchmark. They do **not** activate a trade or automatically approve any arm. A statistically defensible decision requires meaningful out-of-sample coverage, fee evidence, account-level NAV reconciliation, sufficient independent rebalances/market weeks, market regime variation, split/delist PIT audit for stocks, and for futures independently verified contract mapping, roll, spreads and margin. **180 days may still be insufficient**.

No changes to H089, H111, H114 code, production, central decision registry or automated real-money routing. GitHub repository settings must permit Actions `contents: write` to create and push the isolated `paper/h115-180d` branch.
