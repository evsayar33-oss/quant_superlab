# Eleme motoru — crypto_alts 1d_long (yön: long)

Veri: 2018-01-01 → 2026-11-01. Coin: 34 uygun (toplam 35). Denenen varyant: 592 × coin = **41783 deneme**.
Her (coin, kural) için tek en iyi nokta değil, **en sağlam bölgenin merkezi** seçildi. Bu bir aday listesidir, karar değildir. Karar sadece doğrulama kapısında verilir.

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bu liste binlerce deneme arasından seçildi; seçim süreçleri backtest'te iyi görünüp ileride çökebilir (2026-10-17 ve 10-19 testleri). Gerçek paraya aday olmadan önce `Time machine test` workflow'unu aynı yön (side) ve zaman dilimiyle çalıştırın. Kural: CLAUDE.md / AGENTS.md.

## Huni

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 68 | 2312 |
| S1 | her dönemde kârlı değil / az işlem | 2043 | 269 |
| S2 | kâr faktörü veya düşüş zayıf | 247 | 22 |
| S3 | yüksek maliyette zarar | 0 | 22 |
| S4 | plato yok (komşu ayarlar zararda) | 3 | 19 |
| S5 | 1 bar gecikmeye dayanıksız | 2 | 17 |
| S6 | yılların çoğunda kârlı değil | 4 | 13 |
| S7 | istatistiksel güven düşük (PSR) | 4 | 9 |

## 2. aşama: filtre × çıkış × kombo (sadece S1'i geçen adaylarda)

