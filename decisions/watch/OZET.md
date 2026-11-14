# Paper izleme: H063–H065

Başlangıç: 2026-10-22. Son çalışma: 2026-11-14. Sadece sanal para; emir gönderilmez.

UYARI: NAV geçmiş fiyatlardan yeniden hesaplanır; gerçek zamanlı ileri performans sicili değildir. İlk gözlem kanıtı: observations.csv. Eksik tarihler sonradan doldurulmaz.

| Hipotez | Fikir | Son bar | Pozisyon (+1 = varlığın 1/N payı tam long, −1 = tam short) | Paper 1x $1000 → | Başlangıç kaldıraç | Paper başlangıç $1000 → | Seçilen (tavan) kaldıraç | Paper tavan $1000 → | Sadece işlenebilir varlıklar 1x |
|---|---|---|---|---|---|---|---|---|---|
| H063 | Metal Vortex(28) + SMC order block (long) | 2026-11-13 | nakit | 999 | 2x | 999 | 5x | 997 | 999 (GC=F, HG=F, PA=F, PL=F, SI=F) |
| H064 | Metal 52 hafta zirvesi + SMC BOS (iki yön) | 2026-11-13 | nakit | 1,000 | 2x | 1,000 | 4x | 1,000 | 1,000 (GC=F, HG=F, PA=F, PL=F, SI=F) |
| H065 | Endeks IBS ortalamaya dönüş + SMA200 (long) | 2026-11-13 | YM=F +1.00 | 1,031 | 2x | 1,062 | 4x | 1,127 | 1,031 (ES=F, NKD=F, NQ=F, RTY=F, YM=F) |

Kontrol: 2027-01-22 (ara) ve 2027-04-22 (karar). Kural: `config/mega.yaml` baseline (rastgele giriş + al-tut).
Tüm geçmiş kayıt: `decisions/watch/history.csv` (her gün bir satır). Kontrol yapılmazsa bu iki dosyayı (OZET.md, history.csv) Claude'a gönder.
