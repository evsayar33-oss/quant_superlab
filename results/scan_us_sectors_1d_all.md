# Scan — us_sectors

- Variants tried: **1469** · global PBO: **0.402** · equal-weight benchmark Sharpe: 0.828 · Reality Check p (best vs benchmark): 0.9933333333333333 · timeframe 1d · runtime 488s
- Single ideas and two-signal combinations (`A+B` = A confirmed by B): 30 combo families. Every variant's own result is in the matching `_variants.csv`.
- Ranked by walk-forward OOS Sharpe per family. Full-sample DSR is deflated by ALL trials.
- A scan result is a LEAD, not a decision. Register a hypothesis and run the gate.

| # | family | variants | WF OOS Sharpe | OOS CAGR | OOS MaxDD | 2x-cost Sharpe | family PBO | best full Sharpe | DSR(all trials) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | macd_divergence | 4 | 1.1 | 0.022 | -0.0264 | 1.049 | 0.399 | 1.129 | 0.908 |
| 2 | stoch_reversal+ibs_reversion | 3 | 1.08 | 0.0279 | -0.0226 | 1.028 | 0.465 | 1.081 | 0.837 |
| 3 | wavetrend_reversal | 54 | 1.04 | 0.0201 | -0.0257 | 1.013 | 0.103 | 1.192 | 0.927 |
| 4 | wavetrend_reversal+ibs_reversion | 3 | 0.978 | 0.013 | -0.0253 | 0.952 | 0.626 | 1.05 | 0.814 |
| 5 | price_ma+ibs_reversion | 3 | 0.976 | 0.0339 | -0.0399 | 0.95 | 0.945 | 0.73 | 0.338 |
| 6 | macd_divergence+ibs_reversion | 3 | 0.964 | 0.0115 | -0.0224 | 0.933 | 0.976 | 0.993 | 0.759 |
| 7 | frog_in_pan | 4 | 0.944 | 0.1563 | -0.3575 | 0.936 | 0.56 | 0.902 | 0.625 |
| 8 | wavetrend_reversal+stoch_reversal | 3 | 0.931 | 0.0194 | -0.0272 | 0.907 | 0.664 | 1.075 | 0.838 |
| 9 | low_vol | 6 | 0.889 | 0.13 | -0.3198 | 0.885 | 0.639 | 0.877 | 0.564 |
| 10 | breadth_timing | 6 | 0.877 | 0.0877 | -0.1663 | 0.829 | 0.905 | 0.658 | 0.291 |
| 11 | inside_bar+ibs_reversion | 3 | 0.86 | 0.0534 | -0.0903 | 0.847 | 0.012 | 0.795 | 0.458 |
| 12 | dual_momentum | 6 | 0.858 | 0.1688 | -0.3152 | 0.847 | 0.488 | 0.823 | 0.509 |
| 13 | vol_managed_momentum | 4 | 0.844 | 0.1087 | -0.2842 | 0.839 | 0.747 | 0.83 | 0.519 |
| 14 | volume_shock | 4 | 0.844 | 0.1347 | -0.3725 | 0.83 | 0.002 | 0.84 | 0.489 |
| 15 | stoch_reversal | 96 | 0.839 | 0.0301 | -0.0362 | 0.779 | 0.251 | 1.072 | 0.842 |
| 16 | usdtry_hedge_switch | 4 | 0.836 | 0.1325 | -0.3634 | 0.836 | 1.0 | 0.86 | 0.49 |
| 17 | xs_momentum | 18 | 0.833 | 0.1344 | -0.3412 | 0.822 | 0.591 | 0.901 | 0.61 |
| 18 | inside_bar+price_ma | 3 | 0.826 | 0.0216 | -0.0453 | 0.809 | 0.405 | 0.857 | 0.541 |
| 19 | max_effect | 4 | 0.818 | 0.1193 | -0.3238 | 0.807 | 0.323 | 0.874 | 0.538 |
| 20 | trend_quality | 4 | 0.813 | 0.1309 | -0.346 | 0.805 | 0.338 | 0.848 | 0.522 |
| 21 | ml_ridge_rank | 8 | 0.796 | 0.1307 | -0.3591 | 0.785 | 0.136 | 0.789 | 0.458 |
| 22 | macro_risk_switch | 12 | 0.796 | 0.0621 | -0.1572 | 0.746 | 0.529 | 0.861 | 0.584 |
| 23 | macd_divergence+stoch_reversal | 3 | 0.782 | 0.0075 | -0.0178 | 0.755 | 0.487 | 0.774 | 0.47 |
| 24 | ibs_reversion+macd_divergence | 3 | 0.777 | 0.0075 | -0.0226 | 0.709 | 0.612 | 0.576 | 0.132 |
| 25 | betting_against_beta | 4 | 0.775 | 0.1112 | -0.3198 | 0.772 | 0.679 | 0.849 | 0.528 |

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
  rule: macd_divergence
  universe: us_sectors
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 1.1, family PBO 0.399"
- id: S901
  rule: stoch_reversal
  confirm: ibs_reversion
  confirm_within: [0, 3, 5]
  universe: us_sectors
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 1.08, family PBO 0.465"
- id: S902
  rule: wavetrend_reversal
  universe: us_sectors
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 1.04, family PBO 0.103"
- id: S903
  rule: wavetrend_reversal
  confirm: ibs_reversion
  confirm_within: [0, 3, 5]
  universe: us_sectors
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.978, family PBO 0.626"
- id: S904
  rule: price_ma
  confirm: ibs_reversion
  confirm_within: [0, 3, 5]
  universe: us_sectors
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.976, family PBO 0.945"
```
