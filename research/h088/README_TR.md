# H088 — Prospektif bağımsız kaynak ve maliyet kanıt zinciri

**Bu bir altyapı/doğrulama çalışmasıdır; strateji geliştirme, canlı işlem veya kâr onayı değildir.**

## 1. Bağımsız veri
Her hafta içi 23:25 UTC'de (Paper Watch 22:37 UTC'den sonra) Binance USDT-M ve Bybit linear USDT-M API'lerinden **BTCUSDT ve ETHUSDT** için gerçek zamanlı bid/ask fiyat ve miktarı istenir. Yanıtlar tek tek kaynak adı, alınma zamanı, varsa borsa olay zamanı, spread, top-of-book kapasitesi ve iki borsa arasındaki mid-price farkıyla kaydedilir. Yanıt hatası, eski zaman damgası, yanlış sembol, çapraz fiyat veya büyük istek aralığı geçersizdir. **Biri yoksa diğerinin değeriyle doldurulmaz.** Her iki kaynak aynı kripto piyasasına duyarlı olduğu için bağımsız ekonomik alfa örneklemi sayılmaz.

## 2. Maliyet kanıtı
İşlem büyüklüğü **1.000 USD** varsayılarak o andaki en iyi bid/ask'ın nominal kapasiteyi karşılayıp karşılamadığı kaydedilir. Tek yönlü komisyon oranı **gerçek hesap komisyonu bilinmediğinden otomatik atanmaz**. `--fee-bps-per-side` girilirse bu açıkça *varsayım* diye etiketlenir. Gerçekleşmiş fill, spread dışı price impact, taker/maker rebate, funding, borrow, kaldıraç marjı ve gecikme **doğrulanmış sayılmaz**. Kullanıcının broker işlem raporları olmadan 'gerçek işlem maliyeti ölçüldü' denmez.

## 3. İlk kez gözlenen ileri karar
`decisions/watch/state.json` ilk kez okunduğunda, kaynak dosyanın SHA256'sı, gözlem saati, son kapanmış bar tarihi, pozisyonlar ve veri yaşı saklanır. Bar üç günden eskiyse `all_fresh=false`; geçmiş NAV **ileri getiri gibi kaydedilmez**. İleri gerçekleşen getiriyi hesaplamak için ileride ilk gözlem sonrasındaki piyasa fiyatlarıyla ayrı, sıralı muhasebe gerekir; H088 bu henüz olmayan sonucu üretmez.

## 4. Bütünlük ve eksiklik
`decisions/evidence/quotes.jsonl` ve `watch_decisions.jsonl` her satır için önceki satırın SHA256'sına bağlıdır. Git geçmişi ek denetim izi sağlar. Zincir bozulursa yeni satır ekleme reddedilir. Her kaynak için hata ayrı kaydedilir; eksik veri **başarısız workflow** olarak işaretlenir, mümkünse eksikliği belgeleyen JSONL önce commit edilir. Git push başarısızsa workflow da başarısızdır. GitHub Actions zamanlayıcısının dakikası garantili değildir.

## 5. Kurulum ve denetim
PR ana dala alındıktan sonra `H088 — Prospective independent market evidence` workflow'unu `Run workflow` ile başlatın. Başarılı olursa `decisions/evidence/` altında iki zincir görünür. Watch eskiyse kırmızı sonuç **doğru davranıştır**; önce `Paper watch H063-H065` / `daily` workflow'unun gerçek zamanlı tamamlanmasını sağlayın.

**30 günün başlangıcı:** ilk taze, bütünlüğü doğrulanmış, iki sağlayıcısı tamam gözlem. 30 takvim günü geçmeden ve ileri getiri muhasebesi ayrıca doğrulanmadan hiçbir stratejiye yeni ACCEPT verilmez.

### Açık kalan zorunlu kanıtlar
1. Gerçek broker fill ve fee raporları; komisyon kademesi, gerçekleşen spread, impact, funding ve borrow.
2. Aynı stratejinin sinyallerinin iki bağımsız veri sağlayıcıda *yeniden hesaplanması*. H088 şu anda yalnızca anlık piyasa quote karşılaştırır; bağımsız tarihsel strateji backtest'i değildir.
3. Emir/sinyal zamanı ile sonraki kapanmış barı eşleyen, finansman ve nakit akışını içeren prospektif portföy muhasebesi; bugün H088 yalnızca ilk-gözlem pozisyon kaydıdır.
4. Delisted semboller, split/corporate actions, data leakage ve zaman senkronizasyonunun ayrıca incelenmesi.

İlk aşama **ölçüm altyapısı ve fail-closed veri toplama**; henüz tam bağımsız performans kanıtı değil.
