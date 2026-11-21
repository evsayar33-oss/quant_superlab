# Kasa koruma testi — crypto_alts 1d

Portföy: arenadaki **63 aktif üye**, eşit ağırlık, coin başı en fazla %20. Kabul kuralları sonuçlardan önce yazıldı (`config/arena.yaml` → `protection.accept`). Bir koruma sadece **komşu eşiklerin hepsinde** ve **her zaman diliminde** geçerse açılır.

## Korumasız portföy

Tüm geçmiş: CAGR +27.7%, Sharpe 2.029, maks. düşüş -12.9%, günlük CVaR95 -1.4%. Coin sınırı olmadan: maks. düşüş -15.1%.

Monte Carlo (1 yıl): P(düşüş ≤ −%50) = 0.0%, medyan +28%, kötü %5 +4%.

| Kriz | Getiri | Maks. düşüş |
|---|---|---|
| covid_2020 | +1.7% | -4.3% |
| may_2021 | +0.2% | -5.0% |
| luna_2022 | +2.9% | -3.3% |
| ftx_2022 | -3.8% | -4.1% |
| aug_2024 | -1.7% | -2.9% |
| oct_2025 | -1.7% | -3.2% |

## Kasa düşüş sigortası — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| (0.08, 0.16) | +26.4% | 2.023 | -10.4% | 0/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.1, 0.2) | +27.3% | 2.019 | -11.6% | 0/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.12, 0.25) | +27.2% | 2.012 | -12.6% | 0/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |

## Volatilite hedefi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.25 | +27.7% | 2.029 | -12.9% | 0/6 | ✗✗✓✓ | kaldı |
| 0.35 | +27.7% | 2.029 | -12.9% | 0/6 | ✗✗✓✓ | kaldı |
| 0.5 | +27.7% | 2.029 | -12.9% | 0/6 | ✗✗✓✓ | kaldı |

## Kasa eğrisi filtresi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 30 | +17.2% | 1.529 | -12.8% | 5/6 | ✓✓✗✗ | kaldı |
| 60 | +20.4% | 1.711 | -12.4% | 0/6 | ✗✓✗✗ | kaldı |
| 90 | +22.4% | 1.818 | -15.0% | 0/6 | ✗✗✗✓ | kaldı |

## Günlük kayıp limiti — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.04 | +27.7% | 2.029 | -12.9% | 0/6 | ✗✗✓✓ | kaldı |
| 0.05 | +27.7% | 2.029 | -12.9% | 0/6 | ✗✗✓✓ | kaldı |
| 0.07 | +27.7% | 2.029 | -12.9% | 0/6 | ✗✗✓✓ | kaldı |

## BTC çöküş bekçisi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.08 | +27.2% | 2.002 | -12.3% | 1/6 | ✗✓✓✓ | kaldı |
| 0.1 | +27.7% | 2.03 | -12.3% | 0/6 | ✗✓✓✓ | kaldı |
| 0.15 | +27.6% | 2.022 | -12.9% | 0/6 | ✗✗✓✓ | kaldı |

## Felaket stopu — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.1 | +25.0% | 1.925 | -13.2% | 4/6 | ✗✗✓✓ | kaldı |
| 0.12 | +25.8% | 1.951 | -12.8% | 4/6 | ✗✓✓✓ | kaldı |
| 0.15 | +25.8% | 1.94 | -12.9% | 3/6 | ✗✗✓✓ | kaldı |

## Portföy seçenekleri ($1000 ile başlangıç, maliyet ve funding dahil)

| Portföy | Başlangıç | Bugün ($) | Yıllık | Sharpe | Maks. düşüş | En kötü yıl | Son 3y | Son 5y | En kötü kriz |
|---|---|---|---|---|---|---|---|---|---|
| Hepsi eşit ağırlık (63 strateji), 1x | 2018-01-29 | 8,692 | +28% | 2.04 | -13% | -2% (2018) | +114% | +156% | -5% |
| En iyi 10 (farklı coin), 1x | 2018-04-01 | 23,119 | +44% | 1.98 | -26% | -7% (2018) | +289% | +420% | -7% |
| En iyi 5 (farklı coin), 1x | 2018-07-18 | 17,505 | +41% | 1.62 | -25% | -15% (2022) | +452% | +482% | -5% |
| En iyi 5 (farklı coin), 2x | 2018-07-18 | 200,067 | +89% | 1.62 | -46% | -29% (2022) | +2497% | +2663% | -10% |
| En iyi 5 (farklı coin), 3x | 2018-07-18 | 1,499,333 | +142% | 1.62 | -62% | -41% (2022) | +10382% | +10678% | -15% |
| En iyi 5, 3x + düşüş sigortası (−%10 yarım / −%20 nakit) | 2018-07-18 | 27,536 | +49% | 1.12 | -54% | -27% (2019) | +1856% | +1507% | -9% |
| En iyi 5, 3x + volatilite hedefi %35 | 2018-07-18 | 68,916 | +67% | 1.5 | -48% | -35% (2022) | +1144% | +1320% | -10% |
| En iyi 10, ters volatilite ağırlık, 1x | 2018-04-01 | 18,310 | +40% | 1.63 | -46% | -38% (2018) | +333% | +537% | -8% |
| En iyi 10, HRP ağırlık, 1x | 2018-04-01 | 3,017 | +14% | 0.83 | -34% | -13% (2022) | +170% | +108% | -8% |
| En iyi 5, ters volatilite ağırlık, 1x | 2018-07-18 | 22,639 | +46% | 1.6 | -31% | -12% (2022) | +547% | +581% | -3% |
| En iyi 5, HRP ağırlık, 1x | 2018-07-18 | 7,798 | +28% | 1.29 | -27% | -13% (2022) | +527% | +551% | -8% |
| Rastgele 5 strateji (300 deneme), 1x — medyan | – | 7,685 | – | 1.16 (p10–p90: 0.8–1.45) | -31% | – | – | – | – |
|  | En iyi 5'in Sharpe'ı 1.62: rastgele portföylerin %98'inden iyi |  |  |  |  |  |  |  |  |
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