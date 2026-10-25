# Sentez raporu — iki laboratuvar, tek sonuç (2026-10-24)

Bu dosya iki deponun bütün araştırmasını birleştirir:
[`quant_lab`](README.md) (karar merkezi) ve
[`islem_onerisi_alarmi`](https://github.com/evsayar33-oss/islem_onerisi_alarmi) (ICT/SMC laboratuvarı).
Yeni çalışma: **H072 sentez çalışması**. Kod: `lab/synthesis.py`. Kurallar: `config/synthesis.yaml`.
Otomatik rapor: [`decisions/synthesis/report.md`](decisions/synthesis/report.md).

## 1. Kısa cevap

1. Kurallar sonuçlardan ÖNCE yazıldı (commit `c1566c0`). Ölçüt nakit değil, **endeksin kendisi**.
2. Veri 1928'den bugüne (98 yıl, günlük). 80 deneme. Hepsi DSR'a sayıldı.
3. **7 kontrolün hepsini geçen strateji yok** (Blok A ve B). Kurala göre: **daha iyisi bulunamadı.**
4. **Kuralı geçen ve hemen uygulanabilen tek iyileştirme:** S&P 500 fonu + %10–20 H054 kripto kolu.
   2018–2026: yıllık %15,1 → %17,6 (%10 kol) ve %20,0 (%20 kol). Düşüş daha derin değil (−%33,7 → −%31,1).
   Geçmiş kısa (8 yıl). Bu yüzden ileri kayıtla izlenir.
5. **En güçlü aday:** endeks + trend takibi kolu (B1). 1988–2026'da her alt dönemde endeksi geçti.
   2x maliyette de geçti. Düşüş daha az. Zaman makinesi 2/2. Sadece şans testinde (C7) kaldı.
   Dikkat: trend primi 2012'den sonra çok azaldı. Bu yüzden sadece İZLEME.
6. Kaldıraç tek başına çözüm değil. 2x endeks 1929–1932'de kasayı −%98 düşürdü.
7. Teknik ve ICT kural taraması bitti. İki labda on milyonlarca deneme var. Kilitli dönemde hiçbiri kalmadı.
   Bu yöne yeni kaynak harcamayı önermiyorum.

## 2. Neden şimdiye kadar endeksi yenen bir şey çıkmadı?

| Sebep | Kanıt (iki depodan) |
|---|---|
| Yanlış ölçüt | H001–H071 her fikri tek başına **nakde** karşı ölçtü. Zamanın %30'unda piyasada olan bir kural, iyi zamanlamayla bile endeksten fazla kazanamaz. H070: Sharpe 0,69 ama yıllık %5. |
| Seçim şansı | islem: geçmiş (IS) ile ileri (OOS) sıralama korelasyonu 0,007 (NQ), 0,055 (SPX). quant_lab arena: ~0. H062: 73.005 deneme → 0 finalist. |
| Fiyat kalıbı ≠ prim | Likit piyasalarda fiyat kalıpları (ICT blokları, indikatör kesişimleri) maliyetten sonra şanstan farksız. Kalıcı getiri, **risk primlerinden** gelir: hisse primi, trend primi, carry. |
| Kaldıraç yanlış yerde | Kaldıraç bir kenarı büyütür, kenar yaratmaz. Kenar yoksa sadece düşüşü büyütür (A0 kontrol ailesi). |

Büyük fonların ve merkez bankası rezerv yöneticilerinin yöntemi farklıdır: hisse primini çekirdek tutarlar.
Üstüne korelasyonu düşük primler eklerler. Kuyruk riskini sınırlarlar. Pozisyonu riske göre boyutlarlar.
H072 bu yöntemi test etti.

## 3. Yöntem (H072)

| Blok | Veri | Aileler (yayınlanmış kurallar) | Deneme |
|---|---|---|---|
| A | ABD piyasası toplam getiri, Ken French/CRSP, **1928–2026 günlük** | A0 sabit kaldıraç (kontrol), A1 trend + kaldıraç (Faber 2007; Gayed-Bilello 2016), A2 volatilite yönetimi (Moreira-Muir 2017), A3 A1×A2, A4 momentum hisseleri + trend filtresi | 68 |
| B | Endeks + 10 yıllık tahvil + AQR TSMOM, **1988–2026 aylık** | B1 endeks + trend kolu ("return stacking"), B2 risk dengeli (eşit risk, vol hedefi) | 10 |
| C | **SPY + ^IRX** (gerçek ETF), **H054** kripto | A seçiminin SPY tekrarı, %10/%20 kripto kolu | 2 |

Gerçekçilik: sinyal t kapanışı, işlem t+1 kapanışı (2 gün gecikme). Nakit T-bill kazanır.
Borç T-bill + %1,25 öder (2x kontrolde + %2,5). İşlem başı %0,10. Momentum için yıllık %1,5 ek maliyet.
Trend kolu için yıllık %1 fon ücreti.

Kabul (hepsi şart): **C1** tüm dönem: yıllık getiri ve Sharpe endeksten yüksek, düşüş en çok 5 puan derin.
**C2** her alt dönemde getiri endeksten yüksek. **C3** 2x maliyette C1 + en çok 1 alt dönem kaybı.
**C4** 1 gün daha geç işlemde C1. **C5** aynı oynaklığa kaldıraçlanmış endeksi geçer (sadece kaldıraç değil).
**C6** komşu ayarların ≥ %75'i C1'i geçer (plato). **C7** aktif getirinin DSR'ı ≥ 0,90 (80 deneme).
Seçim süreci ayrıca zaman makinesinden geçer (Blok A: 4 kesim, Blok B: 2 kesim).

## 4. Sonuçlar

### Blok A — 1928–2026 (endeks: yıllık %10,0, Sharpe 0,45, düşüş −%84,1)

| Aile | En iyi ayar | Yıllık | Sharpe | Maks. düşüş | Kaldığı kontrol |
|---|---|---|---|---|---|
| A0 sabit 2x (kontrol) | L=2 | %12,3 | 0,42 | **−%98,4** | hepsi |
| A1 trend + 2x | SMA200, L=2 | %14,2 | 0,55 | −%69,2 | C2 (1982–99 düşüş, 2000–12 getiri), C3, C7 |
| A3 trend + vol hedefi | SMA200, hedef %25, ≤2x | %13,4 | **0,60** | −%56,9 | C3, C7 |
| A4 momentum + trend | 1x, SMA200 | %13,0 | 0,58 | −%44,9 | C2 (2013–26 geride), C3, C7 |

A3 her alt dönemde 1x maliyette endeksi geçti. Ama 1966 sonrası fark çok küçük (yılda +0,1 ile +1 puan).
2x maliyette bu fark 4 alt dönemde kayboldu. Yani trend filtresinin asıl faydası **düşüşü azaltmaktır**
(−%84 → −%57), getiriyi artırmak değildir. Zaman makinesi: **0/4**. Hiçbir kesimden önce kuralı geçen yoktu.

### Blok B — 1988–2026 (endeks: yıllık %11,7, Sharpe 0,62, düşüş −%50,2)

| Portföy | Yıllık | Sharpe | Maks. düşüş | 2x maliyet | 2012–2026 yıllık (endeks %15,3) | Sonuç |
|---|---|---|---|---|---|---|
| Endeks + %50 trend | %16,8 | 0,91 | −%43,0 | %15,4 | %17,0 | C7 dışında hepsi geçti |
| Endeks + %75 trend | %19,3 | 0,99 | −%39,3 | %17,2 | %17,6 | C7 dışında hepsi geçti; zaman makinesi seçimi |
| Endeks + %100 trend | %21,7 | 1,03 | −%35,5 | %18,9 | — | C7 dışında hepsi geçti |
| Risk dengeli (B2) | %13,8–18,2 | 0,88–0,93 | −%25 ile −%39 | — | geride | C2, C3, C7 (2022'de tahvil + hisse birlikte düştü) |

Zaman makinesi (B1): **2/2 geçti.** 2004 kesimi → 2004–2011 ileri: %10,1 (endeks %4,3).
2012 kesimi → 2012–2026 ileri: %17,6 (endeks %15,3), düşüş −%18 (endeks −%25).
Kriz yılları: 2008 −%25 (endeks −%37), 2022 −%5 (endeks −%20).

**Neden yine de kabul değil:** C7 (DSR 0,56 < 0,90). Bilgi olarak: aktif getirinin t-değeri 4,59.
80 deneme için Bonferroni eşiği 3,23. Kural değişmedi; bu satır karar değildir.
**İleriye bakış için asıl uyarı:** trend priminin Sharpe'ı dönem dönem düştü:

| Dönem | 1985–95 | 1996–2003 | 2004–11 | 2012–19 | 2020–26 |
|---|---|---|---|---|---|
| AQR TSMOM Sharpe | 1,49 | 1,69 | 0,82 | 0,44 | 0,32 |
| B1 aktif t-değeri | 5,50 (1988–2003) | | 1,78 | 0,79 (2012–26) | 0,36 |

Yayından (Moskowitz-Ooi-Pedersen 2012) sonra prim azaldı. Kalan fayda: kriz yıllarında koruma ve biraz ek getiri.

### Blok C — gerçek enstrüman ve kripto kolu (2018-07 → 2026-09)

| Portföy | Yıllık | Sharpe | Maks. düşüş | 2x maliyet | 3 ileri pencere | Kabul |
|---|---|---|---|---|---|---|
| SPY al-tut | %15,1 | 0,69 | −%33,7 | — | — | ölçüt |
| %90 SPY + %10 H054 | %17,6 | 0,85 | −%32,3 | %17,5 | 3/3 | **evet** |
| %80 SPY + %20 H054 | %20,0 | 1,00 | −%31,1 | %19,8 | 3/3 | **evet** |

H054 karar kaydında zaten ACCEPT (BTC+ETH, SMA200 + TSMOM + %40 vol hedefi + %10 bant).
Kripto kolu, endeksle düşük korelasyonlu bir trend primi ekler.

## 5. Öneri (karar sahibindir)

| Katman | Ne | Pay | Durum |
|---|---|---|---|
| Çekirdek | S&P 500 endeks fonu | %80–90 | Ölçütün kendisi. Uzun vadede yenmesi en zor varlık. |
| Uydu 1 | H054 botu (mevcut) | %10–20 | Blok C kuralını geçti. H054 ACCEPT. Canlı kayıt çok kısa (36 bar). |
| Uydu 2 | Trend takibi kolu (çok varlıklı TSMOM) | %0 → izleme | Kâğıt üzerinde izlenir. Önce işlenebilir bir araçla yeni hipotez + karar kapısı gerekir. |
| Yapma | Trend filtresiz kaldıraçlı endeks; yeni teknik/ICT taraması | — | Kanıt: A0, H062, islem RESEARCH_LOG |

**Gerçekçi beklenti (ileriye dönük).** Büyük kurumların 2026 on yıllık ABD büyük şirket beklentileri düşük:
J.P. Morgan %6,7, Callan %7,25, PGIM %5,2, MFS %0,8 (yüksek değerleme). Bu ortamda çekirdek + uydu
portföyü endeksin birkaç puan üstünü hedefleyebilir. Yılda %30–50 gibi hedefler için **sağlam kanıt yok.**
Bu seviyeyi vaat eden her backtest bu iki labda kilitli dönemde çöktü.

## 6. Kendini geliştiren döngü

- Workflow **"Synthesis study"** her ayın 9'unda çalışır (`.github/workflows/synthesis.yml`). Elle de çalışır.
- Yeni veriyle aynı kurallar uygulanır. Eşik değişmez.
- İleri kayıt: `decisions/synthesis/forward.json`. İzlenenler: B1 %75, kripto kolu %10 ve %20. Dondurma: 2026-10-24.
- Bir kayıt, kendi geçmişindeki en kötü %5'in altına düşerse **bozuldu** olarak işaretlenir.
- Ken French ve AQR verisi 1–4 ay gecikir. İlk anlamlı ileri kontrol: 2027 ilkbaharı (≥ 6 ay).

## 7. Zayıf yönler

- Blok A verisi tüm ABD piyasasıdır (CRSP). S&P 500 ile çok yakın, aynı değil.
- 1990 öncesinde kaldıraçlı fon yoktu. Finansman maliyeti bugünkü araçlardan tahmin edildi.
- AQR TSMOM akademik bir seridir (58 vadeli piyasa). Perakende yatırımcının aynı sonucu alması zordur.
  Yönetilen vadeli fon ETF'leri 2019 sonrası vardır ve sonuçları faktörden zayıftır.
- Tahvil serisi 10 yıllık getiriden sentetik üretildi (FRED DGS10; bu çalışmada FRED kapalıydı, Yahoo ^TNX kullanıldı).
- Kripto kolu sadece 8 yıl. Bu dönem kripto için güçlüydü. Kripto verisi Binance Vision 4h (Bitget'e ulaşılamadı).
- Kripto kolu için zaman makinesi yok (2 deneme, sabit kural). Pencereler H054'ün dondurulmasından önce.
- Vergi, TL kur etkisi ve aracı kurum erişimi modellenmedi. Sonuçlar USD'dir.
- Geçmişteki en kötü düşüş, gelecekteki en kötü düşüş değildir.

## 8. Deneme muhasebesi (iki depo birlikte)

| Çalışma | Deneme | Kilitli/ileri dönemi geçen |
|---|---|---|
| quant_lab H001–H071 (karar kapısı) | 70 hipotez, binlerce varyant | 2 ACCEPT (H052, H054 — sabit literatür kuralları) |
| quant_lab arena + H062 dev tarama | 73.005 (H062) + arena hunisi | 0 |
| islem ICT çoklu zaman dilimi araması | varlık başına 43.000–90.000 kombinasyon × 810 ayar | 2/6 varlık, ortalama −0,002 R |
| islem Stage A–D (boyut, 15 dk, haber, yeni ICT modelleri) | 13 yöntem | 0 (t ≥ 2 yok) |
| **H072 sentez** | 80 | Blok A/B: 0; Blok C kripto kolu: 2/2 |

## 9. Sonraki adımlar (her biri önce ön kayıt)

1. **Yeni hipotez (id sonra verilir):** işlenebilir trend kolu. Seçenek: Bitget/OKX'te işlem gören endeks, metal ve emtia perp'leri
   (`lab/venues.py`) ile çok varlıklı TSMOM. Sabit literatür ayarı (12 ay işaret, vol hedefi). Karar kapısı + zaman makinesi.
2. **Yeni hipotez:** çekirdek + H054 + trend kolu birleşik portföyü. Ölçüt yine endeksin kendisi.
3. Sahibin kâr hedefi yazılı değil. Hedef (yıllık % ve kabul edilebilir en kötü düşüş) yazılırsa
   `config/synthesis.yaml` → `ladder_max_dd` bu hedefe göre güncellenir (yeni çalışma, yeni ön kayıt).
