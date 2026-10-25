# Varlık başına strateji kitabı — tek platform (Bitget), tek bot (2026-10-24)

Bu dosya sahibin ikinci isteğinin cevabıdır: her varlığa özel, basit, Bitget üzerinden bir bota
bağlanabilen kârlı kural. Fibonacci premium/discount bölgesinden giriş ayrıca test edildi.
Ayrıntılı otomatik raporlar: [`decisions/assetbook/report.md`](decisions/assetbook/report.md) (H073 tarama),
[`decisions/coreassets/report.md`](decisions/coreassets/report.md) (H074 sabit kural),
[`decisions/assetbook/persistence.md`](decisions/assetbook/persistence.md) (geçmişte en iyi olan sonra ne yaptı).

## 1. Kısa cevap

1. Kurallar sonuçlardan ÖNCE yazıldı: `config/assetbook.yaml` (commit `c50eac5`), `config/coreassets.yaml` (commit `b590dda`).
2. Tarama (H073): 8 varlık, 11 iş, **29.912 deneme**. 68 kuralın hepsi tek tek; hepsi Fibonacci filtresiyle;
   1.296 Fibonacci giriş ayarı; 144 Fibonacci + ikinci sinyal kombosu. Her biri long, short ve iki yön.
3. **Taramadan çıkan kural yok.** Hiçbir varlıkta hiçbir kural şans testini (DSR) geçmedi. Kurala göre: daha iyisi bulunamadı.
4. **Fibonacci:** premium/discount filtresi 11 işin **0'ında** yardım etti. Keşif döneminde 11 işin 10'unda
   kâr faktörünü düşürdü. Saf Fibonacci girişleri de hiçbir varlıkta geçmedi.
5. **Çalışan kural taramadan değil, önceden seçilmiş sabit kuraldan çıktı.** H054 çekirdek kuralı
   (SMA200 + momentum + oynaklık hedefi, ayar değişmeden) **BTC, ETH ve SOL**'de varlık başına kabul şartını
   her pencerede, 2x maliyette de geçti. SPX, NDX, altın, gümüş ve bakırda geçmedi.
6. **Bot:** BTC ve ETH için mevcut H054 botu (karar kaydında ACCEPT). SOL için H075 karar kapısında (Cumartesi
   "Validate hypotheses" çalışmasında otomatik test edilir).
7. **Bitget'te endeks ve metal perp'lerini uzun tutmak pahalı.** Son 16–33 günün funding oranı yıllık:
   SPX %11, XAU %12, XAG %15, NDX100 %8. Bu maliyet, bu varlıklarda bir kuralın kârını büyük ölçüde siler.

## 2. "Çok strateji varsa birkaçı kesin kârlı çıkar" — neden yanıltıcı?

Geçmişte çok kârlı görünen kural gerçekten çıkıyor. Örnek (keşif dönemi, 2x maliyet):

| Varlık | Keşifte en iyi görünen | Keşif getirisi | Kâr faktörü | Şans testi (DSR, eşik 0,95) |
|---|---|---|---|---|
| BTC 1d | rsi_midline (RSI 21 > 55) long | +%3.119 | 5,18 | 0,27 |
| ETH 4h | volume_breakout long | +%3.242 | 3,60 | 0,19 |
| SOL 4h | smc_fvg (ICT FVG) long | +%10.492 | 2,51 | 0,28 |
| NDX 1d | Fibonacci 0,786–0,886 + SMA200 long | +%115 | 3,09 | 0,06 |
| XAG 1d | Fibonacci 0,786–0,886 long | +%144 | 2,01 | 0,05 |
| SPX 1d | Fibonacci 0,786–0,886 + SMA200 long | +%52 | 2,49 | 0,01 |

Sorun şu: yaklaşık 2.800 deneme yapınca, en iyisi şans eseri de bu kadar iyi görünür.
DSR bu şans payını ölçer. BTC günlükte şans eşiği yıllık Sharpe ≈ 1,5; en iyi kural 1,29'da kaldı.
Kriptodaki "en iyi" kuralların çoğu "trendde long kal" türündedir. Bunlar varlığın kendi yükselişini taşır.

