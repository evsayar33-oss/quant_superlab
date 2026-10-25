# H062 zaman makinesi — dev tarama geçmişe gönderildi

Seçim, her kesim tarihinde sadece o tarihten önceki veriyle yeniden yapıldı. İleri = kesimden bugüne, 2x maliyet. Kural sonuçlardan önce yazıldı (`config/mega.yaml` → timemachine).

| Kesim | D1–D4 aday | Kitap | Keşif Sharpe | İleri 2x getiri (toplam) | Yıllık | İleri Sharpe | Sıra ilişkisi | Aralıkta |
|---|---|---|---|---|---|---|---|---|
| 2022-10-20 (4y) | 337 | 27 | 0.762 | +5% | +1% | 0.287 | -0.059 | hayır |
| 2023-10-20 (3y) | 451 | 31 | 0.905 | -6% | -2% | 0.071 | -0.471 | hayır |
| 2024-10-20 (2y) | 415 | 35 | 0.797 | +7% | +4% | 0.389 | -0.226 | hayır |

Sonuç: **0/3** kesim aralıkta (gerekli 2). **KALDI**.

Sıra ilişkisi = keşif Sharpe sırası ile ileri Sharpe sırası arasındaki Spearman ilişkisi (0 = backtest sırası ileriyi hiç tahmin etmiyor).

- 2022-10-20: atlanan işler: crypto/both: only 0 assets with >= 5 years; crypto/long: only 0 assets with >= 5 years; crypto/short: only 0 assets with >= 5 years

## Hayatta kalanlar (152)

En az 2 kesimde D1–D4 listesinde olup her kesimde ileride 2x maliyetle kârlı kalan stratejiler. Bunlar paper izlemeye adaydır, karar değildir.

