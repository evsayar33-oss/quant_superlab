# H070 kaldıraç testi

Kural sonuçlardan ÖNCE yazıldı (`config/watch.yaml`): en yüksek kaldıraç seçilir, şu şartla: tüm geçmişte VE her pencerede maks. düşüş ≥ %-40, hiçbir gün %-25'ten kötü değil, kasa hiç sıfırlanmamış.

## H070 — Endeks IBS ortalamaya dönüş + VIX vade filtresi (long)

Seçilen kaldıraç: **2x**

| Kaldıraç | Tüm geçmiş: $1000 → | Yıllık | Sharpe | Maks. düşüş | En kötü gün | 2022-10-21 → bugün yıllık / DD | 2023-10-21 → bugün yıllık / DD | 2024-10-21 → bugün yıllık / DD |
|---|---|---|---|---|---|---|---|---|
| 1x | 3,087 | +4% | 0.526 | -22% | -5% | +12% / -8% | +12% / -8% | +12% / -7% |
| 2x | 7,718 | +8% | 0.526 | -40% | -10% | +24% / -16% | +23% / -16% | +24% / -14% |
| 3x | 15,610 | +11% | 0.526 | -54% | -15% | +35% / -24% | +35% / -24% | +36% / -21% |
| 4x | 25,504 | +13% | 0.526 | -66% | -21% | +46% / -31% | +46% / -31% | +47% / -28% |
| 5x | 33,581 | +14% | 0.526 | -75% | -26% | +57% / -38% | +57% / -38% | +58% / -35% |
| vol hedefi %20 (ort. 3.08x) | 6,112 | +7% | 0.443 | -51% | -13% | +19% / -22% | +21% / -22% | +21% / -15% |
| al-tut | 4,541 | +6% | 0.381 | -64% | -11% | +21% / -20% | +23% / -20% | +17% / -20% |

## Zayıf yönler

- Kaldıraç kenar yaratmaz; kârı ve zararı aynı oranda büyütür. Sharpe değişmez.
- Geçmişteki en kötü düşüş, gelecekteki en kötü düşüş değildir. Seçilen kaldıraç bu yüzden bir üst sınırdır, hedef değil.
- Vadeli işlem kontrat büyüklüğü hesaba katılmadı (küçük kasada mikro kontrat gerekir). Roll maliyeti modellenmedi.
- Bu üç fikir binlerce aday içinden seçildi. Paper kayıt gerçek testtir.
