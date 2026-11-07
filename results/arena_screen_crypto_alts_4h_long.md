# Eleme motoru — crypto_alts 4h_long (yön: long)

Veri: 2018-01-01 → 2026-11-02. Coin: 34 uygun (toplam 35). Denenen varyant: 592 × coin = **37884 deneme**.
Her (coin, kural) için tek en iyi nokta değil, **en sağlam bölgenin merkezi** seçildi. Bu bir aday listesidir, karar değildir. Karar sadece doğrulama kapısında verilir.

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bu liste binlerce deneme arasından seçildi; seçim süreçleri backtest'te iyi görünüp ileride çökebilir (2026-10-17 ve 10-19 testleri). Gerçek paraya aday olmadan önce `Time machine test` workflow'unu aynı yön (side) ve zaman dilimiyle çalıştırın. Kural: CLAUDE.md / AGENTS.md.

## Huni

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 68 | 2312 |
| S1 | her dönemde kârlı değil / az işlem | 2083 | 229 |
| S2 | kâr faktörü veya düşüş zayıf | 166 | 63 |
| S3 | yüksek maliyette zarar | 6 | 57 |
| S4 | plato yok (komşu ayarlar zararda) | 9 | 48 |
| S5 | 1 bar gecikmeye dayanıksız | 5 | 43 |
| S6 | yılların çoğunda kârlı değil | 14 | 29 |
| S7 | istatistiksel güven düşük (PSR) | 7 | 22 |

## 2. aşama: filtre × çıkış × kombo (sadece S1'i geçen adaylarda)

