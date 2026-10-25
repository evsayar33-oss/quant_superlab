# H063–H065 kaldıraç testi

Kural sonuçlardan ÖNCE yazıldı (`config/watch.yaml`): en yüksek kaldıraç seçilir, şu şartla: tüm geçmişte VE her pencerede maks. düşüş ≥ %-40, hiçbir gün %-25'ten kötü değil, kasa hiç sıfırlanmamış.

## H063 — Metal Vortex(28) + SMC order block (long)

Seçilen kaldıraç: **5x**

| Kaldıraç | Tüm geçmiş: $1000 → | Yıllık | Sharpe | Maks. düşüş | En kötü gün | 2022-10-21 → bugün yıllık / DD | 2023-10-21 → bugün yıllık / DD | 2024-10-21 → bugün yıllık / DD |
|---|---|---|---|---|---|---|---|---|
| 1x | 2,444 | +3% | 0.958 | -6% | -3% | +6% / -3% | +5% / -3% | +7% / -3% |
| 2x | 5,777 | +7% | 0.958 | -11% | -6% | +11% / -6% | +11% / -6% | +14% / -6% |
| 3x | 13,204 | +10% | 0.958 | -17% | -10% | +17% / -9% | +17% / -9% | +21% / -9% |
| 4x | 29,190 | +13% | 0.958 | -22% | -13% | +23% / -12% | +23% / -12% | +28% / -12% |
| 5x | 62,422 | +17% | 0.958 | -27% | -16% | +30% / -15% | +29% / -15% | +35% / -15% |
| vol hedefi %20 (ort. 4.67x) | 30,801 | +14% | 0.928 | -26% | -9% | +23% / -14% | +25% / -14% | +29% / -12% |
| al-tut | 12,602 | +10% | 0.525 | -54% | -22% | +17% / -34% | +24% / -34% | +24% / -34% |

## H064 — Metal 52 hafta zirvesi + SMC BOS (iki yön)

Seçilen kaldıraç: **4x**

| Kaldıraç | Tüm geçmiş: $1000 → | Yıllık | Sharpe | Maks. düşüş | En kötü gün | 2022-10-21 → bugün yıllık / DD | 2023-10-21 → bugün yıllık / DD | 2024-10-21 → bugün yıllık / DD |
|---|---|---|---|---|---|---|---|---|
| 1x | 1,947 | +3% | 0.637 | -8% | -5% | +6% / -8% | +8% / -8% | +9% / -8% |
| 2x | 3,627 | +5% | 0.637 | -16% | -10% | +11% / -16% | +16% / -16% | +18% / -16% |
| 3x | 6,464 | +7% | 0.637 | -23% | -16% | +16% / -23% | +23% / -23% | +27% / -23% |
| 4x | 11,011 | +9% | 0.637 | -30% | -21% | +21% / -30% | +31% / -30% | +35% / -30% |
| 5x | 17,912 | +11% | 0.637 | -37% | -26% | +25% / -37% | +38% / -37% | +42% / -37% |
| vol hedefi %20 (ort. 4.65x) | 10,106 | +9% | 0.718 | -29% | -8% | +20% / -16% | +31% / -16% | +32% / -16% |
| al-tut | 12,602 | +10% | 0.525 | -54% | -22% | +17% / -34% | +24% / -34% | +24% / -34% |

## H065 — Endeks IBS ortalamaya dönüş + SMA200 (long)

Seçilen kaldıraç: **4x**

| Kaldıraç | Tüm geçmiş: $1000 → | Yıllık | Sharpe | Maks. düşüş | En kötü gün | 2022-10-21 → bugün yıllık / DD | 2023-10-21 → bugün yıllık / DD | 2024-10-21 → bugün yıllık / DD |
|---|---|---|---|---|---|---|---|---|
| 1x | 2,447 | +3% | 0.643 | -9% | -5% | +8% / -6% | +10% / -4% | +8% / -4% |
| 2x | 5,518 | +7% | 0.643 | -18% | -10% | +16% / -11% | +20% / -8% | +17% / -8% |
| 3x | 11,466 | +10% | 0.643 | -26% | -14% | +24% / -17% | +30% / -12% | +25% / -12% |
| 4x | 21,935 | +13% | 0.643 | -35% | -19% | +33% / -22% | +40% / -16% | +34% / -16% |
| 5x | 38,607 | +15% | 0.643 | -43% | -24% | +41% / -27% | +51% / -20% | +42% / -20% |
| vol hedefi %20 (ort. 3.94x) | 9,582 | +9% | 0.528 | -37% | -19% | +23% / -20% | +28% / -14% | +23% / -14% |
| al-tut | 4,533 | +6% | 0.381 | -64% | -11% | +21% / -20% | +23% / -20% | +17% / -20% |

## Zayıf yönler

- Kaldıraç kenar yaratmaz; kârı ve zararı aynı oranda büyütür. Sharpe değişmez.
- Geçmişteki en kötü düşüş, gelecekteki en kötü düşüş değildir. Seçilen kaldıraç bu yüzden bir üst sınırdır, hedef değil.
- Vadeli işlem kontrat büyüklüğü hesaba katılmadı (küçük kasada mikro kontrat gerekir). Roll maliyeti modellenmedi.
- Bu üç fikir binlerce aday içinden seçildi. Paper kayıt gerçek testtir.
