# Eleme motoru — crypto_alts 4h (yön: both)

Veri: 2018-01-01 → 2026-11-02. Coin: 34 uygun (toplam 35). Denenen varyant: 592 × coin = **28229 deneme**.
Her (coin, kural) için tek en iyi nokta değil, **en sağlam bölgenin merkezi** seçildi. Bu bir aday listesidir, karar değildir. Karar sadece doğrulama kapısında verilir.

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bu liste binlerce deneme arasından seçildi; seçim süreçleri backtest'te iyi görünüp ileride çökebilir (2026-10-17 ve 10-19 testleri). Gerçek paraya aday olmadan önce `Time machine test` workflow'unu aynı yön (side) ve zaman dilimiyle çalıştırın. Kural: CLAUDE.md / AGENTS.md.

## Huni

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 68 | 2312 |
| S1 | her dönemde kârlı değil / az işlem | 2211 | 101 |
| S2 | kâr faktörü veya düşüş zayıf | 87 | 14 |
| S3 | yüksek maliyette zarar | 1 | 13 |
| S4 | plato yok (komşu ayarlar zararda) | 5 | 8 |
| S5 | 1 bar gecikmeye dayanıksız | 0 | 8 |
| S6 | yılların çoğunda kârlı değil | 2 | 6 |
| S7 | istatistiksel güven düşük (PSR) | 2 | 4 |

## 2. aşama: filtre × çıkış × kombo (sadece S1'i geçen adaylarda)

