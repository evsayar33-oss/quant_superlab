# H072 sentez çalışması — endeksi yenen kurallar

Tarih: 2026-10-24. Veri sonu: Blok A 2026-08-31, Blok B 2026-05-31. Toplam deneme: **80** (DSR bu sayıyla hesaplandı).

Kurallar sonuçlardan ÖNCE yazıldı: `config/synthesis.yaml` (commit `c1566c0`). Ölçüt nakit değil, **endeksin kendisi** (ABD piyasası toplam getiri, 1x).

## Blok A — ABD piyasası, 1928 → bugün (günlük)

Endeks (al-tut): yıllık **10.0%**, Sharpe 0.452, maks. düşüş -84.1%, $1000 → $12,122,066.

C1–C7'nin hepsini geçen nokta: **0** / 68.

| Aile | Seçilen ayar | Yıllık | Endeks farkı | Sharpe | Maks. düşüş | 2x maliyet yıllık | DSR | Plato | Sonuç |
|---|---|---|---|---|---|---|---|---|---|
| A0_const_lev | `L=1.5` | 11.6% | +1.6% | 0.428 | -94.7% | 10.8% | 0.352 | 0% | kaldı (C1,C2,C3,C4,C5,C7,C6) |
| A1_trend_lev | `N=150,L=3.0` | 17.8% | +7.8% | 0.561 | -84.5% | 13.0% | 0.511 | 100% | kaldı (C2,C3,C7) |
| A2_volman_lev | `target=0.25,Lmax=3.0` | 13.7% | +3.7% | 0.491 | -87.0% | 11.0% | 0.32 | 100% | kaldı (C2,C3,C7) |
| A3_trend_volman | `N=200,target=0.25,Lmax=2.0` | 13.4% | +3.4% | 0.601 | -56.9% | 11.2% | 0.018 | 100% | kaldı (C3,C7) |
| A4_mom_trend | `L=1.0,filter=sma200` | 13.0% | +2.9% | 0.582 | -44.9% | 11.0% | 0.006 | 100% | kaldı (C2,C3,C7) |

Bir aile geçmediyse tabloda en çok kontrolü geçen ayarı gösterilir.

### Kâr hedefi merdiveni (düşüş sınırına göre en sağlam geçen ayar)

| Düşüş sınırı | Ayar | Yıllık | Maks. düşüş | $1000 → |
|---|---|---|---|---|
| -35% | `yok` | — | — | — |
| -50% | `yok` | — | — | — |
| -65% | `yok` | — | — | — |

### Zaman makinesi (seçim süreci geçmişte, ileri dönem görülmeden)

Geçme şartı: 3/4 kesimde ileri kayıt endeksin üstünde ve düşüş en çok 5 puan derin. Sonuç: **0/4 → KALDI**. Kontrolsüz 'en yüksek getiri' seçimi: 1/4.

| Kesim | İleri dönem | Kesimden önce geçen | Seçim | İleri yıllık | Endeks ileri yıllık | İleri düşüş | Endeks düşüş | İçeride |
|---|---|---|---|---|---|---|---|---|
| 1966-01-01 | → 1982-01-01 | 0 | `yok` | — | 6.6% | — | -48.2% | hayır |
| 1982-01-01 | → 2000-01-01 | 0 | `yok` | — | 17.8% | — | -33.1% | hayır |
| 2000-01-01 | → 2013-01-01 | 0 | `yok` | — | 2.1% | — | -54.6% | hayır |
| 2013-01-01 | → 2026-08-31 | 0 | `yok` | — | 15.0% | — | -34.2% | hayır |

Aile bazında zaman makinesi: A0_const_lev kaldı, A1_trend_lev kaldı, A2_volman_lev kaldı, A3_trend_volman kaldı, A4_mom_trend kaldı

## Blok B — çoklu varlık + trend takibi, 1988 → bugün (aylık)

Endeks: yıllık 11.7%, Sharpe 0.618, maks. düşüş -50.2%. Geçen nokta: **0** / 10.

