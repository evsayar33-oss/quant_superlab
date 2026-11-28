# Eleme motoru — crypto_alts 4h_short (yön: short)

Veri: 2018-01-01 → 2026-11-02. Coin: 34 uygun (toplam 35). Denenen varyant: 592 × coin = **31684 deneme**.
Her (coin, kural) için tek en iyi nokta değil, **en sağlam bölgenin merkezi** seçildi. Bu bir aday listesidir, karar değildir. Karar sadece doğrulama kapısında verilir.

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bu liste binlerce deneme arasından seçildi; seçim süreçleri backtest'te iyi görünüp ileride çökebilir (2026-10-17 ve 10-19 testleri). Gerçek paraya aday olmadan önce `Time machine test` workflow'unu aynı yön (side) ve zaman dilimiyle çalıştırın. Kural: CLAUDE.md / AGENTS.md.

## Huni

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 68 | 2312 |
| S1 | her dönemde kârlı değil / az işlem | 2168 | 144 |
| S2 | kâr faktörü veya düşüş zayıf | 126 | 18 |
| S3 | yüksek maliyette zarar | 5 | 13 |
| S4 | plato yok (komşu ayarlar zararda) | 0 | 13 |
| S5 | 1 bar gecikmeye dayanıksız | 2 | 11 |
| S6 | yılların çoğunda kârlı değil | 4 | 7 |
| S7 | istatistiksel güven düşük (PSR) | 2 | 5 |

## 2. aşama: filtre × çıkış × kombo (sadece S1'i geçen adaylarda)

