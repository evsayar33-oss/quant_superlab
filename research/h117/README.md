# H117 — Protect profits from turnover costs

Follow-on to the fully completed H116 actual-market evidence. No bot code or trading configuration is modified.

Predeclared: H054-MOM2 baseline, H116 BTC-regime winner, 7/14/28 day scheduled rebalances, 20/30/40 percent trade bands, combinations, and MOM2/regime mixtures (25/50/75%). Fifteen candidates, 15/30/45bp cost per traded side, same independent next-open execution and frozen source/splits as H116.

A stricter historical selection gate requires outperforming H054-MOM2 at **all three cost levels** and on both 2023–24 and 2025–present (already exposed) historical partitions, with max drawdown <= MOM2 + 5 percentage points and at least 10% lower turnover than original BTC regime rotation. It is valid for **zero** candidates to pass. No statistical claim of prospective alpha.

The GitHub Actions pull request event runs deterministic no-lookahead tests and downloads actual Binance Vision 4h archived OHLC through existing quant_superlab modules, then uploads full \`h117-spot-turnover-discovery\` evidence. Use the workflow's \`workflow_dispatch\` after merging if desired. This workflow cannot submit orders.

Known limitation: fixed-weight OHLC backtests do not model market impact, venue-specific live spread/fill, funding, or exact balance drift. Funding arbitrage is deliberately excluded from both baseline and candidates.
