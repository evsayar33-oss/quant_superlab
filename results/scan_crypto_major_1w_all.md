# Scan — crypto_major

- Variants tried: **1469** · global PBO: **0.4** · equal-weight benchmark Sharpe: 0.852 · Reality Check p (best vs benchmark): 0.44 · timeframe 1w · runtime 95s
- Single ideas and two-signal combinations (`A+B` = A confirmed by B): 30 combo families. Every variant's own result is in the matching `_variants.csv`.
- Ranked by walk-forward OOS Sharpe per family. Full-sample DSR is deflated by ALL trials.
- A scan result is a LEAD, not a decision. Register a hypothesis and run the gate.

| # | family | variants | WF OOS Sharpe | OOS CAGR | OOS MaxDD | 2x-cost Sharpe | family PBO | best full Sharpe | DSR(all trials) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | supertrend_flip+roc_breakout | 3 | 0.705 | 0.1606 | -0.376 | 0.701 | 0.761 | 0.878 | 0.176 |
| 2 | hammer_star | 4 | 0.697 | 0.0504 | -0.0517 | 0.681 | 0.573 | 0.558 | 0.001 |
| 3 | supertrend_flip+psar_flip | 3 | 0.696 | 0.108 | -0.2123 | 0.692 | 0.974 | 0.953 | 0.107 |
| 4 | heikin_ashi | 6 | 0.663 | 0.2095 | -0.4587 | 0.632 | 0.009 | 1.269 | 0.556 |
| 5 | psar_flip+cci_breakout | 3 | 0.64 | 0.1345 | -0.3299 | 0.634 | 0.707 | 0.92 | 0.177 |
| 6 | supertrend_flip+heikin_ashi | 3 | 0.624 | 0.1676 | -0.3193 | 0.619 | 0.54 | 1.024 | 0.232 |
| 7 | cci_breakout+roc_breakout | 3 | 0.613 | 0.1474 | -0.3642 | 0.605 | 0.918 | 1.007 | 0.245 |
| 8 | psar_flip+heikin_ashi | 3 | 0.608 | 0.1587 | -0.3587 | 0.603 | 0.939 | 1.02 | 0.251 |
| 9 | roc_breakout+supertrend_flip | 3 | 0.605 | 0.0817 | -0.23 | 0.597 | 0.983 | 0.497 | 0.025 |
| 10 | cci_breakout+heikin_ashi | 3 | 0.602 | 0.1583 | -0.3772 | 0.592 | 0.39 | 1.047 | 0.293 |
| 11 | psar_flip | 6 | 0.582 | 0.153 | -0.4705 | 0.574 | 0.092 | 1.102 | 0.304 |
| 12 | roc_breakout+cci_breakout | 3 | 0.577 | 0.1274 | -0.2677 | 0.568 | 0.521 | 0.931 | 0.145 |
| 13 | psar_flip+roc_breakout | 3 | 0.567 | 0.1273 | -0.3205 | 0.563 | 0.93 | 0.842 | 0.152 |
| 14 | supertrend_flip | 10 | 0.562 | 0.1513 | -0.3938 | 0.556 | 0.051 | 1.044 | 0.265 |
| 15 | cci_breakout | 12 | 0.555 | 0.1375 | -0.424 | 0.546 | 0.082 | 1.006 | 0.25 |
| 16 | roc_breakout+heikin_ashi | 3 | 0.528 | 0.1349 | -0.4968 | 0.516 | 0.182 | 0.954 | 0.2 |
| 17 | hammer_star+heikin_ashi | 3 | 0.504 | 0.0063 | -0.0125 | 0.49 | 0.923 | 0.565 | 0.002 |
| 18 | macro_risk_switch | 12 | 0.493 | 0.1323 | -0.6118 | 0.488 | 0.026 | 0.964 | 0.238 |
| 19 | supertrend_flip+cci_breakout | 3 | 0.485 | 0.0995 | -0.3271 | 0.48 | 0.523 | 0.922 | 0.162 |
| 20 | roc_breakout | 30 | 0.472 | 0.1093 | -0.4703 | 0.462 | 0.174 | 0.977 | 0.235 |
| 21 | vwap_cross | 6 | 0.458 | 0.112 | -0.5733 | 0.44 | 0.02 | 1.05 | 0.3 |
| 22 | psar_flip+supertrend_flip | 3 | 0.457 | 0.0848 | -0.2703 | 0.451 | 0.521 | 0.918 | 0.144 |
| 23 | elder_impulse | 4 | 0.457 | 0.1122 | -0.5745 | 0.442 | 0.013 | 1.009 | 0.293 |
| 24 | seasonality_same_month | 4 | 0.439 | 0.1005 | -0.6625 | 0.43 | 0.108 | 0.351 | 0.005 |
| 25 | ppo_cross | 4 | 0.437 | 0.1006 | -0.489 | 0.427 | 0.114 | 0.834 | 0.139 |

## Skipped / failed families
- dxy_metal_switch: macro series DX-Y.NYB unavailable
- real_yield_switch: macro series TIP unavailable
- gold_silver_ratio: macro series GC=F unavailable
- copper_gold_rotation: macro series HG=F unavailable
- cot_contrarian: COT positioning unavailable for this universe
- cot_commercial_follow: COT positioning unavailable for this universe
- cot_commercial: no trades / flat returns in every variant
- cot_extreme: no trades / flat returns in every variant
- funding_extreme: no trades / flat returns in every variant
- gap_fade: no trades / flat returns in every variant
- halloween: no trades / flat returns in every variant
- hammer_star+cci_breakout: no trades / flat returns in every variant
- hammer_star+supertrend_flip: no trades / flat returns in every variant
- ml_ridge_rank: no trades / flat returns in every variant
- weekday_long: no trades / flat returns in every variant

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bir tarama sonucu karar değil, adaydır; birçok varyant arasından seçilen sonuçlar ileride çökebilir. Önce `run.py --hypothesis` kapısı, seçim süreci için `Time machine test`. Kural: CLAUDE.md / AGENTS.md.


```yaml
# Suggested hypotheses from the scan (copy into hypotheses/registry.yaml, give real ids)
```
