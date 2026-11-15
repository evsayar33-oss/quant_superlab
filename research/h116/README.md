# H116 — BTC/ETH/SOL/BNB 4h net-profit discovery

This is a new **research-only** campaign in quant_superlab. It **does not change h054_spot_bot** or live execution.

- Frozen baseline: H054 legacy and H054-MOM2 (SMA200 + 30/90/180 TSMOM + 40% vol + 10% band on BTC/ETH).
- Predefined variants: stricter 3-vote momentum, diversified four-asset momentum, risk-targeted four-asset basket, cross-sectional 90/180d top-1/top-2 rotation, 50% vol target stress, BTC risk regime, moving-average ensemble, 55/20d breakout, BTC drawdown guard. All **long-only or cash, total exposure <= 100%, no borrowing**.
- Directly reuse **quant_superlab/lab/assetdata.py** Binance Vision archived 4h spot candles with complete-bar, no gap, monotonic/index and SHA256 checks. No synthetic financial bars in empirical evidence; synthetic data used only for tests.
- Every candidate is evaluated identically at next-open prices, with 15/30/45 basis points cost **per traded side** (fees+slippage assumed, not real fills), opening rebalances and terminal liquidation fees. Funding hedges are excluded; don't mix results with H054+arb claims.
- Fixed chronological 2021–2022 discovery, 2023–2024 validation, 2025–present **reused** historical tail. The tail is NOT a sealed true OOS sample, since we examined the period during prior H054 work. Descriptive paired monthly bootstrap CI is not an alpha-acceptance test.
- Historical winner gate: baseline beat on total return at 15/30 bps, 2023–2024 and reused 2025–present returns both higher, max drawdown no worse than MOM2 by >5 pp. A winner is research-only.
- The +200% total historical return target is **not a guaranteed target**, and arbitrary leverage is never counted as alpha.

## Trigger
This PR triggers an evidence workflow automatically on \`pull_request\` and a standalone GitHub Actions \`workflow_dispatch\` is available after merge.

Workflow: **H116 — 4H crypto spot profit discovery**.

Download artifact \`h116-spot-discovery-...\` with \`summary.json\`, \`matrix.json\`, \`matrix.csv\`, \`committee.md\`, and complete dated per-candidate net NAV return ledgers \`nav_...csv\`.

**Do not modify strategy weights in the live bot, or claim a winner, until empirical outputs and limitations have been reviewed.**
