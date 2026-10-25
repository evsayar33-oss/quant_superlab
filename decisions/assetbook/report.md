# H073 varlık başına strateji kitabı (tek platform: Bitget perp)

Tarih: 2026-10-24. Kurallar sonuçlardan ÖNCE yazıldı: `config/assetbook.yaml` (commit `c50eac5`). Toplam deneme: **29,912**.

Seçim her kesimde sadece kesimden önceki barları okur. Kilitli dönem = son 2 yıl. Zaman makinesi = aynı seçim 6 ve 4 yıl önce yapılmış gibi.

## Varlık başına sonuç

| Varlık | TF | Bitget | Deneme | D1–D3 | D4 | D5 | D6 (hepsi) | Seçilen kural | Kilitli 2 yıl (2x maliyet) | PF | İşlem | Al-tut 2 yıl | Zaman makinesi | Sonuç |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 1d | BTCUSDT | 2,831 | 58 | 56 | 46 | 0 | yok | — | — | — | +21.8% | 0/3 | kaldı |
| BTC | 4h | BTCUSDT | 2,846 | 84 | 75 | 57 | 0 | yok | — | — | — | +21.8% | 0/3 | kaldı |
| ETH | 1d | ETHUSDT | 2,878 | 52 | 52 | 41 | 0 | yok | — | — | — | -5.4% | 0/3 | kaldı |
| ETH | 4h | ETHUSDT | 2,877 | 47 | 42 | 34 | 0 | yok | — | — | — | -5.4% | 0/3 | kaldı |
| SOL | 1d | SOLUSDT | 2,652 | 18 | 17 | 13 | 0 | yok | — | — | — | -39.8% | 0/1 | kaldı |
| SOL | 4h | SOLUSDT | 2,671 | 27 | 27 | 19 | 0 | yok | — | — | — | -39.8% | 0/1 | kaldı |
| SPX | 1d | SPXUSDT | 2,616 | 17 | 16 | 14 | 0 | yok | — | — | — | +31.5% | 0/3 | kaldı |
| NDX | 1d | NDX100USDT | 2,614 | 33 | 31 | 25 | 0 | yok | — | — | — | +44.3% | 0/3 | kaldı |
| XAU | 1d | XAUUSDT | 2,681 | 18 | 18 | 18 | 0 | yok | — | — | — | +46.1% | 0/3 | kaldı |
| XAG | 1d | XAGUSDT | 2,624 | 2 | 1 | 1 | 0 | yok | — | — | — | +58.7% | 0/3 | kaldı |
| COPPER | 1d | COPPERUSDT | 2,622 | 4 | 2 | 0 | 0 | yok | — | — | — | +43.5% | 0/3 | kaldı |

D1 işlem sayısı · D2 2x maliyette kâr, PF ≥ 1,20, kazanma oranı başa baş oranının üstünde · D3 her üçte birde kârlı · D4 plato · D5 1 bar gecikme · D6 şans testi (DSR ≥ 0,95).

## Aday kurallar (karar kapısına gidecek)

**Daha iyisi bulunamadı.** Önceden yazılan kurala göre hiçbir varlıkta, kilitli 2 yılı ve zaman makinesini birlikte geçen bir kural çıkmadı.

## Zaman makinesi ayrıntısı