**Geçmişte en iyi olan sonra ne yaptı?** ([`persistence.md`](decisions/assetbook/persistence.md), 6 ve 4 yıl önceki
kesimler; kilitli dönem okunmadı). Her kesimde keşifte en iyi 10 kural seçildi, sonraki 2 yıl ölçüldü:

- En iyi 10'un çoğu sonra da kârda kaldı (18 kesimin 12'sinde 7/10 veya daha fazla).
- Ama piyasa yükselirken **neredeyse hiçbiri al-tutu geçmedi** (yükselen 13 kesimde toplam 9/130).
- Al-tutu geçtikleri tek durum piyasanın düştüğü dönemler (NDX 2020–22, altın ve gümüş 2020–22). Sebep zamanlama değil,
  daha az piyasada kalmak.
- Geçmiş Sharpe ile sonraki Sharpe arasındaki sıra korelasyonu −0,25 ile +0,60 arasında; bakırda ve ETH 2022'de ~0 veya negatif.

Sonuç: taramada "en iyi" görünen kural, çoğu zaman sadece varlığı daha az tutan bir al-tut kopyasıdır.

## 3. Varlık başına sonuç

| Varlık | Bitget | Tarama (H073) | Sabit çekirdek kural (H074): yıllık / en büyük düşüş / son 2 yıl | Al-tut: yıllık / düşüş / son 2 yıl | Bot |
|---|---|---|---|---|---|
| BTC | BTCUSDT | geçen yok | %21,1 / −%46 / %12,1 | %25,5 / −%77 / %9,7 | **H054 (mevcut, ACCEPT)** |
| ETH | ETHUSDT | geçen yok | %25,6 / −%41 / %5,7 | %12,7 / −%90 / −%4,6 | **H054 (mevcut, ACCEPT)** |
| SOL | SOLUSDT | geçen yok | %35,8 / −%41 / %10,5 | %43,9 / −%96 / −%21,7 | **H075 (karar kapısında)** |
| SPX | SPXUSDT | geçen yok | −%0,9 / −%51 / %6,2 | %6,4 / −%57 / %14,2 | yok |
| NDX | NDX100USDT | geçen yok | %1,8 / −%53 / %6,5 | %7,8 / −%80 / %19,2 | yok |
| Altın | XAUUSDT | geçen yok | %2,8 / −%41 / %13,9 | %10,6 / −%46 / %20,2 | yok |
| Gümüş | XAGUSDT | geçen yok | %2,4 / −%74 / %29,4 | %6,9 / −%76 / %24,0 | yok |
| Bakır | COPPERUSDT | geçen yok | −%3,6 / −%51 / %1,7 | %3,7 / −%55 / %19,1 | yok |

Kural sütunu 1x maliyet ve funding (kripto %8, diğer %5) içerir. Al-tut sütununda funding yoktur (sıkı karşılaştırma).
Kripto verisi 2017'den (SOL 2020'den), endeks 2000'den, altın 2004'ten, gümüş 2006'dan, bakır 2011'den başlar.

**Kriptoda kuralın değeri:** getiri al-tuta yakın veya üstünde, ama düşüş yarıya veya daha aşağı iner.
Kripto çöküşlerinde (2018, 2022) kural nakitte bekler. Bu, kaldıraçsız bir botun hayatta kalmasını sağlar.

**Endeks ve metallerde neden kaldı:** trend filtresi bu varlıklarda sık yanlış sinyal verdi. Perp funding
de getiriyi düşürdü. Funding olmadan bile SPX, altın, gümüş ve bakırda Sharpe al-tutun altında kaldı
(ör. SPX 0,30 / al-tut 0,42). NDX'te funding olmadan Sharpe eşitti (0,43 / 0,42); funding ile kaldı.

## 4. Bot tarifi (BTC, ETH, SOL için aynı kural, varlık başına)

Bu, H054'te kapıdan geçen kuralın aynısıdır. Ayar değiştirmeyin.

1. Bar kapanınca hesaplayın: SMA = son 200 günün kapanış ortalaması. R30, R90, R180 = 30, 90, 180 gün önceki
   kapanışa göre getiri. σ = son 30 günün yıllıklandırılmış oynaklığı.
