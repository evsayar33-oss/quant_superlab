# H111 — 30-day prospective BTC 4H paper observation

**Exactly two frozen H110 watchlist hypotheses**: BTC 4H z-score reversion **long** and BTC 4H two-bar reversal **short**. Independently observed on OKX and Gate USDT perpetuals. No other parameters or signals optimized. **Never submits orders or uses API keys.**

## Operation

1. Merge the PR after CI and smoke tests are green.
2. Actions > **H111 — 30-day forward paper** > Run workflow on main, select `start` **once**. The 30-day UTC observation clock starts when this job executes, not at PR creation.
3. GitHub Actions hourly schedule (minute 10 UTC) automatically performs `tick`. A separate state-only branch `paper/h111-30d` holds append-only observations; main remains untouched. Never delete or force-push this branch.
4. Read each run's `h111-paper-report` artifact for summary and state. At 30 elapsed days the next tick closes any open positions and finalizes the study; no automatic alpha promotion.
5. `tick` dispatch is available for an additional observation, but does not replace missing hourly observations. Repeated `start` is rejected.

## Method

- Fetch native closed 1H BTC perpetual bars independently from OKX/Gate and aggregate complete 4H candles; fetch live public bid/ask quotes at observation time.
- Evaluate only the newest fully closed 4H signal. Enter *paper* at observed ask for long, bid for short (never retrospectively at the next-open price). Enforce one open position per venue/strategy and at most one entry per signal candle.
- Frozen H109 signal parameters, stop = 2× 14-bar mean range, target = 3× mean range, 48-hour maximum. Exit via later fully closed 1H OHLC using stop-first conservative proxy, or observed bid/ask for time/window close.
- Fee+slippage **assumptions**: 12, 16 and 20 bps round-trip; no actual fill, funding, market impact, realized NAV or spread history is claimed.
- Only fully closed 1H bars beginning after the entry's hour are evaluated for stop/target; the entry-hour path is an explicitly flagged blind spot. An hourly observer may miss intrahour path and does not simulate exchange-side protective orders.
- Missing quotes, stale quotes, OHLC gaps, network failures or missing venue data generate explicit outages. No interpolation or backfilling. A missed tick cannot be reconstructed as prospective.
- All tick timestamps, bar hashes, observed quotes, open positions and trades are committed to a dedicated persistent branch; GitHub Actions artifacts are secondary evidence. 30 days is a duration, not a guarantee of sufficient trades or valid statistical significance.
- State updates are serialized with Actions concurrency; branch protection/permissions must allow Actions to create/push `paper/h111-30d`.

## Important

**No production/H089 changes, no order routing, no API secrets, no automatic strategy promotion.** GitHub scheduled jobs may be delayed or skipped. An uninterrupted 30-day calendar period is not proof of 30-day market coverage. Funding and executable order fills remain unverified; report remains research-only.
