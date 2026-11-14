# P17 — H088 sonrasinda veri erisimi ve ileri gozlem kanit duzeltmesi

14 Kasim 2026 ana dal H088 run 43583351181: regresyon basarili, collect basarisiz. Binance BTC/ETH HTTP 451; Bybit BTC/ETH HTTP 403. Hata verileri Git JSONL dosyalarina saklanmis. Watch kaynagi 21 Ekim tarihli ve 24 gun eski. 13 ve 14 Kasim eski Paper Watch scheduled run'lari NameError suffix ile basarisizdi, ancak guncel main watch.py imzasi artik suffix parametresi iceriyor.

## Kaynak duzeltmesi

Dort USDT linear perpetual kaynagi: Binance, Bybit, OKX, Bitget. BTCUSDT ve ETHUSDT icin her biri ayri iki borsadan taze kotasyon gerekli. Bir borsa HTTP hatasi verirken digerinin borsa ismiyle gizlenmez. Kaynak saatlerinin farki 90 saniyeyi asarsa karsilastirma yapilmaz.

OKX ve Bitget sozlesmelerinin kontrat carpani dogrulanmadigindan alis-satis miktarini coin miktari saymiyoruz: parasal top-of-book kapasitesi ve fee dahil tam maliyet bos birakiliyor. Gorunen spread islem fill kaniti degildir.

## Gercek Actions kaniti

Run: https://github.com/evsayar33-oss/quant_superlab/actions/runs/43583846589

Binance ve Bybit hata vermeye devam ediyor. OKX ve Bitget, BTC ve ETH icin toplam 4 kotasyon sagladi; iki farkli kaynak sarti gecti. Paper Watch gercek Yahoo verileriyle H063/H064/H065 icin 2026-11-13 son kapanis barini hesaplayabildi. H063 ve H064 nakit, H065 YM=F long. Bu salt okunur smoke kaniti, main uzerinde yeni ileri sicil yerine gecmez.

## Merge sonrasi yapilacaklar

1. PR'yi main dalina merge edin.
2. Actions > Paper watch H063-H065 > Run workflow > mode=daily. Isin basarili oldugunu ve decisions/watch/state.json ile decisions/watch/observations.csv dosyalarinin main'e islenmis oldugunu kontrol edin.
3. Actions > H088 — Prospective independent market evidence > Run workflow. Yeni surum dort borsayi dener; en az iki ayri borsa olmasi yeterli.
4. Workflow_run tetigi Paper Watch basariyla bitince H088'i de calistirir. GitHub schedule gercek calisma saati gecikebildigi icin iki farkli cron'un kesin sirayla bitmesi garanti edilmez.
5. decisions/evidence/quotes.jsonl ve watch_decisions.jsonl dosyalarinda hasli, tarihli, borsa kaynakli kayitlari dogrulayin.

## Eksik kalanlar

- Gercek broker fill raporu: anonim hale getirilmis zaman, sembol, yon, fiyat, adet, islem komisyonu, funding ve marj. Bu veriler olmadan gercek execution maliyeti olculemez.
- OKX ve Bitget sozlesme carpani, funding interval ve emir defteri miktar birimi; piyasa etkisi ve kayma.
- H056 icin zaman uyumlu ve tarihsel olarak bagimsiz funding verisi, delisted kontratlar, borsa bazli ayni strateji tekrar testi.
- H063-H065 icin ilk-gorulen pozisyondan sonraki gercekten ilerleyen fiyat adimlarini kaydeden maliyetli, nakit akisi tutarli forward NAV muhasebesi. Eski NAV yeniden hesaplamalari ileri kanit yerine kullanilmaz.
- Ilk taze ve eksiksiz karar anindan sonra 30 takvim gunu. 30 gun istatistiksel islem stratejisi kaniti icin tek basina yeterli olmayabilir.

Bu PR yeni strateji onayi, para ile emir, parametre optimizasyonu ve ana dalda otomatik merge yapmaz.