| Sınıf | Yön | Strateji | Kesimler | İleri 2x getiriler |
|---|---|---|---|---|
| metals | long | `ma_cross|{"kind": "tema", "pair": [50, 150]}|x20|none` | 2 | 2y: +30%, 4y: +39% |
| metals | long | `trix_cross|{"n": 21, "signal": 7}|x13|none` | 2 | 3y: +30%, 4y: +30% |
| indices | long | `price_ma|{"kind": "ema", "n": 200}|x0|none` | 3 | 2y: +28%, 3y: +64%, 4y: +62% |
| metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none` | 2 | 2y: +27%, 4y: +38% |
| metals | long | `ma_cross|{"kind": "dema", "pair": [20, 50]}|x0|trend_sma200` | 2 | 2y: +25%, 4y: +29% |
| indices | long | `roc_breakout|{"n": 252, "th": 0}|x0|none` | 2 | 2y: +22%, 4y: +62% |
| metals | long | `bollinger_breakout|{"k": 2.0, "n": 50}|x13|trend_sma200` | 2 | 3y: +24%, 4y: +20% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 2 | 2y: +19%, 4y: +23% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 2 | 2y: +19%, 4y: +23% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 2 | 2y: +19%, 4y: +23% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 2 | 2y: +19%, 4y: +23% |
| indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|none` | 3 | 2y: +19%, 3y: +31%, 4y: +42% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 2 | 2y: +19%, 4y: +21% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 2 | 2y: +19%, 4y: +21% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w5` | 2 | 2y: +19%, 4y: +21% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w5` | 2 | 2y: +19%, 4y: +21% |
| metals | long | `trix_cross|{"n": 12, "signal": 9}|x20|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 2 | 3y: +19%, 4y: +18% |
| metals | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 14}|x13|none` | 3 | 2y: +18%, 3y: +37%, 4y: +38% |
| indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|none` | 3 | 2y: +17%, 3y: +28%, 4y: +42% |
| indices | long | `inside_bar|{"trend_n": 200}|x0|none` | 2 | 2y: +15%, 4y: +47% |
| indices | long | `inside_bar|{"trend_n": 200}|x0|trend_sma200` | 2 | 2y: +15%, 4y: +47% |
| indices | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 9}|x0|trend_sma200` | 3 | 2y: +15%, 3y: +36%, 4y: +34% |
| indices | long | `cot_commercial|{"n": 260, "th": 1.0}|x0|none` | 3 | 2y: +14%, 3y: +18%, 4y: +32% |
| metals | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 21}|x13|none` | 2 | 2y: +14%, 3y: +26% |
| energy | long | `coppock_turn|{"scale": 5}|x20|none` | 2 | 3y: +24%, 4y: +14% |

## Her kesimin kitabı

### 2022-10-20

| Sınıf | Yön | Strateji | Keşif Sharpe | İleri 2x | İleri Sharpe | Varlık payı |
|---|---|---|---|---|---|---|
| energy | both | `coppock_turn|{"scale": 5}|x28|none` | 0.633 | +15% | 0.399 | 60% |
| energy | both | `coppock_turn|{"scale": 5}|x20|none` | 0.578 | +12% | 0.319 | 80% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 1.061 | -23% | -1.125 | 0% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.985 | -19% | -0.943 | 0% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.889 | -12% | -0.829 | 0% |
| energy | long | `trix_cross|{"n": 21, "signal": 9}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.839 | -25% | -1.289 | 0% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|trend_sma200` | 0.831 | -26% | -0.749 | 25% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.716 | -3% | -0.064 | 40% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200` | 0.609 | -6% | -0.093 | 40% |
| indices | both | `rsi_midline|{"level": 50, "n": 28}|x13|trend_sma200|pivot_bounce:{"window": 5}:w3` | 0.607 | +6% | 0.557 | 80% |
| indices | both | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:w5` | 0.597 | +5% | 0.455 | 100% |
| indices | both | `rsi_midline|{"level": 50, "n": 28}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.594 | -2% | 0.01 | 40% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": false}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w3` | 0.952 | +4% | 0.44 | 60% |
| indices | long | `ppo_cross|{"cfg": [12, 26, 9]}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w3` | 0.914 | +5% | 0.502 | 60% |
| indices | long | `ppo_cross|{"cfg": [10, 30, 9]}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w3` | 0.889 | +5% | 0.531 | 60% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": false}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.88 | +3% | 0.346 | 60% |
| indices | long | `ppo_cross|{"cfg": [12, 26, 9]}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.873 | +4% | 0.383 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 0.609 | +23% | 0.835 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 0.609 | +23% | 0.835 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 0.609 | +23% | 0.835 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 0.609 | +23% | 0.835 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 0.596 | +21% | 0.777 | 60% |
| metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.885 | +14% | 1.044 | 60% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.861 | +22% | 1.284 | 100% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.86 | +22% | 1.476 | 100% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w0` | 0.746 | +10% | 1.167 | 80% |
| metals | long | `price_ma|{"kind": "hma", "n": 200}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.743 | -5% | -0.193 | 40% |

### 2023-10-20

| Sınıf | Yön | Strateji | Keşif Sharpe | İleri 2x | İleri Sharpe | Varlık payı |
|---|---|---|---|---|---|---|
| crypto | both | `ma_cross|{"kind": "tema", "pair": [20, 100]}|x18|trend_sma200` | 1.185 | -16% | -0.245 | 20% |
| crypto | both | `price_ma|{"kind": "hma", "n": 150}|x13|trend_sma200` | 1.136 | -36% | -0.623 | 20% |
| crypto | both | `ma_cross|{"kind": "tema", "pair": [20, 100]}|x28|trend_sma200` | 1.046 | -15% | -0.13 | 40% |
| crypto | both | `ma_cross|{"kind": "tema", "pair": [20, 100]}|x13|trend_sma200` | 1.044 | -26% | -0.43 | 20% |
| crypto | both | `awesome_zero|{"fast": 5, "slow": 50}|x13|trend_sma200` | 1.017 | -30% | -0.52 | 20% |
| crypto | long | `ichimoku_cloud|{"cfg": [9, 26, 52]}|x13|none` | 1.409 | -7% | 0.098 | 40% |
| crypto | long | `price_ma|{"kind": "hma", "n": 200}|x13|trend_sma200` | 1.312 | -26% | -0.757 | 20% |
| crypto | long | `price_ma|{"kind": "hma", "n": 150}|x18|trend_sma200` | 1.306 | -25% | -0.655 | 0% |
| crypto | long | `roc_breakout|{"n": 10, "th": 10}|x13|none` | 1.265 | -31% | -0.409 | 20% |
| crypto | long | `price_ma|{"kind": "sma", "n": 50}|x13|trend_sma200` | 1.233 | -32% | -0.938 | 20% |
| energy | both | `coppock_turn|{"scale": 5}|x20|none` | 0.526 | +24% | 0.5 | 80% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.918 | -15% | -1.17 | 20% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.873 | -12% | -0.938 | 20% |
| energy | long | `ichimoku_cloud|{"cfg": [7, 22, 44]}|x13|none|smc_ote:{"fib_lo": 0.618, "k": 5}:w5` | 0.829 | -6% | -0.393 | 20% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|none|smc_bos:{"k": 5}:w5` | 0.78 | -11% | -0.505 | 20% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|trend_sma200|smc_bos:{"k": 5}:w5` | 0.756 | -15% | -0.738 | 0% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.705 | -4% | -0.175 | 40% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200` | 0.562 | -0% | 0.114 | 80% |
| indices | both | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:w5` | 0.539 | +11% | 0.838 | 100% |
| indices | both | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:w3` | 0.532 | +4% | 0.579 | 60% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x18|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.913 | +3% | 0.542 | 80% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.903 | +5% | 0.845 | 80% |
| indices | long | `ppo_cross|{"cfg": [10, 30, 9]}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w3` | 0.882 | +4% | 0.48 | 60% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x20|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.88 | +6% | 0.896 | 80% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x28|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.87 | +5% | 0.751 | 80% |
| metals | both | `rsi_reversal|{"exit": 50, "lo": 35, "n": 14}|x0|trend_sma200` | 0.5 | +4% | 0.443 | 80% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.901 | +15% | 1.147 | 80% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.898 | +16% | 1.378 | 80% |
| metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.833 | +17% | 1.435 | 80% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w0` | 0.779 | +6% | 1.017 | 80% |
| metals | long | `price_ma|{"kind": "hma", "n": 200}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.714 | -5% | -0.233 | 60% |

