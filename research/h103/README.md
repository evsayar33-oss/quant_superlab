# H103 — Fixed lower-turnover hypotheses (research-only)

Predeclared, unchanged parameters before running new H103 evidence:
- **TREND_24_72**: 24/72 completed-bar simple moving-average cross, next candle open.
- **BREAKOUT_24**: close crosses prior 24 completed-bar high/low, next candle open.
- BTC and ETH perpetual markets on OKX, Gate, Bitget and MEXC. Native 1H and strictly complete 4H candles derived from 1H.
- 14-bar mean high-low range proxy; stop at 2x range, target at 3x range; stop-first candle ordering, max 48 bars on 1H or 12 bars on 4H.
- Independent per-family/per-side non-overlapping trades, fixed 20/40/80 bps assumed round-trip cost; historical 70/30 chronological partition. No optimization or winner selection.
- Cross-asset relative strength explicitly **deferred** pending synchronized causal cross-asset data and portfolio accounting. Do not represent it as tested.

## Restrictions
This is a fresh *historical exploratory* test, not prospective independent OOS, verified execution, funding or portfolio NAV. 30-trade eligibility is a descriptive coverage floor, not statistical significance. Data from venues is dependent and 1H/4H observations overlap. All alpha acceptance flags remain false. No production/H089 changes.

## Execute
```bash
python -m unittest discover -s research/h103 -p 'test_*.py' -v
python research/h103/run.py --pages 8 --out results/h103
```
After successful PR checks, merge and manually run **H103 — Fixed lower-turnover hypothesis screen (read-only)** on main. Inspect summary and ledgers in the 90-day Actions artifact.
