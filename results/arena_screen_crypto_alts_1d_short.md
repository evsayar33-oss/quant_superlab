# Eleme motoru — crypto_alts 1d_short (yön: short)

Veri: 2018-01-01 → 2026-11-01. Coin: 34 uygun (toplam 35). Denenen varyant: 592 × coin = **29909 deneme**.
Her (coin, kural) için tek en iyi nokta değil, **en sağlam bölgenin merkezi** seçildi. Bu bir aday listesidir, karar değildir. Karar sadece doğrulama kapısında verilir.

> ⚠️ **Zaman makinesi kontrolü önerilir.** Bu liste binlerce deneme arasından seçildi; seçim süreçleri backtest'te iyi görünüp ileride çökebilir (2026-10-17 ve 10-19 testleri). Gerçek paraya aday olmadan önce `Time machine test` workflow'unu aynı yön (side) ve zaman dilimiyle çalıştırın. Kural: CLAUDE.md / AGENTS.md.

## Huni

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 68 | 2312 |
| S1 | her dönemde kârlı değil / az işlem | 2190 | 122 |
| S2 | kâr faktörü veya düşüş zayıf | 119 | 3 |
| S3 | yüksek maliyette zarar | 1 | 2 |
| S4 | plato yok (komşu ayarlar zararda) | 0 | 2 |
| S5 | 1 bar gecikmeye dayanıksız | 1 | 1 |
| S6 | yılların çoğunda kârlı değil | 1 | 0 |
| S7 | istatistiksel güven düşük (PSR) | 0 | 0 |

## 2. aşama: filtre × çıkış × kombo (sadece S1'i geçen adaylarda)

