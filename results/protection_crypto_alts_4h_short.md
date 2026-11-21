# Kasa koruma testi — crypto_alts 4h

Portföy: arenadaki **100 aktif üye**, eşit ağırlık, coin başı en fazla %20. Kabul kuralları sonuçlardan önce yazıldı (`config/arena.yaml` → `protection.accept`). Bir koruma sadece **komşu eşiklerin hepsinde** ve **her zaman diliminde** geçerse açılır.

## Korumasız portföy

Tüm geçmiş: CAGR +15.4%, Sharpe 1.292, maks. düşüş -21.0%, günlük CVaR95 -1.0%. Coin sınırı olmadan: maks. düşüş -26.0%.

Monte Carlo (1 yıl): P(düşüş ≤ −%50) = 0.0%, medyan +14%, kötü %5 -4%.

| Kriz | Getiri | Maks. düşüş |
|---|---|---|
| covid_2020 | -0.4% | -2.4% |
| may_2021 | +10.4% | -5.3% |
| luna_2022 | +12.0% | -3.3% |
| ftx_2022 | +5.7% | -4.4% |
| aug_2024 | +7.8% | -2.9% |
| oct_2025 | +3.4% | -0.7% |

## Kasa düşüş sigortası — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| (0.08, 0.16) | +13.9% | 1.282 | -14.3% | 1/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.1, 0.2) | +14.2% | 1.287 | -16.8% | 1/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.12, 0.25) | +15.0% | 1.327 | -16.6% | 1/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |

## Volatilite hedefi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.25 | +15.4% | 1.298 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.35 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.5 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |

## Kasa eğrisi filtresi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 30 | +9.6% | 0.913 | -17.6% | 1/6 | ✗✓✗✗ | kaldı |
| 60 | +9.9% | 0.942 | -14.9% | 2/6 | ✗✓✗✗ | kaldı |
| 90 | +11.7% | 1.094 | -12.5% | 1/6 | ✗✓✗✓ | kaldı |

## Günlük kayıp limiti — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.04 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.05 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.07 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |

## BTC çöküş bekçisi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.08 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.1 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |
| 0.15 | +15.4% | 1.292 | -21.0% | 0/6 | ✗✗✓✓ | kaldı |

## Felaket stopu — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.1 | +15.5% | 1.304 | -20.4% | 0/6 | ✗✓✓✓ | kaldı |
| 0.12 | +15.5% | 1.304 | -20.5% | 0/6 | ✗✓✓✓ | kaldı |
| 0.15 | +15.5% | 1.305 | -20.4% | 0/6 | ✗✓✓✓ | kaldı |

## Portföy seçenekleri ($1000 ile başlangıç, maliyet ve funding dahil)

| Portföy | Başlangıç | Bugün ($) | Yıllık | Sharpe | Maks. düşüş | En kötü yıl | Son 3y | Son 5y | En kötü kriz |
|---|---|---|---|---|---|---|---|---|---|
| Hepsi eşit ağırlık (100 strateji), 1x | 2018-01-29 | 3,539 | +16% | 1.3 | -21% | -7% (2020) | +109% | +239% | -5% |
| En iyi 10 (farklı coin), 1x | 2018-02-02 | 6,243 | +23% | 1.23 | -36% | -18% (2020) | +170% | +427% | -10% |
| En iyi 5 (farklı coin), 1x | 2020-09-11 | 6,563 | +36% | 1.24 | -44% | -27% (2021) | +247% | +855% | -18% |
| En iyi 5 (farklı coin), 2x | 2020-09-11 | 27,172 | +71% | 1.24 | -72% | -54% (2021) | +965% | +7136% | -34% |
| En iyi 5 (farklı coin), 3x | 2020-09-11 | 71,185 | +100% | 1.24 | -88% | -75% (2021) | +2809% | +43668% | -49% |
| En iyi 5, 3x + düşüş sigortası (−%10 yarım / −%20 nakit) | 2020-09-11 | 3,250 | +21% | 0.7 | -64% | -57% (2020) | +492% | +658% | -10% |
| En iyi 5, 3x + volatilite hedefi %35 | 2020-09-11 | 21,211 | +64% | 1.44 | -61% | -38% (2020) | +769% | +4827% | -14% |
| En iyi 10, ters volatilite ağırlık, 1x | 2018-02-02 | 10,194 | +30% | 1.51 | -28% | -13% (2020) | +167% | +460% | -8% |
| En iyi 10, HRP ağırlık, 1x | 2018-02-02 | 1,229 | +2% | 0.26 | -16% | -9% (2020) | +41% | +45% | -3% |
| En iyi 5, ters volatilite ağırlık, 1x | 2020-09-11 | 11,512 | +49% | 1.66 | -27% | -14% (2021) | +271% | +1042% | -13% |
| En iyi 5, HRP ağırlık, 1x | 2020-09-11 | 3,228 | +21% | 1.19 | -21% | -14% (2020) | +213% | +277% | -4% |
| Rastgele 5 strateji (300 deneme), 1x — medyan | – | 3,057 | – | 0.8 (p10–p90: 0.44–1.18) | -38% | – | – | – | – |
|  | En iyi 5'in Sharpe'ı 1.24: rastgele portföylerin %94'inden iyi |  |  |  |  |  |  |  |  |
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