### 2024-10-20

| Sınıf | Yön | Strateji | Keşif Sharpe | İleri 2x | İleri Sharpe | Varlık payı |
|---|---|---|---|---|---|---|
| crypto | both | `cmf_flow|{"n": 40, "th": 0.05}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.865 | +22% | 0.793 | 71% |
| crypto | both | `hurst_switch|{"fast": 20, "n": 200, "rsi_n": 2}|x20|none|pivot_bounce:{"window": 5}:w3` | 0.796 | +8% | 0.49 | 71% |
| crypto | both | `hurst_switch|{"fast": 20, "n": 200, "rsi_n": 2}|x13|none|pivot_bounce:{"window": 5}:w3` | 0.796 | +8% | 0.49 | 71% |
| crypto | both | `price_ma|{"kind": "hma", "n": 200}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.765 | -8% | -0.335 | 43% |
| crypto | both | `hurst_switch|{"fast": 20, "n": 100, "rsi_n": 2}|x13|none|pivot_bounce:{"window": 5}:w5` | 0.762 | +12% | 0.629 | 71% |
| crypto | long | `cci_breakout|{"level": 100, "n": 14}|x0|none` | 1.131 | +16% | -0.028 | 14% |
| crypto | long | `ma_cross|{"kind": "dema", "pair": [10, 50]}|x28|trend_sma200` | 1.101 | -11% | -0.461 | 29% |
| crypto | long | `cci_breakout|{"level": 100, "n": 14}|x0|trend_sma200` | 1.077 | +18% | 0.161 | 14% |
| crypto | long | `cci_breakout|{"level": 150, "n": 14}|x0|none|smc_bos:{"k": 5}:w5` | 1.06 | +46% | 0.485 | 57% |
| crypto | long | `cci_breakout|{"level": 150, "n": 14}|x0|none|smc_bos:{"k": 5}:w3` | 1.047 | +46% | 0.485 | 57% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|trend_sma200|smc_bos:{"k": 5}:w5` | 0.724 | -14% | -0.773 | 0% |
| energy | long | `trix_cross|{"n": 21, "signal": 9}|x13|trend_sma200|smc_bos:{"k": 5}:w5` | 0.687 | -12% | -0.532 | 0% |
| energy | long | `tsi_cross|{"cfg": [40, 20, 10]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.677 | +7% | 0.592 | 80% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|trend_sma200` | 0.674 | -9% | -0.432 | 40% |
| energy | long | `ma_cross|{"kind": "tema", "pair": [20, 100]}|x13|none` | 0.673 | +2% | 0.317 | 60% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.752 | -7% | -0.719 | 20% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.735 | -10% | -0.925 | 0% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200` | 0.601 | -12% | -0.538 | 0% |
| indices | both | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:w5` | 0.573 | +5% | 0.607 | 100% |
| indices | both | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:w5` | 0.528 | +6% | 0.876 | 100% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.942 | +1% | 0.324 | 40% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x18|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.936 | +0% | 0.129 | 40% |
| indices | long | `ppo_cross|{"cfg": [10, 30, 9]}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w3` | 0.926 | -1% | -0.088 | 20% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x20|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.92 | +1% | 0.396 | 40% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x28|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.91 | +1% | 0.193 | 40% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 0.624 | +19% | 0.996 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 0.624 | +19% | 0.996 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 0.624 | +19% | 0.996 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 0.624 | +19% | 0.996 | 60% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 0.602 | +19% | 0.951 | 60% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.905 | +13% | 1.491 | 60% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.881 | +13% | 1.491 | 60% |
| metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.88 | +10% | 1.219 | 80% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w0` | 0.775 | +5% | 1.172 | 60% |
| metals | long | `williams_reversal|{"lo": -90, "n": 21}|x18|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.697 | +4% | 1.163 | 80% |

## Zayıf yönler

- 2 yıllık kesimin ileri dönemi, ana taramanın kilitli dönemiyle aynı. Bu test o dönemi tüm adaylar için harcadı.
- 3 kesim birbirine bağımlı: ileri dönemler üst üste biniyor (2024-10 → bugün hepsinde var).
- Hayatta kalan listesi binlerce aday içinden seçildi; liste de şans içerir. Paper izleme ve karar kapısı yine gerekli.