122 aday → 9781 ek deneme (DSR'a eklendi). Her aday için en sağlam filtre/çıkış hücresi ve en sağlam kombo seçildi; kombo sadece kuralı tek başına geçerse aday olur. Seçilenler aynı S1–S7 adımlarından geçti.

| Adım | Ne kontrol edilir | Elenen | Kalan |
|---|---|---|---|
| S0 | veri yetersiz | 0 | 223 |
| S1 | her dönemde kârlı değil / az işlem | 140 | 83 |
| S2 | kâr faktörü veya düşüş zayıf | 55 | 28 |
| S3 | yüksek maliyette zarar | 1 | 27 |
| S4 | plato yok (komşu ayarlar zararda) | 4 | 23 |
| S5 | 1 bar gecikmeye dayanıksız | 5 | 18 |
| S6 | yılların çoğunda kârlı değil | 2 | 16 |
| S7 | istatistiksel güven düşük (PSR) | 2 | 14 |

## Geçenler (14)

Kazanma oranı tek başına bir şey söylemez. Sistem sadece **kazanma oranı > başabaş oranı** olduğunda kârlıdır. Başabaş = 1 / (1 + ödeme oranı); ödeme oranı = ortalama kazanç / ortalama kayıp (maliyet sonrası). Pay = kazanma oranı − başabaş. Beklenen = işlem başına ortalama net getiri.

| Tier | Aşama | Coin | Kural | Ayar | Varyant | 3y | 5y | Tüm | Sharpe | 1x DD | PF | Kazanma | Ödeme | Başabaş | Pay | Beklenen | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 2 | APT/USDT | cci_reversal | `n=14,lo=-100` | filtre=low_vol · çıkış=trail_atr=3.0 | +224% | veri yok | +289% | 1.268 | -22% | 3.66 | 84% | 0.708 | 58% | +25% | +4.24% | 0.127 |
| B | 2 | IMX/USDT | triple_ma | `set=(5, 20, 50),kind=sma` | filtre=htf_week_sma10 · çıkış=stop_atr=2.0,max_hold=10 | +204% | veri yok | +461% | 1.039 | -30% | 4.993 | 66% | 2.615 | 28% | +38% | +7.25% | 0.057 |
| B | 2 | APT/USDT | smc_order_block | `k=3,max_age=50` | filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +123% | veri yok | +209% | 0.93 | -37% | 1.957 | 39% | 3.098 | 24% | +14% | +3.70% | 0.051 |
| B | 2 | MINA/USDT | macd_cross | `cfg=(12, 26, 9),zero_filter=False` | filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +146% | +487% | +487% | 1.033 | -28% | 2.586 | 60% | 1.691 | 37% | +23% | +5.05% | 0.044 |
| B | 2 | MINA/USDT | rsi_midline | `n=21,level=50` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=vwap_cross(≤3 bar) | +332% | +967% | +914% | 1.05 | -40% | 2.666 | 33% | 5.332 | 16% | +18% | +6.14% | 0.043 |
| B | 2 | DOT/USDT | smc_liquidity_sweep | `k=3` | filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +153% | +283% | +352% | 1.0 | -38% | 2.232 | 60% | 1.514 | 40% | +20% | +3.68% | 0.028 |
| B | 2 | MINA/USDT | atr_breakout | `n=20,k=1.0` | filtre=low_vol · çıkış=stop_atr=2.0,tp_r=3.0 | +37% | +294% | +269% | 0.829 | -31% | 2.915 | 53% | 2.551 | 28% | +25% | +4.39% | 0.011 |
| B | 2 | MINA/USDT | smc_ote | `k=3,fib_lo=0.618` | filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10 | +131% | +122% | +122% | 0.719 | -26% | 1.838 | 58% | 1.313 | 43% | +15% | +2.67% | 0.009 |
| B | 2 | DOT/USDT | smc_ote | `k=3,fib_lo=0.5` | filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0 | +45% | +116% | +206% | 0.787 | -28% | 2.289 | 60% | 1.553 | 39% | +20% | +3.00% | 0.007 |
| B | 2 | DOT/USDT | rsi_reversal | `n=5,lo=35,exit=50` | filtre=htf_week_sma10 · çıkış=trail_atr=3.0 | +41% | +68% | +111% | 0.754 | -21% | 2.372 | 81% | 0.552 | 64% | +17% | +1.70% | 0.006 |
| B | 2 | MINA/USDT | vwap_cross | `n=10` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_order_block(≤3 bar) | +53% | +202% | +202% | 0.705 | -35% | 2.873 | 39% | 4.515 | 18% | +21% | +4.50% | 0.005 |
| B | 2 | AAVE/USDT | smc_ote | `k=5,fib_lo=0.5` | çıkış=stop_atr=2.0,max_hold=10 | +108% | +191% | +134% | 0.614 | -34% | 1.661 | 56% | 1.3 | 44% | +13% | +2.70% | 0.002 |
| B | 2 | XLM/USDT | macd_cross | `cfg=(8, 21, 5),zero_filter=True` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤5 bar) | +34% | +54% | +244% | 0.641 | -27% | 3.76 | 62% | 2.256 | 31% | +32% | +5.38% | 0.0 |
| B | 2 | XLM/USDT | smc_ote | `k=8,fib_lo=0.5` | çıkış=stop_atr=2.0,trail_atr=3.0 · onay=pivot_bounce(≤5 bar) | +102% | +207% | +127% | 0.563 | -28% | 2.128 | 47% | 2.432 | 29% | +18% | +3.43% | 0.0 |

## Coin coin özet (ajan günlüğü)