101 aday → 8101 ek deneme (DSR'a eklendi). Her aday için en sağlam filtre/çıkış hücresi ve en sağlam kombo seçildi; kombo sadece kuralı tek başına geçerse aday olur. Seçilenler aynı S1–S7 adımlarından geçti.

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 0 | 179 |
| S1 | her dönemde kârlı değil / az işlem | 45 | 134 |
| S2 | kâr faktörü veya düşüş zayıf | 65 | 69 |
| S3 | yüksek maliyette zarar | 0 | 69 |
| S4 | plato yok (komşu ayarlar zararda) | 27 | 42 |
| S5 | 1 bar gecikmeye dayanıksız | 0 | 42 |
| S6 | yılların çoğunda kârlı değil | 9 | 33 |
| S7 | istatistiksel güven düşük (PSR) | 0 | 33 |

## Geçenler (37)

Kazanma oranı tek başına bir şey söylemez. Sistem sadece **kazanma oranı > başabaş oranı** olduğunda kârlıdır. Başabaş = 1 / (1 + ödeme oranı); ödeme oranı = ortalama kazanç / ortalama kayıp (maliyet sonrası). Pay = kazanma oranı − başabaş. Beklenen = işlem başına ortalama net getiri.

| Tier | Aşama | Coin | Kural | Ayar | Varyant | 3y | 5y | Tüm | Sharpe | 1x DD | PF | Kazanma | Ödeme | Başabaş | Pay | Beklenen | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 2 | SUI/USDT | roc_breakout | `n=252,th=10` | filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0 | +813% | veri yok | +1202% | 1.786 | -30% | 2.8 | 44% | 3.617 | 22% | +22% | +5.22% | 0.091 |
| B | 2 | ARB/USDT | price_ma | `kind=kama,n=200` | filtre=trend_sma200 · çıkış=trail_atr=3.0 | +974% | veri yok | +1058% | 1.538 | -32% | 2.133 | 30% | 5.103 | 16% | +13% | +1.71% | 0.027 |
| B | 2 | ARB/USDT | smc_bos | `k=8` | filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +546% | veri yok | +568% | 1.453 | -36% | 1.775 | 60% | 1.162 | 46% | +14% | +1.60% | 0.021 |
| B | 2 | ARB/USDT | macd_zero | `cfg=(12, 26, 9)` | filtre=regime_bench200 · çıkış=stop_atr=2.0,tp_r=3.0 | +584% | veri yok | +674% | 1.446 | -40% | 1.743 | 37% | 2.97 | 25% | +12% | +1.99% | 0.021 |
| B | 2 | ARB/USDT | smc_choch | `k=8` | filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0 | +465% | veri yok | +530% | 1.309 | -32% | 1.903 | 42% | 2.643 | 27% | +14% | +2.68% | 0.011 |
| B | 2 | ARB/USDT | bollinger_breakout | `n=50,k=2.5` | filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +107% | veri yok | +145% | 1.3 | -19% | 2.493 | 65% | 1.36 | 42% | +22% | +1.93% | 0.009 |
| B | 2 | ARB/USDT | triple_ma | `set=(10, 50, 200),kind=ema` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +363% | veri yok | +403% | 1.217 | -34% | 1.729 | 35% | 3.234 | 24% | +11% | +2.14% | 0.006 |
| B | 2 | ARB/USDT | bb_squeeze | `n=20,q=0.1,look=126` | filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10 | +151% | veri yok | +179% | 1.171 | -26% | 1.858 | 49% | 1.904 | 34% | +15% | +1.45% | 0.005 |
| B | 2 | OP/USDT | adx_trend | `n=10,th=30` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +112% | veri yok | +227% | 1.179 | -21% | 2.319 | 38% | 3.71 | 21% | +17% | +1.95% | 0.002 |
| B | 2 | ARB/USDT | ma_cross | `kind=sma,pair=(10, 30)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤5 bar) | +284% | veri yok | +241% | 1.021 | -36% | 2.428 | 48% | 2.595 | 28% | +20% | +2.65% | 0.002 |
| B | 1 | ARB/USDT | hurst_switch | `n=200,fast=20,rsi_n=5` | çıkış=stop_atr=2.0,trail_atr=3.0 | +143% | veri yok | +135% | 0.953 | -31% | 2.171 | 41% | 3.121 | 24% | +17% | +2.76% | 0.001 |
| B | 2 | ARB/USDT | macd_zero | `cfg=(12, 26, 9)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤5 bar) | +123% | veri yok | +192% | 0.928 | -30% | 2.251 | 44% | 2.908 | 26% | +18% | +2.56% | 0.001 |
| B | 2 | ETH/USDT | bb_squeeze | `n=20,q=0.2,look=252` | filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10 | +61% | +50% | +1296% | 1.352 | -36% | 1.858 | 48% | 1.992 | 33% | +15% | +1.16% | 0.0 |
| B | 2 | ETH/USDT | bollinger_breakout | `n=50,k=2.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤3 bar) | +247% | +453% | +5726% | 1.348 | -37% | 2.547 | 49% | 2.624 | 28% | +22% | +2.52% | 0.0 |
| B | 2 | ETH/USDT | volume_breakout | `n=50,rv=3.0` | filtre=htf_week_sma10 · çıkış=trail_atr=3.0 | +162% | +265% | +1391% | 1.277 | -31% | 3.352 | 52% | 3.106 | 24% | +28% | +3.96% | 0.0 |
| B | 2 | XRP/USDT | high_52w_break | `n=126,exit_ma=50` | filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10 | +293% | +285% | +2110% | 1.143 | -40% | 2.562 | 49% | 2.663 | 27% | +22% | +3.78% | 0.0 |
| B | 2 | ETH/USDT | volume_breakout | `n=50,rv=3.0` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤3 bar) | +96% | +172% | +977% | 1.011 | -34% | 2.444 | 47% | 2.754 | 27% | +20% | +2.22% | 0.0 |
| B | 2 | DOGE/USDT | high_52w_break | `n=252,exit_ma=50` | filtre=htf_week_sma10 · çıkış=trail_atr=3.0 | +67% | +70% | +3663% | 0.986 | -36% | 5.937 | 60% | 3.958 | 20% | +40% | +13.95% | 0.0 |
| B | 2 | BTC/USDT | high_52w_break | `n=252,exit_ma=50` | filtre=adx20 · çıkış=stop_atr=2.0,be_r=1.0 | +38% | +53% | +407% | 0.928 | -37% | 2.879 | 31% | 6.282 | 14% | +18% | +3.00% | 0.0 |
| B | 2 | DOGE/USDT | high_52w_break | `n=252,exit_ma=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=chop_switch(≤0 bar) | +44% | +57% | +2533% | 0.928 | -33% | 6.656 | 62% | 4.051 | 20% | +42% | +13.25% | 0.0 |
| B | 2 | ETH/USDT | high_52w_break | `n=126,exit_ma=50` | filtre=low_vol · çıkış=signal_only | +74% | +91% | +691% | 0.927 | -33% | 2.577 | 44% | 3.288 | 23% | +21% | +4.12% | 0.0 |
| B | 2 | DOT/USDT | rsi_divergence | `n=14,k=3,exit_level=70` | filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10 | +88% | +88% | +121% | 0.87 | -19% | 1.935 | 57% | 1.464 | 41% | +16% | +1.35% | 0.0 |
| B | 1 | XRP/USDT | high_52w_break | `n=126,exit_ma=50` | çıkış=stop_atr=2.0,trail_atr=3.0 | +131% | +148% | +741% | 0.848 | -39% | 2.259 | 44% | 2.904 | 26% | +18% | +2.79% | 0.0 |
| B | 2 | BTC/USDT | keltner_breakout | `n=20,k=2.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=chop_switch(≤3 bar) | +26% | +71% | +261% | 0.832 | -25% | 2.03 | 45% | 2.505 | 28% | +16% | +1.46% | 0.0 |
| B | 2 | ARB/USDT | cci_breakout | `n=40,level=150` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_choch(≤3 bar) | +229% | veri yok | +181% | 0.823 | -32% | 1.651 | 38% | 2.752 | 27% | +11% | +1.59% | 0.0 |
| B | 2 | DOT/USDT | rsi_divergence | `n=14,k=3,exit_level=70` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar) | +68% | +104% | +130% | 0.822 | -29% | 2.035 | 44% | 2.543 | 28% | +16% | +2.04% | 0.0 |
| B | 2 | DOT/USDT | bb_squeeze | `n=20,q=0.1,look=252` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +19% | +14% | +194% | 0.808 | -37% | 1.87 | 43% | 2.494 | 29% | +14% | +1.57% | 0.0 |
| B | 2 | ETH/USDT | bb_squeeze | `n=20,q=0.2,look=252` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=ma_cross(≤5 bar) | +4% | +80% | +296% | 0.804 | -35% | 1.979 | 42% | 2.736 | 27% | +15% | +1.48% | 0.0 |
| B | 2 | DOT/USDT | bb_squeeze | `n=20,q=0.1,look=252` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=ma_cross(≤3 bar) | +23% | +44% | +172% | 0.791 | -33% | 3.184 | 57% | 2.42 | 29% | +28% | +2.84% | 0.0 |
| B | 2 | BTC/USDT | volume_breakout | `n=50,rv=3.0` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=chop_switch(≤0 bar) | +32% | +63% | +122% | 0.777 | -14% | 2.708 | 47% | 3.095 | 24% | +22% | +2.02% | 0.0 |
| B | 2 | ADA/USDT | high_52w_break | `n=126,exit_ma=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar) | +70% | +46% | +474% | 0.776 | -40% | 2.087 | 36% | 3.77 | 21% | +15% | +2.75% | 0.0 |
| B | 2 | BTC/USDT | volume_breakout | `n=50,rv=3.0` | filtre=trend_sma200 · çıkış=stop_atr=2.0,trail_atr=3.0 | +29% | +117% | +248% | 0.694 | -27% | 1.873 | 39% | 2.908 | 26% | +14% | +1.35% | 0.0 |
| B | 2 | APT/USDT | funding_extreme | `n=90,th=1.5` | filtre=trend_sma200 · çıkış=stop_atr=2.0,trail_atr=3.0 | +83% | veri yok | +80% | 0.684 | -38% | 1.595 | 52% | 1.441 | 41% | +12% | +1.22% | 0.0 |
| B | 2 | BTC/USDT | roc_breakout | `n=252,th=10` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_choch(≤5 bar) | +33% | +48% | +110% | 0.616 | -23% | 3.169 | 49% | 3.345 | 23% | +26% | +2.43% | 0.0 |
| B | 2 | SAND/USDT | rsi_divergence | `n=14,k=3,exit_level=70` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar) | +33% | +43% | +74% | 0.56 | -35% | 1.705 | 43% | 2.302 | 30% | +12% | +1.57% | 0.0 |
| B | 1 | BTC/USDT | volume_breakout | `n=50,rv=3.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +24% | +114% | +160% | 0.55 | -35% | 1.599 | 38% | 2.634 | 28% | +10% | +1.00% | 0.0 |
| B | 1 | BTC/USDT | high_52w_break | `n=252,exit_ma=50` | çıkış=stop_atr=2.0,trail_atr=3.0 | +11% | +3% | +75% | 0.436 | -40% | 1.499 | 37% | 2.581 | 28% | +9% | +0.80% | 0.0 |

## Coin coin özet (ajan günlüğü)

- **AAVE/USDT**: 68 aday denendi, 0 kaldı. En iyi aday coppock_turn (`scale=5`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +25%, 5y -3%, full +89%; 152 işlem (zararlı: 5y).
- **ADA/USDT**: 75 aday denendi, 1 kaldı. En iyi aday high_52w_break (`n=126,exit_ma=50`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar)): OK — tüm adımlar geçti.
- **ALGO/USDT**: 70 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=70`, filtre=regime_bench200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 1.627, 1x maks. düşüş -41%.
- **APT/USDT**: 74 aday denendi, 1 kaldı. En iyi aday funding_extreme (`n=90,th=1.5`, filtre=trend_sma200 · çıkış=stop_atr=2.0,trail_atr=3.0): OK — tüm adımlar geçti.
- **ARB/USDT**: 103 aday denendi, 11 kaldı. En iyi aday price_ma (`kind=kama,n=200`, filtre=trend_sma200 · çıkış=trail_atr=3.0): OK — tüm adımlar geçti.
- **ATOM/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=14,lo=10,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +19%, 5y +19%, full +21%; 4 işlem.
- **AVAX/USDT**: 72 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=63,th=5`, filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0): S2 — PF 2.533, 1x maks. düşüş -55%.
- **AXS/USDT**: 71 aday denendi, 0 kaldı. En iyi aday smc_ote (`k=8,fib_lo=0.5`, filtre=regime_bench200 · çıkış=trail_atr=3.0): S2 — PF 1.475, 1x maks. düşüş -67%.
- **BCH/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=2,lo=10,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +0%, 5y +0%, full +0%; 0 işlem (zararlı: 3y, 5y, full).
- **BNB/USDT**: 76 aday denendi, 0 kaldı. En iyi aday high_52w_break (`n=252,exit_ma=50`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar)): S6 — yılların %56'i kârlı.
- **BTC/USDT**: 82 aday denendi, 7 kaldı. En iyi aday high_52w_break (`n=252,exit_ma=50`, filtre=adx20 · çıkış=stop_atr=2.0,be_r=1.0): OK — tüm adımlar geçti.
- **CRV/USDT**: 70 aday denendi, 0 kaldı. En iyi aday funding_extreme (`n=90,th=1.5`, filtre=regime_bench200 · çıkış=signal_only): S2 — PF 1.815, 1x maks. düşüş -73%.
- **DOGE/USDT**: 73 aday denendi, 2 kaldı. En iyi aday high_52w_break (`n=252,exit_ma=50`, filtre=htf_week_sma10 · çıkış=trail_atr=3.0): OK — tüm adımlar geçti.
- **DOT/USDT**: 74 aday denendi, 4 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=70`, filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **ETC/USDT**: 70 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=252,th=10`, filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0): S2 — PF 1.576, 1x maks. düşüş -52%.
- **ETH/USDT**: 83 aday denendi, 6 kaldı. En iyi aday bb_squeeze (`n=20,q=0.2,look=252`, filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **FIL/USDT**: 76 aday denendi, 0 kaldı. En iyi aday stoch_reversal (`k=14,d=5,smooth=3,lo=10`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_ote(≤3 bar)): S4 — komşu ayarların %20'i kârlı.
- **IMX/USDT**: 71 aday denendi, 0 kaldı. En iyi aday ultimate_reversal (`a=5,lo=25`, filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10): S4 — komşu ayarların %0'i kârlı.
- **INJ/USDT**: 69 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=14,lo=20,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.529, 1x maks. düşüş -51%.
- **LINK/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=28,lo=10,exit=70`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +0%, 5y +0%, full +13%; 1 işlem (zararlı: 3y, 5y).
- **LTC/USDT**: 68 aday denendi, 0 kaldı. En iyi aday bb_squeeze (`n=20,q=0.1,look=126`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -35%, 5y -57%, full -3%; 271 işlem (zararlı: 3y, 5y, full).
- **MANA/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=21,lo=10,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +0%, 5y +19%, full +17%; 2 işlem (zararlı: 3y).
- **MINA/USDT**: 72 aday denendi, 0 kaldı. En iyi aday atr_breakout (`n=20,k=2.0`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤3 bar)): S4 — komşu ayarların %0'i kârlı.
- **NEAR/USDT**: 68 aday denendi, 0 kaldı. En iyi aday force_index (`n=2`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -47%, 5y -80%, full +5%; 1086 işlem (zararlı: 3y, 5y).
- **OP/USDT**: 74 aday denendi, 1 kaldı. En iyi aday adx_trend (`n=10,th=30`, filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **PYTH/USDT**: elendi (S0: 2.9 yıl veri var, en az 3.0 yıl gerekli).
- **SAND/USDT**: 81 aday denendi, 1 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=70`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar)): OK — tüm adımlar geçti.
- **SNX/USDT**: 68 aday denendi, 0 kaldı. En iyi aday gap_fade (`g=0.02`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +0%, 5y +0%, full +4%; 1 işlem (zararlı: 3y, 5y).
- **SOL/USDT**: 74 aday denendi, 0 kaldı. En iyi aday high_52w_break (`n=126,exit_ma=50`, filtre=regime_bench200 · çıkış=signal_only): S6 — yılların %57'i kârlı.
- **SUI/USDT**: 83 aday denendi, 1 kaldı. En iyi aday roc_breakout (`n=252,th=10`, filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **THETA/USDT**: 68 aday denendi, 0 kaldı. En iyi aday cci_breakout (`n=40,level=100`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -15%, 5y -56%, full -84%; 689 işlem (zararlı: 3y, 5y, full).
- **TRX/USDT**: 70 aday denendi, 0 kaldı. En iyi aday mfi_reversal (`n=14,lo=10`, filtre=htf_week_sma10 · çıkış=trail_atr=3.0): S4 — komşu ayarların %33'i kârlı.
- **UNI/USDT**: 72 aday denendi, 0 kaldı. En iyi aday macd_divergence (`k=3,fast=12,slow=26`, filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S4 — komşu ayarların %0'i kârlı.
- **XLM/USDT**: 73 aday denendi, 0 kaldı. En iyi aday chop_switch (`n=14,lo=38.2,hi=61.8`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar)): S4 — komşu ayar yok.
- **XRP/USDT**: 71 aday denendi, 2 kaldı. En iyi aday high_52w_break (`n=126,exit_ma=50`, filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.

## Zayıf yönler (dürüst liste)

- 28229 deneme yapıldı. Bu kadar çok denemede şans eseri iyi görünen strateji çıkar. DSR bunu düzeltir; tier A sadece DSR ≥ eşik olanlardır.
- Seçim ve test aynı geçmiş veride yapıldı. Gerçek test arenadaki ileri (paper) kayıttır.
- Survivorship: liste bugünün coinlerinden oluşur. Borsadan silinen coinler yok, bu sonucu iyimser yapar.
- Funding sabit yıllık oranla, likidasyon işlem bazında yaklaşık modellenir.
- Tek borsa verisi (Bitget, yoksa OKX/KuCoin). Emir defteri ve piyasa etkisi modellenmez.

## Arena

Arena: 74 aktif (eleme geçen), 26 kontrol (yakın aday, switcher kullanmaz), 18 yeni üye, 0 kontrolden aktife. Üst sınır 100.

## Switcher backtest kapısı

Geçti: **False** — kontroller: `{"beats_equal_weight_all_windows": false, "positive_at_cost_stress": true, "max_dd_ok": true}`

Pencereler: `{"3y": {"sharpe": 1.154, "ew_sharpe": 2.753}, "5y": {"sharpe": 1.091, "ew_sharpe": 2.26}, "full": {"sharpe": 1.017, "ew_sharpe": 2.071}}`
