# Çekirdek çalışma — 1d

Sabit ayarlı 6 kural × 3 portföy = **18 deneme** (ayar taraması yok). Kabul kuralları sonuçlardan önce yazıldı (`config/core.yaml`): her ileri pencerede aynı varlığın al-tutuna göre düşüş ≥ 1/3 az, Sharpe en fazla 0.10 düşük, getiri pozitif.

## BTC

| Kural | Tüm geçmiş $1000 → | Yıllık | Sharpe | Maks. düşüş | 2022-10 → $ | 2023-10 → $ | 2024-10 → $ | 2022-10 DD | 2023-10 DD | 2024-10 DD | Onay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Al-tut | 5,735 | +22% | 0.63 | -81% | 3,929 | 2,705 | 1,139 | -53% | -53% | -53% | – |
| Volatilite hedefi %40 | 5,596 | +22% | 0.67 | -65% | 3,212 | 2,475 | 1,063 | -52% | -52% | -52% | ❌ |
| Trend (SMA200) | 10,891 | +31% | 0.85 | -64% | 3,237 | 2,483 | 1,274 | -32% | -32% | -32% | ✅ |
| Zaman serisi momentumu (30/90/180g) | 11,249 | +32% | 0.9 | -51% | 3,140 | 2,612 | 1,390 | -26% | -26% | -26% | ✅ |
| Momentum + vol hedefi | 6,999 | +25% | 0.95 | -39% | 2,649 | 2,431 | 1,305 | -25% | -25% | -25% | ✅ |
| SMA200 + momentum + vol hedefi | 7,189 | +25% | 0.9 | -45% | 2,859 | 2,447 | 1,284 | -25% | -25% | -25% | ✅ |

## ETH

| Kural | Tüm geçmiş $1000 → | Yıllık | Sharpe | Maks. düşüş | 2022-10 → $ | 2023-10 → $ | 2024-10 → $ | 2022-10 DD | 2023-10 DD | 2024-10 DD | Onay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Al-tut | 2,981 | +13% | 0.57 | -94% | 1,693 | 1,440 | 865 | -68% | -68% | -68% | – |
| Volatilite hedefi %40 | 3,844 | +16% | 0.57 | -71% | 2,011 | 1,655 | 880 | -56% | -56% | -56% | ❌ |
| Trend (SMA200) | 16,514 | +37% | 0.85 | -74% | 2,169 | 1,831 | 1,096 | -39% | -39% | -39% | ✅ |
| Zaman serisi momentumu (30/90/180g) | 11,854 | +32% | 0.79 | -64% | 1,571 | 1,656 | 1,142 | -40% | -40% | -37% | ✅ |
| Momentum + vol hedefi | 6,895 | +24% | 0.91 | -31% | 1,589 | 1,625 | 1,034 | -27% | -27% | -27% | ✅ |
| SMA200 + momentum + vol hedefi | 9,926 | +30% | 1.0 | -38% | 2,031 | 1,805 | 1,045 | -28% | -28% | -28% | ✅ |

## BTC+ETH

| Kural | Tüm geçmiş $1000 → | Yıllık | Sharpe | Maks. düşüş | 2022-10 → $ | 2023-10 → $ | 2024-10 → $ | 2022-10 DD | 2023-10 DD | 2024-10 DD | Onay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Al-tut | 5,322 | +21% | 0.63 | -88% | 2,752 | 2,089 | 1,033 | -60% | -60% | -60% | – |
| Volatilite hedefi %40 | 4,983 | +20% | 0.65 | -63% | 2,619 | 2,076 | 982 | -53% | -53% | -53% | ❌ |
| Trend (SMA200) | 16,866 | +38% | 0.94 | -62% | 2,781 | 2,228 | 1,216 | -29% | -29% | -29% | ✅ |
| Zaman serisi momentumu (30/90/180g) | 13,553 | +34% | 0.91 | -56% | 2,305 | 2,148 | 1,285 | -30% | -30% | -30% | ✅ |
| Momentum + vol hedefi | 7,291 | +25% | 1.0 | -35% | 2,096 | 2,024 | 1,172 | -26% | -26% | -26% | ✅ |
| SMA200 + momentum + vol hedefi | 9,017 | +28% | 1.04 | -38% | 2,480 | 2,156 | 1,175 | -21% | -21% | -21% | ✅ |

## Zayıf yönler

- Kurallar literatürden; ama kriptoda bu literatür kısa (2014 sonrası). Ayarlar (200 gün, 30/90/180 gün, %40) standart değerlerdir, kriptoya göre seçilmedi.
- Sadece BTC/ETH: alt-coin getirisi yok; buna karşılık survivorship riski çok düşük.
- Spot varsayımı: perp ile yapılırsa funding maliyeti eklenir.
- Üç ileri pencere iç içedir (2022 penceresi 2023 ve 2024'ü de içerir); bağımsız üç test değildir.