# Eleme motoru — crypto_alts 1d (yön: both)

Veri: 2018-01-01 → 2026-11-01. Coin: 34 uygun (toplam 35). Denenen varyant: 592 × coin = **33412 deneme**.
Her (coin, kural) için tek en iyi nokta değil, **en sağlam bölgenin merkezi** seçildi. Bu bir aday listesidir, karar değildir. Karar sadece doğrulama kapısında verilir.

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bu liste binlerce deneme arasından seçildi; seçim süreçleri backtest'te iyi görünüp ileride çökebilir (2026-10-17 ve 10-19 testleri). Gerçek paraya aday olmadan önce `Time machine test` workflow'unu aynı yön (side) ve zaman dilimiyle çalıştırın. Kural: CLAUDE.md / AGENTS.md.

## Huni

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 68 | 2312 |
| S1 | her dönemde kârlı değil / az işlem | 2147 | 165 |
| S2 | kâr faktörü veya düşüş zayıf | 157 | 8 |
| S3 | yüksek maliyette zarar | 1 | 7 |
| S4 | plato yok (komşu ayarlar zararda) | 2 | 5 |
| S5 | 1 bar gecikmeye dayanıksız | 1 | 4 |
| S6 | yılların çoğunda kârlı değil | 2 | 2 |
| S7 | istatistiksel güven düşük (PSR) | 0 | 2 |

## 2. aşama: filtre × çıkış × kombo (sadece S1'i geçen adaylarda)

