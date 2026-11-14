# Çekirdek çalışma — 4h

Sabit ayarlı 6 kural × 3 portföy = **18 deneme** (ayar taraması yok). Kabul kuralları sonuçlardan önce yazıldı (`config/core.yaml`): her ileri pencerede aynı varlığın al-tutuna göre düşüş ≥ 1/3 az, Sharpe en fazla 0.10 düşük, getiri pozitif.

## BTC

| Kural | Tüm geçmiş $1000 → | Yıllık | Sharpe | Maks. düşüş | 2022-10 → $ | 2023-10 → $ | 2024-10 → $ | 2022-10 DD | 2023-10 DD | 2024-10 DD | Onay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Al-tut | 5,721 | +22% | 0.63 | -78% | 4,018 | 2,727 | 1,141 | -53% | -53% | -53% | – |
| Volatilite hedefi %40 | 5,949 | +22% | 0.7 | -66% | 3,360 | 2,476 | 1,088 | -52% | -52% | -52% | ❌ |
| Trend (SMA200) | 12,979 | +34% | 0.9 | -63% | 3,368 | 2,597 | 1,282 | -37% | -37% | -37% | ❌ |
| Zaman serisi momentumu (30/90/180g) | 12,625 | +33% | 0.94 | -49% | 3,372 | 2,693 | 1,384 | -26% | -26% | -26% | ✅ |
| Momentum + vol hedefi | 8,659 | +28% | 1.06 | -38% | 3,014 | 2,600 | 1,358 | -22% | -22% | -22% | ✅ |
| SMA200 + momentum + vol hedefi | 9,253 | +29% | 1.01 | -43% | 3,161 | 2,636 | 1,320 | -30% | -30% | -30% | ✅ |

## ETH

| Kural | Tüm geçmiş $1000 → | Yıllık | Sharpe | Maks. düşüş | 2022-10 → $ | 2023-10 → $ | 2024-10 → $ | 2022-10 DD | 2023-10 DD | 2024-10 DD | Onay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Al-tut | 1,891 | +8% | 0.5 | -94% | 1,742 | 1,427 | 859 | -68% | -68% | -68% | – |
| Volatilite hedefi %40 | 3,029 | +13% | 0.51 | -72% | 1,820 | 1,493 | 870 | -60% | -60% | -60% | ❌ |
| Trend (SMA200) | 27,506 | +46% | 0.96 | -58% | 1,908 | 1,579 | 1,011 | -41% | -41% | -41% | ✅ |
| Zaman serisi momentumu (30/90/180g) | 18,135 | +39% | 0.9 | -55% | 1,578 | 1,653 | 1,075 | -43% | -43% | -42% | ✅ |
| Momentum + vol hedefi | 7,210 | +25% | 0.96 | -31% | 1,580 | 1,629 | 1,052 | -30% | -30% | -30% | ✅ |
| SMA200 + momentum + vol hedefi | 10,717 | +31% | 1.06 | -31% | 1,864 | 1,617 | 1,047 | -29% | -29% | -29% | ✅ |

## BTC+ETH

| Kural | Tüm geçmiş $1000 → | Yıllık | Sharpe | Maks. düşüş | 2022-10 → $ | 2023-10 → $ | 2024-10 → $ | 2022-10 DD | 2023-10 DD | 2024-10 DD | Onay |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Al-tut | 4,100 | +17% | 0.58 | -88% | 2,811 | 2,079 | 1,029 | -60% | -60% | -60% | – |
| Volatilite hedefi %40 | 4,520 | +19% | 0.63 | -65% | 2,542 | 1,968 | 987 | -56% | -56% | -56% | ❌ |
| Trend (SMA200) | 22,578 | +42% | 1.02 | -56% | 2,654 | 2,110 | 1,173 | -32% | -32% | -32% | ✅ |
| Zaman serisi momentumu (30/90/180g) | 17,331 | +38% | 0.99 | -50% | 2,386 | 2,173 | 1,243 | -33% | -33% | -33% | ✅ |
| Momentum + vol hedefi | 8,239 | +27% | 1.08 | -34% | 2,225 | 2,092 | 1,207 | -26% | -26% | -26% | ✅ |
| SMA200 + momentum + vol hedefi | 10,533 | +31% | 1.12 | -36% | 2,492 | 2,113 | 1,194 | -24% | -24% | -24% | ✅ |

## Zayıf yönler

