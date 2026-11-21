# Scan — global_assets

- Variants tried: **1469** · global PBO: **0.533** · equal-weight benchmark Sharpe: 0.711 · Reality Check p (best vs benchmark): 0.7033333333333334 · timeframe 1d · runtime 332s
- Single ideas and two-signal combinations (`A+B` = A confirmed by B): 30 combo families. Every variant's own result is in the matching `_variants.csv`.
- Ranked by walk-forward OOS Sharpe per family. Full-sample DSR is deflated by ALL trials.
- A scan result is a LEAD, not a decision. Register a hypothesis and run the gate.

| # | family | variants | WF OOS Sharpe | OOS CAGR | OOS MaxDD | 2x-cost Sharpe | family PBO | best full Sharpe | DSR(all trials) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | betting_against_beta | 4 | 0.925 | 0.0941 | -0.2145 | 0.923 | 0.674 | 0.756 | 0.408 |
| 2 | inside_bar+macd_zero | 3 | 0.837 | 0.0334 | -0.0572 | 0.824 | 0.078 | 0.808 | 0.506 |
| 3 | frog_in_pan | 4 | 0.819 | 0.1079 | -0.248 | 0.808 | 0.423 | 0.803 | 0.477 |
| 4 | usdtry_hedge_switch | 4 | 0.813 | 0.0988 | -0.248 | 0.813 | 1.0 | 0.748 | 0.335 |
| 5 | high_52w | 3 | 0.797 | 0.0947 | -0.2264 | 0.776 | 0.628 | 0.866 | 0.585 |
| 6 | core_tsmom_vt | 1 | 0.793 | 0.0511 | -0.1022 | 0.682 | nan | 0.703 | 0.341 |
| 7 | inside_bar | 4 | 0.791 | 0.0472 | -0.0656 | 0.76 | 0.03 | 0.823 | 0.526 |
| 8 | low_vol | 6 | 0.775 | 0.0799 | -0.2624 | 0.769 | 0.254 | 0.719 | 0.335 |
| 9 | trend_quality | 4 | 0.772 | 0.1094 | -0.333 | 0.754 | 0.39 | 0.819 | 0.512 |
| 10 | mom_acceleration | 2 | 0.763 | 0.0934 | -0.2667 | 0.752 | 0.81 | 0.685 | 0.329 |
| 11 | idio_vol | 4 | 0.761 | 0.1039 | -0.3043 | 0.754 | 0.358 | 0.787 | 0.438 |
| 12 | xs_momentum | 18 | 0.757 | 0.1095 | -0.333 | 0.746 | 0.2 | 0.903 | 0.615 |
| 13 | max_effect | 4 | 0.755 | 0.0862 | -0.2853 | 0.743 | 0.597 | 0.727 | 0.335 |
| 14 | inside_bar+high_52w_break | 3 | 0.752 | 0.0362 | -0.0604 | 0.744 | 0.952 | 0.691 | 0.337 |
| 15 | ml_ridge_rank | 8 | 0.748 | 0.0954 | -0.248 | 0.741 | 0.051 | 0.69 | 0.336 |
| 16 | dual_momentum | 6 | 0.733 | 0.0905 | -0.1978 | 0.719 | 0.223 | 0.88 | 0.575 |
| 17 | macro_risk_switch | 12 | 0.725 | 0.053 | -0.1785 | 0.672 | 0.257 | 0.673 | 0.304 |
| 18 | core_dual_trend_vt | 1 | 0.723 | 0.0509 | -0.1197 | 0.652 | nan | 0.7 | 0.351 |
| 19 | core_dual_trend_vt_band | 1 | 0.72 | 0.0505 | -0.119 | 0.649 | nan | 0.698 | 0.348 |
| 20 | volume_shock | 4 | 0.712 | 0.0884 | -0.248 | 0.663 | 0.661 | 0.721 | 0.335 |
| 21 | engulfing | 6 | 0.705 | 0.03 | -0.094 | 0.637 | 0.636 | 0.789 | 0.464 |
| 22 | residual_momentum | 4 | 0.695 | 0.0877 | -0.248 | 0.686 | 0.913 | 0.712 | 0.335 |
| 23 | seasonality_same_month | 4 | 0.694 | 0.0835 | -0.248 | 0.683 | 0.153 | 0.611 | 0.236 |
| 24 | macd_zero+psar_flip | 3 | 0.678 | 0.0218 | -0.0417 | 0.644 | 0.912 | 0.607 | 0.195 |
| 25 | wavetrend_reversal | 54 | 0.677 | 0.0103 | -0.0339 | 0.652 | 0.313 | 0.98 | 0.734 |

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
- wavetrend_reversal+high_52w_break: no trades / flat returns in every variant
- wavetrend_reversal+macd_zero: no trades / flat returns in every variant

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bir tarama sonucu karar değil, adaydır; birçok varyant arasından seçilen sonuçlar ileride çökebilir. Önce `run.py --hypothesis` kapısı, seçim süreci için `Time machine test`. Kural: CLAUDE.md / AGENTS.md.


```yaml
# Suggested hypotheses from the scan (copy into hypotheses/registry.yaml, give real ids)
- id: S900
  strategy: betting_against_beta
  universe: global_assets
  for_system: TODO
  status: active
  note: "scan lead: WF OOS Sharpe 0.925, family PBO 0.674"
- id: S901
  rule: inside_bar
  confirm: macd_zero
  confirm_within: [0, 3, 5]
  universe: global_assets
  for_system: TODO
  status: active
  filters: [none, trend_sma200, regime_bench200]
  side: long
  note: "scan lead: WF OOS Sharpe 0.837, family PBO 0.078"
- id: S902
  strategy: frog_in_pan
  universe: global_assets
  for_system: TODO
  status: active
  note: "scan lead: WF OOS Sharpe 0.819, family PBO 0.423"
- id: S903
  strategy: usdtry_hedge_switch
  universe: global_assets
  for_system: TODO
  status: active
  note: "scan lead: WF OOS Sharpe 0.813, family PBO 1.0"
- id: S904
  strategy: high_52w
  universe: global_assets
  for_system: TODO
  status: active
  note: "scan lead: WF OOS Sharpe 0.797, family PBO 0.628"
```
