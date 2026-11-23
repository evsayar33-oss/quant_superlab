# BIST, ABD ve Kripto — Ücretsiz Tarihsel Veri Araştırması (23 Kasım 2026)

**Durum: kanıta dayalı kaynak keşfi / DO NOT PROMOTE.** İşbu envanter
tarihsel veriye gerçek erişimin, hakların, örneklerin ve bağımsız strateji
testlerinin tümünün doğrulandığı anlamına gelmez. Tanımlı 36 kaynak,
[free_history_catalog.json](free_history_catalog.json) dosyasında
piyasa, geçmiş kapsam, bilinebilirlik zamanı, hukuki kısıtlar ve bağlanacak
repolar ile ayrı ayrı listelenmiştir. Çalıştırılabilir değerlendirme:
`python -m research.source_discovery.audit --out out/free_history_atlas`.

## 1. Kod denetiminde gerçek eksik alan

- **eaverse**: `eaverse/research.py` SMA/EMA, RSI, ADX, OBV, MACD,
  volatilite, Bollinger, momentum, kırılım ve teknik kombinasyonlarını
  tarar. `eaverse/events.py` ABD makro duyuru ve takvim olaylarını
  ölçer. Ancak KAP/SEC şirket bildiriminin kabul anındaki metninden,
  geçmiş yabancı fon varlıklarından, ayrıntılı kamuya açık vadeli order
  book arşivinden ve geçmişte endeks üyeliğinden oluşan kapsamlı
  **olay × öncü akış** çalışması mevcut tarama motorunun kapsamı değildir.
  README'deki 34.636 teknik yapı, 34.636 **geçmişi doğrulanmış alpha**
  değildir.
- **quant_superlab**: `lab/indicators.py` içindeki onlarca OHLCV
  göstergesi zaten var; `lab/fundamentals.py` İş Yatırım ve SEC XBRL'yi
  kullanır. Mevcut kurallar/H090 prototipleri çok farklı tarihsel
  olay kanıtlarını aynı güçte içermez. Örneğin gerçek eski L2 orderbook
  yeniden oynatması, zaman-sabit bir finansal açıklama etüdünün
  yerine geçmez; fiyat hareketinden sonra oluşan indikatörler
  fiyat öncesi sinyalle karıştırılmamalıdır.
- **Diğer repolar**: `research/portfolio_qualification/mesh.py`
  şu an her erişilebilir repoda gerçekten mevcut yerel JSON/CSV/Release
  verilerinin kaynak SHA'sını ve özet analizini ayrı kanıt dalına yazar.
  Bu PR'daki `source_discovery/telemetry.py` kaynak alanları, kayıt
  sayıları, açık zaman damgası aralıkları, eksik değer ve durum sayılarını
  **ham pozisyonları/yatırımcı verisini taşımadan** ayrıntılandırır.
  Mevcut geçmişi geriye dönük `first_seen` diye yeniden üretmez.

## 2. En yüksek yeni araştırma getirisi: ücretsiz **geçmiş** kaynaklar