| Ayar | Yıllık | Fark | Sharpe | Maks. düşüş | 2x maliyet | DSR | Plato | Sonuç |
|---|---|---|---|---|---|---|---|---|
| `B1_stack|k=0.25` | 14.3% | +2.6% | 0.779 | -46.7% | 13.6% | 0.556 | 100% | kaldı (C7) |
| `B1_stack|k=0.5` | 16.8% | +5.1% | 0.905 | -43.0% | 15.4% | 0.556 | 100% | kaldı (C7) |
| `B1_stack|k=0.75` | 19.3% | +7.6% | 0.987 | -39.3% | 17.2% | 0.557 | 100% | kaldı (C7) |
| `B1_stack|k=1.0` | 21.7% | +10.1% | 1.031 | -35.5% | 18.9% | 0.557 | 100% | kaldı (C7) |
| `B2_risk_balanced|target=0.12,Lmax=2.0` | 13.8% | +2.1% | 0.919 | -25.1% | 11.7% | 0.0 | 100% | kaldı (C2,C3,C7) |
| `B2_risk_balanced|target=0.12,Lmax=3.0` | 14.3% | +2.7% | 0.886 | -27.2% | 11.9% | 0.0 | 100% | kaldı (C2,C3,C7) |
| `B2_risk_balanced|target=0.15,Lmax=2.0` | 14.4% | +2.8% | 0.927 | -25.2% | 12.2% | 0.0 | 100% | kaldı (C2,C3,C7) |
| `B2_risk_balanced|target=0.15,Lmax=3.0` | 16.6% | +4.9% | 0.881 | -35.0% | 13.3% | 0.002 | 100% | kaldı (C2,C3,C7) |
| `B2_risk_balanced|target=0.18,Lmax=2.0` | 14.5% | +2.9% | 0.928 | -25.2% | 12.2% | 0.0 | 100% | kaldı (C2,C3,C7) |
| `B2_risk_balanced|target=0.18,Lmax=3.0` | 18.2% | +6.6% | 0.882 | -39.4% | 14.3% | 0.01 | 100% | kaldı (C2,C3,C7) |

Zaman makinesi (Blok B): **2/2 → GEÇTİ** (şart 2).

### Sadece şans testinde (C7) kalanlar — bilgi, karar değil

Kural değişmedi: bu satırlar KABUL DEĞİLDİR. C7 eşiği denemeler arası Sharpe dağılımından hesaplanır. Ek bilgi olarak aktif getirinin t-değeri ve 80 deneme için Bonferroni eşiği (tek yönlü %5: t ≥ 3.23) verilir.

| Ayar | Yıllık fark | DSR | Aktif t | Bonferroni eşiği geçer mi |
|---|---|---|---|---|
| `B1_stack|k=0.25` | +2.6% | 0.556 | 4.59 | evet |
| `B1_stack|k=0.5` | +5.1% | 0.556 | 4.59 | evet |
| `B1_stack|k=0.75` | +7.6% | 0.557 | 4.59 | evet |
| `B1_stack|k=1.0` | +10.1% | 0.557 | 4.59 | evet |

## Blok C — gerçek enstrüman (SPY) ve kripto kolu

Blok A'da geçen aile yok; SPY tekrarı yapılmadı.

Kripto kolu (H054) çekirdek: `SPY al-tut`.

| c | Yıllık | Sharpe | Maks. düşüş | Çekirdek yıllık | Çekirdek düşüş | Kabul |
|---|---|---|---|---|---|---|
| 0.1 | 17.6% | 0.85 | -32.3% | 15.1% | -33.7% | evet |
| 0.2 | 20.0% | 0.999 | -31.1% | 15.1% | -33.7% | evet |

## İleri kayıt (kendini güncelleyen döngü)

Dondurma tarihi: 2026-10-24. Her aylık çalışma yeni ayları ekler. Bozulma = ileri aktif getiri, kendi geçmişindeki aynı uzunluktaki dönemlerin en kötü %5'inin altında.

| Kayıt | Ay | İleri aktif getiri (toplam) | Bozuldu mu |
|---|---|---|---|
| `watch:B1_stack|k=0.75` | 0 | +0.0% | henüz erken |
| `watch:C2_crypto|c=0.1` | 0 | +0.0% | henüz erken |
| `watch:C2_crypto|c=0.2` | 0 | +0.0% | henüz erken |

## Zayıf yönler (her zaman)

- Blok A verisi CRSP tüm ABD piyasası (Ken French). S&P 500 ile korelasyonu çok yüksek ama aynı değildir.
- 1928–1990 döneminde kaldıraçlı endeks fonu yoktu. Finansman maliyeti (T-bill + %1,25) bugünkü kaldıraçlı ETF ve vadeli işlem maliyetinden türetildi.
- Kaldıraç kenar yaratmaz. Geçen kurallarda kenar düşüşten kaçınmadan gelir (trend filtresi). V şeklindeki çöküşlerde (1987, 2020) bu koruma geç kalır.
- Momentum ailesi (A4) akademik portföydür. Gerçek ETF (ör. MTUM) daha az getiri verir; %1,5 yıllık ek maliyet bir tahmindir.
- AQR TSMOM serisi brüt yönetim ücretidir; %1 ücret düşüldü. Perakende yatırımcı için en yakın araç yönetilen vadeli fon ETF'leridir (2019+).
- Geçmişteki en kötü düşüş, gelecekteki en kötü düşüş değildir. Ladder tablosu bir üst sınırdır, hedef değil.
- Vergi, kur (TL) ve aracı kurum erişimi modellenmedi.
- Bu çalışma bir ön elemedir. Geçen kural yine de karar kapısından (validation.GATE) ve ileri kayıttan geçmelidir.
