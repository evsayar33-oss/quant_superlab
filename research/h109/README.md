# H109 — One-shot exhaustive-within-scope historical research campaign

This PR **replaces the series of small H109+ merges** with ONE merge and ONE Actions workflow. It includes H103–H109 evidence reconstruction and a large, pre-fixed research matrix. Production trading, H089 and existing published dashboards remain untouched.

## Fixed test universe (no adaptive parameter search)

- 2 liquid perpetual assets: BTC and ETH, 2 venues: OKX and Gate, 2 causal timeframes: native 1H and strict complete-candle 4H, 2 directions: long/short.
- 8 signal families: 24/72 trend crossover, 24 Donchian breakout, z-score mean reversion, RSI2 reversal, 24-bar momentum, compression breakout, channel reentry, two-bar reversal; plus a calendar negative control.
- 144 venue-level strategy/control trials and 72 paired comparisons, with 64 paired non-control hypotheses.
- 6 assumed round-trip fee/slippage stress levels: 0, 10, 20, 40, 80, 120 basis points.
- Fixed 2x mean-bar-range stop, 3x mean-bar-range target, 48-hour maximum hold, next-bar open and stop-first when a candle touches both stops and targets. OHLC execution **proxy**, not actual execution.
- Same common BTC/ETH/OKX/Gate UTC window, strict source hash validation, no synthetic candles, fail on gaps, 50/25/25 train/validation/historical-tail splits with boundary-crossing trades purged.
- Causal BTC risk-on/off (last 72 bars) and historical high/low volatility (24/72 rolling range) subcohorts; report all regimes, do not choose after seeing outcomes.
- Weekly-cluster bootstrap interval, weekly sign-flip null and Benjamini–Hochberg descriptive q values over all eligible non-control venue-level hypotheses. Rejection gates: each venue n>=30 plus historical tail n>=10, both net R positive at 40 and 80 bps, both historical tails positive at 40 bps, both lower bootstrap limits >0, and both adjusted q<0.05. No alpha automatically accepted even if these conditions appear to pass.

## Single GitHub procedure

1. Wait for the PR's **CI** and **H109 one-shot evidence** checks to finish successfully.
2. Merge **only this PR** to main.
3. In Actions, select **H109 — ONE-SHOT multi-strategy research campaign** and **Run workflow** on main exactly once.

The run first retrieves H104 data a single time and reproduces H105–H109 diagnostics, then performs the full matrix. Download the **h109-one-shot-campaign** artifact. Its results include:

- `results/h109/campaign/committee.md` — committee decision counts;
- `results/h109/campaign/matrix.csv` — all paired decisions;
- `results/h109/campaign/summary.json` — machine-readable gate flags and failure/untestable reasons;
- `results/h109/campaign/trials.json` — full cost, regime, split and diagnostic metrics;
- `results/h109/campaign/manifest.json` — fixed hypothesis specification, time windows and source provenance;
- `results/h109/campaign/ledgers/*.json` — 144 SHA-256-checked trade ledgers;
- H105/H106/H107/H108/H109 baseline summaries.

## Non-negotiable limitations

**No historical test can finish a future, prospective OOS or live-execution observation today.** The universe above is comprehensive only within available comparable crypto OHLC data. Funding/mark prices, order-book market impact, liquidations, options, other exchanges/assets, 5m/15m 180-day native series, independent data and 30-day forward paper NAV are explicitly marked **NOT_TESTABLE** instead of fabricated. Results do not authorize deployment or H089 promotion.

The weekly resampling and BH q values are *descriptive*, not valid corrections for every form of snooping or market nonstationarity. Both venues are strongly correlated; passing both is not independent evidence. A `WATCHLIST_ONLY_NOT_ALPHA` result (if any) is a future-validation research proposal, not a profit claim.

This replaces serial merges with one verifiable historical decision artifact. No universal guarantee of profitability or exhaustive proof over all conceivable strategies is possible.