### BIST
**A — tarihsel evren**: Borsa İstanbul'un endeks üyeliği yayınlarından
derlenmiş
[2000–2026 BIST constituents](https://github.com/GocmenCo/bist-constituents).
Önemli: Son üyelik kaydı, araştırma deposunun kendi uyarısına göre
2026-07-01; son `2026-10-01` satırı yeni bir üye listesi olarak
kullanılamaz. Kaynağın 927 şirket/134 tarih iddiası **kod ve kaynak
workbookları bağımsız karşılaştırılmalı**. `XU030/XU050/XU100` sütunu
birbirini kapsayan endeksler yerine münhasır katman kodlarıdır.
Bu veri **fiyat veya delist tasfiye getirisi sağlamaz**. BIST tarihsel
veri sahipliği ve ticari tekrar yayım koşulları ayrı kontrol edilir.

**B — olay**: KAP'ın şirket finansalları, özel durum açıklamaları,
rüçhan/sermaye artışı, geri alım, ortaklık/finansman bildirimi. MKK
KAP Veri Yayın REST API'sinin portal ürünü ile doğrudan açık HTML
aynı erişim yetkisi değildir. Kayıt, abonelik, IP allowlist, blocked
disclosure ve üretim izni sağlanmadan API çağrısı etkinleştirilmez.
KAP **gerçek yayın zamanı**, geçmiş çeyrek bitiş günü değildir.

**C — makro/kurumsal akış**: TCMB EVDS tarihsel faiz, kredi, döviz,
enflasyon ve TCMB gösterge oranları; TEFAS browser tarihsel fon fiyatları
ve dağılımı; Borsa İstanbul genel piyasa raporları; MKK RISE,
Hazine ihale duyuruları. Bunlar ticker seviyesinde ücretsiz tarihsel
aracı-kurum/derinlik akışını garanti etmez. TEFAS için belgeli açık
API yok; scrape kodu resmi ücretsiz API sayılamaz.

**BIST katı koşulu:** Her testte o gün var olan şirket ve o günkü
kod/ISIN, split/bedelli/temettü etkisi ve gerçekten indirilebilen
tarihi fiyat olmalı. Üyelik verisi **tek başına** sağkalım yanlılığını
tamamen gidermez.

### ABD hisseleri
**A — SEC EDGAR**: 1994/95 sonrası filing index'i, 2009+ ağırlıklı
XBRL companyfacts, 8-K, 10-K, 10-Q, Form 4, SC13D/G, 13F, S-3/424B,
iflas/çıkış bildirimleri. SEC bulk `submissions.zip` ve
`companyfacts.zip` ücretsiz. Periyodun bitişi değil SEC filing
acceptance/dissemination tarih ve zamanı, değiştirilmiş dosya geçmişi
ve gecikme önemlidir; kısa vadeli backtest'te günün hangi saatinde
kamuya açıldığı ayrıca doğrulanır. SEC iyi niyetli User-Agent
ve 10 req/s fair-access sınırı ister.

**B — ücretsiz tarihsel evren**:
[dfjmax/index-constituents](https://github.com/dfjmax/index-constituents)
1993'ten itibaren S&P 500 üyeliklerini SEC/Vanguard, S&P'nin eski
yayımları ve Wikipedia tarihçesinden yeniden kuruyor. `exact`,
`snapshot`, `unreconciled` zaman kalite sınıfları vardır. Eski
ticker farklı bir ihraççıya yeniden verilmiş olabilir; veri doğrudan
kusursuz endeks listesi veya delist fiyatı sayılmaz. Mevcut Nasdaq
Trader sembol listesi geçmiş tüm ABD üyelerini temsil etmez.

**C — konum/duyarlılık**: FINRA off-exchange kısa satış hacmi,
aylık/yarım aylık **ayrı short interest** serileri; Cboe VIX, SKEW
ve yayınlandığı tarihlerdeki toplam put/call oranları; CFTC
haftalık pozisyon raporları; FRED/ALFRED makro veri *vintage*
ve revision kayıtları; Treasury TIC. CFTC'nin salı pozisyonları
Cuma yayımlanır. FINRA'da o gün açılan kısa işlem hacmi,
açık kısa pozisyon toplamı değildir. Ücretsiz Cboe aggregate veri,
ücretli OPRA tam opsiyon trade/Greeks datası **değildir**.

### Kripto
**A — Binance açık arşivi**:
[binance-public-data](https://github.com/binance/binance-public-data)
spot ve USD-M/COIN-M günlük/aylık gerçek `trades`,
`aggTrades`, `klines`; alıcı-maker bayrağı, taker quote
hacmi ile geçmiş agresif alım/satım dengesi hesaplanabilir.
Böylece yalnız RSI'ya bakmak yerine gerçek işlem akışı
zamanlı olarak ölçülebilir. Spot 2025-01-01 sonrası mikro-saniye
timestamp'e döndü. ZIP için .CHECKSUM doğrulaması ve kaynak arşiv
revizyon denetimi zorunludur.

**A/B — OKX tarihsel arşiv**:
[OKX historical-data](https://www.okx.com/historical-data),
tick işlemleri **09/2021+**, funding **03/2022+**, detaylı L2 orderbook
**03/2023+**, mum **07/2023+** olarak tanımlanmış. İndirme biçimi,
otomasyon izni, coğrafi erişim ve enstrüman bazında dosya sürekliliği
test edilmeden üretim araştırmasına alınmayacak. Order book
yeniden oynatılması snapshot ile incremental update'in
birlikte olması ve gap/reset doğrulamasını gerektirir.

**B — Kraken**: Resmî geçmiş OHLCVT ve time & sales indirmeleri,
spot paritelerin ilk işleminden itibaren bazı arşivleri kapsar.
Spot aggressor/tape kıyası için bağımsız borsa kaynağıdır,
ancak aynı borsanın açılış fiyatı, spread'i ve fill'i değildir.

**C — diğer ücretsiz**: Bybit `public.bybit.com` işlemleri
(bölgesel 403 yaygın), Deribit fonlama geçmişi + ücretsiz güncel
opsiyon OI/IV zincir snapshot'ı, Coin Metrics Community
tarihi zincir metrikleri, DefiLlama TVL/stablecoin serileri.
Coin Metrics, DefiLlama geçmişe dönük düzeltmeler yapabilir.
Ücretsiz Crypto Lake/Tardis L2 örnek tarihleri **tam evrenin
ücretsiz sürekli L2 tarihi değildir**.

## 3. Gerçekte test edilmeye değer *farklı* etki aileleri

| Evren | Yalnız teknik indikatör değil; ek **neden/olay** | Gerekli tarihsel ayrım |
|---|---|---|
| BIST | KAP özel durum × sektör göreli akış × tarihsel endeks değişimi | Bildirim yayın zamanı; o günkü şirket/sermaye; delist fiyatı |
| BIST | Bedelli/geri alım × kur/faiz/sıkılaşma rejimi × fon tahsis değişimi | Eylemin ilanı / onayı / gerçekleşmesi ayrı |
| ABD | 8-K/shelf/insider işlemi × 13F sahiplik + short-interest rejimi | SEC acceptance, 13F filing gecikmesi, SI yayın |
| ABD | CFTC/Cboe sistematik risk × alım-satım likiditesi | Haftalık raporların kamuya çıkışı, endeks futures/ETF ayrımı |
| Kripto | Gerçek spot taker akışı × perp mark/index/funding/OI × L2 replenishment | Aynı venue, aynı t; L2 sequence gap-free |
| Kripto | Stablecoin ihraç/çekim × CEX/DEX fon girişleri × unlock takvimi | Blok zamanı, indeksleme/geç görünme ve tarihsel revizyon |

Kombinasyonları sınırsız brute-force denemek **çoklu test yanlılığı**
yaratır. Bilgi içeriği düşük ve tamamen aynı fiyat hareketinden
üretilen göstergeler tekrar tekrar aday üretmemelidir. Farklı
bilgi aileleri için ayrı negatif kontrol, gecikmeli olay kontrolü,
olay-öncesi return/likidite kıyası, net maliyet, regime ve OOS
gereklidir.

## 4. Repo entegrasyon sırası (mevcut kayıtlar korunarak)

1. **BIST** `bist_orderflow_quant` + eaverse + Superlab:
   yeniden kurulan üyelik listesini öncelikle salt okunur PIT
   denetiminden geçir; eski/delist hisselerin eksik fiyatlarını
   **kanıt boşluğu** bırak. KAP/EVDS olay dosyalarını ayrı,
   açıklanma zamanlarıyla bağla.
2. **ABD** eaverse + `us_f1_bot` (özel veri yalnız özel repo içinde)
   + Superlab: SEC 8-K/Form4/13F olayı, takvim gecikmeleri,
   FINRA ve tarihsel üyelik farkları için alternatif araştırma
   hipotezleri üret; 13F'yi anlık alım baskısı sayma.
3. **Kripto** eaverse + `early_accumulation_radar` + Superlab:
   önce Binance arşivli spot/perp gerçek tick/taker ölçümleri,
   sonra OKX geçmiş L2 ile book replenishment, daha sonra
   bağımsız Kraken/Deribit/onchain çapraz teyit. Her tarihsel
   türev eşlemesi aynı enstrüman ve kontrat birimini kullanmalı.
4. **Kendi repolarında detay**: H054, Tier1, Federal Radar,
   Global Capital, ICT, F1, BIST her çalışmada kaynak SHA'sı,
   önce/sonra ilk-gözlem, veri kullanılabilirliği, metrik
   field coverage, düzeltilen revizyonlar, olgunlaşma durumu
   ve araştırma kararı gibi kanıtları kendi ayrı SHA zincirinde
   saklamalı. Kamuya açık Superlab private F1 portföy satırı
   **asla kopyalamamalı**.
5. **PAPER/LIVE** sadece strateji ailesine özgü bağımsız
   metrik/örnek/gerçek fill koşulları geçilince; geçmiş
   backfill ve veri miktarının artması kendiliğinden
   izin üretmez.

## 5. Durum / dürüst sınırlar

Bu değişiklik **36 kaynaklık envanter + ayrıntılı yerel
meta-kanıt katmanı** sağlar. Uçtan uca tüm arşivlerin
indirildiği, bütün sembollerin fiyatlarının tamamlandığı,
eski ikili kombinasyonların optimize edildiği veya
yeni alpha bulunduğu anlamına gelmez. Özellikle tam BIST
seviye-2/üye bazlı işlem geçmişi, tam ABD OPRA/TAQ/delist
toplam getiri ve eksiksiz bütün borsalardan 7/24 tarihsel
liquidation/L2 serileri halen kaynak ve lisans sınırları
nedeniyle **kanıtsız**dır.

En yüksek getiriyi verebilecek adım, fiyat fiyatlandıktan
sonra teknik teyit değil, **o anda kamuya ulaşmış olayın ve
gerçek işlem akışının öncü bilgi değerini** bağımsız
test etmektir. Veri yoksa bunu strateji başarısızlığı
olarak değil veri kapsamı eksikliği olarak kaydet.
