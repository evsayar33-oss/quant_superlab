# Scan — crypto_major

- Variants tried: **1469** · global PBO: **0.156** · equal-weight benchmark Sharpe: 0.851 · Reality Check p (best vs benchmark): 0.84 · timeframe 1d · runtime 283s
- Single ideas and two-signal combinations (`A+B` = A confirmed by B): 30 combo families. Every variant's own result is in the matching `_variants.csv`.
- Ranked by walk-forward OOS Sharpe per family. Full-sample DSR is deflated by ALL trials.
- A scan result is a LEAD, not a decision. Register a hypothesis and run the gate.

| # | family | variants | WF OOS Sharpe | OOS CAGR | OOS MaxDD | 2x-cost Sharpe | family PBO | best full Sharpe | DSR(all trials) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | chop_switch+bollinger_breakout | 3 | 0.983 | 0.1727 | -0.1792 | 0.957 | 0.837 | 1.652 | 0.456 |
| 2 | chop_switch+ichimoku_cloud | 3 | 0.971 | 0.1556 | -0.1693 | 0.946 | 0.42 | 1.348 | 0.164 |
| 3 | chop_switch+volume_breakout | 3 | 0.936 | 0.1537 | -0.1911 | 0.912 | 0.843 | 1.597 | 0.358 |
| 4 | volume_breakout+chop_switch | 3 | 0.936 | 0.1526 | -0.1969 | 0.912 | 0.992 | 1.601 | 0.363 |
| 5 | bollinger_breakout+chop_switch | 3 | 0.904 | 0.1161 | -0.1458 | 0.882 | 0.649 | 1.633 | 0.455 |
| 6 | chop_switch | 2 | 0.891 | 0.167 | -0.2438 | 0.86 | 0.204 | 1.668 | 0.423 |
| 7 | ichimoku_cloud+chop_switch | 3 | 0.854 | 0.0979 | -0.098 | 0.837 | 0.919 | 1.023 | 0.025 |
| 8 | chop_switch+rsi_midline | 3 | 0.835 | 0.1385 | -0.2344 | 0.808 | 0.432 | 1.46 | 0.243 |
| 9 | ichimoku_cloud+keltner_breakout | 3 | 0.819 | 0.0931 | -0.103 | 0.796 | 0.83 | 1.519 | 0.35 |
| 10 | keltner_breakout+bollinger_breakout | 3 | 0.815 | 0.1383 | -0.2054 | 0.784 | 0.593 | 1.678 | 0.395 |
| 11 | keltner_breakout+chop_switch | 3 | 0.813 | 0.1053 | -0.1375 | 0.787 | 0.807 | 1.484 | 0.228 |
| 12 | keltner_breakout+volume_breakout | 3 | 0.801 | 0.1196 | -0.1831 | 0.773 | 0.351 | 1.494 | 0.247 |
| 13 | keltner_breakout | 12 | 0.793 | 0.1575 | -0.2193 | 0.764 | 0.428 | 1.617 | 0.322 |
| 14 | bollinger_breakout+volume_breakout | 3 | 0.79 | 0.1282 | -0.1849 | 0.762 | 0.781 | 1.566 | 0.311 |
| 15 | bollinger_breakout+keltner_breakout | 3 | 0.787 | 0.133 | -0.1983 | 0.756 | 0.806 | 1.727 | 0.477 |
| 16 | keltner_breakout+ichimoku_cloud | 3 | 0.775 | 0.1015 | -0.1878 | 0.742 | 0.903 | 1.365 | 0.22 |
| 17 | keltner_breakout+rsi_midline | 3 | 0.766 | 0.1513 | -0.2488 | 0.731 | 0.269 | 1.589 | 0.324 |
| 18 | chop_switch+keltner_breakout | 3 | 0.722 | 0.1104 | -0.2069 | 0.69 | 0.585 | 1.668 | 0.422 |
| 19 | volume_breakout+keltner_breakout | 3 | 0.721 | 0.113 | -0.2053 | 0.691 | 0.916 | 1.575 | 0.343 |
| 20 | bollinger_breakout+ichimoku_cloud | 3 | 0.72 | 0.0923 | -0.1527 | 0.69 | 0.444 | 1.495 | 0.277 |
| 21 | volume_breakout+ichimoku_cloud | 3 | 0.704 | 0.0966 | -0.2017 | 0.678 | 0.891 | 1.205 | 0.074 |
| 22 | ichimoku_cloud | 6 | 0.698 | 0.1561 | -0.3061 | 0.644 | 0.112 | 1.407 | 0.218 |
| 23 | volume_breakout+bollinger_breakout | 3 | 0.677 | 0.1119 | -0.2134 | 0.648 | 0.992 | 1.537 | 0.305 |
| 24 | ichimoku_cloud+volume_breakout | 3 | 0.67 | 0.0798 | -0.1191 | 0.641 | 0.483 | 1.32 | 0.14 |
| 25 | bollinger_breakout | 12 | 0.661 | 0.1239 | -0.2841 | 0.622 | 0.443 | 1.612 | 0.342 |

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

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bir tarama sonucu karar değil, adaydır; birçok varyant arasından seçilen sonuçlar ileride çökebilir. Önce `run.py --hypothesis` kapısı, seçim süreci için `Time machine test`. Kural: CLAUDE.md / AGENTS.md.


```yaml
# Suggested hypotheses from the scan (copy into hypotheses/registry.yaml, give real ids)
- id: S900
  rule: chop_switch
  confirm: bollinger_breakout
  confirm_within: [0, 3, 5]
  universe: crypto_major
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.983, family PBO 0.837"
- id: S901
  rule: chop_switch
  confirm: ichimoku_cloud
  confirm_within: [0, 3, 5]
  universe: crypto_major
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.971, family PBO 0.42"
- id: S902
  rule: chop_switch
  confirm: volume_breakout
  confirm_within: [0, 3, 5]
  universe: crypto_major
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.936, family PBO 0.843"
- id: S903
  rule: volume_breakout
  confirm: chop_switch
  confirm_within: [0, 3, 5]
  universe: crypto_major
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.936, family PBO 0.992"
- id: S904
  rule: bollinger_breakout
  confirm: chop_switch
  confirm_within: [0, 3, 5]
  universe: crypto_major
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.904, family PBO 0.649"
```
