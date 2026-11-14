# Kasa koruma testi — crypto_alts 4h

Portföy: arenadaki **74 aktif üye**, eşit ağırlık, coin başı en fazla %20. Kabul kuralları sonuçlardan önce yazıldı (`config/arena.yaml` → `protection.accept`). Bir koruma sadece **komşu eşiklerin hepsinde** ve **her zaman diliminde** geçerse açılır.

## Korumasız portföy

Tüm geçmiş: CAGR +30.4%, Sharpe 2.171, maks. düşüş -7.0%, günlük CVaR95 -1.1%. Coin sınırı olmadan: maks. düşüş -11.7%.

Monte Carlo (1 yıl): P(düşüş ≤ −%50) = 0.0%, medyan +29%, kötü %5 +7%.

| Kriz | Getiri | Maks. düşüş |
|---|---|---|
| covid_2020 | +1.8% | -4.4% |
| may_2021 | -1.0% | -4.0% |
| luna_2022 | +8.0% | -3.0% |
| ftx_2022 | -0.5% | -3.9% |
| aug_2024 | +5.5% | -2.1% |
| oct_2025 | +2.7% | -1.4% |

## Kasa düşüş sigortası — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| (0.08, 0.16) | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.1, 0.2) | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.12, 0.25) | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |

## Volatilite hedefi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.25 | +30.3% | 2.17 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.35 | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.5 | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |

## Kasa eğrisi filtresi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 30 | +18.1% | 1.484 | -11.3% | 1/6 | ✗✗✗✗ | kaldı |
| 60 | +22.3% | 1.75 | -10.9% | 1/6 | ✗✗✗✗ | kaldı |
| 90 | +24.4% | 1.875 | -10.8% | 0/6 | ✗✗✗✓ | kaldı |

## Günlük kayıp limiti — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.04 | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.05 | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.07 | +30.4% | 2.171 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |

## BTC çöküş bekçisi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.08 | +29.7% | 2.13 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.1 | +29.8% | 2.135 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.15 | +30.1% | 2.154 | -7.0% | 0/6 | ✗✗✓✓ | kaldı |

## Felaket stopu — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.1 | +29.7% | 2.144 | -7.0% | 2/6 | ✗✗✓✓ | kaldı |
| 0.12 | +29.6% | 2.133 | -7.0% | 1/6 | ✗✗✓✓ | kaldı |
| 0.15 | +30.0% | 2.155 | -7.0% | 1/6 | ✗✗✓✓ | kaldı |

## Portföy seçenekleri ($1000 ile başlangıç, maliyet ve funding dahil)

| Portföy | Başlangıç | Bugün ($) | Yıllık | Sharpe | Maks. düşüş | En kötü yıl | Son 3y | Son 5y | En kötü kriz |
|---|---|---|---|---|---|---|---|---|---|
| Hepsi eşit ağırlık (74 strateji), 1x | 2018-01-17 | 10,418 | +31% | 2.18 | -7% | +14% (2018) | +165% | +262% | -4% |
| En iyi 10 (farklı coin), 1x | 2018-02-21 | 39,121 | +52% | 2.31 | -14% | +13% (2019) | +345% | +585% | -9% |
| En iyi 5 (farklı coin), 1x | 2018-02-21 | 77,779 | +65% | 2.11 | -25% | -7% (2022) | +477% | +598% | -7% |
| En iyi 5 (farklı coin), 2x | 2018-02-21 | 3,510,258 | +156% | 2.11 | -45% | -16% (2022) | +2799% | +3906% | -14% |
| En iyi 5 (farklı coin), 3x | 2018-02-21 | 92,590,461 | +272% | 2.11 | -60% | -25% (2022) | +12595% | +18850% | -21% |
| En iyi 5, 3x + düşüş sigortası (−%10 yarım / −%20 nakit) | 2018-02-21 | 215,608 | +86% | 1.43 | -61% | -50% (2019) | +1540% | +1657% | -11% |
| En iyi 5, 3x + volatilite hedefi %35 | 2018-02-21 | 1,344,743 | +129% | 2.25 | -48% | -10% (2022) | +2352% | +4613% | -20% |
| En iyi 10, ters volatilite ağırlık, 1x | 2018-02-21 | 40,893 | +53% | 2.35 | -14% | +2% (2022) | +376% | +502% | -6% |
| En iyi 10, HRP ağırlık, 1x | 2018-02-21 | 5,468 | +22% | 1.03 | -28% | -6% (2020) | +305% | +430% | -2% |
| En iyi 5, ters volatilite ağırlık, 1x | 2018-02-21 | 102,711 | +70% | 2.17 | -28% | -15% (2022) | +637% | +626% | -7% |
| En iyi 5, HRP ağırlık, 1x | 2018-02-21 | 5,281 | +21% | 0.99 | -25% | -11% (2020) | +388% | +479% | -3% |
| Rastgele 5 strateji (300 deneme), 1x — medyan | – | 8,604 | – | 1.27 (p10–p90: 0.79–1.6) | -26% | – | – | – | – |
|  | En iyi 5'in Sharpe'ı 2.11: rastgele portföylerin %100'inden iyi |  |  |  |  |  |  |  |  |
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