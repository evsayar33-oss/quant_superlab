# Kasa koruma testi — crypto_alts 1d

Portföy: arenadaki **39 aktif üye**, eşit ağırlık, coin başı en fazla %20. Kabul kuralları sonuçlardan önce yazıldı (`config/arena.yaml` → `protection.accept`). Bir koruma sadece **komşu eşiklerin hepsinde** ve **her zaman diliminde** geçerse açılır.

## Korumasız portföy

Tüm geçmiş: CAGR +25.4%, Sharpe 2.302, maks. düşüş -14.7%, günlük CVaR95 -1.0%. Coin sınırı olmadan: maks. düşüş -14.8%.

Monte Carlo (1 yıl): P(düşüş ≤ −%50) = 0.0%, medyan +25%, kötü %5 +6%.

| Kriz | Getiri | Maks. düşüş |
|---|---|---|
| covid_2020 | +5.0% | -1.4% |
| may_2021 | -3.4% | -5.2% |
| luna_2022 | +13.3% | -1.4% |
| ftx_2022 | +1.4% | -3.2% |
| aug_2024 | -0.5% | -1.2% |
| oct_2025 | +3.8% | -0.6% |

## Kasa düşüş sigortası — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| (0.08, 0.16) | +24.8% | 2.347 | -11.8% | 0/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.1, 0.2) | +25.0% | 2.328 | -12.5% | 0/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.12, 0.25) | +25.0% | 2.301 | -13.4% | 0/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |

## Volatilite hedefi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.25 | +25.4% | 2.302 | -14.7% | 0/6 | ✗✗✓✓ | kaldı |
| 0.35 | +25.4% | 2.302 | -14.7% | 0/6 | ✗✗✓✓ | kaldı |
| 0.5 | +25.4% | 2.302 | -14.7% | 0/6 | ✗✗✓✓ | kaldı |

## Kasa eğrisi filtresi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 30 | +18.5% | 1.982 | -9.6% | 2/6 | ✗✓✗✗ | kaldı |
| 60 | +20.3% | 2.066 | -7.4% | 0/6 | ✗✓✗✓ | kaldı |
| 90 | +21.1% | 2.135 | -8.5% | 1/6 | ✗✓✓✓ | kaldı |

## Günlük kayıp limiti — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.04 | +25.4% | 2.302 | -14.7% | 0/6 | ✗✗✓✓ | kaldı |
| 0.05 | +25.4% | 2.302 | -14.7% | 0/6 | ✗✗✓✓ | kaldı |
| 0.07 | +25.4% | 2.302 | -14.7% | 0/6 | ✗✗✓✓ | kaldı |

## BTC çöküş bekçisi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.08 | +24.6% | 2.239 | -15.7% | 0/6 | ✗✗✓✓ | kaldı |
| 0.1 | +25.1% | 2.274 | -15.5% | 0/6 | ✗✗✓✓ | kaldı |
| 0.15 | +25.4% | 2.302 | -14.7% | 0/6 | ✗✗✓✓ | kaldı |

## Felaket stopu — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.1 | +23.6% | 2.163 | -13.8% | 0/6 | ✗✓✓✓ | kaldı |
| 0.12 | +24.1% | 2.195 | -14.2% | 1/6 | ✗✓✓✓ | kaldı |
| 0.15 | +24.5% | 2.23 | -14.2% | 1/6 | ✗✓✓✓ | kaldı |

## Portföy seçenekleri ($1000 ile başlangıç, maliyet ve funding dahil)

| Portföy | Başlangıç | Bugün ($) | Yıllık | Sharpe | Maks. düşüş | En kötü yıl | Son 3y | Son 5y | En kötü kriz |
|---|---|---|---|---|---|---|---|---|---|
| Hepsi eşit ağırlık (39 strateji), 1x | 2018-03-15 | 7,405 | +26% | 2.33 | -15% | +8% (2018) | +138% | +234% | -5% |
| En iyi 10 (farklı coin), 1x | 2018-06-28 | 13,475 | +37% | 1.87 | -21% | -6% (2018) | +203% | +419% | -12% |
| En iyi 5 (farklı coin), 1x | 2021-01-05 | 18,524 | +65% | 1.57 | -40% | +22% (2024) | +228% | +802% | -37% |
| En iyi 5 (farklı coin), 2x | 2021-01-05 | 156,402 | +138% | 1.57 | -72% | +47% (2024) | +865% | +5733% | -68% |
| En iyi 5 (farklı coin), 3x | 2021-01-05 | 482,237 | +189% | 1.57 | -92% | +43% (2021) | +2475% | +27350% | -90% |
| En iyi 5, 3x + düşüş sigortası (−%10 yarım / −%20 nakit) | 2021-01-05 | 2,929 | +20% | 0.62 | -82% | -69% (2021) | +689% | +840% | -61% |
| En iyi 5, 3x + volatilite hedefi %35 | 2021-01-05 | 121,009 | +128% | 2.09 | -23% | +51% (2024) | +884% | +4686% | -18% |
| En iyi 10, ters volatilite ağırlık, 1x | 2018-06-28 | 13,587 | +37% | 1.48 | -31% | -4% (2019) | +149% | +294% | -12% |
| En iyi 10, HRP ağırlık, 1x | 2018-06-28 | 3,421 | +16% | 0.9 | -20% | -1% (2018) | +171% | +205% | -10% |
| En iyi 5, ters volatilite ağırlık, 1x | 2021-01-05 | 26,324 | +75% | 1.69 | -43% | +22% (2024) | +235% | +997% | -39% |
| En iyi 5, HRP ağırlık, 1x | 2021-01-05 | 3,152 | +22% | 1.18 | -16% | +4% (2022) | +155% | +178% | -1% |
| Rastgele 5 strateji (300 deneme), 1x — medyan | – | 6,386 | – | 1.18 (p10–p90: 0.74–1.62) | -28% | – | – | – | – |
|  | En iyi 5'in Sharpe'ı 1.57: rastgele portföylerin %86'inden iyi |  |  |  |  |  |  |  |  |
| Karşılaştırma: BTC al-tut | 2018-01-12 | 5,895 | +22% | 0.64 | -77% | -72% (2018) | +121% | +28% | -52% |

## Likidasyon tamponu (matematik, test gerekmez)

Kural: likidasyon mesafesi ≥ 2.0 × felaket stop mesafesi → **en fazla 4.08x**.

| Kaldıraç | Likidasyon mesafesi | Kurala uygun | −%30 gap'te hayatta |
|---|---|---|---|
| 1x | %99.5 | ✓ | ✓ |
| 2x | %49.5 | ✓ | ✓ |
| 3x | %32.8 | ✓ | ✓ |
| 5x | %19.5 | ✗ | ✗ |
| 10x | %9.5 | ✗ | ✗ |
| 20x | %4.5 | ✗ | ✗ |

## Zayıf yönler

- Portföy, aynı geçmişte seçilmiş üyelerden oluşur; korumasız sonuç iyimserdir. Korumanın **farkı** daha güvenilirdir.
- Bar verisi kullanılır: bar içindeki ani iğneler (wick) ve borsa kesintileri modellenmez.
- Kriz sayısı az (en fazla 6). 'Krizlerin 2/3'ü' kuralı küçük örneklemle çalışır.
- Monte Carlo blokları geçmişten alınır; geçmişte hiç olmamış bir şok kapsanmaz.