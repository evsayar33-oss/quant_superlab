# Calibration — 8/8 passed

If any check fails, verdicts are not trustworthy until it is fixed.

| id | check | pass | result | expected |
|---|---|---|---|---|
| C1 | identity: engine buy&hold == raw returns | ✅ | max abs diff 0.00e+00 | < 1e-10 |
| C2 | Faber SMA200 timing on SPY (2000+) | ✅ | timing SR 0.696 DD -0.2154 | buy&hold SR 0.589 DD -0.5519 | timing DD at least 15 pts shallower, Sharpe within +-0.4 |
| C3 | TSMOM 12m cross-asset (2006+) | ✅ | TSMOM SR 0.753 DD -0.1578 | EW SR 0.583 DD -0.3701 | Sharpe > 0.1 and drawdown shallower than equal weight |
| C4 | low-vol portfolio volatility vs equal weight | ✅ | vol ratio 0.90 | < 0.92 |
| C5 | GLD buy&hold CAGR 2005+ (data sanity) | ✅ | CAGR 0.102 | 5%..14% |
| C6 | USDTRY rise since 2010 (FX sanity) | ✅ | x33.9 | > x10 |
| C7 | look-ahead canary (today's return as signal) | ✅ | with lag SR 0.39 | without lag SR 11.50 | lag < 1.5, no-lag > 5 |
| C8 | trade engine vs weight engine (same SMA200 idea) | ✅ | trade engine SR 0.667 | weight engine SR 0.696 | within +-0.25 (fills differ: next open vs close) |