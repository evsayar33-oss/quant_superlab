# H062 hayatta kalanlar: al-tut ve rastgele girişe karşı

Kural sonuçlardan ÖNCE yazıldı (`config/mega.yaml` → baseline). Sadece ileri dönem (kesimden bugüne), 2x maliyet.

- **B1 rastgele giriş:** aynı varlık, aynı işlem sayısı, aynı tutma süresi ve yön; giriş tarihleri rastgele (300 deneme). Gerçek işlemler denemelerin en az %90'ini geçmeli.
- **B2 al-tut:** stratejinin ileri Sharpe değeri, sınıfın eşit ağırlıklı al-tut Sharpe değerinden düşük olmamalı.
- Geçmek için: seçildiği HER kesimde B1 ve B2.

Hayatta kalan: **152**. B1'i her kesimde geçen: **25**. B2'yi her kesimde geçen: **20**. İkisini de geçen: **10**.

| Sonuç | Sınıf | Yön | Strateji | Kesim | İleri getiri | Al-tut getiri | İleri Sharpe | Al-tut Sharpe | Rastgeleyi geçme | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|---|
| ✅ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|trend_sma200` | 2022-10-21 | +36% | +107% | 1.201 | 1.184 | %98 | %37 |
| ✅ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|trend_sma200` | 2024-10-21 | +17% | +38% | 1.181 | 0.98 | %96 | %36 |
| ✅ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 2022-10-21 | +25% | +85% | 1.479 | 0.687 | %99 | %8 |
| ✅ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 2023-10-21 | +17% | +90% | 1.383 | 0.864 | %94 | %10 |
| ✅ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 2024-10-21 | +14% | +55% | 1.497 | 0.823 | %95 | %10 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 2022-10-21 | +24% | +85% | 0.835 | 0.687 | %96 | %9 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 2024-10-21 | +19% | +55% | 0.996 | 0.823 | %93 | %12 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 2022-10-21 | +24% | +85% | 0.835 | 0.687 | %96 | %9 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 2024-10-21 | +19% | +55% | 0.996 | 0.823 | %93 | %12 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 2022-10-21 | +24% | +85% | 0.835 | 0.687 | %98 | %9 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 2024-10-21 | +19% | +55% | 0.996 | 0.823 | %92 | %12 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 2022-10-21 | +22% | +85% | 0.777 | 0.687 | %94 | %10 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 2024-10-21 | +18% | +55% | 0.951 | 0.823 | %92 | %12 |
| ✅ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 2022-10-21 | +25% | +85% | 1.287 | 0.687 | %98 | %11 |
| ✅ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 2023-10-21 | +17% | +90% | 1.15 | 0.864 | %91 | %12 |
| ✅ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 2024-10-21 | +14% | +55% | 1.497 | 0.823 | %95 | %10 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w5` | 2022-10-21 | +22% | +85% | 0.777 | 0.687 | %97 | %10 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w5` | 2024-10-21 | +18% | +55% | 0.951 | 0.823 | %91 | %12 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 2022-10-21 | +22% | +85% | 0.777 | 0.687 | %96 | %10 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w5` | 2024-10-21 | +18% | +55% | 0.951 | 0.823 | %91 | %12 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w5` | 2022-10-21 | +22% | +85% | 0.777 | 0.687 | %94 | %10 |
| ✅ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w5` | 2024-10-21 | +18% | +55% | 0.951 | 0.823 | %91 | %12 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|none` | 2022-10-21 | +57% | +107% | 1.209 | 1.184 | %100 | %44 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|none` | 2023-10-21 | +41% | +86% | 1.221 | 1.302 | %100 | %43 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|none` | 2024-10-21 | +26% | +38% | 1.107 | 0.98 | %99 | %44 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2022-10-21 | +23% | +107% | 0.956 | 1.184 | %99 | %16 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2023-10-21 | +23% | +86% | 1.247 | 1.302 | %100 | %13 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2024-10-21 | +8% | +38% | 0.842 | 0.98 | %98 | %12 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 14, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2022-10-21 | +17% | +107% | 0.911 | 1.184 | %98 | %12 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 14, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2023-10-21 | +17% | +86% | 1.273 | 1.302 | %100 | %9 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 14, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2024-10-21 | +7% | +38% | 0.903 | 0.98 | %99 | %8 |
| ❌ | metals | long | `trix_cross|{"n": 12, "signal": 9}|x20|none|smc_order_block:{"k": 5, "max_age": 5` | 2022-10-21 | +18% | +85% | 0.578 | 0.687 | %97 | %9 |
| ❌ | metals | long | `trix_cross|{"n": 12, "signal": 9}|x20|none|smc_order_block:{"k": 5, "max_age": 5` | 2023-10-21 | +19% | +90% | 0.708 | 0.864 | %97 | %11 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x20|none` | 2022-10-21 | +25% | +107% | 1.056 | 1.184 | %100 | %20 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x20|none` | 2023-10-21 | +16% | +86% | 1.092 | 1.302 | %99 | %18 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x20|none` | 2024-10-21 | +9% | +38% | 0.846 | 0.98 | %95 | %17 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x28|none` | 2022-10-21 | +25% | +107% | 1.061 | 1.184 | %100 | %20 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x28|none` | 2023-10-21 | +16% | +86% | 1.094 | 1.302 | %99 | %18 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x28|none` | 2024-10-21 | +9% | +38% | 0.848 | 0.98 | %94 | %17 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|none` | 2022-10-21 | +55% | +107% | 1.076 | 1.184 | %99 | %50 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|none` | 2023-10-21 | +37% | +86% | 1.034 | 1.302 | %96 | %49 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|none` | 2024-10-21 | +22% | +38% | 0.894 | 0.98 | %94 | %49 |
| ❌ | indices | long | `cot_commercial|{"n": 260, "th": 1.0}|x0|none` | 2022-10-21 | +32% | +107% | 1.289 | 1.184 | %96 | %23 |
| ❌ | indices | long | `cot_commercial|{"n": 260, "th": 1.0}|x0|none` | 2023-10-21 | +19% | +86% | 1.246 | 1.302 | %96 | %21 |
| ❌ | indices | long | `cot_commercial|{"n": 260, "th": 1.0}|x0|none` | 2024-10-21 | +15% | +38% | 1.237 | 0.98 | %93 | %30 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x0|none` | 2022-10-21 | +31% | +107% | 1.155 | 1.184 | %100 | %21 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x0|none` | 2023-10-21 | +20% | +86% | 1.185 | 1.302 | %99 | %19 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x0|none` | 2024-10-21 | +10% | +38% | 0.818 | 0.98 | %93 | %18 |
| ❌ | indices | both | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:` | 2022-10-21 | +10% | +107% | 0.634 | 1.184 | %93 | %15 |
| ❌ | indices | both | `ibs_reversion|{"hi": 0.7, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:` | 2024-10-21 | +8% | +38% | 0.876 | 0.98 | %97 | %15 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x13|none` | 2022-10-21 | +25% | +107% | 1.056 | 1.184 | %100 | %20 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x13|none` | 2023-10-21 | +16% | +86% | 1.092 | 1.302 | %99 | %18 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x13|none` | 2024-10-21 | +9% | +38% | 0.846 | 0.98 | %93 | %17 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x0|none` | 2022-10-21 | +32% | +107% | 1.041 | 1.184 | %99 | %25 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x0|none` | 2023-10-21 | +20% | +86% | 0.984 | 1.302 | %95 | %23 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x0|none` | 2024-10-21 | +11% | +38% | 0.763 | 0.98 | %93 | %21 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 25, "smooth": 3}|x0|trend_sma200|smc_liqu` | 2022-10-21 | +19% | +107% | 0.832 | 1.184 | %95 | %15 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 25, "smooth": 3}|x0|trend_sma200|smc_liqu` | 2024-10-21 | +11% | +38% | 0.813 | 0.98 | %91 | %17 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 21, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2022-10-21 | +20% | +107% | 0.71 | 1.184 | %95 | %16 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 21, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2023-10-21 | +19% | +86% | 0.886 | 1.302 | %96 | %14 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 21, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2024-10-21 | +7% | +38% | 0.54 | 0.98 | %91 | %12 |
| ❌ | metals | long | `bollinger_reversion|{"k": 2.0, "n": 30}|x0|trend_sma200` | 2022-10-21 | +13% | +85% | 0.615 | 0.687 | %90 | %6 |
| ❌ | metals | long | `bollinger_reversion|{"k": 2.0, "n": 30}|x0|trend_sma200` | 2023-10-21 | +12% | +90% | 0.713 | 0.864 | %95 | %4 |
| ❌ | metals | long | `bollinger_reversion|{"k": 2.0, "n": 30}|x0|trend_sma200` | 2024-10-21 | +10% | +55% | 0.756 | 0.823 | %94 | %4 |
| ❌ | metals | long | `trix_cross|{"n": 21, "signal": 7}|x13|none` | 2022-10-21 | +35% | +85% | 0.912 | 0.687 | %89 | %25 |
| ❌ | metals | long | `trix_cross|{"n": 21, "signal": 7}|x13|none` | 2023-10-21 | +35% | +90% | 1.19 | 0.864 | %91 | %24 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 21, "lo": 20, "smooth": 1}|x0|trend_sma200` | 2022-10-21 | +22% | +107% | 0.721 | 1.184 | %93 | %19 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 21, "lo": 20, "smooth": 1}|x0|trend_sma200` | 2024-10-21 | +8% | +38% | 0.502 | 0.98 | %89 | %16 |
| ❌ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 2022-10-21 | +24% | +85% | 0.835 | 0.687 | %98 | %9 |
| ❌ | metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 2024-10-21 | +19% | +55% | 0.996 | 0.823 | %89 | %12 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x0|trend_sma200` | 2022-10-21 | +20% | +107% | 0.922 | 1.184 | %94 | %21 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x0|trend_sma200` | 2023-10-21 | +17% | +86% | 1.03 | 1.302 | %93 | %21 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x0|trend_sma200` | 2024-10-21 | +9% | +38% | 0.814 | 0.98 | %89 | %19 |
| ❌ | indices | long | `cot_extreme|{"n": 260, "th": 1.5}|x13|none` | 2023-10-21 | +9% | +86% | 1.243 | 1.302 | %95 | %9 |
| ❌ | indices | long | `cot_extreme|{"n": 260, "th": 1.5}|x13|none` | 2024-10-21 | +7% | +38% | 1.274 | 0.98 | %88 | %13 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x18|none` | 2022-10-21 | +23% | +107% | 1.003 | 1.184 | %99 | %20 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x18|none` | 2023-10-21 | +15% | +86% | 1.016 | 1.302 | %97 | %18 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.7, "lo": 0.1}|x18|none` | 2024-10-21 | +7% | +38% | 0.726 | 0.98 | %88 | %17 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 9, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2022-10-21 | +16% | +107% | 0.76 | 1.184 | %88 | %15 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 9, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2024-10-21 | +6% | +38% | 0.698 | 0.98 | %89 | %12 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200` | 2022-10-21 | +34% | +107% | 0.994 | 1.184 | %93 | %43 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200` | 2024-10-21 | +16% | +38% | 0.962 | 0.98 | %88 | %43 |
| ❌ | crypto | long | `bollinger_breakout|{"k": 2.5, "n": 20}|x13|none` | 2023-10-20 | +23% | +46% | 0.473 | 0.51 | %86 | %15 |
| ❌ | crypto | long | `bollinger_breakout|{"k": 2.5, "n": 20}|x13|none` | 2024-10-20 | +16% | +27% | 0.554 | 0.494 | %86 | %14 |
| ❌ | indices | long | `rsi_reversal|{"exit": 60, "lo": 35, "n": 9}|x0|trend_sma200` | 2022-10-21 | +23% | +107% | 0.733 | 1.184 | %95 | %19 |
| ❌ | indices | long | `rsi_reversal|{"exit": 60, "lo": 35, "n": 9}|x0|trend_sma200` | 2023-10-21 | +23% | +86% | 0.886 | 1.302 | %95 | %20 |
| ❌ | indices | long | `rsi_reversal|{"exit": 60, "lo": 35, "n": 9}|x0|trend_sma200` | 2024-10-21 | +10% | +38% | 0.583 | 0.98 | %86 | %21 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [50, 150]}|x20|none` | 2022-10-21 | +33% | +85% | 0.545 | 0.687 | %86 | %26 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [50, 150]}|x20|none` | 2024-10-21 | +31% | +55% | 0.756 | 0.823 | %88 | %29 |
| ❌ | metals | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 21}|x13|none` | 2023-10-21 | +25% | +90% | 0.955 | 0.864 | %97 | %18 |
| ❌ | metals | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 21}|x13|none` | 2024-10-21 | +14% | +55% | 0.804 | 0.823 | %86 | %19 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "m` | 2022-10-21 | +15% | +85% | 1.044 | 0.687 | %92 | %8 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "m` | 2023-10-21 | +17% | +90% | 1.435 | 0.864 | %96 | %9 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "m` | 2024-10-21 | +11% | +55% | 1.219 | 0.823 | %85 | %9 |
| ❌ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w0` | 2022-10-21 | +11% | +85% | 1.173 | 0.687 | %96 | %5 |
| ❌ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w0` | 2023-10-21 | +7% | +90% | 1.025 | 0.864 | %85 | %5 |
| ❌ | metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w0` | 2024-10-21 | +5% | +55% | 1.184 | 0.823 | %85 | %5 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "m` | 2022-10-21 | +10% | +85% | 0.774 | 0.687 | %84 | %6 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "m` | 2023-10-21 | +13% | +90% | 1.187 | 0.864 | %90 | %8 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "m` | 2024-10-21 | +9% | +55% | 1.194 | 0.823 | %87 | %8 |
| ❌ | crypto | long | `down_days|{"hold_exit": 1, "n": 3}|x0|trend_sma200` | 2023-10-20 | +6% | +46% | 0.249 | 0.51 | %84 | %6 |
| ❌ | crypto | long | `down_days|{"hold_exit": 1, "n": 3}|x0|trend_sma200` | 2024-10-20 | +12% | +27% | 0.84 | 0.494 | %93 | %7 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x28|none` | 2022-10-21 | +24% | +107% | 0.962 | 1.184 | %98 | %23 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x28|none` | 2023-10-21 | +14% | +86% | 0.915 | 1.302 | %86 | %21 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x28|none` | 2024-10-21 | +7% | +38% | 0.722 | 0.98 | %84 | %19 |
| ❌ | crypto | both | `hurst_switch|{"fast": 20, "n": 100, "rsi_n": 2}|x18|none` | 2023-10-20 | +24% | +46% | 0.443 | 0.51 | %91 | %19 |
| ❌ | crypto | both | `hurst_switch|{"fast": 20, "n": 100, "rsi_n": 2}|x18|none` | 2024-10-20 | +15% | +27% | 0.446 | 0.494 | %83 | %22 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x13|none` | 2022-10-21 | +22% | +107% | 0.916 | 1.184 | %95 | %23 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x13|none` | 2023-10-21 | +13% | +86% | 0.872 | 1.302 | %93 | %21 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x13|none` | 2024-10-21 | +7% | +38% | 0.72 | 0.98 | %83 | %19 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x20|none` | 2022-10-21 | +22% | +107% | 0.916 | 1.184 | %97 | %23 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x20|none` | 2023-10-21 | +13% | +86% | 0.872 | 1.302 | %87 | %21 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x20|none` | 2024-10-21 | +7% | +38% | 0.72 | 0.98 | %83 | %19 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 21, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2022-10-21 | +15% | +107% | 0.565 | 1.184 | %82 | %16 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 21, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2024-10-21 | +6% | +38% | 0.479 | 0.98 | %84 | %12 |
| ❌ | metals | long | `cci_reversal|{"lo": -200, "n": 20}|x28|trend_sma200` | 2022-10-21 | +5% | +85% | 0.391 | 0.687 | %82 | %2 |
| ❌ | metals | long | `cci_reversal|{"lo": -200, "n": 20}|x28|trend_sma200` | 2024-10-21 | +7% | +55% | 0.71 | 0.823 | %89 | %4 |
| ❌ | crypto | both | `hurst_switch|{"fast": 20, "n": 100, "rsi_n": 2}|x20|none` | 2023-10-20 | +19% | +46% | 0.379 | 0.51 | %91 | %19 |
| ❌ | crypto | both | `hurst_switch|{"fast": 20, "n": 100, "rsi_n": 2}|x20|none` | 2024-10-20 | +13% | +27% | 0.4 | 0.494 | %81 | %22 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 21, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2022-10-21 | +17% | +107% | 0.584 | 1.184 | %81 | %18 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 21, "lo": 10, "smooth": 1}|x0|trend_sma200` | 2024-10-21 | +6% | +38% | 0.443 | 0.98 | %84 | %15 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 14, "lo": 20, "smooth": 1}|x0|trend_sma200` | 2022-10-21 | +15% | +107% | 0.638 | 1.184 | %80 | %18 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 14, "lo": 20, "smooth": 1}|x0|trend_sma200` | 2024-10-21 | +6% | +38% | 0.59 | 0.98 | %83 | %15 |
| ❌ | metals | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 14}|x13|none` | 2022-10-21 | +42% | +85% | 0.85 | 0.687 | %87 | %33 |
| ❌ | metals | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 14}|x13|none` | 2023-10-21 | +39% | +90% | 1.097 | 0.864 | %96 | %28 |
| ❌ | metals | long | `rsi_reversal|{"exit": 70, "lo": 35, "n": 14}|x13|none` | 2024-10-21 | +19% | +55% | 0.883 | 0.823 | %80 | %26 |
| ❌ | indices | both | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:` | 2022-10-21 | +9% | +107% | 0.453 | 1.184 | %80 | %19 |
| ❌ | indices | both | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:` | 2023-10-21 | +14% | +86% | 0.834 | 1.302 | %95 | %18 |
| ❌ | indices | both | `ibs_reversion|{"hi": 0.8, "lo": 0.2}|x0|trend_sma200|pivot_bounce:{"window": 5}:` | 2024-10-21 | +7% | +38% | 0.603 | 0.98 | %89 | %20 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 21, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2022-10-21 | +16% | +107% | 0.584 | 1.184 | %79 | %18 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 21, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2023-10-21 | +19% | +86% | 0.829 | 1.302 | %93 | %16 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 21, "lo": 10, "smooth": 3}|x0|trend_sma200` | 2024-10-21 | +7% | +38% | 0.492 | 0.98 | %85 | %15 |
| ❌ | indices | long | `cot_extreme|{"n": 260, "th": 1.5}|x20|none` | 2023-10-21 | +11% | +86% | 0.916 | 1.302 | %79 | %15 |
| ❌ | indices | long | `cot_extreme|{"n": 260, "th": 1.5}|x20|none` | 2024-10-21 | +11% | +38% | 1.18 | 0.98 | %84 | %22 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none` | 2022-10-21 | +40% | +85% | 0.835 | 0.687 | %86 | %33 |
| ❌ | metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none` | 2024-10-21 | +31% | +55% | 1.132 | 0.823 | %79 | %35 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 5, "lo": 20, "smooth": 1}|x0|trend_sma200` | 2022-10-21 | +11% | +107% | 0.658 | 1.184 | %78 | %12 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 5, "lo": 20, "smooth": 1}|x0|trend_sma200` | 2023-10-21 | +8% | +86% | 0.665 | 1.302 | %79 | %12 |
| ❌ | indices | long | `stoch_reversal|{"d": 5, "k": 5, "lo": 20, "smooth": 1}|x0|trend_sma200` | 2024-10-21 | +6% | +38% | 0.757 | 0.98 | %87 | %12 |
| ❌ | crypto | both | `hurst_switch|{"fast": 20, "n": 100, "rsi_n": 2}|x13|none` | 2023-10-20 | +15% | +46% | 0.335 | 0.51 | %82 | %18 |
| ❌ | crypto | both | `hurst_switch|{"fast": 20, "n": 100, "rsi_n": 2}|x13|none` | 2024-10-20 | +11% | +27% | 0.357 | 0.494 | %77 | %22 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x18|none` | 2022-10-21 | +22% | +107% | 0.936 | 1.184 | %97 | %22 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x18|none` | 2023-10-21 | +13% | +86% | 0.899 | 1.302 | %90 | %21 |
| ❌ | indices | long | `ibs_reversion|{"hi": 0.8, "lo": 0.1}|x18|none` | 2024-10-21 | +6% | +38% | 0.59 | 0.98 | %77 | %19 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 25, "smooth": 3}|x0|trend_sma200` | 2022-10-21 | +30% | +107% | 0.913 | 1.184 | %92 | %28 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 25, "smooth": 3}|x0|trend_sma200` | 2023-10-21 | +31% | +86% | 1.176 | 1.302 | %97 | %26 |
| ❌ | indices | long | `stoch_reversal|{"d": 3, "k": 14, "lo": 25, "smooth": 3}|x0|trend_sma200` | 2024-10-21 | +12% | +38% | 0.701 | 0.98 | %77 | %28 |
| ❌ | metals | long | `ultimate_reversal|{"a": 7, "lo": 35}|x20|trend_sma200` | 2022-10-21 | +13% | +85% | 0.576 | 0.687 | %76 | %10 |
| ❌ | metals | long | `ultimate_reversal|{"a": 7, "lo": 35}|x20|trend_sma200` | 2024-10-21 | +13% | +55% | 0.914 | 0.823 | %89 | %10 |

## Zayıf yönler

- Rastgele girişler açılış fiyatıyla hesaplandı; stratejinin stop dolumları biraz farklı olabilir.
- Al-tut karşılaştırması long al-tut ile yapıldı (short ve iki yönlü stratejiler için de).
- Kesimlerin ileri dönemleri üst üste biniyor; sonuçlar bağımsız değil.
- Geçenler hâlâ binlerce aday içinden seçildi. Sonraki adım paper izleme ve karar kapısı.