- Kurallar literatürden; ama kriptoda bu literatür kısa (2014 sonrası). Ayarlar (200 gün, 30/90/180 gün, %40) standart değerlerdir, kriptoya göre seçilmedi.
- Sadece BTC/ETH: alt-coin getirisi yok; buna karşılık survivorship riski çok düşük.
- Spot varsayımı: perp ile yapılırsa funding maliyeti eklenir.
- Üç ileri pencere iç içedir (2022 penceresi 2023 ve 2024'ü de içerir); bağımsız üç test değildir.

## H052 varyantları (4 deneme, kabul kuralları önceden yazıldı)

Kabul: tüm geçmişte VE her ileri pencerede Sharpe temel kuraldan (H052) yüksek, maks. düşüş en fazla 5 puan derin. Karşılaştırma aynı zaman diliminde ve ortak dönemde; perp funding her ikisinde de düşüldü.

| Varyant | Sharpe (tüm) | Temel | Maks. düşüş | Temel | 2022-10 SR v/t | 2023-10 SR v/t | 2024-10 SR v/t | Onay |
|---|---|---|---|---|---|---|---|---|
| Daha fazla büyük coin (BTC, ETH, SOL, BNB, XRP) | 0.91 | 1.02 | -35% | -37% | 0.57/0.81 | 0.86/0.88 | 0.5/0.35 | ❌ |
| Düşüşte short (perp) | 0.95 | 1.02 | -42% | -37% | 0.65/0.81 | 0.78/0.88 | 0.42/0.35 | ❌ |
| İşlem yapmama bandı %10 | 1.03 | 1.02 | -38% | -37% | 0.84/0.81 | 0.92/0.88 | 0.4/0.35 | ✅ |
| 1h zaman dilimi | 0.94 | 1.02 | -37% | -37% | 0.73/0.81 | 0.83/0.88 | 0.44/0.35 | ❌ |

## H054 risk seviyeleri (kaldıraç yok; seçim kuralı önceden yazıldı)

Kural: tüm geçmişte ve her ileri pencerede maks. düşüş ≥ -40% kalan EN YÜKSEK hedef.

| Vol hedefi | $1000 → | Yıllık | Sharpe | Maks. düşüş | 2022-10 → $ / DD | 2023-10 → $ / DD | 2024-10 → $ / DD | Sınırda |
|---|---|---|---|---|---|---|---|---|
| %40 | 8,835 | +28% | 1.03 | -38% | 2,254 / -24% | 1,955 / -24% | 1,149 / -24% | ✅ |
| %60 | 12,404 | +33% | 0.97 | -47% | 2,290 / -32% | 1,926 / -32% | 1,118 / -32% | ❌ |
| %80 | 15,663 | +37% | 0.97 | -55% | 2,200 / -33% | 1,835 / -33% | 1,084 / -33% | ❌ |

**Seçilen:** %40

## Funding arbitrajı (spot long + perp short)

Veri (Binance, Bitget için vekil): {'BTCUSDT': ['2020-01-01', '2026-10-31'], 'ETHUSDT': ['2020-01-01', '2026-10-31']}

| Kural | $1000 → | Yıllık | Sharpe | Maks. düşüş | H054 ile korelasyon | 50/50 H054+arb Sharpe | H054 Sharpe | Onay |
|---|---|---|---|---|---|---|---|---|
| always_on | 1,540 | +7% | 10.35 | -0% | 0.078 | 1.3 | 1.1 | ✅ |
|  ↳ 2022-10 → | 1,151 | +4% | 15.52 | -0% | | 0.95 (DD -12%) | 0.83 (DD -23%) | |
|  ↳ 2023-10 → | 1,121 | +4% | 15.64 | -0% | | 1.02 (DD -12%) | 0.9 (DD -23%) | |
|  ↳ 2024-10 → | 1,052 | +3% | 17.29 | -0% | | 0.5 (DD -12%) | 0.4 (DD -23%) | |
| positive_only | 1,432 | +5% | 8.1 | -1% | 0.067 | 1.27 | 1.1 | ✅ |
|  ↳ 2022-10 → | 1,101 | +2% | 8.51 | -0% | | 0.91 (DD -12%) | 0.83 (DD -23%) | |
|  ↳ 2023-10 → | 1,084 | +3% | 9.03 | -0% | | 0.99 (DD -12%) | 0.9 (DD -23%) | |
|  ↳ 2024-10 → | 1,025 | +1% | 6.2 | -0% | | 0.45 (DD -12%) | 0.4 (DD -23%) | |

Sınırlar: spot–perp baz farkı ve Binance/Bitget farkı modellenmez; büyük yükselişte short perp için marjin eklemek gerekir.

## Boştaki nakitle funding arbitrajı (kriter: ileri dönemlerde en yüksek kâr)

H054'ün ortalama boştaki nakdi: %58. Kabul: her ileri pencerede H054'ten fazla kazanmalı, düşüşü en fazla 3 puan derin olmalı. Kabul edilenlerden ileri dönemlerde en çok kazanan seçilir.

| Seçenek | Tüm geçmiş → | Yıllık | Maks. düşüş | 2022-10 → | 2023-10 → | 2024-10 → | Onay |
|---|---|---|---|---|---|---|---|
| H054 tek başına | 6,990 | +33% | -26% | 2,256 | 1,953 | 1,152 | – |
| H054 + boştaki nakitle arbitraj (always_on) | 8,105 | +36% | -24% | 2,299 | 1,985 | 1,165 | ✅ |
| H054 + boştaki nakitle arbitraj (positive_only) | 7,844 | +35% | -26% | 2,270 | 1,970 | 1,158 | ✅ |

**Bot için seçilen:** `idle_always_on`