269 aday → 21655 ek deneme (DSR'a eklendi). Her aday için en sağlam filtre/çıkış hücresi ve en sağlam kombo seçildi; kombo sadece kuralı tek başına geçerse aday olur. Seçilenler aynı S1–S7 adımlarından geçti.

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 0 | 412 |
| S1 | her dönemde kârlı değil / az işlem | 228 | 184 |
| S2 | kâr faktörü veya düşüş zayıf | 129 | 55 |
| S3 | yüksek maliyette zarar | 0 | 55 |
| S4 | plato yok (komşu ayarlar zararda) | 14 | 41 |
| S5 | 1 bar gecikmeye dayanıksız | 4 | 37 |
| S6 | yılların çoğunda kârlı değil | 10 | 27 |
| S7 | istatistiksel güven düşük (PSR) | 0 | 27 |

## Geçenler (36)

Kazanma oranı tek başına bir şey söylemez. Sistem sadece **kazanma oranı > başabaş oranı** olduğunda kârlıdır. Başabaş = 1 / (1 + ödeme oranı); ödeme oranı = ortalama kazanç / ortalama kayıp (maliyet sonrası). Pay = kazanma oranı − başabaş. Beklenen = işlem başına ortalama net getiri.

| Tier | Aşama | Coin | Kural | Ayar | Varyant | 3y | 5y | Tüm | Sharpe | 1x DD | PF | Kazanma | Ödeme | Başabaş | Pay | Beklenen | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 2 | SUI/USDT | price_ma | `kind=sma,n=20` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +808% | veri yok | +890% | 1.573 | -28% | 4.369 | 33% | 8.738 | 10% | +23% | +8.27% | 0.402 |
| B | 2 | SUI/USDT | elder_impulse | `ema_n=13,macd_cfg=(12, 26, 9)` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +235% | veri yok | +281% | 1.004 | -36% | 2.078 | 33% | 4.286 | 19% | +14% | +4.26% | 0.087 |
| B | 2 | FIL/USDT | turn_of_month | `pre=2,post=2` | filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0 | +130% | +113% | +536% | 1.143 | -28% | 3.431 | 66% | 1.771 | 36% | +30% | +4.53% | 0.056 |
| B | 2 | BTC/USDT | cci_breakout | `n=40,level=100` | filtre=low_vol · çıkış=signal_only | +81% | +105% | +1807% | 1.151 | -32% | 6.061 | 50% | 6.061 | 14% | +36% | +16.04% | 0.052 |
| B | 2 | BTC/USDT | awesome_zero | `fast=5,slow=34` | filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0 | +55% | +64% | +1264% | 1.138 | -36% | 5.551 | 39% | 8.673 | 10% | +29% | +10.88% | 0.045 |
| B | 2 | AAVE/USDT | down_days | `n=4,hold_exit=3` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤5 bar) | +194% | +269% | +566% | 1.02 | -29% | 3.137 | 67% | 1.569 | 39% | +28% | +8.18% | 0.038 |
| B | 2 | BTC/USDT | trix_cross | `n=12,signal=7` | filtre=trend_sma200 · çıkış=stop_atr=2.0,be_r=1.0 | +41% | +103% | +922% | 1.104 | -39% | 3.828 | 49% | 4.01 | 20% | +29% | +7.12% | 0.033 |
| B | 2 | APT/USDT | force_index | `n=2` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +96% | veri yok | +96% | 0.853 | -34% | 2.397 | 74% | 0.863 | 54% | +20% | +2.31% | 0.033 |
| B | 1 | AAVE/USDT | hammer_star | `lookback_low=10` | çıkış=stop_atr=2.0,trail_atr=3.0 | +71% | +137% | +405% | 0.946 | -29% | 6.211 | 80% | 1.553 | 39% | +41% | +5.14% | 0.023 |
| B | 2 | ARB/USDT | down_days | `n=3,hold_exit=1` | çıkış=trail_atr=3.0 | +42% | veri yok | +93% | 0.701 | -40% | 1.586 | 77% | 0.485 | 67% | +9% | +0.94% | 0.023 |
| B | 2 | BTC/USDT | wavetrend_reversal | `n1=9,n2=18,lo=-40` | çıkış=stop_atr=2.0,max_hold=10 | +25% | +55% | +545% | 1.0 | -22% | 3.832 | 73% | 1.423 | 41% | +32% | +4.70% | 0.015 |
| B | 2 | OP/USDT | force_index | `n=2` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_fvg(≤5 bar) | +77% | veri yok | +123% | 0.667 | -31% | 1.718 | 67% | 0.838 | 54% | +13% | +1.75% | 0.011 |
| B | 2 | XRP/USDT | heikin_ashi | `confirm=3` | filtre=low_vol · çıkış=signal_only | +154% | +287% | +1751% | 0.988 | -33% | 2.84 | 40% | 4.347 | 19% | +21% | +3.61% | 0.009 |
| B | 2 | AAVE/USDT | bollinger_reversion | `n=30,k=1.5` | filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10 | +81% | +140% | +240% | 0.698 | -39% | 1.922 | 65% | 1.018 | 50% | +16% | +3.39% | 0.007 |
| B | 2 | TRX/USDT | turn_of_month | `pre=3,post=3` | çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +56% | +144% | +924% | 1.014 | -34% | 3.118 | 62% | 1.881 | 35% | +28% | +2.82% | 0.006 |
| B | 2 | BTC/USDT | cci_breakout | `n=40,level=100` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤5 bar) | +49% | +38% | +564% | 0.875 | -29% | 3.02 | 46% | 3.473 | 22% | +24% | +5.90% | 0.006 |
| B | 2 | UNI/USDT | rsi_reversal | `n=3,lo=10,exit=60` | filtre=adx20 · çıkış=stop_atr=2.0,trail_atr=3.0 | +79% | +136% | +242% | 0.763 | -36% | 2.823 | 78% | 0.82 | 55% | +22% | +3.60% | 0.006 |
| B | 2 | BNB/USDT | ma_cross | `kind=dema,pair=(5, 20)` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +69% | +86% | +644% | 0.889 | -31% | 2.883 | 46% | 3.363 | 23% | +23% | +5.07% | 0.004 |
| B | 2 | BNB/USDT | psar_flip | `cfg=(0.03, 0.3)` | filtre=regime_bench200 · çıkış=stop_atr=2.0,trail_atr=3.0 | +50% | +48% | +1723% | 0.915 | -37% | 2.968 | 47% | 3.313 | 23% | +24% | +5.48% | 0.003 |
| B | 1 | BTC/USDT | atr_breakout | `n=10,k=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +33% | +77% | +236% | 0.733 | -28% | 3.531 | 55% | 2.908 | 26% | +29% | +4.84% | 0.003 |
| B | 2 | LTC/USDT | hurst_switch | `n=100,fast=20,rsi_n=2` | filtre=htf_week_sma10 · çıkış=signal_only | +81% | +119% | +318% | 0.773 | -24% | 3.406 | 75% | 1.135 | 47% | +28% | +3.75% | 0.002 |
| B | 2 | BTC/USDT | tsi_cross | `cfg=(25, 13, 7)` | filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0 | +29% | +41% | +312% | 0.749 | -37% | 2.145 | 39% | 3.329 | 23% | +16% | +2.75% | 0.002 |
| B | 2 | TRX/USDT | smc_ote | `k=3,fib_lo=0.5` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,tp_r=3.0 | +75% | +133% | +455% | 0.829 | -33% | 2.664 | 59% | 1.85 | 35% | +24% | +3.64% | 0.001 |
| B | 2 | BTC/USDT | smc_order_block | `k=5,max_age=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤3 bar) | +34% | +19% | +199% | 0.707 | -29% | 3.015 | 30% | 6.958 | 13% | +18% | +3.48% | 0.001 |
| B | 1 | BNB/USDT | cci_reversal | `n=20,lo=-150` | çıkış=stop_atr=2.0,trail_atr=3.0 | +37% | +76% | +326% | 0.674 | -32% | 2.001 | 72% | 0.792 | 56% | +16% | +2.98% | 0.001 |
| B | 2 | BNB/USDT | mfi_reversal | `n=10,lo=30` | filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +34% | +85% | +264% | 0.662 | -31% | 2.399 | 76% | 0.738 | 57% | +19% | +3.21% | 0.001 |
| B | 1 | BTC/USDT | cci_breakout | `n=40,level=100` | çıkış=stop_atr=2.0,trail_atr=3.0 | +19% | +49% | +326% | 0.653 | -37% | 1.985 | 41% | 2.895 | 26% | +15% | +3.95% | 0.001 |
| B | 2 | TRX/USDT | hurst_switch | `n=100,fast=20,rsi_n=2` | filtre=regime_bench200 · çıkış=trail_atr=3.0 | +76% | +75% | +150% | 0.632 | -35% | 2.168 | 65% | 1.172 | 46% | +19% | +2.02% | 0.001 |
| B | 1 | ETH/USDT | roc_breakout | `n=63,th=5` | çıkış=stop_atr=2.0,trail_atr=3.0 | +68% | +21% | +254% | 0.618 | -40% | 2.334 | 46% | 2.801 | 26% | +19% | +4.20% | 0.001 |
| B | 1 | BTC/USDT | awesome_zero | `fast=5,slow=34` | çıkış=stop_atr=2.0,trail_atr=3.0 | +13% | +35% | +252% | 0.609 | -38% | 2.043 | 40% | 3.027 | 25% | +16% | +3.02% | 0.001 |
| B | 2 | TRX/USDT | ultimate_reversal | `a=5,lo=35` | filtre=adx20 · çıkış=signal_only | +20% | +20% | +223% | 0.596 | -39% | 2.462 | 71% | 0.985 | 50% | +21% | +4.16% | 0.001 |
| B | 1 | TRX/USDT | turn_of_month | `pre=3,post=3` | çıkış=stop_atr=2.0,trail_atr=3.0 | +103% | +221% | +1256% | 0.861 | -37% | 3.516 | 60% | 2.306 | 30% | +30% | +3.44% | 0.0 |
| B | 2 | ADA/USDT | turn_of_month | `pre=3,post=2` | filtre=adx20 · çıkış=signal_only | +63% | +108% | +803% | 0.824 | -32% | 2.762 | 55% | 2.236 | 31% | +24% | +3.76% | 0.0 |
| B | 1 | TRX/USDT | smc_ote | `k=3,fib_lo=0.5` | çıkış=stop_atr=2.0,trail_atr=3.0 | +157% | +182% | +639% | 0.708 | -35% | 2.422 | 55% | 2.018 | 33% | +21% | +3.27% | 0.0 |
| B | 2 | LTC/USDT | hurst_switch | `n=100,fast=20,rsi_n=2` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤5 bar) | +79% | +62% | +176% | 0.576 | -29% | 2.034 | 67% | 1.017 | 50% | +17% | +2.41% | 0.0 |
| B | 1 | BTC/USDT | wavetrend_reversal | `n1=9,n2=18,lo=-40` | çıkış=stop_atr=2.0,trail_atr=3.0 | +19% | +36% | +154% | 0.508 | -35% | 2.077 | 51% | 1.982 | 34% | +18% | +3.13% | 0.0 |

