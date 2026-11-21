# Kasa koruma testi — crypto_alts 4h

Portföy: arenadaki **100 aktif üye**, eşit ağırlık, coin başı en fazla %20. Kabul kuralları sonuçlardan önce yazıldı (`config/arena.yaml` → `protection.accept`). Bir koruma sadece **komşu eşiklerin hepsinde** ve **her zaman diliminde** geçerse açılır.

## Korumasız portföy

Tüm geçmiş: CAGR +25.8%, Sharpe 2.064, maks. düşüş -7.8%, günlük CVaR95 -1.1%. Coin sınırı olmadan: maks. düşüş -7.8%.

Monte Carlo (1 yıl): P(düşüş ≤ −%50) = 0.0%, medyan +25%, kötü %5 +3%.

| Kriz | Getiri | Maks. düşüş |
|---|---|---|
| covid_2020 | -1.3% | -2.4% |
| may_2021 | -7.0% | -7.3% |
| luna_2022 | -1.8% | -3.3% |
| ftx_2022 | -2.5% | -3.3% |
| aug_2024 | -0.1% | -2.1% |
| oct_2025 | +0.2% | -1.2% |

## Kasa düşüş sigortası — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| (0.08, 0.16) | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.1, 0.2) | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.12, 0.25) | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |

## Volatilite hedefi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.25 | +25.7% | 2.068 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |
| 0.35 | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |
| 0.5 | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |

## Kasa eğrisi filtresi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 30 | +19.5% | 1.695 | -9.8% | 5/6 | ✓✗✗✓ | kaldı |
| 60 | +20.0% | 1.725 | -8.7% | 4/6 | ✗✗✗✓ | kaldı |
| 90 | +20.3% | 1.743 | -11.8% | 3/6 | ✗✗✗✓ | kaldı |

## Günlük kayıp limiti — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.04 | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |
| 0.05 | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |
| 0.07 | +25.8% | 2.064 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |

## BTC çöküş bekçisi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.08 | +23.3% | 1.913 | -9.0% | 1/6 | ✗✗✓✓ | kaldı |
| 0.1 | +23.6% | 1.935 | -9.5% | 0/6 | ✗✗✓✓ | kaldı |
| 0.15 | +24.9% | 2.008 | -7.8% | 0/6 | ✗✗✓✓ | kaldı |

## Felaket stopu — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.1 | +25.2% | 2.035 | -8.6% | 2/6 | ✗✗✓✓ | kaldı |
| 0.12 | +25.2% | 2.035 | -8.2% | 0/6 | ✗✗✓✓ | kaldı |
| 0.15 | +25.4% | 2.046 | -8.3% | 0/6 | ✗✗✓✓ | kaldı |

## Portföy seçenekleri ($1000 ile başlangıç, maliyet ve funding dahil)

| Portföy | Başlangıç | Bugün ($) | Yıllık | Sharpe | Maks. düşüş | En kötü yıl | Son 3y | Son 5y | En kötü kriz |
|---|---|---|---|---|---|---|---|---|---|
| Hepsi eşit ağırlık (100 strateji), 1x | 2018-01-16 | 7,592 | +26% | 2.07 | -8% | -0% (2022) | +109% | +165% | -7% |
| En iyi 10 (farklı coin), 1x | 2018-02-15 | 16,337 | +38% | 1.95 | -12% | -4% (2022) | +165% | +280% | -7% |
| En iyi 5 (farklı coin), 1x | 2018-03-05 | 18,557 | +40% | 1.22 | -49% | -24% (2019) | +197% | +391% | -10% |
| En iyi 5 (farklı coin), 2x | 2018-03-05 | 142,628 | +77% | 1.22 | -80% | -51% (2019) | +688% | +1887% | -19% |
| En iyi 5 (farklı coin), 3x | 2018-03-05 | 445,278 | +102% | 1.22 | -94% | -74% (2019) | +1765% | +6539% | -28% |
| En iyi 5, 3x + düşüş sigortası (−%10 yarım / −%20 nakit) | 2018-03-05 | 12,682 | +34% | 0.92 | -48% | -24% (2022) | +430% | +714% | -3% |
| En iyi 5, 3x + volatilite hedefi %35 | 2018-03-05 | 19,372 | +41% | 1.03 | -57% | -36% (2019) | +455% | +1323% | -25% |
| En iyi 10, ters volatilite ağırlık, 1x | 2018-02-15 | 23,580 | +44% | 2.19 | -17% | -1% (2022) | +192% | +332% | -6% |
| En iyi 10, HRP ağırlık, 1x | 2018-02-15 | 5,271 | +21% | 1.65 | -8% | -2% (2021) | +264% | +438% | -7% |
| En iyi 5, ters volatilite ağırlık, 1x | 2018-03-05 | 35,033 | +51% | 1.45 | -49% | -24% (2019) | +267% | +459% | -10% |
| En iyi 5, HRP ağırlık, 1x | 2018-03-05 | 7,048 | +25% | 1.46 | -18% | -5% (2022) | +413% | +626% | -4% |
| Rastgele 5 strateji (300 deneme), 1x — medyan | – | 5,299 | – | 1.16 (p10–p90: 0.84–1.48) | -22% | – | – | – | – |
|  | En iyi 5'in Sharpe'ı 1.22: rastgele portföylerin %60'inden iyi |  |  |  |  |  |  |  |  |
| Karşılaştırma: BTC al-tut | 2018-01-11 | 5,757 | +22% | 0.63 | -78% | -73% (2018) | +121% | +26% | -55% |

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