| Varlık | TF | Kesim | Test edilebilir | Seçim | İleri 2 yıl (2x) | PF | İşlem | İçeride |
|---|---|---|---|---|---|---|---|---|
| BTC | 1d | 2020-10-23 | evet | yok | — | — | — | hayır |
| BTC | 1d | 2022-10-23 | evet | yok | — | — | — | hayır |
| BTC | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |
| BTC | 4h | 2020-10-23 | evet | yok | — | — | — | hayır |
| BTC | 4h | 2022-10-23 | evet | yok | — | — | — | hayır |
| BTC | 4h | 2024-10-23 | evet | yok | — | — | — | hayır |
| ETH | 1d | 2020-10-23 | evet | yok | — | — | — | hayır |
| ETH | 1d | 2022-10-23 | evet | yok | — | — | — | hayır |
| ETH | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |
| ETH | 4h | 2020-10-23 | evet | yok | — | — | — | hayır |
| ETH | 4h | 2022-10-23 | evet | yok | — | — | — | hayır |
| ETH | 4h | 2024-10-23 | evet | yok | — | — | — | hayır |
| SOL | 1d | 2020-10-23 | hayır | yok | — | — | — | hayır |
| SOL | 1d | 2022-10-23 | hayır | yok | — | — | — | hayır |
| SOL | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |
| SOL | 4h | 2020-10-23 | hayır | yok | — | — | — | hayır |
| SOL | 4h | 2022-10-23 | hayır | yok | — | — | — | hayır |
| SOL | 4h | 2024-10-23 | evet | yok | — | — | — | hayır |
| SPX | 1d | 2020-10-23 | evet | yok | — | — | — | hayır |
| SPX | 1d | 2022-10-23 | evet | yok | — | — | — | hayır |
| SPX | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |
| NDX | 1d | 2020-10-23 | evet | yok | — | — | — | hayır |
| NDX | 1d | 2022-10-23 | evet | yok | — | — | — | hayır |
| NDX | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |
| XAU | 1d | 2020-10-23 | evet | yok | — | — | — | hayır |
| XAU | 1d | 2022-10-23 | evet | yok | — | — | — | hayır |
| XAU | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |
| XAG | 1d | 2020-10-23 | evet | yok | — | — | — | hayır |
| XAG | 1d | 2022-10-23 | evet | yok | — | — | — | hayır |
| XAG | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |
| COPPER | 1d | 2020-10-23 | evet | yok | — | — | — | hayır |
| COPPER | 1d | 2022-10-23 | evet | yok | — | — | — | hayır |
| COPPER | 1d | 2024-10-23 | evet | yok | — | — | — | hayır |

## Fibonacci sorusu

### 1) Fibonacci premium/discount filtresi diğer kuralları iyileştiriyor mu? (eşli test)

| Varlık | TF | Çift | Keşif: medyan PF farkı | Keşif: iyileşen | Kilitli: medyan PF farkı | Kilitli: iyileşen | Yardım ediyor |
|---|---|---|---|---|---|---|---|
| BTC | 1d | 233 | -0.102 | 0.191 | -0.124 | 0.18 | hayır |
| BTC | 4h | 420 | -0.053 | 0.234 | -0.007 | 0.438 | hayır |
| ETH | 1d | 228 | -0.032 | 0.382 | -0.09 | 0.211 | hayır |
| ETH | 4h | 400 | -0.05 | 0.311 | 0.02 | 0.535 | hayır |
| SOL | 1d | 232 | -0.206 | 0.15 | -0.037 | 0.276 | hayır |
| SOL | 4h | 409 | -0.074 | 0.206 | 0.014 | 0.545 | hayır |
| SPX | 1d | 169 | -0.014 | 0.326 | -0.019 | 0.379 | hayır |
| NDX | 1d | 167 | -0.014 | 0.381 | 0.0 | 0.443 | hayır |
| XAU | 1d | 189 | -0.032 | 0.283 | -0.086 | 0.217 | hayır |
| XAG | 1d | 181 | -0.045 | 0.258 | -0.12 | 0.282 | hayır |
| COPPER | 1d | 193 | 0.002 | 0.509 | 0.0 | 0.456 | hayır |

Genel karar (ön kayıt: en az 6 işte yardım etmeli): **0/11 → YARDIM ETMİYOR**.

### 2) Saf Fibonacci giriş ailesi (F1) — her varlıkta en sağlam ayar

| Varlık | TF | F1 geçen (D1–D6) | F1 seçimi | Kilitli 2 yıl (2x) | PF | İşlem |
|---|---|---|---|---|---|---|
| BTC | 1d | 0 | yok | — | — | — |
| BTC | 4h | 0 | yok | — | — | — |
| ETH | 1d | 0 | yok | — | — | — |
| ETH | 4h | 0 | yok | — | — | — |
| SOL | 1d | 0 | yok | — | — | — |
| SOL | 4h | 0 | yok | — | — | — |
| SPX | 1d | 0 | yok | — | — | — |
| NDX | 1d | 0 | yok | — | — | — |
| XAU | 1d | 0 | yok | — | — | — |
| XAG | 1d | 0 | yok | — | — | — |
| COPPER | 1d | 0 | yok | — | — | — |

## Keşifte en iyi görünen ama bir kontrolde kalanlar (bilgi, karar değil)

