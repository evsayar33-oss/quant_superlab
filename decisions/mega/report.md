# H062 dev tarama — tüm varlık sınıfları

Tarih: 2026-10-21. Toplam deneme: **73,005** (DSR bu sayıyla hesaplandı).

Kurallar sonuçlardan ÖNCE yazıldı: `config/mega.yaml`. Son 2 yıl kilitli; seçim bu dönemi hiç görmedi. Kilitli dönem sadece finalistler için bir kez okundu.

## Huni (iş başına)

| Sınıf | Yön | Kesim | Varlık | Deneme | D1 çok varlık | D2 kalite | D3 plato | D4 yıllar |
|---|---|---|---|---|---|---|---|---|
| crypto | both | 2024-10-20 | 7 | 6,530 | 94 | 43 | 29 | 16 |
| crypto | long | 2024-10-20 | 7 | 6,530 | 1106 | 341 | 286 | 89 |
| crypto | short | 2024-10-20 | 7 | 5,630 | 2 | 0 | 0 | 0 |
| energy | both | 2024-10-21 | 5 | 5,720 | 261 | 3 | 0 | 0 |
| energy | long | 2024-10-21 | 5 | 6,530 | 1590 | 94 | 54 | 34 |
| energy | short | 2024-10-21 | 4 | 5,630 | 28 | 0 | 0 | 0 |
| indices | both | 2024-10-21 | 5 | 6,170 | 911 | 36 | 22 | 5 |
| indices | long | 2024-10-21 | 5 | 6,518 | 3117 | 281 | 255 | 192 |
| indices | short | 2024-10-21 | 5 | 5,630 | 65 | 0 | 0 | 0 |
| metals | both | 2024-10-21 | 5 | 5,960 | 610 | 37 | 27 | 10 |
| metals | long | 2024-10-21 | 5 | 6,527 | 2485 | 112 | 89 | 69 |
| metals | short | 2024-10-21 | 5 | 5,630 | 60 | 0 | 0 | 0 |

D1–D4'ü geçen: **415**. D5 (DSR ≥ 0.9) geçen finalist: **0**. Kilitli dönemi de geçen: **0**.


**Daha iyisi bulunamadı:** önceden yazılan kurala göre hiçbir strateji kilitli dönemi geçmedi. Bot kuralı (H054) değişmez.

## En iyi D1–D4 adayları (DSR'ı geçmeyenler dahil, iş başına 3)

| Sınıf | Yön | Strateji | Keşif Sharpe | Varlık payı |
|---|---|---|---|---|
| crypto | both | `cmf_flow|{"n": 40, "th": 0.05}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.865 | 86% |
| crypto | both | `hurst_switch|{"fast": 20, "n": 200, "rsi_n": 2}|x20|none|pivot_bounce:{"window": 5}:w3` | 0.796 | 86% |
| crypto | both | `hurst_switch|{"fast": 20, "n": 200, "rsi_n": 2}|x13|none|pivot_bounce:{"window": 5}:w3` | 0.796 | 86% |
| crypto | long | `cci_breakout|{"level": 100, "n": 14}|x0|none` | 1.131 | 100% |
| crypto | long | `ma_cross|{"kind": "dema", "pair": [10, 50]}|x28|trend_sma200` | 1.101 | 100% |
| crypto | long | `cci_breakout|{"level": 100, "n": 14}|x0|trend_sma200` | 1.077 | 100% |
| energy | long | `trix_cross|{"n": 21, "signal": 7}|x13|trend_sma200|smc_bos:{"k": 5}:w5` | 0.724 | 100% |
| energy | long | `trix_cross|{"n": 21, "signal": 9}|x13|trend_sma200|smc_bos:{"k": 5}:w5` | 0.687 | 100% |
| energy | long | `tsi_cross|{"cfg": [40, 20, 10]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.677 | 80% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.752 | 80% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.735 | 60% |
| indices | both | `supertrend_flip|{"cfg": [7, 2.0]}|x13|trend_sma200` | 0.601 | 80% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.942 | 80% |
| indices | long | `macd_cross|{"cfg": [12, 26, 9], "zero_filter": true}|x18|trend_sma200|smc_liquidity_sweep:{"k": 5}:w5` | 0.936 | 100% |
| indices | long | `ppo_cross|{"cfg": [10, 30, 9]}|x0|trend_sma200|smc_liquidity_sweep:{"k": 5}:w3` | 0.926 | 80% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 0.624 | 100% |
| metals | both | `high_52w_break|{"exit_ma": 100, "n": 252}|x28|none|smc_bos:{"k": 5}:w3` | 0.624 | 100% |
| metals | both | `high_52w_break|{"exit_ma": 50, "n": 252}|x28|trend_sma200|smc_bos:{"k": 5}:w3` | 0.624 | 100% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w3` | 0.905 | 100% |
| metals | long | `vortex_cross|{"n": 28}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.881 | 100% |
| metals | long | `ma_cross|{"kind": "tema", "pair": [20, 50]}|x13|none|smc_order_block:{"k": 5, "max_age": 50}:w5` | 0.88 | 100% |

## Zayıf yönler

- Yahoo `=F` serileri sürekli ön ay vadeli seridir; vade geçiş günlerinde küçük sıçramalar olabilir. Roll maliyeti modellenmedi.
- Vadeli işlemlerde sadece günlük (1d) test var: ücretsiz kaynakta saatlik veri yalnız son 2 yıl.
- Vade yapısı (carry) verisi ücretsiz değil; test edilemedi. Temel veri olarak sadece CFTC COT kullanıldı.
- Kripto sınıfında 5 yıldan kısa verisi olan coinler dışarıda kaldı (listelenme yanlılığı azalır, kapsam düşer).
- Sınıf başına varlık sayısı az (4–5): 'çok varlıkta çalışıyor' şartı küçük örneklemle ölçülür.

> ⚠️ Bu bir seçim sürecidir (binlerce aday). Gerçek paraya aday olmadan önce **zaman makinesi** testi gerekir (`lab/timemachine.py`, workflow "Time machine test"). Kilitli dönem bu testin yerini tutmaz.