## Coin coin özet (ajan günlüğü)

- **AAVE/USDT**: 88 aday denendi, 3 kaldı. En iyi aday down_days (`n=4,hold_exit=3`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤5 bar)): OK — tüm adımlar geçti.
- **ADA/USDT**: 77 aday denendi, 1 kaldı. En iyi aday turn_of_month (`pre=3,post=2`, filtre=adx20 · çıkış=signal_only): OK — tüm adımlar geçti.
- **ALGO/USDT**: 85 aday denendi, 0 kaldı. En iyi aday down_days (`n=5,hold_exit=1`, çıkış=stop_atr=2.0,trail_atr=3.0): S7 — PSR 0.833.
- **APT/USDT**: 73 aday denendi, 1 kaldı. En iyi aday force_index (`n=2`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar)): OK — tüm adımlar geçti.
- **ARB/USDT**: 82 aday denendi, 1 kaldı. En iyi aday down_days (`n=3,hold_exit=1`, çıkış=trail_atr=3.0): OK — tüm adımlar geçti.
- **ATOM/USDT**: 71 aday denendi, 0 kaldı. En iyi aday hurst_switch (`n=200,fast=20,rsi_n=2`, filtre=adx20 · çıkış=signal_only): S2 — PF 2.039, 1x maks. düşüş -46%.
- **AVAX/USDT**: 75 aday denendi, 0 kaldı. En iyi aday cci_breakout (`n=14,level=100`, çıkış=signal_only): S2 — PF 4.99, 1x maks. düşüş -52%.
- **AXS/USDT**: 76 aday denendi, 0 kaldı. En iyi aday mfi_reversal (`n=10,lo=20`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 2.622, 1x maks. düşüş -55%.
- **BCH/USDT**: 89 aday denendi, 0 kaldı. En iyi aday price_ma (`kind=kama,n=100`, filtre=regime_bench200 · çıkış=stop_atr=2.0,max_hold=10): S6 — yılların %43'i kârlı.
- **BNB/USDT**: 92 aday denendi, 4 kaldı. En iyi aday ma_cross (`kind=dema,pair=(5, 20)`, filtre=htf_week_sma10 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **BTC/USDT**: 107 aday denendi, 11 kaldı. En iyi aday cci_breakout (`n=40,level=100`, filtre=low_vol · çıkış=signal_only): OK — tüm adımlar geçti.
- **CRV/USDT**: 83 aday denendi, 0 kaldı. En iyi aday force_index (`n=2`, filtre=regime_bench200 · çıkış=signal_only): S4 — komşu ayarların %0'i kârlı.
- **DOGE/USDT**: 72 aday denendi, 0 kaldı. En iyi aday smc_ote (`k=3,fib_lo=0.5`, filtre=htf_week_sma10 · çıkış=signal_only): S2 — PF 2.125, 1x maks. düşüş -56%.
- **DOT/USDT**: 68 aday denendi, 0 kaldı. En iyi aday turn_of_month (`pre=2,post=3`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -49%, 5y -48%, full +202%; 73 işlem (zararlı: 3y, 5y).
- **ETC/USDT**: 75 aday denendi, 0 kaldı. En iyi aday ma_cross (`kind=sma,pair=(10, 50)`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 2.885, 1x maks. düşüş -46%.
- **ETH/USDT**: 90 aday denendi, 1 kaldı. En iyi aday roc_breakout (`n=63,th=5`, çıkış=stop_atr=2.0,trail_atr=3.0): OK — tüm adımlar geçti.
- **FIL/USDT**: 74 aday denendi, 1 kaldı. En iyi aday turn_of_month (`pre=2,post=2`, filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **IMX/USDT**: 80 aday denendi, 0 kaldı. En iyi aday price_ma (`kind=kama,n=100`, filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10): S4 — komşu ayarların %33'i kârlı.
- **INJ/USDT**: 73 aday denendi, 0 kaldı. En iyi aday down_days (`n=3,hold_exit=3`, filtre=adx20 · çıkış=signal_only): S2 — PF 2.119, 1x maks. düşüş -86%.
- **LINK/USDT**: 74 aday denendi, 0 kaldı. En iyi aday hammer_star (`lookback_low=10`, çıkış=stop_atr=2.0,trail_atr=3.0): S6 — yılların %50'i kârlı.
- **LTC/USDT**: 79 aday denendi, 2 kaldı. En iyi aday hurst_switch (`n=100,fast=20,rsi_n=2`, filtre=htf_week_sma10 · çıkış=signal_only): OK — tüm adımlar geçti.
- **MANA/USDT**: 71 aday denendi, 0 kaldı. En iyi aday rsi_midline (`n=21,level=60`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 4.114, 1x maks. düşüş -44%.
- **MINA/USDT**: 69 aday denendi, 0 kaldı. En iyi aday bollinger_breakout (`n=20,k=1.5`, çıkış=stop_atr=2.0,be_r=1.0): S2 — PF 2.091, 1x maks. düşüş -75%.
- **NEAR/USDT**: 84 aday denendi, 0 kaldı. En iyi aday rsi_midline (`n=9,level=50`, çıkış=signal_only): S2 — PF 2.722, 1x maks. düşüş -69%.
- **OP/USDT**: 75 aday denendi, 1 kaldı. En iyi aday force_index (`n=2`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_fvg(≤5 bar)): OK — tüm adımlar geçti.
- **PYTH/USDT**: elendi (S0: 2.9 yıl veri var, en az 3.0 yıl gerekli).
- **SAND/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_midline (`n=9,level=60`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -34%, 5y -36%, full +544%; 73 işlem (zararlı: 3y, 5y).
- **SNX/USDT**: 68 aday denendi, 0 kaldı. En iyi aday halloween (`start=11,end=4`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +128%, 5y +95%, full +151%; 6 işlem.
- **SOL/USDT**: 89 aday denendi, 0 kaldı. En iyi aday donchian_breakout (`entry=20,exit=20`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_bos(≤0 bar)): S6 — yılların %57'i kârlı.
- **SUI/USDT**: 91 aday denendi, 2 kaldı. En iyi aday price_ma (`kind=sma,n=20`, filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **THETA/USDT**: 73 aday denendi, 0 kaldı. En iyi aday down_days (`n=5,hold_exit=1`, çıkış=stop_atr=2.0,trail_atr=3.0): S5 — 1 bar geç girişte Sharpe'ın %0'i kalıyor.
- **TRX/USDT**: 107 aday denendi, 6 kaldı. En iyi aday turn_of_month (`pre=3,post=3`, çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **UNI/USDT**: 80 aday denendi, 1 kaldı. En iyi aday rsi_reversal (`n=3,lo=10,exit=60`, filtre=adx20 · çıkış=stop_atr=2.0,trail_atr=3.0): OK — tüm adımlar geçti.
- **XLM/USDT**: 83 aday denendi, 0 kaldı. En iyi aday nr7_breakout (`n=4`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=down_days(≤5 bar)): S4 — komşu ayarların %0'i kârlı.
- **XRP/USDT**: 83 aday denendi, 1 kaldı. En iyi aday heikin_ashi (`confirm=3`, filtre=low_vol · çıkış=signal_only): OK — tüm adımlar geçti.

## Zayıf yönler (dürüst liste)

- 41783 deneme yapıldı. Bu kadar çok denemede şans eseri iyi görünen strateji çıkar. DSR bunu düzeltir; tier A sadece DSR ≥ eşik olanlardır.
- Seçim ve test aynı geçmiş veride yapıldı. Gerçek test arenadaki ileri (paper) kayıttır.
- Survivorship: liste bugünün coinlerinden oluşur. Borsadan silinen coinler yok, bu sonucu iyimser yapar.
- Funding sabit yıllık oranla, likidasyon işlem bazında yaklaşık modellenir.
- Tek borsa verisi (Bitget, yoksa OKX/KuCoin). Emir defteri ve piyasa etkisi modellenmez.

## Arena

Arena: 63 aktif (eleme geçen), 37 kontrol (yakın aday, switcher kullanmaz), 14 yeni üye, 2 kontrolden aktife. Üst sınır 100.

## Switcher backtest kapısı

Geçti: **False** — kontroller: `{"beats_equal_weight_all_windows": false, "positive_at_cost_stress": true, "max_dd_ok": true}`

Pencereler: `{"3y": {"sharpe": 0.881, "ew_sharpe": 2.443}, "5y": {"sharpe": 0.404, "ew_sharpe": 1.926}, "full": {"sharpe": 0.926, "ew_sharpe": 2.0}}`