144 aday → 11556 ek deneme (DSR'a eklendi). Her aday için en sağlam filtre/çıkış hücresi ve en sağlam kombo seçildi; kombo sadece kuralı tek başına geçerse aday olur. Seçilenler aynı S1–S7 adımlarından geçti.

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 0 | 260 |
| S1 | her dönemde kârlı değil / az işlem | 67 | 193 |
| S2 | kâr faktörü veya düşüş zayıf | 64 | 129 |
| S3 | yüksek maliyette zarar | 2 | 127 |
| S4 | plato yok (komşu ayarlar zararda) | 31 | 96 |
| S5 | 1 bar gecikmeye dayanıksız | 3 | 93 |
| S6 | yılların çoğunda kârlı değil | 15 | 78 |
| S7 | istatistiksel güven düşük (PSR) | 5 | 73 |

## Geçenler (78)

Kazanma oranı tek başına bir şey söylemez. Sistem sadece **kazanma oranı > başabaş oranı** olduğunda kârlıdır. Başabaş = 1 / (1 + ödeme oranı); ödeme oranı = ortalama kazanç / ortalama kayıp (maliyet sonrası). Pay = kazanma oranı − başabaş. Beklenen = işlem başına ortalama net getiri.

| Tier | Aşama | Coin | Kural | Ayar | Varyant | 3y | 5y | Tüm | Sharpe | 1x DD | PF | Kazanma | Ödeme | Başabaş | Pay | Beklenen | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 2 | ARB/USDT | price_ma | `kind=kama,n=200` | filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0 | +961% | veri yok | +1003% | 2.048 | -39% | 2.569 | 27% | 7.065 | 12% | +14% | +2.36% | 0.336 |
| B | 2 | ARB/USDT | smc_bos | `k=2` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +678% | veri yok | +941% | 1.833 | -38% | 2.098 | 45% | 2.601 | 28% | +17% | +2.26% | 0.194 |
| B | 2 | ARB/USDT | roc_breakout | `n=63,th=0` | filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0 | +511% | veri yok | +682% | 1.739 | -23% | 2.419 | 39% | 3.77 | 21% | +18% | +1.94% | 0.15 |
| B | 2 | ARB/USDT | ppo_cross | `cfg=(12, 26, 9)` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +443% | veri yok | +744% | 1.692 | -36% | 1.903 | 42% | 2.681 | 27% | +14% | +1.49% | 0.134 |
| B | 2 | ARB/USDT | keltner_breakout | `n=50,k=2.0` | filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10 | +399% | veri yok | +466% | 1.634 | -28% | 2.435 | 54% | 2.094 | 32% | +21% | +2.05% | 0.09 |
| B | 2 | ARB/USDT | cci_breakout | `n=14,level=100` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +583% | veri yok | +595% | 1.55 | -29% | 1.766 | 40% | 2.635 | 28% | +13% | +1.33% | 0.082 |
| B | 2 | APT/USDT | macd_zero | `cfg=(12, 26, 9)` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +148% | veri yok | +399% | 1.551 | -23% | 2.52 | 60% | 1.663 | 38% | +23% | +2.15% | 0.071 |
| B | 2 | ARB/USDT | macd_cross | `cfg=(12, 26, 9),zero_filter=True` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +175% | veri yok | +303% | 1.372 | -34% | 2.123 | 48% | 2.282 | 30% | +18% | +1.90% | 0.044 |
| B | 2 | ARB/USDT | vwap_cross | `n=50` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +264% | veri yok | +337% | 1.347 | -36% | 1.727 | 24% | 5.426 | 16% | +9% | +1.10% | 0.038 |
| B | 2 | ARB/USDT | macd_cross | `cfg=(12, 26, 9),zero_filter=True` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +208% | veri yok | +206% | 1.415 | -16% | 3.844 | 56% | 2.989 | 25% | +31% | +3.76% | 0.037 |
| B | 2 | ARB/USDT | inside_bar | `trend_n=50` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +303% | veri yok | +318% | 1.332 | -27% | 2.234 | 41% | 3.171 | 24% | +17% | +2.19% | 0.035 |
| B | 2 | ARB/USDT | aroon_cross | `n=14` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +544% | veri yok | +449% | 1.319 | -40% | 1.662 | 40% | 2.493 | 29% | +11% | +1.28% | 0.032 |
| B | 2 | ARB/USDT | trix_cross | `n=15,signal=7` | filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +215% | veri yok | +269% | 1.305 | -24% | 1.815 | 54% | 1.522 | 40% | +15% | +1.34% | 0.029 |
| B | 2 | ARB/USDT | psar_flip | `cfg=(0.01, 0.1)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤5 bar) | +155% | veri yok | +199% | 1.307 | -17% | 4.509 | 70% | 1.933 | 34% | +36% | +4.13% | 0.023 |
| B | 2 | ARB/USDT | supertrend_flip | `cfg=(7, 2.0)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +308% | veri yok | +313% | 1.281 | -34% | 2.709 | 51% | 2.608 | 28% | +23% | +3.13% | 0.023 |
| B | 2 | ARB/USDT | awesome_zero | `fast=5,slow=34` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +271% | veri yok | +322% | 1.203 | -32% | 1.799 | 40% | 2.699 | 27% | +13% | +1.63% | 0.02 |
| B | 2 | ARB/USDT | ichimoku_cloud | `cfg=(7, 22, 44)` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +174% | veri yok | +214% | 1.189 | -26% | 1.769 | 36% | 3.134 | 24% | +12% | +1.32% | 0.017 |
| B | 2 | ARB/USDT | smc_order_block | `k=3,max_age=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤3 bar) | +171% | veri yok | +267% | 1.207 | -34% | 2.014 | 35% | 3.731 | 21% | +14% | +1.52% | 0.016 |
| B | 2 | ARB/USDT | smc_choch | `k=3` | filtre=low_vol · çıkış=stop_atr=2.0,trail_atr=3.0 | +252% | veri yok | +285% | 1.2 | -24% | 2.277 | 46% | 2.691 | 27% | +19% | +2.22% | 0.016 |
| B | 2 | ARB/USDT | aroon_cross | `n=14` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤5 bar) | +203% | veri yok | +222% | 1.199 | -20% | 3.196 | 55% | 2.64 | 28% | +27% | +3.20% | 0.014 |
| B | 2 | ARB/USDT | donchian_breakout | `entry=40,exit=10` | filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +102% | veri yok | +124% | 1.16 | -14% | 3.036 | 69% | 1.349 | 43% | +27% | +2.39% | 0.013 |
| B | 2 | ARB/USDT | ppo_cross | `cfg=(12, 26, 9)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +231% | veri yok | +285% | 1.167 | -25% | 1.891 | 39% | 2.979 | 25% | +14% | +1.55% | 0.011 |
| B | 2 | ARB/USDT | smc_order_block | `k=3,max_age=50` | filtre=low_vol · çıkış=trail_atr=3.0 | +281% | veri yok | +362% | 1.101 | -38% | 1.533 | 29% | 3.79 | 21% | +8% | +0.78% | 0.011 |
| B | 2 | ARB/USDT | cmf_flow | `n=20,th=0.05` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +117% | veri yok | +193% | 1.048 | -30% | 1.906 | 46% | 2.218 | 31% | +15% | +1.24% | 0.009 |
| B | 2 | ARB/USDT | linreg_slope | `n=20,th=0.001` | filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +214% | veri yok | +193% | 1.045 | -30% | 1.585 | 55% | 1.292 | 44% | +12% | +1.13% | 0.009 |
| B | 2 | ARB/USDT | triple_ma | `set=(10, 50, 200),kind=ema` | filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0 | +139% | veri yok | +135% | 0.96 | -21% | 2.195 | 41% | 3.136 | 24% | +17% | +2.86% | 0.006 |
| B | 2 | ARB/USDT | ma_cross | `kind=hma,pair=(20, 100)` | filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +116% | veri yok | +111% | 0.945 | -21% | 1.694 | 53% | 1.477 | 40% | +13% | +1.23% | 0.006 |
| B | 2 | APT/USDT | cmf_flow | `n=20,th=0.05` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +118% | veri yok | +244% | 1.0 | -30% | 1.803 | 47% | 2.024 | 33% | +14% | +1.43% | 0.005 |
| B | 2 | ARB/USDT | obv_trend | `n=20,price_n=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +167% | veri yok | +193% | 0.942 | -37% | 1.605 | 33% | 3.272 | 23% | +10% | +0.89% | 0.005 |
| B | 2 | ARB/USDT | macd_zero | `cfg=(12, 26, 9)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=cmf_flow(≤5 bar) | +128% | veri yok | +138% | 0.92 | -18% | 3.3 | 56% | 2.55 | 28% | +28% | +2.92% | 0.005 |
| B | 2 | ARB/USDT | vwap_cross | `n=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤5 bar) | +151% | veri yok | +164% | 1.014 | -27% | 2.198 | 31% | 4.946 | 17% | +14% | +1.73% | 0.004 |
| B | 1 | ARB/USDT | donchian_breakout | `entry=40,exit=10` | çıkış=stop_atr=2.0,trail_atr=3.0 | +191% | veri yok | +231% | 0.944 | -26% | 2.089 | 53% | 1.885 | 35% | +18% | +2.16% | 0.004 |
| B | 2 | ARB/USDT | bollinger_breakout | `n=50,k=2.5` | çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +106% | veri yok | +119% | 0.931 | -24% | 2.32 | 57% | 1.763 | 36% | +21% | +2.24% | 0.004 |
| B | 2 | ARB/USDT | vortex_cross | `n=14` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤3 bar) | +103% | veri yok | +102% | 0.936 | -17% | 2.716 | 49% | 2.859 | 26% | +23% | +2.12% | 0.003 |
| B | 2 | ARB/USDT | trix_cross | `n=15,signal=7` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=cmf_flow(≤5 bar) | +107% | veri yok | +135% | 0.892 | -30% | 2.259 | 56% | 1.791 | 36% | +20% | +2.11% | 0.003 |
| B | 2 | ARB/USDT | supertrend_flip | `cfg=(7, 2.0)` | filtre=htf_week_sma10 · çıkış=trail_atr=3.0 | +220% | veri yok | +184% | 0.849 | -30% | 1.615 | 40% | 2.384 | 30% | +11% | +1.43% | 0.003 |
| B | 2 | ARB/USDT | roc_breakout | `n=63,th=0` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤0 bar) | +81% | veri yok | +75% | 0.811 | -19% | 2.077 | 47% | 2.374 | 30% | +17% | +1.48% | 0.003 |
| B | 2 | OP/USDT | trix_cross | `n=21,signal=9` | filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +143% | veri yok | +163% | 0.914 | -33% | 1.602 | 56% | 1.25 | 44% | +12% | +1.29% | 0.002 |
| B | 2 | OP/USDT | macd_zero | `cfg=(5, 35, 5)` | filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0 | +12% | veri yok | +269% | 0.911 | -34% | 1.929 | 35% | 3.55 | 22% | +13% | +2.40% | 0.002 |
| B | 2 | ARB/USDT | ma_cross | `kind=hma,pair=(20, 100)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤3 bar) | +150% | veri yok | +142% | 0.841 | -36% | 1.955 | 48% | 2.106 | 32% | +16% | +2.15% | 0.002 |
| B | 1 | ARB/USDT | bollinger_breakout | `n=50,k=2.5` | çıkış=stop_atr=2.0,trail_atr=3.0 | +119% | veri yok | +137% | 0.827 | -29% | 2.519 | 52% | 2.3 | 30% | +22% | +2.73% | 0.002 |
| B | 2 | ARB/USDT | smc_choch | `k=3` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤5 bar) | +118% | veri yok | +113% | 0.822 | -30% | 1.988 | 51% | 1.894 | 35% | +17% | +2.34% | 0.002 |
| B | 2 | ARB/USDT | adx_trend | `n=10,th=20` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +78% | veri yok | +92% | 0.779 | -25% | 1.721 | 34% | 3.279 | 23% | +11% | +1.27% | 0.002 |
| B | 2 | ARB/USDT | ichimoku_cloud | `cfg=(7, 22, 44)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +117% | veri yok | +116% | 0.767 | -26% | 1.856 | 38% | 3.048 | 25% | +13% | +1.44% | 0.002 |
| B | 1 | SUI/USDT | linreg_slope | `n=100,th=0.0005` | çıkış=stop_atr=2.0,trail_atr=3.0 | +91% | veri yok | +94% | 0.724 | -35% | 1.897 | 40% | 2.908 | 26% | +14% | +2.28% | 0.002 |
| B | 2 | FIL/USDT | wavetrend_reversal | `n1=12,n2=18,lo=-60` | filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +295% | +277% | +479% | 1.035 | -29% | 1.896 | 60% | 1.264 | 44% | +16% | +1.82% | 0.001 |
| B | 2 | IMX/USDT | price_ma | `kind=sma,n=150` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar) | +84% | veri yok | +262% | 0.921 | -29% | 2.626 | 31% | 5.752 | 15% | +16% | +2.34% | 0.001 |
| B | 2 | APT/USDT | ichimoku_cloud | `cfg=(7, 22, 44)` | filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +54% | veri yok | +94% | 0.81 | -35% | 1.62 | 50% | 1.65 | 38% | +12% | +0.77% | 0.001 |
| B | 2 | ARB/USDT | rsi_midline | `n=21,level=60` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,max_hold=10 | +114% | veri yok | +127% | 0.76 | -28% | 1.563 | 48% | 1.731 | 37% | +11% | +1.01% | 0.001 |
| B | 2 | OP/USDT | smc_ote | `k=8,fib_lo=0.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=cmf_flow(≤3 bar) | +82% | veri yok | +58% | 0.736 | -27% | 1.905 | 53% | 1.715 | 37% | +16% | +1.35% | 0.001 |
| B | 2 | ARB/USDT | awesome_zero | `fast=5,slow=34` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=cmf_flow(≤5 bar) | +89% | veri yok | +105% | 0.721 | -34% | 1.928 | 44% | 2.41 | 29% | +15% | +1.68% | 0.001 |
| B | 1 | APT/USDT | triple_ma | `set=(5, 20, 50),kind=ema` | çıkış=stop_atr=2.0,trail_atr=3.0 | +63% | veri yok | +143% | 0.673 | -39% | 1.402 | 36% | 2.501 | 29% | +7% | +0.86% | 0.001 |
| B | 2 | ETH/USDT | price_ma | `kind=sma,n=150` | filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10 | +77% | +117% | +297% | 1.084 | -24% | 2.034 | 38% | 3.313 | 23% | +15% | +0.90% | 0.0 |
| B | 2 | XRP/USDT | ma_cross | `kind=sma,pair=(20, 50)` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +35% | +144% | +688% | 1.01 | -27% | 2.047 | 44% | 2.654 | 27% | +16% | +1.92% | 0.0 |
| B | 2 | FIL/USDT | ppo_cross | `cfg=(12, 26, 9)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤0 bar) | +80% | +280% | +331% | 1.0 | -25% | 2.455 | 46% | 2.919 | 26% | +20% | +2.06% | 0.0 |
| B | 2 | FIL/USDT | tsi_cross | `cfg=(25, 13, 7)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤0 bar) | +80% | +242% | +287% | 0.935 | -26% | 2.078 | 41% | 2.953 | 25% | +16% | +1.67% | 0.0 |
| B | 2 | XLM/USDT | ma_cross | `kind=sma,pair=(10, 50)` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +19% | +80% | +837% | 0.894 | -35% | 2.075 | 44% | 2.683 | 27% | +16% | +2.21% | 0.0 |
| B | 1 | FIL/USDT | rsi_reversal | `n=14,lo=30,exit=50` | çıkış=stop_atr=2.0,trail_atr=3.0 | +31% | +123% | +335% | 0.884 | -33% | 1.538 | 58% | 1.128 | 47% | +11% | +1.19% | 0.0 |
| B | 2 | DOT/USDT | smc_ote | `k=8,fib_lo=0.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤5 bar) | +120% | +238% | +176% | 0.863 | -32% | 1.784 | 45% | 2.167 | 32% | +14% | +1.25% | 0.0 |
| B | 2 | ETH/USDT | bollinger_breakout | `n=50,k=2.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=ma_cross(≤5 bar) | +55% | +135% | +421% | 0.862 | -30% | 3.525 | 51% | 3.378 | 23% | +28% | +4.04% | 0.0 |
| B | 2 | DOGE/USDT | linreg_slope | `n=100,th=0.0005` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +118% | +180% | +338% | 0.861 | -36% | 2.549 | 42% | 3.488 | 22% | +20% | +3.87% | 0.0 |
| B | 2 | ETH/USDT | bollinger_breakout | `n=50,k=2.5` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +93% | +280% | +455% | 0.838 | -37% | 2.108 | 45% | 2.584 | 28% | +17% | +2.96% | 0.0 |
| B | 2 | FIL/USDT | macd_cross | `cfg=(8, 21, 5),zero_filter=False` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar) | +47% | +143% | +277% | 0.794 | -33% | 1.47 | 36% | 2.624 | 28% | +8% | +0.72% | 0.0 |
| B | 2 | FIL/USDT | trix_cross | `n=9,signal=7` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar) | +90% | +219% | +255% | 0.767 | -32% | 1.593 | 41% | 2.266 | 31% | +11% | +1.08% | 0.0 |
| B | 2 | DOGE/USDT | roc_breakout | `n=126,th=5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤5 bar) | +58% | +71% | +147% | 0.754 | -33% | 2.41 | 45% | 2.934 | 25% | +20% | +2.02% | 0.0 |
| B | 2 | FIL/USDT | psar_flip | `cfg=(0.03, 0.3)` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤3 bar) | +16% | +166% | +160% | 0.712 | -31% | 1.698 | 43% | 2.279 | 30% | +12% | +1.28% | 0.0 |
| B | 2 | IMX/USDT | triple_ma | `set=(20, 50, 100),kind=ema` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +164% | veri yok | +140% | 0.71 | -39% | 1.7 | 40% | 2.595 | 28% | +12% | +2.32% | 0.0 |
| B | 2 | ETH/USDT | price_ma | `kind=sma,n=150` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_ote(≤3 bar) | +76% | +106% | +102% | 0.703 | -16% | 2.777 | 43% | 3.703 | 21% | +22% | +2.10% | 0.0 |
| B | 2 | IMX/USDT | donchian_breakout | `entry=100,exit=10` | filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +26% | veri yok | +90% | 0.697 | -27% | 1.946 | 67% | 0.973 | 51% | +16% | +1.79% | 0.0 |
| B | 2 | ETH/USDT | volume_breakout | `n=50,rv=3.0` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +29% | +67% | +117% | 0.686 | -24% | 1.941 | 62% | 1.205 | 45% | +16% | +1.77% | 0.0 |
| B | 2 | XRP/USDT | bb_squeeze | `n=20,q=0.1,look=252` | çıkış=stop_atr=2.0,tp_r=3.0 | +35% | +38% | +203% | 0.663 | -36% | 1.598 | 40% | 2.383 | 30% | +11% | +0.96% | 0.0 |
| B | 2 | ADA/USDT | smc_ote | `k=3,fib_lo=0.5` | filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0 | +20% | +37% | +155% | 0.662 | -28% | 1.316 | 46% | 1.563 | 39% | +7% | +0.37% | 0.0 |
| B | 2 | AVAX/USDT | roc_breakout | `n=252,th=10` | filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10 | +54% | +111% | +103% | 0.653 | -26% | 2.542 | 65% | 1.362 | 42% | +23% | +2.03% | 0.0 |
| B | 2 | MINA/USDT | bb_squeeze | `n=20,q=0.1,look=252` | çıkış=signal_only | +99% | +135% | +125% | 0.621 | -33% | 1.76 | 44% | 2.213 | 31% | +13% | +1.42% | 0.0 |
| B | 2 | DOT/USDT | bb_squeeze | `n=20,q=0.2,look=252` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=ma_cross(≤0 bar) | +10% | +54% | +90% | 0.611 | -22% | 3.202 | 61% | 2.022 | 33% | +28% | +2.71% | 0.0 |
| B | 2 | ETH/USDT | keltner_breakout | `n=20,k=2.5` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +46% | +44% | +103% | 0.576 | -35% | 2.171 | 51% | 2.084 | 32% | +19% | +1.78% | 0.0 |
| B | 2 | FIL/USDT | cci_reversal | `n=40,lo=-100` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_ote(≤5 bar) | +28% | +21% | +36% | 0.55 | -12% | 1.788 | 70% | 0.756 | 57% | +13% | +0.93% | 0.0 |
| B | 2 | XRP/USDT | bb_squeeze | `n=20,q=0.1,look=252` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=roc_breakout(≤5 bar) | +31% | +29% | +98% | 0.491 | -37% | 2.519 | 48% | 2.771 | 26% | +21% | +2.09% | 0.0 |

## Coin coin özet (ajan günlüğü)

- **AAVE/USDT**: 68 aday denendi, 0 kaldı. En iyi aday triple_ma (`set=(10, 50, 200),kind=ema`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -5%, 5y +69%, full +12%; 105 işlem (zararlı: 3y).
- **ADA/USDT**: 70 aday denendi, 1 kaldı. En iyi aday smc_ote (`k=3,fib_lo=0.5`, filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0): OK — tüm adımlar geçti.
- **ALGO/USDT**: 72 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=5,exit_level=50`, filtre=regime_bench200 · çıkış=signal_only): S7 — PSR 0.878.
- **APT/USDT**: 89 aday denendi, 4 kaldı. En iyi aday macd_zero (`cfg=(12, 26, 9)`, filtre=htf_week_sma10 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **ARB/USDT**: 129 aday denendi, 42 kaldı. En iyi aday price_ma (`kind=kama,n=200`, filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **ATOM/USDT**: 68 aday denendi, 0 kaldı. En iyi aday gap_fade (`g=0.02`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +0%, 5y +0%, full +2%; 1 işlem (zararlı: 3y, 5y).
- **AVAX/USDT**: 71 aday denendi, 1 kaldı. En iyi aday roc_breakout (`n=252,th=10`, filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **AXS/USDT**: 71 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=252,th=5`, filtre=low_vol · çıkış=trail_atr=3.0): S4 — komşu ayarların %33'i kârlı.
- **BCH/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=2,lo=10,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +0%, 5y +0%, full +0%; 0 işlem (zararlı: 3y, 5y, full).
- **BNB/USDT**: 70 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=70`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.205, 1x maks. düşüş -43%.
- **BTC/USDT**: 74 aday denendi, 0 kaldı. En iyi aday volume_breakout (`n=50,rv=3.0`, filtre=trend_sma200 · çıkış=stop_atr=2.0,trail_atr=3.0): S6 — yılların %56'i kârlı.
- **CRV/USDT**: 74 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=252,th=0`, filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0): S2 — PF 1.411, 1x maks. düşüş -52%.
- **DOGE/USDT**: 73 aday denendi, 2 kaldı. En iyi aday linreg_slope (`n=100,th=0.0005`, filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **DOT/USDT**: 79 aday denendi, 2 kaldı. En iyi aday smc_ote (`k=8,fib_lo=0.5`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤5 bar)): OK — tüm adımlar geçti.
- **ETC/USDT**: 69 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=252,th=10`, filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0): S2 — PF 1.979, 1x maks. düşüş -55%.
- **ETH/USDT**: 86 aday denendi, 6 kaldı. En iyi aday price_ma (`kind=sma,n=150`, filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **FIL/USDT**: 95 aday denendi, 8 kaldı. En iyi aday wavetrend_reversal (`n1=12,n2=18,lo=-60`, filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **IMX/USDT**: 77 aday denendi, 3 kaldı. En iyi aday price_ma (`kind=sma,n=150`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar)): OK — tüm adımlar geçti.
- **INJ/USDT**: 70 aday denendi, 0 kaldı. En iyi aday funding_extreme (`n=90,th=2.0`, çıkış=stop_atr=2.0,trail_atr=3.0): S3 — 2.0x maliyette getiri -7%.
- **LINK/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=28,lo=10,exit=60`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +0%, 5y +0%, full +0%; 0 işlem (zararlı: 3y, 5y, full).
- **LTC/USDT**: 68 aday denendi, 0 kaldı. En iyi aday bb_squeeze (`n=20,q=0.1,look=126`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -16%, 5y -27%, full +13%; 134 işlem (zararlı: 3y, 5y).
- **MANA/USDT**: 70 aday denendi, 0 kaldı. En iyi aday funding_extreme (`n=90,th=1.5`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.325, 1x maks. düşüş -56%.
- **MINA/USDT**: 80 aday denendi, 1 kaldı. En iyi aday bb_squeeze (`n=20,q=0.1,look=252`, çıkış=signal_only): OK — tüm adımlar geçti.
- **NEAR/USDT**: 68 aday denendi, 0 kaldı. En iyi aday ma_cross (`kind=kama,pair=(50, 200)`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -15%, 5y +82%, full +55%; 41 işlem (zararlı: 3y).
- **OP/USDT**: 93 aday denendi, 3 kaldı. En iyi aday trix_cross (`n=21,signal=9`, filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **PYTH/USDT**: elendi (S0: 2.9 yıl veri var, en az 3.0 yıl gerekli).
- **SAND/USDT**: 78 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=5,exit_level=50`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=macd_divergence(≤0 bar)): S7 — PSR 0.81.
- **SNX/USDT**: 72 aday denendi, 0 kaldı. En iyi aday bb_squeeze (`n=20,q=0.2,look=252`, filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0): S4 — komşu ayarların %0'i kârlı.
- **SOL/USDT**: 68 aday denendi, 0 kaldı. En iyi aday triple_ma (`set=(5, 20, 50),kind=sma`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -20%, 5y +38%, full -52%; 274 işlem (zararlı: 3y, full).
- **SUI/USDT**: 72 aday denendi, 1 kaldı. En iyi aday linreg_slope (`n=100,th=0.0005`, çıkış=stop_atr=2.0,trail_atr=3.0): OK — tüm adımlar geçti.
- **THETA/USDT**: 70 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=252,th=10`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar)): S2 — PF 2.11, 1x maks. düşüş -47%.
- **TRX/USDT**: 70 aday denendi, 0 kaldı. En iyi aday bb_squeeze (`n=20,q=0.1,look=252`, çıkış=stop_atr=2.0,trail_atr=3.0): S3 — 2.0x maliyette getiri -14%.
- **UNI/USDT**: 79 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=5,lo=10,exit=50`, filtre=low_vol · çıkış=stop_atr=2.0,trail_atr=3.0): S5 — 1 bar geç girişte Sharpe'ın %33'i kalıyor.
- **XLM/USDT**: 72 aday denendi, 1 kaldı. En iyi aday ma_cross (`kind=sma,pair=(10, 50)`, filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **XRP/USDT**: 71 aday denendi, 3 kaldı. En iyi aday ma_cross (`kind=sma,pair=(20, 50)`, filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.

## Zayıf yönler (dürüst liste)

- 31684 deneme yapıldı. Bu kadar çok denemede şans eseri iyi görünen strateji çıkar. DSR bunu düzeltir; tier A sadece DSR ≥ eşik olanlardır.
- Seçim ve test aynı geçmiş veride yapıldı. Gerçek test arenadaki ileri (paper) kayıttır.
- Survivorship: liste bugünün coinlerinden oluşur. Borsadan silinen coinler yok, bu sonucu iyimser yapar.
- Funding sabit yıllık oranla, likidasyon işlem bazında yaklaşık modellenir.
- Tek borsa verisi (Bitget, yoksa OKX/KuCoin). Emir defteri ve piyasa etkisi modellenmez.

## Arena

Arena: 100 aktif (eleme geçen), 0 kontrol (yakın aday, switcher kullanmaz), 3 yeni üye, 0 kontrolden aktife. Üst sınır 100.

## Switcher backtest kapısı

Geçti: **False** — kontroller: `{"beats_equal_weight_all_windows": false, "positive_at_cost_stress": true, "max_dd_ok": true}`

Pencereler: `{"3y": {"sharpe": 1.465, "ew_sharpe": 2.099}, "5y": {"sharpe": 1.559, "ew_sharpe": 2.139}, "full": {"sharpe": 0.836, "ew_sharpe": 1.251}}`
