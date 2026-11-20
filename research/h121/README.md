# H121 — H054-MOM2 and Regime Band-30 independent PAPER intelligence

Source: evsayar33-oss/h054_spot_bot. It is NEVER edited by this lane.

H121 reads by SHA-pinned GitHub sources:
- main: state/state.json, state/paper.json, logs/equity.csv and logs/trades.csv (H054-MOM2 local PAPER).
- paper/regime-band30-bitget: state.json (independent Regime Band-30 PAPER).

The two portfolios NEVER share NAV, simulated orders, instrument universe, start date or baseline.
The H054 main equity ledger has entries from **before** MOM2; a full-log +/-% value is
NOT a MOM2-only walk-forward performance estimate. Regime Band-30 is a different
10,000-USDT test with observed Bitget bids/asks. H116/H117 Binance history
is not a Bitget realized paper or broker execution result.

Research checks: SHA ancestry for each source branch, append-only row counts,
4h candle monotonicity, source timestamp reconciliation, split book coverage,
unique observed candles, cumulative new outages/missed candles and closed
paper approval. No retroactive reconstruction of candles or synthetic fills.

First bootstrap seeds historical gap/outage counts without sending ancient
alerts; only later **new** outages, missing candles, meaningful stale bars
(2+ 4h intervals), evidence of newly observed Band-30 PAPER trades, PAPER
permission revocation or a 15% drawdown threshold crossing trigger messages.
All alerts are explicitly PAPER diagnostics, never alpha ACCEPT.

H121 runs every six hours with immutable source SHAs. A separate dedicated
Superlab branch research/h121-h054-evidence owns the observation journal,
manifest, latest report and acknowledged Telegram (or Issue) receipts.
No change to any Quant Superlab central ACCEPT gate, H119/H120, bot signal,
execution configuration, paper start date, ledger or optimizer.

The source branch may advance between H121 polls: reading its pinned commit
does not mean that the bot processed all scheduled 4h closes. Staleness and
observed historical gaps remain explicit.

Commands: python -m unittest discover -s research/h121 -p 'test_*.py' -v
and original python tests/test_core.py on PR.

## Additional read-only execution quality accounting

Band-30's already-frozen Bitget PAPER ticks record the actual top bid/ask
and quote timestamps. H121 now reports quote count, historical median and
95th-percentile observed top-book spread, quote age, and missing displayed
size. It does not synthesize fills or add these spreads to existing fees a
second time. These are diagnostic values and do not alter band30 NAV.

The MOM2 PAPER engine, by contrast, uses last-close reference prices plus
assumed fixed fees/slippage; it does not record contemporaneous bid/ask
and full order-book depth for each simulated order. H121 explicitly marks
this as an unknown execution-calibration gap, not a profitable or failed
trading decision.

No market-impact capacity, queue priority or brokerage fills are independently
verified for either strategy. No source code, secrets, alerts or already
running PAPER windows are modified by this diagnostics-only addition.

## Prospective liquidity coverage (20 November 2026)

Bitget Band-30's existing source PAPER workflow now archives current top
bid/ask displayed sizes (source change PR #24) without altering its NAV,
trade decisions, or paper fill prices. H121 matches a simulated PAPER
trade's observed timestamp and side to the SAME source tick's quote.
It counts how often simulated order USDT exceeds *displayed top-level*
notional and how many past trades lack contemporaneous size entirely.

This does **not** pretend larger orders failed, invent deeper order-book
prices, or retroactively restate profit. Top-quote capacity is a partial
liquidity warning, not guaranteed or executable fill volume. No bot or
strategy settings changed and the ongoing 90-day forward ledger stays intact.
