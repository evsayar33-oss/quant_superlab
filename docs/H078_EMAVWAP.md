# H078 — 9 EMA x VWAP cross (owner's video, SLV 3m)

Pre-registered: `config/emavwap.yaml` (rules + acceptance written before results). Code: `lab/emavwap.py`.
Run: `python -m lab.emavwap` → `results/h078_emavwap.json`.

## Rule tested
- VWAP anchored at session open (US 09:30 ET; crypto 00:00 UTC). EMA over close.
- Long when EMA crosses above VWAP (signal at bar close, fill next open). Exit on opposite cross (or close back through EMA). Flat at session end.
- Costs per side: stocks 3 bps, crypto 8 bps; 2x run doubles them.

## Data (all free)
| Timeframe | US stocks/ETFs (yahoo) | BTC, ETH (binance vision) |
|---|---|---|
| 3m | 1m resampled, only 2026-09-28 → 2026-10-23 | 2023-01 → 2026-10 |
| 5m / 15m | 2026-07-31 → 2026-10-23 | 15m: 2023-01 → |
| 60m | 2023-11 → 2026-10 | 2023-01 → |

## Result — video setting (EMA 9, exit cross, long only), 1x cost
| Market | 3m | 5m | 15m | 60m |
|---|---|---|---|---|
| SLV | n40, −15.8 bps, PF 0.37 | n57, −12.0, 0.63 | n25, −2.6, 0.92 | n49, +4.8, 1.28 (−1.2 at 2x) |
| GLD | −11.3, 0.18 | −6.9, 0.57 | −10.7, 0.38 | −3.7, 0.75 |
| SPY | −5.3, 0.47 | −6.1, 0.49 | −7.3, 0.41 | −12.4, 0.40 |
| QQQ | −8.6, 0.38 | −7.3, 0.48 | −4.8, 0.63 | −3.9, 0.69 |
| TSLA | −14.8, 0.46 | −13.5, 0.63 | −15.9, 0.61 | −7.7, 0.77 |
| NVDA | −12.8, 0.46 | −16.4, 0.49 | −15.5, 0.50 | −21.9, 0.45 |
| BTC | n5844, −13.0, 0.59 (equity −99.96%) | — | −9.4, 0.78 | −11.1, 0.78 |
| ETH | n5924, −11.5, 0.68 (−99.93%) | — | −4.6, 0.91 | −14.1, 0.78 |

Acceptance passed in **0 / 30** cells. Across all 360 trials, 25 had a positive mean at 1x cost (7%, below what
chance gives) and none was positive in both halves, at 2x cost and on neighbour EMA lengths together.
Win rate on 3m is 13–26%: the cross arrives after the move, and VWAP chop gives many small losses.
Even before costs the 3m edge is ~0 to −10 bps per trade.

## Verdict
Not profitable. Daha iyisi bulunamadı. Do not trade it.

## Weak points
- US 3m sample is only ~4 weeks (yahoo 1m limit); 5m/15m only 60 days. Crypto 3m (3.8 years, ~5,900 trades) is the
  strong evidence, but crypto has no session open, so the VWAP anchor is UTC midnight.
- Only SLV 60m and TSLA 60m (EMA 7) look positive; both fail the halves check — selection luck among 360 trials.
- Indicator code from the video was not available; the exit triangle rule is inferred (two exit variants tested).