229 aday → 17756 ek deneme (DSR'a eklendi). Her aday için en sağlam filtre/çıkış hücresi ve en sağlam kombo seçildi; kombo sadece kuralı tek başına geçerse aday olur. Seçilenler aynı S1–S7 adımlarından geçti.

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 0 | 384 |
| S1 | her dönemde kârlı değil / az işlem | 121 | 263 |
| S2 | kâr faktörü veya düşüş zayıf | 121 | 142 |
| S3 | yüksek maliyette zarar | 1 | 141 |
| S4 | plato yok (komşu ayarlar zararda) | 33 | 108 |
| S5 | 1 bar gecikmeye dayanıksız | 6 | 102 |
| S6 | yılların çoğunda kârlı değil | 24 | 78 |
| S7 | istatistiksel güven düşük (PSR) | 3 | 75 |

## Geçenler (97)

Kazanma oranı tek başına bir şey söylemez. Sistem sadece **kazanma oranı > başabaş oranı** olduğunda kârlıdır. Başabaş = 1 / (1 + ödeme oranı); ödeme oranı = ortalama kazanç / ortalama kayıp (maliyet sonrası). Pay = kazanma oranı − başabaş. Beklenen = işlem başına ortalama net getiri.

| Tier | Aşama | Coin | Kural | Ayar | Varyant | 3y | 5y | Tüm | Sharpe | 1x DD | PF | Kazanma | Ödeme | Başabaş | Pay | Beklenen | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 2 | ARB/USDT | ma_cross | `kind=sma,pair=(20, 50)` | filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10 | +112% | veri yok | +262% | 1.352 | -31% | 2.755 | 51% | 2.64 | 28% | +24% | +3.26% | 0.062 |
| B | 2 | SUI/USDT | bollinger_reversion | `n=30,k=2.5` | filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10 | +270% | veri yok | +234% | 1.238 | -22% | 2.25 | 57% | 1.688 | 37% | +20% | +1.99% | 0.06 |
| B | 2 | ARB/USDT | smc_choch | `k=8` | filtre=regime_bench200 · çıkış=stop_atr=2.0,tp_r=3.0 | +195% | veri yok | +249% | 1.206 | -33% | 2.199 | 43% | 2.894 | 26% | +18% | +3.45% | 0.057 |
| B | 2 | ARB/USDT | macd_divergence | `k=3,fast=12,slow=26` | filtre=regime_bench200 · çıkış=stop_atr=2.0,be_r=1.0 | +326% | veri yok | +282% | 1.209 | -30% | 2.587 | 26% | 7.164 | 12% | +14% | +3.72% | 0.044 |
| B | 2 | ARB/USDT | atr_breakout | `n=10,k=2.0` | filtre=regime_bench200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +83% | veri yok | +124% | 1.085 | -26% | 2.347 | 57% | 1.788 | 36% | +21% | +2.44% | 0.027 |
| B | 2 | SUI/USDT | atr_breakout | `n=20,k=2.0` | filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10 | +120% | veri yok | +108% | 0.979 | -17% | 2.311 | 58% | 1.651 | 38% | +21% | +2.39% | 0.02 |
| B | 1 | SUI/USDT | wavetrend_reversal | `n1=9,n2=26,lo=-60` | çıkış=stop_atr=2.0,trail_atr=3.0 | +109% | veri yok | +138% | 0.953 | -31% | 2.335 | 52% | 2.189 | 31% | +20% | +3.65% | 0.018 |
| B | 2 | SUI/USDT | bollinger_breakout | `n=20,k=2.5` | filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10 | +168% | veri yok | +142% | 0.893 | -26% | 1.717 | 50% | 1.717 | 37% | +13% | +1.61% | 0.015 |
| B | 2 | SUI/USDT | keltner_breakout | `n=50,k=2.5` | filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10 | +251% | veri yok | +161% | 0.891 | -32% | 1.612 | 48% | 1.727 | 37% | +12% | +1.47% | 0.015 |
| B | 1 | ARB/USDT | hurst_switch | `n=200,fast=20,rsi_n=5` | çıkış=stop_atr=2.0,trail_atr=3.0 | +143% | veri yok | +135% | 0.953 | -31% | 2.171 | 41% | 3.121 | 24% | +17% | +2.76% | 0.012 |
| B | 2 | SUI/USDT | wavetrend_reversal | `n1=9,n2=26,lo=-60` | çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +60% | veri yok | +94% | 0.854 | -34% | 2.033 | 58% | 1.468 | 40% | +18% | +2.67% | 0.012 |
| B | 2 | BTC/USDT | linreg_slope | `n=20,th=0.0005` | filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0 | +36% | +72% | +1576% | 1.266 | -37% | 2.181 | 33% | 4.474 | 18% | +14% | +1.55% | 0.011 |
| B | 2 | ETH/USDT | volume_breakout | `n=50,rv=3.0` | filtre=regime_bench200 · çıkış=signal_only | +166% | +254% | +1633% | 1.243 | -25% | 5.403 | 55% | 4.402 | 18% | +37% | +7.10% | 0.01 |
| B | 1 | SUI/USDT | bollinger_reversion | `n=30,k=2.5` | çıkış=stop_atr=2.0,trail_atr=3.0 | +141% | veri yok | +138% | 0.819 | -36% | 1.536 | 53% | 1.365 | 42% | +11% | +1.36% | 0.01 |
| B | 2 | AXS/USDT | smc_ote | `k=8,fib_lo=0.5` | filtre=trend_sma200 · çıkış=signal_only | +120% | +213% | +935% | 1.156 | -38% | 2.289 | 44% | 2.943 | 25% | +18% | +3.24% | 0.009 |
| B | 2 | OP/USDT | hammer_star | `lookback_low=10` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤3 bar) | +75% | veri yok | +132% | 0.93 | -21% | 1.664 | 70% | 0.7 | 59% | +12% | +1.00% | 0.008 |
| B | 2 | OP/USDT | keltner_breakout | `n=20,k=2.5` | filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10 | +31% | veri yok | +175% | 0.967 | -23% | 2.441 | 56% | 1.953 | 34% | +22% | +2.79% | 0.007 |
| B | 2 | ADA/USDT | bollinger_breakout | `n=50,k=2.5` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,max_hold=10 | +90% | +81% | +935% | 1.198 | -20% | 3.267 | 65% | 1.77 | 36% | +29% | +3.57% | 0.005 |
| B | 2 | ETH/USDT | roc_breakout | `n=126,th=5` | filtre=trend_sma200 · çıkış=stop_atr=2.0,trail_atr=3.0 | +84% | +63% | +1024% | 1.193 | -28% | 2.52 | 44% | 3.181 | 24% | +20% | +2.23% | 0.005 |
| B | 2 | ATOM/USDT | macd_divergence | `k=3,fast=12,slow=26` | filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10 | +25% | +155% | +586% | 1.09 | -30% | 1.981 | 57% | 1.492 | 40% | +17% | +1.42% | 0.005 |
| B | 2 | MINA/USDT | adx_trend | `n=20,th=20` | filtre=regime_bench200 · çıkış=stop_atr=2.0,be_r=1.0 | +184% | +223% | +504% | 0.969 | -33% | 3.804 | 26% | 10.779 | 8% | +18% | +5.84% | 0.005 |
| B | 1 | INJ/USDT | rsi_reversal | `n=7,lo=20,exit=50` | çıkış=stop_atr=2.0,trail_atr=3.0 | +49% | +186% | +507% | 1.009 | -39% | 1.728 | 65% | 0.917 | 52% | +13% | +1.47% | 0.004 |
| B | 2 | OP/USDT | adx_trend | `n=10,th=30` | filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10 | +18% | veri yok | +58% | 0.806 | -16% | 2.186 | 40% | 3.206 | 24% | +17% | +1.41% | 0.004 |
| B | 2 | BNB/USDT | smc_bos | `k=5` | filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10 | +51% | +63% | +1339% | 1.149 | -37% | 1.799 | 49% | 1.848 | 35% | +14% | +1.16% | 0.003 |
| B | 2 | BNB/USDT | macd_cross | `cfg=(19, 39, 9),zero_filter=False` | filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0 | +46% | +67% | +1409% | 1.117 | -31% | 1.768 | 38% | 2.952 | 25% | +12% | +1.13% | 0.003 |
| B | 2 | BNB/USDT | ma_cross | `kind=dema,pair=(10, 50)` | filtre=regime_bench200 · çıkış=signal_only | +82% | +61% | +1767% | 1.11 | -32% | 2.157 | 37% | 3.604 | 22% | +16% | +1.59% | 0.003 |
| B | 2 | BTC/USDT | keltner_breakout | `n=50,k=2.0` | filtre=trend_sma200 · çıkış=stop_atr=2.0,be_r=1.0 | +18% | +61% | +1267% | 1.102 | -36% | 2.225 | 28% | 5.83 | 15% | +13% | +2.01% | 0.003 |
| B | 2 | ETH/USDT | bollinger_breakout | `n=50,k=2.5` | filtre=regime_bench200 · çıkış=stop_atr=2.0,tp_r=3.0 | +101% | +212% | +991% | 1.086 | -35% | 1.984 | 45% | 2.388 | 30% | +16% | +2.23% | 0.003 |
| B | 2 | NEAR/USDT | macd_cross | `cfg=(12, 26, 9),zero_filter=True` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar) | +109% | +178% | +345% | 0.969 | -36% | 2.347 | 37% | 4.037 | 20% | +17% | +2.85% | 0.003 |
| B | 2 | XRP/USDT | high_52w_break | `n=126,exit_ma=50` | filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10 | +293% | +285% | +2110% | 1.143 | -40% | 2.562 | 49% | 2.663 | 27% | +22% | +3.78% | 0.002 |
| B | 1 | ETH/USDT | volume_breakout | `n=50,rv=3.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +75% | +87% | +497% | 1.102 | -17% | 3.332 | 45% | 4.11 | 20% | +25% | +3.19% | 0.002 |
| B | 2 | ADA/USDT | keltner_breakout | `n=20,k=2.5` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +137% | +83% | +656% | 1.049 | -32% | 2.271 | 44% | 2.877 | 26% | +18% | +3.65% | 0.002 |
| B | 2 | BTC/USDT | volume_breakout | `n=50,rv=2.0` | filtre=adx20 · çıkış=stop_atr=2.0,be_r=1.0 | +39% | +88% | +567% | 1.027 | -22% | 2.816 | 32% | 5.924 | 14% | +18% | +2.72% | 0.002 |
| B | 1 | UNI/USDT | rsi_divergence | `n=14,k=3,exit_level=70` | çıkış=stop_atr=2.0,trail_atr=3.0 | +99% | +121% | +451% | 0.912 | -33% | 1.745 | 40% | 2.564 | 28% | +12% | +1.88% | 0.002 |
| B | 2 | UNI/USDT | down_days | `n=5,hold_exit=3` | filtre=trend_sma200 · çıkış=signal_only | +209% | +203% | +679% | 1.07 | -37% | 3.954 | 68% | 1.825 | 35% | +33% | +4.36% | 0.001 |
| B | 2 | ETH/USDT | bollinger_breakout | `n=50,k=2.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar) | +70% | +64% | +714% | 1.024 | -26% | 2.377 | 47% | 2.717 | 27% | +20% | +2.19% | 0.001 |
| B | 2 | BTC/USDT | ma_cross | `kind=tema,pair=(20, 100)` | filtre=trend_sma200 · çıkış=stop_atr=2.0,be_r=1.0 | +42% | +54% | +522% | 1.017 | -24% | 2.23 | 30% | 5.342 | 16% | +14% | +1.58% | 0.001 |
| B | 2 | INJ/USDT | rsi_reversal | `n=7,lo=20,exit=50` | filtre=trend_sma200 · çıkış=stop_atr=2.0,be_r=1.0 | +18% | +105% | +147% | 1.015 | -14% | 5.268 | 87% | 0.811 | 55% | +31% | +3.25% | 0.001 |
| B | 2 | BTC/USDT | cci_breakout | `n=20,level=150` | filtre=trend_sma200 · çıkış=signal_only | +46% | +103% | +790% | 1.003 | -31% | 1.791 | 41% | 2.544 | 28% | +13% | +1.16% | 0.001 |
| B | 2 | BTC/USDT | atr_breakout | `n=20,k=2.0` | filtre=adx20 · çıkış=signal_only | +3% | +58% | +465% | 1.002 | -31% | 2.164 | 46% | 2.55 | 28% | +18% | +1.73% | 0.001 |
| B | 2 | TRX/USDT | smc_choch | `k=5` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +72% | +128% | +631% | 0.989 | -35% | 1.993 | 44% | 2.583 | 28% | +16% | +1.99% | 0.001 |
| B | 2 | ETH/USDT | donchian_breakout | `entry=100,exit=20` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +58% | +80% | +450% | 0.945 | -27% | 1.866 | 42% | 2.545 | 28% | +14% | +2.00% | 0.001 |
| B | 2 | BTC/USDT | bb_squeeze | `n=20,q=0.2,look=252` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,trail_atr=3.0 | +23% | +48% | +248% | 0.94 | -21% | 2.21 | 42% | 3.026 | 25% | +17% | +1.35% | 0.001 |
| B | 2 | ETH/USDT | linreg_slope | `n=100,th=0.0005` | filtre=regime_bench200 · çıkış=trail_atr=3.0 | +60% | +38% | +295% | 0.936 | -27% | 2.629 | 45% | 3.213 | 24% | +21% | +2.88% | 0.001 |
| B | 2 | BTC/USDT | high_52w_break | `n=252,exit_ma=50` | filtre=adx20 · çıkış=stop_atr=2.0,be_r=1.0 | +38% | +53% | +407% | 0.928 | -37% | 2.879 | 31% | 6.282 | 14% | +18% | +3.00% | 0.001 |
| B | 2 | ETH/USDT | high_52w_break | `n=126,exit_ma=50` | filtre=low_vol · çıkış=signal_only | +74% | +91% | +691% | 0.927 | -33% | 2.577 | 44% | 3.288 | 23% | +21% | +4.12% | 0.001 |
| B | 2 | UNI/USDT | mfi_reversal | `n=14,lo=20` | filtre=low_vol · çıkış=trail_atr=3.0 | +98% | +120% | +137% | 0.873 | -23% | 1.906 | 67% | 0.933 | 52% | +15% | +1.38% | 0.001 |
| B | 2 | UNI/USDT | down_days | `n=5,hold_exit=3` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤3 bar) | +50% | +134% | +227% | 0.825 | -26% | 1.642 | 57% | 1.244 | 45% | +12% | +1.29% | 0.001 |
| B | 2 | AAVE/USDT | rsi_reversal | `n=5,lo=10,exit=50` | filtre=adx20 · çıkış=signal_only | +99% | +144% | +160% | 0.77 | -34% | 2.321 | 76% | 0.746 | 57% | +18% | +1.49% | 0.001 |
| B | 2 | DOGE/USDT | high_52w_break | `n=252,exit_ma=50` | filtre=htf_week_sma10 · çıkış=trail_atr=3.0 | +67% | +70% | +3663% | 0.986 | -36% | 5.937 | 60% | 3.958 | 20% | +40% | +13.95% | 0.0 |
| B | 2 | ETH/USDT | atr_breakout | `n=10,k=2.0` | filtre=low_vol · çıkış=trail_atr=3.0 | +34% | +42% | +290% | 0.958 | -22% | 2.218 | 44% | 2.797 | 26% | +18% | +1.54% | 0.0 |
| B | 2 | ETH/USDT | roc_breakout | `n=126,th=5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤0 bar) | +34% | +35% | +165% | 0.937 | -21% | 3.974 | 41% | 5.808 | 15% | +26% | +3.64% | 0.0 |
| B | 1 | XRP/USDT | donchian_breakout | `entry=100,exit=10` | çıkış=stop_atr=2.0,trail_atr=3.0 | +142% | +167% | +1030% | 0.928 | -38% | 2.37 | 43% | 3.107 | 24% | +19% | +2.92% | 0.0 |
| B | 2 | ADA/USDT | donchian_breakout | `entry=100,exit=10` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar) | +76% | +51% | +731% | 0.876 | -39% | 2.248 | 42% | 3.126 | 24% | +18% | +2.84% | 0.0 |
| B | 1 | ADA/USDT | ma_cross | `kind=kama,pair=(50, 200)` | çıkış=stop_atr=2.0,trail_atr=3.0 | +102% | +170% | +390% | 0.871 | -28% | 2.561 | 41% | 3.628 | 22% | +20% | +3.47% | 0.0 |
| B | 2 | BTC/USDT | atr_breakout | `n=20,k=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤5 bar) | +33% | +70% | +154% | 0.87 | -16% | 2.373 | 46% | 2.797 | 26% | +20% | +1.77% | 0.0 |
| B | 1 | BTC/USDT | bollinger_breakout | `n=50,k=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +76% | +111% | +420% | 0.867 | -27% | 1.741 | 42% | 2.396 | 29% | +13% | +1.02% | 0.0 |
| B | 2 | ETH/USDT | donchian_breakout | `entry=100,exit=20` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_choch(≤3 bar) | +23% | +11% | +215% | 0.858 | -33% | 2.882 | 43% | 3.842 | 21% | +22% | +3.42% | 0.0 |
| B | 1 | XRP/USDT | high_52w_break | `n=126,exit_ma=50` | çıkış=stop_atr=2.0,trail_atr=3.0 | +131% | +148% | +741% | 0.848 | -39% | 2.259 | 44% | 2.904 | 26% | +18% | +2.79% | 0.0 |
| B | 2 | LTC/USDT | atr_breakout | `n=20,k=2.0` | filtre=regime_bench200 · çıkış=stop_atr=2.0,tp_r=3.0 | +90% | +109% | +440% | 0.845 | -28% | 1.843 | 48% | 1.954 | 34% | +15% | +2.01% | 0.0 |
| B | 2 | BTC/USDT | ma_cross | `kind=tema,pair=(20, 100)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤0 bar) | +61% | +68% | +126% | 0.843 | -29% | 2.819 | 54% | 2.451 | 29% | +24% | +2.17% | 0.0 |
| B | 1 | ETH/USDT | linreg_slope | `n=100,th=0.0005` | çıkış=stop_atr=2.0,trail_atr=3.0 | +53% | +31% | +301% | 0.827 | -36% | 2.069 | 38% | 3.362 | 23% | +15% | +2.19% | 0.0 |
| B | 1 | BTC/USDT | atr_breakout | `n=20,k=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +0% | +27% | +287% | 0.827 | -29% | 1.734 | 41% | 2.525 | 28% | +12% | +1.00% | 0.0 |
| B | 2 | BTC/USDT | cci_breakout | `n=20,level=150` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=donchian_breakout(≤3 bar) | +16% | +57% | +281% | 0.812 | -31% | 1.828 | 43% | 2.388 | 30% | +14% | +1.16% | 0.0 |
| B | 1 | BTC/USDT | bb_squeeze | `n=20,q=0.2,look=252` | çıkış=stop_atr=2.0,trail_atr=3.0 | +46% | +63% | +279% | 0.806 | -31% | 1.619 | 39% | 2.563 | 28% | +11% | +0.79% | 0.0 |
| B | 2 | ETH/USDT | atr_breakout | `n=10,k=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤3 bar) | +42% | +14% | +229% | 0.804 | -31% | 2.018 | 43% | 2.69 | 27% | +16% | +1.28% | 0.0 |
| B | 2 | LTC/USDT | williams_reversal | `n=21,lo=-95` | filtre=adx20 · çıkış=stop_atr=2.0,trail_atr=3.0 | +33% | +74% | +494% | 0.79 | -34% | 1.563 | 55% | 1.286 | 44% | +11% | +1.32% | 0.0 |
| B | 2 | TRX/USDT | trix_cross | `n=21,signal=9` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +46% | +98% | +414% | 0.786 | -39% | 1.647 | 41% | 2.395 | 30% | +11% | +1.14% | 0.0 |
| B | 2 | ADA/USDT | high_52w_break | `n=126,exit_ma=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar) | +70% | +46% | +474% | 0.776 | -40% | 2.087 | 36% | 3.77 | 21% | +15% | +2.75% | 0.0 |
| B | 2 | ADA/USDT | volume_breakout | `n=20,rv=3.0` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +60% | +55% | +201% | 0.775 | -31% | 2.067 | 62% | 1.285 | 44% | +18% | +2.22% | 0.0 |
| B | 1 | ETH/USDT | atr_breakout | `n=10,k=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +25% | +24% | +240% | 0.735 | -28% | 1.682 | 42% | 2.319 | 30% | +12% | +0.98% | 0.0 |
| B | 2 | TRX/USDT | triple_ma | `set=(10, 50, 200),kind=sma` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤3 bar) | +19% | +20% | +169% | 0.723 | -27% | 2.483 | 50% | 2.483 | 29% | +21% | +2.29% | 0.0 |
| B | 2 | XLM/USDT | price_ma | `kind=sma,n=200` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤3 bar) | +58% | +36% | +203% | 0.722 | -30% | 2.98 | 22% | 10.315 | 9% | +14% | +2.61% | 0.0 |
| B | 2 | BTC/USDT | volume_breakout | `n=50,rv=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤5 bar) | +45% | +73% | +114% | 0.693 | -21% | 2.065 | 41% | 2.973 | 25% | +16% | +1.48% | 0.0 |
| B | 1 | BCH/USDT | down_days | `n=5,hold_exit=3` | çıkış=stop_atr=2.0,trail_atr=3.0 | +9% | +39% | +274% | 0.692 | -37% | 1.42 | 58% | 1.024 | 49% | +9% | +0.79% | 0.0 |
| B | 2 | NEAR/USDT | rsi_divergence | `n=14,k=3,exit_level=70` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +84% | +53% | +123% | 0.689 | -37% | 1.851 | 52% | 1.69 | 37% | +15% | +2.26% | 0.0 |
| B | 2 | SOL/USDT | wavetrend_reversal | `n1=12,n2=26,lo=-60` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤3 bar) | +30% | +117% | +153% | 0.682 | -34% | 2.424 | 50% | 2.424 | 29% | +21% | +3.84% | 0.0 |
| B | 1 | BNB/USDT | triple_ma | `set=(10, 50, 200),kind=ema` | çıkış=stop_atr=2.0,trail_atr=3.0 | +12% | +27% | +288% | 0.663 | -40% | 1.684 | 43% | 2.246 | 31% | +12% | +1.24% | 0.0 |
| B | 2 | XLM/USDT | ma_cross | `kind=sma,pair=(20, 100)` | filtre=regime_bench200 · çıkış=stop_atr=2.0,trail_atr=3.0 | +29% | +75% | +199% | 0.65 | -30% | 2.003 | 36% | 3.525 | 22% | +14% | +2.23% | 0.0 |
| B | 2 | AVAX/USDT | atr_breakout | `n=20,k=1.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤3 bar) | +98% | +145% | +113% | 0.631 | -27% | 1.943 | 43% | 2.561 | 28% | +15% | +1.85% | 0.0 |
| B | 2 | AVAX/USDT | macd_divergence | `k=3,fast=12,slow=26` | filtre=regime_bench200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +130% | +109% | +89% | 0.625 | -33% | 1.6 | 49% | 1.646 | 38% | +12% | +1.14% | 0.0 |
| B | 1 | BTC/USDT | volume_breakout | `n=50,rv=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +18% | +71% | +137% | 0.612 | -29% | 1.651 | 41% | 2.392 | 30% | +11% | +0.91% | 0.0 |
| B | 1 | ATOM/USDT | rsi_divergence | `n=14,k=3,exit_level=70` | çıkış=stop_atr=2.0,trail_atr=3.0 | +46% | +74% | +217% | 0.608 | -40% | 1.471 | 36% | 2.669 | 27% | +8% | +1.15% | 0.0 |
| B | 2 | BCH/USDT | down_days | `n=5,hold_exit=3` | filtre=adx20 · çıkış=stop_atr=2.0,trail_atr=3.0 | +12% | +10% | +175% | 0.605 | -28% | 1.435 | 59% | 0.998 | 50% | +9% | +0.86% | 0.0 |
| B | 2 | TRX/USDT | smc_liquidity_sweep | `k=10` | çıkış=stop_atr=2.0,tp_r=3.0 | +30% | +66% | +301% | 0.602 | -38% | 1.414 | 35% | 2.626 | 28% | +7% | +0.75% | 0.0 |
| B | 2 | BNB/USDT | atr_breakout | `n=20,k=1.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_choch(≤0 bar) | +9% | +56% | +133% | 0.587 | -24% | 2.098 | 50% | 2.098 | 32% | +18% | +1.48% | 0.0 |
| B | 1 | AXS/USDT | ma_cross | `kind=sma,pair=(50, 200)` | çıkış=stop_atr=2.0,trail_atr=3.0 | +4% | +53% | +90% | 0.577 | -35% | 2.081 | 33% | 4.162 | 19% | +14% | +2.99% | 0.0 |
| B | 1 | ETH/USDT | ma_cross | `kind=kama,pair=(50, 150)` | çıkış=stop_atr=2.0,trail_atr=3.0 | +33% | +53% | +115% | 0.574 | -21% | 1.766 | 47% | 2.018 | 33% | +14% | +1.33% | 0.0 |
| B | 1 | XRP/USDT | rsi_reversal | `n=7,lo=10,exit=50` | çıkış=stop_atr=2.0,trail_atr=3.0 | +54% | +104% | +155% | 0.572 | -24% | 2.078 | 65% | 1.1 | 48% | +18% | +2.11% | 0.0 |
| B | 2 | BTC/USDT | smc_bos | `k=8` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=ma_cross(≤5 bar) | +34% | +60% | +99% | 0.56 | -35% | 1.708 | 48% | 1.83 | 35% | +13% | +0.99% | 0.0 |
| B | 2 | ATOM/USDT | rsi_divergence | `n=14,k=3,exit_level=70` | çıkış=stop_atr=2.0,max_hold=10 | +11% | +25% | +126% | 0.543 | -34% | 1.383 | 55% | 1.129 | 47% | +8% | +0.71% | 0.0 |
| B | 2 | TRX/USDT | smc_bos | `k=5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=ma_cross(≤3 bar) | +53% | +20% | +130% | 0.529 | -38% | 1.813 | 46% | 2.085 | 32% | +14% | +1.33% | 0.0 |
| B | 2 | INJ/USDT | cmf_flow | `n=10,th=0.1` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤0 bar) | +40% | +67% | +80% | 0.517 | -39% | 1.761 | 51% | 1.688 | 37% | +14% | +1.62% | 0.0 |
| B | 2 | LTC/USDT | stoch_reversal | `k=21,d=5,smooth=1,lo=10` | filtre=regime_bench200 · çıkış=stop_atr=2.0,tp_r=3.0 | +17% | +58% | +129% | 0.512 | -34% | 1.409 | 62% | 0.876 | 53% | +8% | +0.83% | 0.0 |
| B | 2 | XRP/USDT | rsi_reversal | `n=7,lo=10,exit=50` | çıkış=signal_only | +29% | +74% | +135% | 0.498 | -33% | 2.335 | 71% | 0.949 | 51% | +20% | +2.23% | 0.0 |
| B | 2 | ADA/USDT | smc_choch | `k=8` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=ma_cross(≤3 bar) | +98% | +58% | +98% | 0.486 | -35% | 2.216 | 41% | 3.185 | 24% | +17% | +2.24% | 0.0 |
| B | 1 | BTC/USDT | high_52w_break | `n=252,exit_ma=50` | çıkış=stop_atr=2.0,trail_atr=3.0 | +11% | +3% | +75% | 0.436 | -40% | 1.499 | 37% | 2.581 | 28% | +9% | +0.80% | 0.0 |

## Coin coin özet (ajan günlüğü)

- **AAVE/USDT**: 77 aday denendi, 1 kaldı. En iyi aday rsi_reversal (`n=5,lo=10,exit=50`, filtre=adx20 · çıkış=signal_only): OK — tüm adımlar geçti.
- **ADA/USDT**: 97 aday denendi, 7 kaldı. En iyi aday bollinger_breakout (`n=50,k=2.5`, filtre=htf_week_sma10 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **ALGO/USDT**: 72 aday denendi, 0 kaldı. En iyi aday adx_trend (`n=14,th=25`, filtre=trend_sma200 · çıkış=stop_atr=2.0,trail_atr=3.0): S4 — komşu ayarların %25'i kârlı.
- **APT/USDT**: 73 aday denendi, 0 kaldı. En iyi aday funding_extreme (`n=365,th=2.0`, çıkış=stop_atr=2.0,trail_atr=3.0): S6 — yılların %50'i kârlı.
- **ARB/USDT**: 94 aday denendi, 5 kaldı. En iyi aday ma_cross (`kind=sma,pair=(20, 50)`, filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **ATOM/USDT**: 71 aday denendi, 3 kaldı. En iyi aday macd_divergence (`k=3,fast=12,slow=26`, filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **AVAX/USDT**: 72 aday denendi, 2 kaldı. En iyi aday atr_breakout (`n=20,k=1.5`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤3 bar)): OK — tüm adımlar geçti.
- **AXS/USDT**: 72 aday denendi, 2 kaldı. En iyi aday smc_ote (`k=8,fib_lo=0.5`, filtre=trend_sma200 · çıkış=signal_only): OK — tüm adımlar geçti.
- **BCH/USDT**: 77 aday denendi, 2 kaldı. En iyi aday down_days (`n=5,hold_exit=3`, çıkış=stop_atr=2.0,trail_atr=3.0): OK — tüm adımlar geçti.
- **BNB/USDT**: 91 aday denendi, 5 kaldı. En iyi aday smc_bos (`k=5`, filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **BTC/USDT**: 95 aday denendi, 18 kaldı. En iyi aday linreg_slope (`n=20,th=0.0005`, filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0): OK — tüm adımlar geçti.
- **CRV/USDT**: 72 aday denendi, 0 kaldı. En iyi aday funding_extreme (`n=90,th=1.5`, filtre=adx20 · çıkış=signal_only): S2 — PF 2.573, 1x maks. düşüş -65%.
- **DOGE/USDT**: 79 aday denendi, 1 kaldı. En iyi aday high_52w_break (`n=252,exit_ma=50`, filtre=htf_week_sma10 · çıkış=trail_atr=3.0): OK — tüm adımlar geçti.
- **DOT/USDT**: 70 aday denendi, 0 kaldı. En iyi aday macd_divergence (`k=3,fast=12,slow=26`, filtre=regime_bench200 · çıkış=stop_atr=2.0,be_r=1.0): S4 — komşu ayarların %0'i kârlı.
- **ETC/USDT**: 71 aday denendi, 0 kaldı. En iyi aday adx_trend (`n=14,th=20`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_ote(≤3 bar)): S6 — yılların %56'i kârlı.
- **ETH/USDT**: 85 aday denendi, 15 kaldı. En iyi aday volume_breakout (`n=50,rv=3.0`, filtre=regime_bench200 · çıkış=signal_only): OK — tüm adımlar geçti.
- **FIL/USDT**: 74 aday denendi, 0 kaldı. En iyi aday mfi_reversal (`n=14,lo=10`, çıkış=stop_atr=2.0,trail_atr=3.0): S7 — PSR 0.812.
- **IMX/USDT**: 77 aday denendi, 0 kaldı. En iyi aday ultimate_reversal (`a=5,lo=25`, çıkış=stop_atr=2.0,trail_atr=3.0): S7 — PSR 0.837.
- **INJ/USDT**: 75 aday denendi, 3 kaldı. En iyi aday rsi_reversal (`n=7,lo=20,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): OK — tüm adımlar geçti.
- **LINK/USDT**: 77 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=70`, filtre=regime_bench200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S6 — yılların %56'i kârlı.
- **LTC/USDT**: 74 aday denendi, 3 kaldı. En iyi aday atr_breakout (`n=20,k=2.0`, filtre=regime_bench200 · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **MANA/USDT**: 69 aday denendi, 0 kaldı. En iyi aday hammer_star (`lookback_low=10`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.393, 1x maks. düşüş -46%.
- **MINA/USDT**: 77 aday denendi, 1 kaldı. En iyi aday adx_trend (`n=20,th=20`, filtre=regime_bench200 · çıkış=stop_atr=2.0,be_r=1.0): OK — tüm adımlar geçti.
- **NEAR/USDT**: 81 aday denendi, 2 kaldı. En iyi aday macd_cross (`cfg=(12, 26, 9),zero_filter=True`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar)): OK — tüm adımlar geçti.
- **OP/USDT**: 74 aday denendi, 3 kaldı. En iyi aday hammer_star (`lookback_low=10`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤3 bar)): OK — tüm adımlar geçti.
- **PYTH/USDT**: elendi (S0: 2.9 yıl veri var, en az 3.0 yıl gerekli).
- **SAND/USDT**: 70 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=70`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.352, 1x maks. düşüş -55%.
- **SNX/USDT**: 73 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=50`, filtre=regime_bench200 · çıkış=signal_only): S7 — PSR 0.864.
- **SOL/USDT**: 91 aday denendi, 1 kaldı. En iyi aday wavetrend_reversal (`n1=12,n2=26,lo=-60`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤3 bar)): OK — tüm adımlar geçti.
- **SUI/USDT**: 105 aday denendi, 7 kaldı. En iyi aday bollinger_reversion (`n=30,k=2.5`, filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **THETA/USDT**: 72 aday denendi, 0 kaldı. En iyi aday wavetrend_reversal (`n1=9,n2=26,lo=-60`, çıkış=stop_atr=2.0,trail_atr=3.0): S4 — komşu ayarların %33'i kârlı.
- **TRX/USDT**: 86 aday denendi, 5 kaldı. En iyi aday smc_choch (`k=5`, filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **UNI/USDT**: 83 aday denendi, 4 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=70`, çıkış=stop_atr=2.0,trail_atr=3.0): OK — tüm adımlar geçti.
- **XLM/USDT**: 92 aday denendi, 2 kaldı. En iyi aday price_ma (`kind=sma,n=200`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤3 bar)): OK — tüm adımlar geçti.
- **XRP/USDT**: 78 aday denendi, 5 kaldı. En iyi aday high_52w_break (`n=126,exit_ma=50`, filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.

## Zayıf yönler (dürüst liste)

- 37884 deneme yapıldı. Bu kadar çok denemede şans eseri iyi görünen strateji çıkar. DSR bunu düzeltir; tier A sadece DSR ≥ eşik olanlardır.
- Seçim ve test aynı geçmiş veride yapıldı. Gerçek test arenadaki ileri (paper) kayıttır.
- Survivorship: liste bugünün coinlerinden oluşur. Borsadan silinen coinler yok, bu sonucu iyimser yapar.
- Funding sabit yıllık oranla, likidasyon işlem bazında yaklaşık modellenir.
- Tek borsa verisi (Bitget, yoksa OKX/KuCoin). Emir defteri ve piyasa etkisi modellenmez.

## Arena

Arena: 100 aktif (eleme geçen), 0 kontrol (yakın aday, switcher kullanmaz), 0 yeni üye, 0 kontrolden aktife. Üst sınır 100.

## Switcher backtest kapısı

Geçti: **False** — kontroller: `{"beats_equal_weight_all_windows": false, "positive_at_cost_stress": true, "max_dd_ok": true}`

Pencereler: `{"3y": {"sharpe": 1.214, "ew_sharpe": 2.528}, "5y": {"sharpe": 0.997, "ew_sharpe": 2.067}, "full": {"sharpe": 0.975, "ew_sharpe": 2.08}}`
