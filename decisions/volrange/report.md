# H077 — opsiyon beklenen aralığı dışına çıkınca geri dönüş (videodaki strateji)

Tarih: 2026-10-25. Kurallar sonuçlardan ÖNCE yazıldı: `config/volrange.yaml` (commit `f8f3d1a`). Deneme: **240**.

## Varlık başına en iyi 3 ayar (keşif dönemi kâr faktörüne göre) ve kilitli son 2 yıl

| Varlık | Ayar | Keşif: işlem / kazanma / başa baş / en kötü işlem / yıllık / toparlanma | Kilitli 2 yıl: işlem / kazanma / en kötü / yıllık | DSR | Kalan | Aday |
|---|---|---|---|---|---|---|
| SPX | `k=1.0,n=5,max_hold=10,stop=none,side=long` | 250 / 60% / 54% / -11.9% / +2.2% / 5027 g | 14 / 79% / -7.3% / +2.6% | 0.007 | D3,D4,D6 | — |
| SPX | `k=1.0,n=5,max_hold=5,stop=none,side=long` | 290 / 56% / 51% / -11.5% / +2.2% / 3233 g | 17 / 76% / -11.4% / +1.0% | 0.01 | D2,D3,D4,D6,H | — |
| SPX | `k=2.0,n=5,max_hold=10,stop=none,side=long` | 45 / 51% / 47% / -11.5% / +0.2% / 5277 g | 1 / 100% / +6.3% / +3.1% | 0.0 | D2,D3,D6,H | — |
| NDX | `k=2.0,n=5,max_hold=10,stop=none,side=long` | 35 / 54% / 40% / -11.9% / +1.8% / 4125 g | 3 / 33% / -4.4% / -0.1% | 0.031 | D6,H | — |
| NDX | `k=2.0,n=5,max_hold=10,stop=none,side=both` | 45 / 51% / 39% / -11.9% / +1.6% / 4129 g | 3 / 33% / -4.4% / -0.1% | 0.025 | D4,D6,H | — |
| NDX | `k=2.0,n=5,max_hold=5,stop=none,side=long` | 38 / 58% / 49% / -14.1% / +1.0% / 4129 g | 3 / 67% / -2.0% / +3.7% | 0.014 | D3,D6,H | — |
| XAU | `k=2.0,n=5,max_hold=5,stop=none,side=both` | 52 / 44% / 49% / -5.3% / -0.4% / 5135 g | 12 / 58% / -5.7% / +9.6% | 0.0 | D2,D3,D4,D6 | — |
| XAU | `k=1.0,n=5,max_hold=10,stop=none,side=long` | 133 / 52% / 57% / -10.7% / -1.9% / 4710 g | 19 / 74% / -5.5% / +10.8% | 0.0 | D2,D3,D4,D6 | — |
| XAU | `k=1.0,n=5,max_hold=10,stop=em2,side=long` | 140 / 52% / 57% / -9.6% / -2.4% / 4710 g | 19 / 74% / -5.5% / +10.8% | 0.0 | D2,D3,D4,D6 | — |
| BTC | `k=1.0,n=5,max_hold=5,stop=none,side=long` | 45 / 62% / 58% / -28.3% / +1.8% / 918 g | 27 / 44% / -13.9% / -16.1% | 0.049 | D2,D3,D4,D6,H | — |
| BTC | `k=1.0,n=5,max_hold=5,stop=em2,side=long` | 47 / 62% / 61% / -27.7% / -3.1% / 1282 g | 30 / 50% / -11.7% / -14.4% | 0.028 | D2,D3,D4,D6,H | — |
| BTC | `k=1.0,n=5,max_hold=10,stop=none,side=long` | 38 / 50% / 49% / -30.4% / -5.6% / 959 g | 22 / 45% / -17.1% / -16.9% | 0.022 | D2,D3,D6,H | — |
| ETH | `k=1.0,n=5,max_hold=5,stop=none,side=long` | 50 / 54% / 51% / -29.4% / -0.5% / 1043 g | 31 / 52% / -16.2% / -8.8% | 0.029 | D2,D3,D6,H | — |
| ETH | `k=1.0,n=5,max_hold=5,stop=em2,side=long` | 52 / 52% / 50% / -23.2% / -1.7% / 1043 g | 33 / 45% / -18.6% / -25.8% | 0.026 | D2,D3,D6,H | — |
| ETH | `k=1.0,n=5,max_hold=10,stop=none,side=long` | 41 / 44% / 45% / -31.8% / -10.4% / 1035 g | 24 / 38% / -21.2% / -25.3% | 0.012 | D2,D3,D6,H | — |

**Aday (tüm kontroller + kilitli 2 yıl): 0.** Sahibin hedefini (yıllık ≥ %25, toparlanma ≤ 600 gün) iki dönemde de karşılayan: 0.
Keşifte %100 kazanma oranı (≥ 10 işlem) gösteren ayar: 0.

## Al-tut (aynı dönemler)

| Varlık | Keşif yıllık | Kilitli 2 yıl yıllık |
|---|---|---|
| SPX | +8.3% | +14.2% |
| NDX | +8.8% | +19.2% |
| XAU | +6.8% | +20.2% |
| BTC | +7.0% | +10.2% |
| ETH | +13.9% | -3.3% |

## Zayıf yönler

- Endeks ve altın için fiyat vekili (^GSPC, ^NDX, GLD); oynaklık endeksi kapanışı fiyat kapanışıyla aynı saatte değildir.
- Kripto DVOL 2021'den başlar; keşif dönemi kısa (yaklaşık 3,5 yıl).
- Stopsuz ayarlarda tek bir kötü işlem uzun toparlanma yaratabilir; en kötü işlem sütununa bakın.
- Aday bile karar değildir: yeni hipotez id + karar kapısı + ileri kayıt gerekir.
