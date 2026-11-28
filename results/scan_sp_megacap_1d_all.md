# Scan — sp_megacap

- Variants tried: **1469** · global PBO: **0.49** · equal-weight benchmark Sharpe: 1.283 · Reality Check p (best vs benchmark): 0.0 · timeframe 1d · runtime 610s
- Single ideas and two-signal combinations (`A+B` = A confirmed by B): 30 combo families. Every variant's own result is in the matching `_variants.csv`.
- Ranked by walk-forward OOS Sharpe per family. Full-sample DSR is deflated by ALL trials.
- A scan result is a LEAD, not a decision. Register a hypothesis and run the gate.

| # | family | variants | WF OOS Sharpe | OOS CAGR | OOS MaxDD | 2x-cost Sharpe | family PBO | best full Sharpe | DSR(all trials) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | macro_risk_switch | 12 | 1.336 | 0.1276 | -0.161 | 1.281 | 0.421 | 1.48 | 0.962 |
| 2 | trend_quality | 4 | 1.295 | 0.276 | -0.2761 | 1.268 | 0.139 | 1.336 | 0.901 |
| 3 | mom_acceleration | 2 | 1.292 | 0.2536 | -0.2549 | 1.264 | 0.769 | 1.215 | 0.798 |
| 4 | core_tsmom_vt | 1 | 1.269 | 0.1063 | -0.122 | 1.181 | nan | 1.249 | 0.8 |
| 5 | inside_bar | 4 | 1.265 | 0.111 | -0.1237 | 1.247 | 0.0 | 1.231 | 0.805 |
| 6 | usdtry_hedge_switch | 4 | 1.264 | 0.2157 | -0.279 | 1.264 | 1.0 | 1.326 | 0.834 |
| 7 | core_dual_trend_vt | 1 | 1.249 | 0.1125 | -0.1513 | 1.194 | nan | 1.217 | 0.764 |
| 8 | frog_in_pan | 4 | 1.249 | 0.2665 | -0.2808 | 1.231 | 0.768 | 1.216 | 0.764 |
| 9 | triple_ma+ichimoku_cloud | 3 | 1.245 | 0.0517 | -0.0566 | 1.226 | 0.11 | 1.194 | 0.721 |
| 10 | core_dual_trend_vt_band | 1 | 1.242 | 0.1112 | -0.1522 | 1.187 | nan | 1.212 | 0.758 |
| 11 | macd_zero | 6 | 1.241 | 0.0955 | -0.1018 | 1.181 | 0.374 | 1.163 | 0.697 |
| 12 | inside_bar+ibs_reversion | 3 | 1.239 | 0.0933 | -0.1151 | 1.225 | 0.086 | 1.205 | 0.775 |
| 13 | residual_momentum | 4 | 1.234 | 0.2623 | -0.314 | 1.217 | 0.966 | 1.118 | 0.674 |
| 14 | triple_ma | 12 | 1.207 | 0.0877 | -0.1125 | 1.161 | 0.319 | 1.156 | 0.67 |
| 15 | ichimoku_cloud | 6 | 1.189 | 0.0637 | -0.0659 | 1.121 | 0.761 | 1.058 | 0.578 |
| 16 | ml_ridge_rank | 8 | 1.188 | 0.2721 | -0.2659 | 1.168 | 0.1 | 1.119 | 0.686 |
| 17 | ibs_reversion+smc_bos | 3 | 1.186 | 0.0317 | -0.0473 | 0.902 | 0.812 | 1.224 | 0.647 |
| 18 | xs_momentum | 18 | 1.173 | 0.3092 | -0.2632 | 1.161 | 0.756 | 1.22 | 0.769 |
| 19 | macd_zero+smc_bos | 3 | 1.168 | 0.0452 | -0.0549 | 1.123 | 0.891 | 1.237 | 0.784 |
| 20 | breadth_timing | 6 | 1.15 | 0.1278 | -0.1992 | 1.092 | 0.812 | 1.253 | 0.792 |
| 21 | smc_bos | 8 | 1.142 | 0.0881 | -0.1201 | 1.096 | 0.653 | 1.165 | 0.641 |
| 22 | ibs_reversion | 12 | 1.14 | 0.1048 | -0.1756 | 0.893 | 0.513 | 1.264 | 0.778 |
| 23 | vol_managed_momentum | 4 | 1.122 | 0.1597 | -0.1918 | 1.107 | 0.911 | 1.132 | 0.701 |
| 24 | high_52w | 3 | 1.115 | 0.196 | -0.2325 | 1.078 | 0.541 | 1.067 | 0.551 |
| 25 | roc_breakout | 30 | 1.085 | 0.0869 | -0.1331 | 1.058 | 0.229 | 1.254 | 0.835 |

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
  strategy: macro_risk_switch
  universe: sp_megacap
  for_system: TODO
  status: active
  note: "scan lead: WF OOS Sharpe 1.336, family PBO 0.421"
- id: S901
  strategy: trend_quality
  universe: sp_megacap
  for_system: TODO
  status: active
  note: "scan lead: WF OOS Sharpe 1.295, family PBO 0.139"
- id: S902
  strategy: mom_acceleration
  universe: sp_megacap
  for_system: TODO
  status: active
  note: "scan lead: WF OOS Sharpe 1.292, family PBO 0.769"
```