2. Long şartı: kapanış > SMA **ve** R30, R90, R180'den en az biri pozitif.
3. Hedef pozisyon = min(1; 0,40 / σ) × o varlığa ayrılan kasa. Şart yoksa hedef 0 (nakit).
4. Mevcut pozisyon hedeften 0,10'dan fazla farklıysa pozisyonu hedefe getirin (işlem yapmama bandı).
5. Short yok. Kaldıraç yok (1x). Emir bir sonraki barda verilir.
6. Bot sadece `lab/client.py` → `approved()` listesinde ACCEPT görürse işlem yapar (SOL için H075 sonucu beklenir).

## 5. Fibonacci sorusunun cevabı

| Test | Sonuç |
|---|---|
| Premium/discount filtresi 65 kurala eklendi (eşli test, kilitli 2 yıl) | 11 işin 0'ında yardım etti (gereken: 6). Medyan kâr faktörü değişimi çoğunlukla negatif. |
| Saf Fibonacci girişleri (0,5–0,618 / 0,618–0,786 / 0,786–0,886; limit veya onay mumu; Fibonacci stop ve hedefler; 3 filtre; 3 yön) | 11 işin hiçbirinde şans testini geçen ayar yok. |
| Fibonacci OTE + ikinci sinyal (likidite süpürmesi, FVG, RSI uyumsuzluğu, CHoCH) | Geçen yok. |
| En yakın Fibonacci aday | SPX, NDX ve gümüşte "yükselen trendde 0,786–0,886 derin geri çekilmede al". Keşifte kârlı, ama DSR 0,01–0,06 (20 yılda 35–55 işlem). Şanstan ayırt edilemiyor. |

Önceki çalışmalarla birlikte: islem deposunda haftalık premium/discount filtresi (PD) ve quant_lab'da
`smc_ote` kuralı da kilitli dönemde başarısız oldu. Fibonacci bölgeleri bu verilerde kalıcı bir avantaj vermedi.

### Spot veya düşük funding'li borsa

- **Kripto:** kural sadece long ve kaldıraçsız. Spot piyasada (Binance, OKX, Bitget spot) funding sıfırdır; getiri yılda yaklaşık 2–3 puan artar. Önerilen yol: spot.
- **Endeks ve metal:** funding'siz hesapta da kural al-tutu geçmedi (SPX %2,6 / %6,4; altın %6,3 / %10,6). Sorun maliyet değil, avantaj yok. En ucuz yol düşük maliyetli fon (ETF), bot yok.

## 6. Zayıf yönler

- Endeks ve metal perp'leri için fiyat vekili kullanıldı (^GSPC, ^NDX, GLD, SLV, CPER). Bitget fiyatı ve işlem saatleri farklı olabilir.
- Endeks ve metallerde ücretsiz uzun 4 saatlik geçmiş yok; bu varlıklar sadece günlükte test edildi.
- Funding: config'te sabit oran (kripto %8, diğer %5). Gerçek Bitget oranları değişkendir; son ölçüm diğer varlıklarda daha yüksek.
- SOL geçmişi kısa (2020-08). Zaman makinesi için yeterli kesim yok. H075 karar kapısı bunu ayrıca ölçer.
- Kripto sonuçları 2017–2026 dönemine bağlıdır. Bu dönem kripto için çok güçlüydü.
- Geçmişteki en kötü düşüş, gelecekteki en kötü düşüş değildir. Kaldıraç kullanmayın.

## 7. Sonraki adımlar

1. **H075 (SOL):** karar kapısı Cumartesi otomatik çalışır. ACCEPT gelirse SOL, H054 botuna veya ayrı bir bota bağlanabilir.
2. **H054 ileri kaydı:** canlı takip devam ediyor (`decisions/live/H054.csv`).
3. **Endeks/altın için:** Bitget perp yerine düşük maliyetli fon (ETF/endeks fonu) daha uygundur. Bot gerekmez.
4. **Fiyat dışı veri:** iki labda denenmemiş tek açık fikir emir akışı verisidir (islem RESEARCH_LOG §9).
5. Workflow **"Asset book"** her çeyrekte taramayı yeni veriyle tekrarlar. Eşikler değişmez.