165 aday → 13284 ek deneme (DSR'a eklendi). Her aday için en sağlam filtre/çıkış hücresi ve en sağlam kombo seçildi; kombo sadece kuralı tek başına geçerse aday olur. Seçilenler aynı S1–S7 adımlarından geçti.

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 0 | 262 |
| S1 | her dönemde kârlı değil / az işlem | 123 | 139 |
| S2 | kâr faktörü veya düşüş zayıf | 108 | 31 |
| S3 | yüksek maliyette zarar | 0 | 31 |
| S4 | plato yok (komşu ayarlar zararda) | 9 | 22 |
| S5 | 1 bar gecikmeye dayanıksız | 3 | 19 |
| S6 | yılların çoğunda kârlı değil | 0 | 19 |
| S7 | istatistiksel güven düşük (PSR) | 0 | 19 |

## Geçenler (21)

Kazanma oranı tek başına bir şey söylemez. Sistem sadece **kazanma oranı > başabaş oranı** olduğunda kârlıdır. Başabaş = 1 / (1 + ödeme oranı); ödeme oranı = ortalama kazanç / ortalama kayıp (maliyet sonrası). Pay = kazanma oranı − başabaş. Beklenen = işlem başına ortalama net getiri.

| Tier | Aşama | Coin | Kural | Ayar | Varyant | 3y | 5y | Tüm | Sharpe | 1x DD | PF | Kazanma | Ödeme | Başabaş | Pay | Beklenen | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 2 | MINA/USDT | rsi_midline | `n=28,level=50` | filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +152% | +1114% | +1114% | 1.415 | -33% | 3.79 | 50% | 3.79 | 21% | +29% | +5.24% | 0.151 |
| B | 2 | AVAX/USDT | price_ma | `kind=sma,n=100` | filtre=regime_bench200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +84% | +240% | +1686% | 1.332 | -31% | 6.523 | 47% | 7.338 | 12% | +35% | +10.82% | 0.098 |
| B | 2 | ARB/USDT | engulfing | `trend_n=200` | filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +411% | veri yok | +365% | 1.088 | -36% | 2.007 | 45% | 2.466 | 29% | +16% | +2.62% | 0.07 |
| B | 2 | ARB/USDT | rsi_reversal | `n=2,lo=10,exit=50` | filtre=regime_bench200 · çıkış=signal_only | +109% | veri yok | +116% | 0.884 | -30% | 2.064 | 67% | 1.032 | 49% | +18% | +1.34% | 0.031 |
| B | 2 | IMX/USDT | smc_ote | `k=3,fib_lo=0.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_fvg(≤3 bar) | +228% | veri yok | +322% | 1.059 | -40% | 2.889 | 54% | 2.433 | 29% | +25% | +4.97% | 0.027 |
| B | 2 | FIL/USDT | turn_of_month | `pre=2,post=2` | filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0 | +130% | +113% | +536% | 1.143 | -28% | 3.431 | 66% | 1.771 | 36% | +30% | +4.53% | 0.024 |
| B | 2 | APT/USDT | force_index | `n=2` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +96% | veri yok | +96% | 0.853 | -34% | 2.397 | 74% | 0.863 | 54% | +20% | +2.31% | 0.016 |
| B | 2 | AAVE/USDT | hammer_star | `lookback_low=10` | filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +49% | +82% | +401% | 0.927 | -33% | 3.474 | 75% | 1.158 | 46% | +29% | +4.20% | 0.009 |
| B | 2 | ETH/USDT | ichimoku_cloud | `cfg=(20, 60, 120)` | filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10 | +148% | +323% | +596% | 1.052 | -30% | 4.755 | 64% | 2.717 | 27% | +37% | +6.92% | 0.008 |
| B | 2 | OP/USDT | force_index | `n=2` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_fvg(≤5 bar) | +77% | veri yok | +123% | 0.667 | -31% | 1.718 | 67% | 0.838 | 54% | +13% | +1.75% | 0.005 |
| B | 2 | TRX/USDT | turn_of_month | `pre=3,post=3` | çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +56% | +144% | +924% | 1.014 | -34% | 3.118 | 62% | 1.881 | 35% | +28% | +2.82% | 0.001 |
| B | 2 | BTC/USDT | ma_cross | `kind=kama,pair=(10, 50)` | filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10 | +50% | +43% | +225% | 0.788 | -26% | 2.884 | 65% | 1.562 | 39% | +26% | +4.07% | 0.001 |
| B | 2 | BTC/USDT | obv_trend | `n=50,price_n=50` | filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0 | +33% | +136% | +811% | 0.772 | -39% | 2.949 | 28% | 7.451 | 12% | +16% | +3.23% | 0.001 |
| B | 2 | BTC/USDT | atr_breakout | `n=10,k=2.0` | filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10 | +47% | +143% | +411% | 0.881 | -16% | 5.879 | 70% | 2.487 | 29% | +42% | +5.36% | 0.0 |
| B | 1 | TRX/USDT | turn_of_month | `pre=3,post=3` | çıkış=stop_atr=2.0,trail_atr=3.0 | +103% | +221% | +1256% | 0.861 | -37% | 3.516 | 60% | 2.306 | 30% | +30% | +3.44% | 0.0 |
| B | 2 | ADA/USDT | turn_of_month | `pre=3,post=2` | filtre=adx20 · çıkış=signal_only | +63% | +108% | +803% | 0.824 | -32% | 2.762 | 55% | 2.236 | 31% | +24% | +3.76% | 0.0 |
| B | 2 | TRX/USDT | smc_ote | `k=3,fib_lo=0.5` | filtre=regime_bench200 · çıkış=signal_only | +94% | +104% | +927% | 0.789 | -34% | 2.877 | 52% | 2.621 | 28% | +25% | +3.80% | 0.0 |
| B | 2 | LTC/USDT | hurst_switch | `n=100,fast=20,rsi_n=2` | filtre=htf_week_sma10 · çıkış=signal_only | +81% | +119% | +318% | 0.773 | -24% | 3.406 | 75% | 1.135 | 47% | +28% | +3.75% | 0.0 |
| B | 2 | TRX/USDT | hurst_switch | `n=100,fast=20,rsi_n=2` | filtre=regime_bench200 · çıkış=trail_atr=3.0 | +76% | +75% | +150% | 0.632 | -35% | 2.168 | 65% | 1.172 | 46% | +19% | +2.02% | 0.0 |
| B | 2 | ETC/USDT | smc_ote | `k=8,fib_lo=0.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤3 bar) | +19% | +78% | +167% | 0.624 | -35% | 2.025 | 42% | 2.784 | 26% | +16% | +3.22% | 0.0 |
| B | 1 | BTC/USDT | atr_breakout | `n=10,k=2.0` | çıkış=stop_atr=2.0,trail_atr=3.0 | +1% | +42% | +227% | 0.572 | -32% | 2.595 | 49% | 2.691 | 27% | +22% | +3.46% | 0.0 |

## Coin coin özet (ajan günlüğü)