| Varlık | TF | Kural | Kaldığı | Keşif 2x getiri | PF | DSR |
|---|---|---|---|---|---|---|
| BTC | 1d | `F2|{"exit": 0, "filter": "none", "params": {"ema_n": 21, "macd_cfg": [` | D6 | +2464.6% | 2.685 | 0.218 |
| BTC | 1d | `F2|{"exit": 0, "filter": "none", "params": {"level": 55, "n": 21}, "ru` | D6 | +3119.2% | 5.179 | 0.266 |
| BTC | 4h | `F2|{"exit": 0, "filter": "none", "params": {"k": 2.0, "n": 50}, "rule"` | D6 | +2079.6% | 2.363 | 0.09 |
| BTC | 4h | `F2|{"exit": 0, "filter": "none", "params": {"k": 2.0, "n": 50}, "rule"` | D6 | +1265.6% | 2.328 | 0.043 |
| ETH | 1d | `F2|{"exit": 0, "filter": "none", "params": {"level": 150, "n": 20}, "r` | D6 | +2050.8% | 3.796 | 0.172 |
| ETH | 1d | `F2|{"exit": 13, "filter": "none", "params": {"ema_n": 21, "macd_cfg": ` | D6 | +1126.2% | 1.816 | 0.1 |
| ETH | 4h | `F2|{"exit": 0, "filter": "none", "params": {"n": 50, "rv": 2.0}, "rule` | D6 | +3242.5% | 3.597 | 0.185 |
| ETH | 4h | `F2|{"exit": 28, "filter": "none", "params": {"n": 50, "rv": 2.0}, "rul` | D6 | +874.4% | 2.685 | 0.091 |
| SOL | 1d | `F2|{"exit": 0, "filter": "none", "params": {"cfg": [5, 20]}, "rule": "` | D6 | +8189.0% | 5.734 | 0.086 |
| SOL | 1d | `F2|{"exit": 0, "filter": "none", "params": {"n": 20, "th": 0.1}, "rule` | D6 | +7083.1% | 5.523 | 0.062 |
| SOL | 4h | `F2|{"exit": 0, "filter": "none", "params": {"max_age": 20, "min_gap_at` | D6 | +10491.7% | 2.507 | 0.281 |
| SOL | 4h | `F2|{"exit": 0, "filter": "none", "params": {"k": 2.0, "n": 50}, "rule"` | D6 | +6314.4% | 3.227 | 0.164 |
| SPX | 1d | `F1|{"filter": "sma200", "k": 10, "side": "long", "stop": "swing", "tar` | D6 | +52.4% | 2.492 | 0.011 |
| SPX | 1d | `F1|{"filter": "sma200", "k": 5, "side": "long", "stop": "atr", "target` | D6 | +35.1% | 1.833 | 0.003 |
| NDX | 1d | `F1|{"filter": "sma200", "k": 10, "side": "long", "stop": "atr", "targe` | D6 | +114.9% | 3.091 | 0.064 |
| NDX | 1d | `F1|{"filter": "sma200", "k": 10, "side": "long", "stop": "atr", "targe` | D6 | +91.8% | 2.917 | 0.041 |
| XAU | 1d | `F2|{"exit": 28, "filter": "none", "params": {"entry": 55, "exit": 20},` | D6 | +49.8% | 1.764 | 0.002 |
| XAU | 1d | `F2|{"exit": 28, "filter": "none", "params": {"exit_ma": 100, "n": 252}` | D6 | +35.4% | 1.747 | 0.001 |
| XAG | 1d | `F1|{"filter": "none", "k": 10, "side": "long", "stop": "atr", "target"` | D6 | +144.4% | 2.012 | 0.047 |

## Zayıf yönler

- Endeks ve metal perp'leri için fiyat vekili kullanıldı (^GSPC, ^NDX, GLD, SLV, CPER). Bitget perp fiyatı, işlem saatleri ve funding farklı olabilir.
- Endeks ve metallerde ücretsiz 4 saatlik uzun geçmiş yok; bu varlıklar sadece günlükte test edildi.
- SOL geçmişi kısa (2020-08). Zaman makinesi için yeterli kesim yok; kural gereği SOL aday olamaz.
- Maliyet: taker %0,06 + kayma; funding sabit yıllık oran (kripto %8, diğer %5). Gerçek funding değişir.
- Tek pozisyon, 1x büyüklük. Kaldıraç kenar yaratmaz; sadece kârı ve zararı büyütür.
- Aday kural bile karar değildir: hipotez id + run.py --hypothesis (karar kapısı) + ileri kayıt gerekir.