- **AAVE/USDT**: 70 aday denendi, 1 kaldı. En iyi aday smc_ote (`k=5,fib_lo=0.5`, çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **ADA/USDT**: 75 aday denendi, 0 kaldı. En iyi aday rsi_midline (`n=21,level=50`, filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 1.867, 1x maks. düşüş -46%.
- **ALGO/USDT**: 70 aday denendi, 0 kaldı. En iyi aday stochrsi_reversal (`n=21,lo=5`, filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 1.977, 1x maks. düşüş -44%.
- **APT/USDT**: 82 aday denendi, 2 kaldı. En iyi aday cci_reversal (`n=14,lo=-100`, filtre=low_vol · çıkış=trail_atr=3.0): OK — tüm adımlar geçti.
- **ARB/USDT**: 103 aday denendi, 0 kaldı. En iyi aday elder_impulse (`ema_n=13,macd_cfg=(12, 26, 9)`, filtre=htf_week_sma10 · çıkış=stop_atr=2.0,max_hold=10): S7 — PSR 0.899.
- **ATOM/USDT**: 69 aday denendi, 0 kaldı. En iyi aday smc_fvg (`max_age=20,min_gap_atr=0.0`, filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 1.663, 1x maks. düşüş -77%.
- **AVAX/USDT**: 76 aday denendi, 0 kaldı. En iyi aday smc_fvg (`max_age=10,min_gap_atr=0.0`, filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S6 — yılların %57'i kârlı.
- **AXS/USDT**: 70 aday denendi, 0 kaldı. En iyi aday smc_ote (`k=3,fib_lo=0.618`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.338, 1x maks. düşüş -63%.
- **BCH/USDT**: 71 aday denendi, 0 kaldı. En iyi aday williams_reversal (`n=14,lo=-95`, çıkış=stop_atr=2.0,trail_atr=3.0): S5 — 1 bar geç girişte Sharpe'ın %21'i kalıyor.
- **BNB/USDT**: 68 aday denendi, 0 kaldı. En iyi aday stoch_reversal (`k=5,d=5,smooth=3,lo=10`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -17%, 5y +1%, full +14%; 74 işlem (zararlı: 3y).
- **BTC/USDT**: 68 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=252,th=5`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +13%, 5y +30%, full +90%; 14 işlem.
- **CRV/USDT**: 69 aday denendi, 0 kaldı. En iyi aday down_days (`n=3,hold_exit=1`, filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 1.536, 1x maks. düşüş -48%.
- **DOGE/USDT**: 71 aday denendi, 0 kaldı. En iyi aday smc_fvg (`max_age=20,min_gap_atr=0.0`, filtre=adx20 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S2 — PF 1.826, 1x maks. düşüş -59%.
- **DOT/USDT**: 75 aday denendi, 3 kaldı. En iyi aday smc_liquidity_sweep (`k=3`, filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **ETC/USDT**: 75 aday denendi, 0 kaldı. En iyi aday cci_reversal (`n=20,lo=-100`, filtre=low_vol · çıkış=stop_atr=2.0,trail_atr=3.0): S4 — komşu ayarların %33'i kârlı.
- **ETH/USDT**: 74 aday denendi, 0 kaldı. En iyi aday smc_liquidity_sweep (`k=3`, filtre=adx20 · çıkış=stop_atr=2.0,be_r=1.0): S2 — PF 1.379, 1x maks. düşüş -80%.
- **FIL/USDT**: 80 aday denendi, 0 kaldı. En iyi aday rsi_midline (`n=28,level=50`, filtre=trend_sma200 · çıkış=stop_atr=2.0,tp_r=3.0): S2 — PF 2.753, 1x maks. düşüş -49%.
- **IMX/USDT**: 95 aday denendi, 1 kaldı. En iyi aday triple_ma (`set=(5, 20, 50),kind=sma`, filtre=htf_week_sma10 · çıkış=stop_atr=2.0,max_hold=10): OK — tüm adımlar geçti.
- **INJ/USDT**: 68 aday denendi, 0 kaldı. En iyi aday smc_ote (`k=3,fib_lo=0.5`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -7%, 5y +65%, full +98%; 53 işlem (zararlı: 3y).
- **LINK/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=28,lo=20,exit=60`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -6%, 5y -6%, full +63%; 5 işlem (zararlı: 3y, 5y).
- **LTC/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=7,lo=10,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +13%, 5y +13%, full +25%; 4 işlem.
- **MANA/USDT**: 70 aday denendi, 0 kaldı. En iyi aday awesome_zero (`fast=5,slow=34`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.874, 1x maks. düşüş -65%.
- **MINA/USDT**: 120 aday denendi, 5 kaldı. En iyi aday macd_cross (`cfg=(12, 26, 9),zero_filter=False`, filtre=trend_sma200 · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): OK — tüm adımlar geçti.
- **NEAR/USDT**: 70 aday denendi, 0 kaldı. En iyi aday adx_trend (`n=14,th=20`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.6, 1x maks. düşüş -66%.
- **OP/USDT**: 74 aday denendi, 0 kaldı. En iyi aday mfi_reversal (`n=10,lo=30`, çıkış=stop_atr=2.0,trail_atr=3.0): S2 — PF 1.553, 1x maks. düşüş -44%.
- **PYTH/USDT**: elendi (S0: 2.9 yıl veri var, en az 3.0 yıl gerekli).
- **SAND/USDT**: 74 aday denendi, 0 kaldı. En iyi aday mfi_reversal (`n=10,lo=30`, filtre=trend_sma200 · çıkış=stop_atr=2.0,max_hold=10): S4 — komşu ayarların %0'i kârlı.
- **SNX/USDT**: 71 aday denendi, 0 kaldı. En iyi aday smc_ote (`k=5,fib_lo=0.5`, filtre=adx20 · çıkış=stop_atr=2.0,max_hold=10): S4 — komşu ayarların %33'i kârlı.
- **SOL/USDT**: 68 aday denendi, 0 kaldı. En iyi aday smc_liquidity_sweep (`k=3`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y -18%, 5y +99%, full +77%; 70 işlem (zararlı: 3y).
- **SUI/USDT**: 72 aday denendi, 0 kaldı. En iyi aday down_days (`n=4,hold_exit=1`, çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S3 — 2.0x maliyette getiri -2%.
- **THETA/USDT**: 68 aday denendi, 0 kaldı. En iyi aday triple_ma (`set=(20, 50, 100),kind=sma`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +70%, 5y +128%, full +106%; 24 işlem.
- **TRX/USDT**: 68 aday denendi, 0 kaldı. En iyi aday rsi_reversal (`n=14,lo=10,exit=50`, çıkış=stop_atr=2.0,trail_atr=3.0): S1 — 3y +21%, 5y +21%, full +21%; 1 işlem.
- **UNI/USDT**: 70 aday denendi, 0 kaldı. En iyi aday smc_ote (`k=3,fib_lo=0.5`, filtre=low_vol · çıkış=stop_atr=2.0,partial_r=1.0,partial_frac=0.5,partial_to_be=True,trail_atr=3.0): S5 — 1 bar geç girişte Sharpe'ın %38'i kalıyor.
- **XLM/USDT**: 75 aday denendi, 2 kaldı. En iyi aday macd_cross (`cfg=(8, 21, 5),zero_filter=True`, çıkış=stop_atr=2.0,trail_atr=3.0 · onay=smc_liquidity_sweep(≤5 bar)): OK — tüm adımlar geçti.
- **XRP/USDT**: 70 aday denendi, 0 kaldı. En iyi aday roc_breakout (`n=252,th=5`, çıkış=stop_atr=2.0,trail_atr=3.0): S6 — yılların %56'i kârlı.

## Zayıf yönler (dürüst liste)

- 29909 deneme yapıldı. Bu kadar çok denemede şans eseri iyi görünen strateji çıkar. DSR bunu düzeltir; tier A sadece DSR ≥ eşik olanlardır.
- Seçim ve test aynı geçmiş veride yapıldı. Gerçek test arenadaki ileri (paper) kayıttır.
- Survivorship: liste bugünün coinlerinden oluşur. Borsadan silinen coinler yok, bu sonucu iyimser yapar.
- Funding sabit yıllık oranla, likidasyon işlem bazında yaklaşık modellenir.
- Tek borsa verisi (Bitget, yoksa OKX/KuCoin). Emir defteri ve piyasa etkisi modellenmez.

## Arena

Arena: 42 aktif (eleme geçen), 58 kontrol (yakın aday, switcher kullanmaz), 10 yeni üye, 0 kontrolden aktife. Üst sınır 100.

## Switcher backtest kapısı

Geçti: **False** — kontroller: `{"beats_equal_weight_all_windows": false, "positive_at_cost_stress": true, "max_dd_ok": true}`

Pencereler: `{"3y": {"sharpe": 0.847, "ew_sharpe": 1.876}, "5y": {"sharpe": 0.657, "ew_sharpe": 1.815}, "full": {"sharpe": 0.415, "ew_sharpe": 0.812}}`
