# USD Macro Radar V1 — ABD dolarının temel analiz laboratuvarı

**İlk durum: yeni bilgi akışı ve araştırma. Geçmişte kanıtlanmış döviz
stratejisi değildir.** H083 hisse araştırması ve Radar'ın haber/işlem
kanıt sicilinden tamamen ayrıdır.

## Görünüm ve veri akışı

- `dashboard/usd_macro.html` — mobil uyumlu, Türkçe, 6 analiz katmanı,
  resmî bağlantılar, FX/faiz referansı, beklenti denetimi, olası senaryolar.
  `decisions/usd/latest.json` üzerinden çalışır; veri yoksa boş ve doğru
  durum gösterir. Bu, mevcut Arena ekranını bozmaz.
- `research/usd_macro/sources.py` — **8 bağımsız resmî / merkez bankası veri yolu**:
  1. ECB 90 günlük EUR, JPY, GBP, CHF döviz referansları: kendi
     ağırlıkları (EUR %45, JPY %25, GBP %20, CHF %10) ile
     USD çapraz piyasa yönü. **DXY değildir ve DXY yerine pazarlanmaz.**
  2. ABD Hazine nominal 2y/10y getirileri, 5 seans değişimleri ve 10–2 eğrisi.
  3. ABD Hazine 10y TIPS reel getirisi ve 5 seans değişimi.
  4. BLS v1 API: manşet/core TÜFE, NFP, işsizlik, özel sektör saatlik
     ücret (cari revizyon/vintage). CPI yıllık ve NFP aylık değişim.
  5. Federal Reserve'in parasal politika resmî RSS başlıkları; RSS erişimi engellenirse Fed FOMC resmî basın arşivi (yalnız DATE_ONLY, asla kesin yayın saati değil).
  6. BLS'in resmî RSS haber başlıkları.
  7. FRED (St. Louis Fed) açık CSV: PAYEMS, UNRATE, CPIAUCSL,
     CPILFESL. **İkincil güncel-vintage bağlamdır; BLS'in
     ilk yayımlanan resmî verisi, piyasa anketi veya sürpriz değildir.**
  8. New York Fed resmî SOFR API; gecelik teminatlı fonlama
     oranı. **Fed hedef faizi veya FedWatch olasılığı değildir.**
- `research/usd_macro/engine.py` — araştırma katmanları:
  **enflasyon, işgücü, Fed, faiz ve reel faiz, USD çapraz teyit,
  maliye/risk/ticaret**. Her gösterge aynı anda güncellenmeyebilir.
  Fed açıklama başlıkları sadece KONU olarak sınıflandırılır:
  açıklama metninden otomatik 'şahin/güvercin' ve işlem emri ÜRETİLMEZ.
- `research/usd_macro/expectations.csv` — **opsiyonel resmî yayın öncesi
  ekonomik konsensüs girme alanı**; ticari piyasa veri API'si
  bağlanmadıkça BOŞ kalması doğru davranıştır.
  Model tahmini, consensus, nowcast ve açıklanan gerçek birbirinin yerine
  geçirilmez. Sürpriz sadece gerçek önceden mühürlü veriyle hesaplanır.
- `decisions/usd` — ilk gözlem zamanları, gözlenmiş ilk BLS değerleri,
  sonraki revizyonlar, beklenti mühürleri, haberler ve status.
- `.github/workflows/usd_macro.yml` — hafta içi 12:45, 14:45, 18:45,
  22:45 UTC; kıyas/derin doğrulama işi ve (yalnız main + schedule/dispatch)
  ileri veri yazma/Telegram işi. Telegram `TELEGRAM_TOKEN`+`CHAT_ID`
  (mevcut laboratuvar secrets) kullanır. Secret yoksa gönderim YOK;
  fiyat tahmini, AL/SAT sinyali veya emir oluşturmaz.

## Beklenti kaynaklarını nasıl girersin?

Beklenti bir "gelecek olay" için ölçü birimi, veri dönemi, yayın saati,
kaynak URL ve sağlayıcıyla girilir. **Sistem yalnız yayımdan önceki
bir Actions çalışmasında ilk defa gördüğü satırı kilitler.**
Sadece eski tarih yazmakla ex-ante kanıt oluşmaz.

CSV başlığı:

```csv
indicator_id,period,expected_value,unit,release_at_utc,provider,source_url
```

