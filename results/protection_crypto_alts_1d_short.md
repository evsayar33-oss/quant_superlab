# Kasa koruma testi — crypto_alts 1d

Portföy: arenadaki **42 aktif üye**, eşit ağırlık, coin başı en fazla %20. Kabul kuralları sonuçlardan önce yazıldı (`config/arena.yaml` → `protection.accept`). Bir koruma sadece **komşu eşiklerin hepsinde** ve **her zaman diliminde** geçerse açılır.

## Korumasız portföy

Tüm geçmiş: CAGR +14.2%, Sharpe 0.894, maks. düşüş -40.2%, günlük CVaR95 -1.8%. Coin sınırı olmadan: maks. düşüş -49.8%.

Monte Carlo (1 yıl): P(düşüş ≤ −%50) = 0.0%, medyan +13%, kötü %5 -11%.

| Kriz | Getiri | Maks. düşüş |
|---|---|---|
| covid_2020 | +2.5% | -9.1% |
| may_2021 | +11.3% | -9.9% |
| luna_2022 | +24.3% | -8.5% |
| ftx_2022 | +10.9% | -4.2% |
| aug_2024 | +6.4% | -4.1% |
| oct_2025 | +13.1% | -2.1% |

## Kasa düşüş sigortası — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| (0.08, 0.16) | +11.3% | 0.967 | -19.5% | 2/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.1, 0.2) | +12.0% | 0.959 | -21.0% | 2/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |
| (0.12, 0.25) | +11.5% | 0.908 | -26.1% | 1/6 | ✗✓✓✓ | kaldı |
|  | MC P(≤−%50): 0.0% (korumasız 0.0%) |  |  |  |  |  |

## Volatilite hedefi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.25 | +14.1% | 0.95 | -36.1% | 4/6 | ✗✓✓✓ | kaldı |
| 0.35 | +14.2% | 0.917 | -38.7% | 4/6 | ✗✓✓✓ | kaldı |
| 0.5 | +14.2% | 0.894 | -40.2% | 0/6 | ✗✗✓✓ | kaldı |

## Kasa eğrisi filtresi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 30 | +10.7% | 0.769 | -27.0% | 1/6 | ✗✓✗✓ | kaldı |
| 60 | +11.4% | 0.818 | -29.4% | 0/6 | ✗✓✓✓ | kaldı |
| 90 | +11.7% | 0.833 | -24.3% | 0/6 | ✗✓✓✓ | kaldı |

## Günlük kayıp limiti — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.04 | +14.1% | 0.89 | -40.6% | 0/6 | ✗✗✓✓ | kaldı |
| 0.05 | +14.2% | 0.894 | -40.2% | 0/6 | ✗✗✓✓ | kaldı |
| 0.07 | +14.2% | 0.894 | -40.2% | 0/6 | ✗✗✓✓ | kaldı |

## BTC çöküş bekçisi — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.08 | +14.2% | 0.894 | -40.2% | 0/6 | ✗✗✓✓ | kaldı |
| 0.1 | +14.2% | 0.894 | -40.2% | 0/6 | ✗✗✓✓ | kaldı |
| 0.15 | +14.2% | 0.894 | -40.2% | 0/6 | ✗✗✓✓ | kaldı |

## Felaket stopu — ❌ GEÇMEDİ

| Eşik | CAGR | Sharpe | Maks. düşüş | Krizlerde daha az düşüş | Kriz/DD/Sharpe/CAGR | Sonuç |
|---|---|---|---|---|---|---|
| 0.1 | +13.6% | 0.868 | -41.1% | 1/6 | ✗✗✓✓ | kaldı |
| 0.12 | +13.2% | 0.847 | -42.2% | 1/6 | ✗✗✓✓ | kaldı |
| 0.15 | +14.1% | 0.889 | -39.7% | 1/6 | ✗✓✓✓ | kaldı |

## Portföy seçenekleri ($1000 ile başlangıç, maliyet ve funding dahil)

| Portföy | Başlangıç | Bugün ($) | Yıllık | Sharpe | Maks. düşüş | En kötü yıl | Son 3y | Son 5y | En kötü kriz |
|---|---|---|---|---|---|---|---|---|---|
| Hepsi eşit ağırlık (42 strateji), 1x | 2018-07-30 | 3,223 | +15% | 0.92 | -40% | -18% (2020) | +149% | +378% | -10% |
| En iyi 10 (farklı coin), 1x | 2018-09-25 | 2,014 | +9% | 0.46 | -86% | -52% (2020) | +235% | +826% | -11% |
| En iyi 5 (farklı coin), 1x | 2020-09-16 | 4,632 | +28% | 0.92 | -70% | -60% (2021) | +324% | +1329% | -19% |
| En iyi 5 (farklı coin), 2x | 2020-09-16 | 11,155 | +48% | 0.92 | -93% | -87% (2021) | +1401% | +13160% | -37% |
| En iyi 5 (farklı coin), 3x | 2020-09-16 | 13,829 | +54% | 0.92 | -99% | -97% (2021) | +4351% | +81330% | -54% |
| En iyi 5, 3x + düşüş sigortası (−%10 yarım / −%20 nakit) | 2020-09-16 | 2,054 | +12% | 0.53 | -40% | -23% (2020) | +168% | +168% | -12% |
| En iyi 5, 3x + volatilite hedefi %35 | 2020-09-16 | 10,728 | +47% | 1.1 | -73% | -50% (2021) | +788% | +3938% | -15% |
| En iyi 10, ters volatilite ağırlık, 1x | 2018-09-25 | 1,884 | +8% | 0.42 | -88% | -51% (2020) | +348% | +849% | -21% |
| En iyi 10, HRP ağırlık, 1x | 2018-09-25 | 3,447 | +16% | 1.11 | -18% | -9% (2020) | +148% | +278% | -4% |
| En iyi 5, ters volatilite ağırlık, 1x | 2020-09-16 | 2,181 | +14% | 0.52 | -87% | -82% (2021) | +402% | +1360% | -38% |
| En iyi 5, HRP ağırlık, 1x | 2020-09-16 | 4,158 | +26% | 1.26 | -18% | -14% (2021) | +284% | +405% | -12% |
| Rastgele 5 strateji (300 deneme), 1x — medyan | – | 2,766 | – | 0.69 (p10–p90: 0.28–1.0) | -52% | – | – | – | – |
|  | En iyi 5'in Sharpe'ı 0.92: rastgele portföylerin %83'inden iyi |  |  |  |  |  |  |  |  |
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