# H095 — Confirmed-candle ICT event research (first implementation)

This PR introduces a deterministic, **causal** event inventory for the existing H091 BTC/ETH real 1H candles and 4H resampling. No existing production strategy, H089 prospective watch, ACCEPT gate or live trading code is changed.

## Exact rules (operational definitions, not discretionary ICT certification)

- **Swing high/low:** strict higher/lower pivot relative to `left=2` previous and `right=2` subsequent bars; event is *observed only after right-hand bar closes*. Ties are not pivots.
- **LIQ sweep:** a candle wicks beyond the latest *previously confirmed* pivot and closes back inside; side describes anticipated post-sweep direction. An absence of sweep events is **not** proof of no liquidity taken.
- **BOS:** candle close crosses a previously confirmed pivot after previous close on the opposite side. **MSS:** same crossing, but only if an opposite-direction sweep after pivot confirmation was previously recorded. This is an explicit simplified MSS definition, not full swing-structure regime validation.
- **OB formed:** the most recent opposite-color candle among the eight bars preceding a BOS/MSS; full candle high–low is the provisional zone. **OB touch:** first *subsequent* bar intersecting the zone. No entry fill inferred at the touch.
- **FVG formed:** 3-bar nonoverlap (current low > high two bars earlier, or current high < low two bars earlier), only when the third bar closes. **FVG touch:** later intersection. **iFVG confirmed:** a *later close* through the opposite edge of that gap, reversing its directional interpretation. This is not a profitable trade signal.
- **Fibonacci 0.5:** midpoint of latest two independently confirmed high/low pivot anchors, evaluated at candle close. Range validity and anchor timing are enforced; no future swing anchor.

**Data integrity:** 1H/4H timestamp alignment, strictly ascending timestamps, finite positive OHLC and contiguous segment boundaries. Missing hours break the detection segment. All events include `observed_at_ms`, `bar_index`, unique stable event ID, zone or pivot reference and explicit data provenance. No 5m/15m/1D event claims are made from hourly candles.

## Run

```bash
python -m unittest discover -s research/h095 -p 'test_*.py' -v
python research/h095/run.py --pages 12 --out results/h095
```

Actions > **H095 — Causal ICT events (research-only)** > Run workflow on main after merging. Output is an **Actions artifact only**, with raw source hash, event lists and per-timeframe counts. It does not write or modify the production registry or active H089 watch.

## What this does not yet establish

This is a *real-data event detector*, not a completed 5m/15m/1H/4H/daily multi-timeframe entry/TP study. In particular, no fill execution model, stop-loss invalidation, true order block or liquidity TP, future-only prospective strategy record, macro/fundamental PIT integration, independent venue trade replication, multiple-testing correction or independent alpha proof is included. Those are explicit future research gates, not hidden successes.

H095 is designed to be the **first isolated milestone** of the requested multi-timeframe ICT research. Follow-on research must obtain independently verified finer-timeframe candles and daily data before comparing entry families or attaching real costs and portfolio risk to strategies.