Desteklenen `indicator_id` / birim:
- `cpi_all_yoy_pct`, `cpi_core_yoy_pct`: `PCT_YOY`
- `nonfarm_change_k`: `THOUSANDS`
- `unemployment_pct`: `PERCENT`
- `ahe_yoy_pct`: `PCT_YOY`

`period` biçimi YYYY-MM; `release_at_utc` saat dilimli ISO8601.
`provider` gerçek anket/kurum adıdır ve `source_url` gerçek
**https** bağlantısı olmalıdır. Kaynağı olmayan değer BIRAKILMAMALIDIR.
BLS gerçekleşeni API'den **ilk gözlendiği** an saklanır;
sonradan revize gelen gerçek ilk anı değiştiremez.

Not: Bir kullanıcı CSV'yi ilk kez resmî yayın sonrasında eklerse statü
`REJECTED_ENTERED_AFTER_RELEASE`; karşılaştırma YAPILMAZ.
Önceden kilitli değer değiştirilemez. İleriye yönelik ilk gözlem,
resmî bültenin dakika-saniye düzeyinde sürpriz işlemini garanti etmez.

## Yorumlama (güvenli ölçüm)

`MARKET_CONFIGURATION_USD_SUPPORTIVE` örneği: resmî ECB referans
dört-döviz vekili 5 günde >=%0,35 yükselmiş VE ABD 2y nominal getiri
5 iş gününde >=8 baz puan artmış. 10y reel getirinin zıt işareti
varsa `MIXED_REAL_YIELD_DIVERGENCE` olur. Tersi benzer biçimde
"unsupportive". Kur oynaklığı, ABD–yabancı merkez bankası faiz farkı,
risk iştahı ve güncel beklentiler farklı yön gösterebilir;
bu eşikler **ön kayıtlı izleme tanımıdır, test edilmiş alfa eşiği değil**.
Güven derecesi daima `LOW_RESEARCH_ONLY`; kanıt yoksa
`INSUFFICIENT_EVIDENCE`. **Hiçbir durumda BUY/SELL verilmez.**

Fed, BLS ve Treasury yayımları farklı saatlerde revize olabilir.
Tarihsel serileri geriye dönük API çekip geçmişte öğrenilmiş gibi
uydurma backtest yapılmaz; ileri kayıt yayın sonrası başlar.
`first_seen_utc` yalnız motorun ilk görme anıdır, haberi piyasada ilk
gören kişinin anı değildir.

## Gerçekçi kapsam sınırları

V1 ile ilişkili ama **henüz uygulanmayan** girdiler:
BEA PCE/GDP resmi API (kayıtlı anahtar gerektirir), Fed dot-plot
metin içeriği ve OIS/futures faiz patikası, konsensüs veri sağlayıcısı,
ECB/BoE/BoJ faiz farkları, CFTC COT spekülatif konumlanması,
ABD bütçe/borç duyuruları ve jeopolitik haber sağlayıcıları.
Bunlar olmadığında kapsam "tam" veya sonuç "kanıtlandı" etiketi almaz.

## Çalıştırma

```bash
python -m pip install 'requests>=2.31,<3' 'pytest>=8,<10'
python -m pytest -q research/usd_macro/test_usd_macro.py
python research/usd_macro/engine.py --mode smoke --output results/usd_macro
# main scheduled/dispatch only:
python research/usd_macro/engine.py --mode scheduled --output decisions/usd
```

`smoke` gerçek 6 kaynağı dener, sonuçları yalnız artifact'a yazar,
**Telegram göndermez**; en az 4 başarılı resmî/merkez bankası veri kaynağı olmadan yeşil
olamaz. Dış kaynak blokajı, stale fiyatlar ve eksik veri açık uyarıdır.

Önerilen sonraki aşama: gerçek bir dış konsensüs/nowcast kaynağı lisansı,
Fed metin analizi için doğrulanan metin kanıtı, reel faiz farkları,
USD forward-reaction etiketleri ve ex-ante walk-forward risk karşılaştırması.
Bu aşamaların hiçbiri V1'de test edilmiş alpha olarak ileri sürülmez.

### GitHub Actions gerçek bağlantı testi notu

BLS API, BLS RSS ve Fed RSS bazı bulut çalıştırıcılarına 403/503 veya geçersiz XML dönebilir. Her kaynak kendi hata durumunu gösterir; Fed FOMC basın arşivi tarih-düzeyli yedek olarak kullanılabilir. FRED verisi BLS ilk yayın sürprizini taklit etmez. Bütün kaynaklar arızalıysa USD yorumu verilmez; kısmi başarısızlık `PARTIAL` olur.