- **AAVE/USDT**: 71 aday denendi, 1 kaldı. En iyi aday hammer_star (`lookback_low=10`, filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **ADA/USDT**: 79 aday denendi, 1 kaldı. En iyi aday turn_of_month (`pre=3,post=2`, filtre=adx20 · çıkış=signal_only): OK — tüm adımlar geçti.
- **ALGO/USDT**: 73 aday denendi, 0 kaldı. En iyi aday stoch_reversal (`k=5,d=5,smooth=1,lo=10`, filtre=htf_week_sma10 · çıkış=trail_atr=3.0): S4 — komşu ayarların %0'i kârlı.
- **APT/USDT**: 79 aday denendi, 1 kaldı. En iyi aday force_index (`n=2`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar)): OK — tüm adımlar geçti.
- **ARB/USDT**: 94 aday denendi, 2 kaldı. En iyi aday engulfing (`trend_n=200`, filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **ATOM/USDT**: 69 aday denendi, 0 kaldı. En iyi aday hurst_switch (`n=200,fast=20,rsi_n=2`, filtre=adx20 · çıkış=signal_only): S2 — PF 2.039, 1x maks. düşüş -46%.
- **AVAX/USDT**: 81 aday denendi, 1 kaldı. En iyi aday price_ma (`kind=sma,n=100`, filtre=regime_bench200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **AXS/USDT**: 68 aday denendi, 0 kaldı. En iyi aday elder_impulse (`ema_n=13,macd_cfg=(12, 26, 9)`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -78%, 5y -90%, full -14%; 284 işlem (zararlı: 3y, 5y, full).
- **BCH/USDT**: 76 aday denendi, 0 kaldı. En iyi aday hurst_switch (`n=100,fast=20,rsi_n=2`, çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 1.952, 1x maks. düşüş -57%.
- **BNB/USDT**: 70 aday denendi, 0 kaldı. En iyi aday macd_zero (`cfg=(12, 26, 9)`, filtre=low_vol · çıkış=signal_only): S2 — PF 8.76, 1x maks. düşüş -51%.
- **BTC/USDT**: 83 aday denendi, 4 kaldı. En iyi aday ma_cross (`kind=kama,pair=(10, 50)`, filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **CRV/USDT**: 73 aday denendi, 0 kaldı. En iyi aday force_index (`n=2`, filtre=regime_bench200 · çıkış=signal_only): S4 — komşu ayarların %0'i kârlı.
- **DOGE/USDT**: 74 aday denendi, 0 kaldı. En iyi aday rsi_divergence (`n=14,k=3,exit_level=50`, filtre=adx20 · çıkış=trail_atr=3.0): S5 — 1 bar geç girişte Sharpe'ın %38'i kalıyor.
- **DOT/USDT**: 76 aday denendi, 0 kaldı. En iyi aday smc_fvg (`max_age=40,min_gap_atr=0.5`, filtre=htf_week_sma10 · çıkış=stop_atr=2.0,max_hold=10): S2 — PF 1.973, 1x maks. düşüş -64%.
- **ETC/USDT**: 74 aday denendi, 1 kaldı. En iyi aday smc_ote (`k=8,fib_lo=0.5`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤3 bar)): OK — tüm adımlar geçti.
- **ETH/USDT**: 91 aday denendi, 1 kaldı. En iyi aday ichimoku_cloud (`cfg=(20, 60, 120)`, filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **FIL/USDT**: 72 aday denendi, 1 kaldı. En iyi aday turn_of_month (`pre=2,post=2`, filtre=adx20 · çıkış=stop_atr=2.0,tp_r=3.0): OK — tüm adımlar geçti.
- **IMX/USDT**: 81 aday denendi, 1 kaldı. En iyi aday smc_ote (`k=3,fib_lo=0.5`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_fvg(≤3 bar)): OK — tüm adımlar geçti.
- **INJ/USDT**: 69 aday denendi, 0 kaldı. En iyi aday hammer_star (`lookback_low=10`, filtre=adx20 · çıkış=stop_atr=2.0,trail_atr=3.0): S4 — komşu ayarların %0'i kârlı.
- **LINK/USDT**: 71 aday denendi, 0 kaldı. En iyi aday smc_fvg (`max_age=10,min_gap_atr=0.0`, çıkış=signal_only): S2 — PF 1.765, 1x maks. düşüş -87%.
- **LTC/USDT**: 70 aday denendi, 1 kaldı. En iyi aday hurst_switch (`n=100,fast=20,rsi_n=2`, filtre=htf_week_sma10 · çıkış=signal_only): OK — tüm adımlar geçti.
- **MANA/USDT**: 69 aday denendi, 0 kaldı. En iyi aday awesome_zero (`fast=5,slow=34`, filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 2.107, 1x maks. düşüş -63%.
- **MINA/USDT**: 87 aday denendi, 1 kaldı. En iyi aday rsi_midline (`n=28,level=50`, filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **NEAR/USDT**: 82 aday denendi, 0 kaldı. En iyi aday rsi_midline (`n=9,level=50`, filtre=low_vol · çıkış=stop_atr=2.0,be_r=1.0): S2 — PF 3.45, 1x maks. düşüş -61%.
- **OP/USDT**: 79 aday denendi, 1 kaldı. En iyi aday force_index (`n=2`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_fvg(≤5 bar)): OK — tüm adımlar geçti.
- **PYTH/USDT**: elendi (S0: 2.9 yıl veri var, en az 3.0 yıl gerekli).
- **SAND/USDT**: 69 aday denendi, 0 kaldı. En iyi aday macd_divergence (`k=3,fast=12,slow=26`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.951, 1x maks. düşüş -87%.
- **SNX/USDT**: 69 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=126,th=5`, filtre=adx20 · çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 2.869, 1x maks. düşüş -79%.
- **SOL/USDT**: 74 aday denendi, 0 kaldı. En iyi aday atr_breakout (`n=10,k=1.0`, filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0): S2 — PF 3.403, 1x maks. düşüş -41%.
- **SUI/USDT**: 90 aday denendi, 0 kaldı. En iyi aday price_ma (`kind=sma,n=20`, filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10): S5 — 1 bar geç girişte Sharpe'ın %20'i kalıyor.
- **THETA/USDT**: 69 aday denendi, 0 kaldı. En iyi aday ichimoku_cloud (`cfg=(20, 60, 120)`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.755, 1x maks. düşüş -81%.
- **TRX/USDT**: 73 aday denendi, 4 kaldı. En iyi aday turn_of_month (`pre=3,post=3`, çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **UNI/USDT**: 74 aday denendi, 0 kaldı. En iyi aday down_days (`n=3,hold_exit=1`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤3 bar)): S4 — komşu ayarların %0'i kârlı.
- **XLM/USDT**: 74 aday denendi, 0 kaldı. En iyi aday wavetrend_reversal (`n1=10,n2=26,lo=-40`, filtre=low_vol · çıkış=stop_atr=2.0,max_hold=10): S2 — PF 2.519, 1x maks. düşüş -54%.
- **XRP/USDT**: 71 aday denendi, 0 kaldı. En iyi aday coppock_turn (`scale=5`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 3.53, 1x maks. düşüş -47%.

## Zayıf yönler (dürüst liste)

- 33412 deneme yapıldı. Bu kadar çok denemede şans eseri iyi görünen strateji çıkar. DSR bunu düzeltir; tier A sadece DSR ≥ eşik olanlardır.
- Seçim ve test aynı geçmiş veride yapıldı. Gerçek test arenadaki ileri (paper) kayıttır.
- Survivorship: liste bugünün coinlerinden oluşur. Borsadan silinen coinler yok, bu sonucu iyimser yapar.
- Funding sabit yıllık oranla, likidasyon işlem bazında yaklaşık modellenir.
- Tek borsa verisi (Bitget, yoksa OKX/KuCoin). Emir defteri ve piyasa etkisi modellenmez.

## Arena

Arena: 39 aktif (eleme geçen), 61 kontrol (yakın aday, switcher kullanmaz), 7 yeni üye, 0 kontrolden aktife. Üst sınır 100.

## Switcher backtest kapısı

Geçti: **False** — kontroller: `{"beats_equal_weight_all_windows": false, "positive_at_cost_stress": true, "max_dd_ok": true}`

Pencereler: `{"3y": {"sharpe": 0.632, "ew_sharpe": 3.315}, "5y": {"sharpe": 0.969, "ew_sharpe": 2.829}, "full": {"sharpe": 1.116, "ew_sharpe": 2.318}}`
