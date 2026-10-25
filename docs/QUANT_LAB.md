> **Başka bir yapay zekâ veya kişi test çalıştıracaksa önce [`AGENTS.md`](AGENTS.md) okunmalı.** Her seçim testinden sonra zaman makinesi kontrolü önerilir.

> **Varlık başına bot kuralları (Bitget/spot, Fibonacci testi dahil):** [`VARLIK_STRATEJI_KITABI.md`](VARLIK_STRATEJI_KITABI.md).

> **İki labın birleşik sonucu (endeksin kendisine karşı, 1928–2026):** [`SENTEZ_RAPORU.md`](SENTEZ_RAPORU.md) — H072 sentez çalışması.

# quant_lab — Strateji Laboratuvarı ve Karar Merkezi

Bu repo tüm al-sat botlarının **nihai karar merkezidir**. Bir bot bir stratejiyi ancak burada doğrulanmış ve
`ACCEPT` almışsa kullanır. LLM yok, ücretli API yok. Her şey GitHub Actions'ta çalışır.

## Akış

```
Fikir → Discovery scan (her şeyi dener, dürüst sıralar)
      → Hipotez (hypotheses/registry.yaml)
      → Karar kapısı: walk-forward + DSR + PBO + Reality Check + gecikme + rastgele giriş + parametre komşuluğu + ...
      → decisions/registry.json (ACCEPT / WATCH / REJECT / DEGRADED + hedefler + bot başına HRP sermaye dağılımı)
      → Canlı (paper) takip: bozulan strateji otomatik DEGRADED olur
      → Botlar lab/client.py ile okur, sadece ACCEPT'e göre işlem yapar
```

## Kapsam (`python run.py --list`)

| Katman | İçerik |
|---|---|
| **Zaman dilimleri** | `1h`, `4h`, `1d`, `1w`, `1mo`. Haftalık/aylık barlar günlükten üretilir. Hisse 1h verisi ~2 yıl (Yahoo sınırı), kripto 1h/4h uzun geçmiş. Bütün metrikler bar/yıl ölçülerek yıllıklandırılır |
| **Çoklu zaman dilimi** | Üst zaman dilimi trend filtreleri (`htf_week_sma10/30`, `htf_month_sma10`), sadece **tamamlanmış** üst barlarla |
| **İndikatörler** | 60+: 7 hareketli ortalama tipi, RSI, Stoch, StochRSI, %R, CCI, MFI, ROC, MACD, PPO, TRIX, TSI, AO, UO, Coppock, DMI/ADX, Aroon, Vortex, WaveTrend, Supertrend, PSAR, Ichimoku, Heikin-Ashi, Bollinger, Keltner, Donchian, ATR, Choppiness, Z-skor, Hurst, OBV, CMF, A/D, Chaikin, Force, VWAP, EOM, mum formasyonları |
| **Giriş kuralları** | 53 kural / **518 parametre varyantı** (ör. RSI 2,3,5,7,9,14,21,28 × seviye × çıkış). Long, short, ikisi |
| **Kombinasyonlar** | İki sinyal onayı: `A+B` = A sinyali, B sinyali aynı barda veya son 3/5 bar içinde geldiyse. Taramada en iyi 6 kural ailesi ikili eşlenir (30 kombinasyon); hipotezde `confirm:` ile tüm ızgara denenir (çok büyük alanda 1500 varyantlık rastgele arama) |
| **Filtreler (19)** | Trend SMA50/100/200, ADX, endeks rejimi, düşük vol, hacim, temel kalite/değer, üst zaman dilimi trendi, VIX, VIX-spike, USDTRY stresi, faiz eğrisi, endeks üyeliği |
| **Stop-loss** | ATR (1.5/2/3), yüzde (3/5/8/12), swing-low (5/10/20 bar), breakeven, ATR/yüzde trailing (chandelier), MA trailing, zaman stopu |
| **Kâr alma** | ATR hedef, yüzde hedef, R-katı (1.5/2/3), **kısmi kâr alma** (1R/2R'de %50 + kalan trailing + stop başabaş), sabit tutma süresi |
| **44 çıkış ayarı** | Yukarıdakilerin seçilmiş kombinasyonları (`run.py --list`) |
| **Pozisyon boyutu** | Eşit, ATR-risk (%0.5/%1/%2 risk), pozisyon başı vol hedefi; brüt kaldıraç sınırı; Kelly oranı raporu |
| **Ağırlık stratejileri (47)** | Momentum (kesitsel, zaman serisi, residual, frog-in-pan, ivme, vol-yönetimli, trend kalitesi), düşük vol, idiosenkratik vol, MAX, BAB, mevsimsellik, ay dönümü, RSI rotasyonu, hacim şoku, **pairs trading**, **walk-forward ML (ridge)**, **bilanço sonrası drift**, **makro risk anahtarı**, breadth, USDTRY korunma |
| **Temel faktörler (21)** | E/P, B/P, S/P, CF/P, EBIT/EV, ROE, ROA, brüt kârlılık, accruals, varlık büyümesi, kaldıraç, net hisse ihracı, büyüme, küçük şirket, Piotroski F, Magic Formula, QVM, değer+momentum, kalite+düşük vol |
| **Veri (ücretsiz)** | yfinance, ccxt (Bitget/OKX/KuCoin), İş Yatırım (BIST bilanço, TTM, yayın gecikmeli), SEC EDGAR (ABD, gerçek dosyalama tarihi), makro (^VIX, ^TNX, ^IRX, USDTRY=X), S&P 500 geçmiş üyelik |

## Karar kapısı (`lab/validation.py` → `GATE`)

| Kontrol | Eşik | Neden |
|---|---|---|
| OOS süresi | ≥ 3 yıl | Kısa örnek şans olabilir |
| Deflated Sharpe | ≥ 0.90 | Denenen **tüm** varyantların şişirdiği Sharpe'ı düzeltir |
| PBO (CSCV) | ≤ 0.50 | "En iyi backtesti seçme" adımı aşırı uyum mu? |
| White Reality Check p | ≤ 0.10 | En iyi sonuç veri madenciliği mi? |
| OOS Sharpe | ≥ 0.5 | **Risksiz faizin üstünde** ölçülür; TL piyasada **USD'ye çevrilerek** ölçülür |
| OOS MaxDD | ≥ -45% | Dayanılabilir kayıp |
| Bootstrap P(Sharpe>0) | ≥ 0.85 | Tek döneme bağlı değil |
| Pozitif yıl oranı | ≥ 55% | Zamanda istikrar |
| 2× maliyet | eşit ağırlıklı benchmark'ı geçmeli | Maliyete dayanıklı, beta değil |
| İşlem sayısı (kurallar) | ≥ 30 | İstatistik anlam |
| 1 bar gecikme | Sharpe'ın ≥ %40'ı kalmalı | Gecikmeye dayanıklı |
| Rastgele giriş testi | p ≤ 0.10 | Kâr çıkışlardan değil sinyalden gelmeli (işlem sayısı ve maruziyet eşlenir) |
| Parametre komşuluğu | komşuların ≥ %50'si kârlı | Tepe değil plato |

Raporda ayrıca: gürültü testi, Monte Carlo işlem karıştırma, walk-forward verimliliği, rejim analizi (boğa/ayı,
sakin/stresli, VIX bantları, faiz eğrisi), haftanın günü / ay / saat profili, VaR/CVaR, Ulcer, Omega, tail ratio,
up/down capture, aylık getiri ısı haritası ve grafikler.

## Zamanlama ve kâr maksimizasyonu çalışmaları (her rapor)

- **Event study:** Sinyalden sonra 1, 2, 3, 5, 10, 15, 20, 40, 60 bar ileri getiri, isabet oranı ve t-istatistiği. En iyi tutma süresini verir.
- **Stop × hedef × süre ızgarası:** Gerçek high/low yollarıyla stop %2–12, hedef %3–25, süre 3–40 bar. Isı haritası olarak verilir.
- **Portföy katmanları:** Vol hedefleme, drawdown freni, equity-curve filtresi. Calmar oranına göre en iyisi önerilir.
- **MFE/MAE:** Her işlemde en iyi ve en kötü fiyat hareketi, edge ratio, R-katı, SQN, Kelly.

Bunlar örneklem içi teşhislerdir. Daha iyi bir çıkış bulunursa hipoteze `exits: [...]` olarak eklenir ve kapıdan geçmesi beklenir.

## Gerçekçilik

- Sinyal t kapanışında, işlem t+1 açılışında. Gün içi stop ve hedef high/low ile kontrol edilir; ikisi aynı barda olursa stop sayılır. Boşlukta dolum açılış fiyatıdır.
- BIST ±%10 tavan/taban: kilitli açılışta emir dolmaz, bir sonraki bara bekler.
- Likidite: `min_adv` altındaki hissede pozisyon açılmaz.
- Maliyet: komisyon + slipaj, açığa satış borç maliyeti, kripto funding.
- Temel veri yayın tarihinden önce görünmez. SEC'de ilk açıklanan değer kullanılır (sonradan yapılan düzeltme geçmişe sızmaz).
- Intraday barlarda günlük makro veri bir gün sonra görünür.
- S&P evrenlerinde geçmiş üyelik maskesi uygulanır (survivorship kontrolü).

## Sonuçlar nerede? (repo şişmez)

- **`main` dalı:** Sadece kod ve küçük karar dosyaları (`decisions/`). Botlar buradan okur.
- **`results` dalı:** Tüm raporlar, grafikler, OOS serileri, tarama tabloları ve her varyantın ayrı sonucu (`*_variants.csv`). Bu dal her yayında **tek commit** olarak yeniden yazılır. Eski grafikler git geçmişinde birikmez, repo boyutu sabit kalır.
- Telefondan: repo → dal seçici → `results` → `results/` klasörü.
- Ad-hoc denemeler sadece artifact (14 gün) ve Telegram olarak gelir.
- Veri her çalıştırmada bir kez indirilir ve paralel işlere cache ile dağıtılır. Yahoo isteği 25'lik gruplar ve 4 deneme ile yapılır (rate-limit koruması).

## Telefondan kullanım (GitHub → Actions)

| Workflow | Ne zaman | Ne yapar |
|---|---|---|
| **Discovery scan** | Her ayın 1'i + elle | Evren × zaman dilimi matrisi. Tüm kuralları, varyantları ve stratejileri dener. `results/scan_*.md` + önerilen YAML |
| **Validate hypotheses** | Cumartesi + elle (id veya id listesi) | Her hipotez **paralel** bir işte doğrulanır. Sonra kayıt birleştirilir, commit edilir, Telegram'a gönderilir |
| **Live tracking** | Hafta içi 21:47 | ACCEPT stratejileri dondurulmuş varyantla paper takip edilir. Bozulma olursa DEGRADED yapılır |
| **Ad-hoc backtest** | Elle | `strategy`, `rule`, `scan`, `vbt`, `bt` modları; zaman dilimi seçilir. Karar yazmaz |
| **Arena screen** | Her ayın 2'si + elle | Eleme motoru → arena kadrosu + switcher backtest kapısı. Karar yazmaz |
| **Synthesis study** | Her ayın 9'u + elle | H072: yayınlanmış kurallar endeksin kendisine karşı (1928–2026), C1–C7 + zaman makinesi, izlenenlerin ileri kaydı. Karar yazmaz |
| **Arena** | Her 4 saatte bir | ~100 strateji paper takip, emeklilik, rejim switcher, Telegram, panel (Pages) |

Secrets: `TELEGRAM_TOKEN`, `CHAT_ID`. İsteğe bağlı: `SEC_USER_AGENT` ("ad eposta").
Settings → Actions → General → Workflow permissions → **Read and write**.

## Hipotez ekleme (`hypotheses/registry.yaml`)

```yaml
- id: H040                      # asla tekrar kullanılmaz
  rule: wavetrend_reversal      # veya  strategy: qvm_composite
  universe: bist30
  timeframe: 4h                 # 1h | 4h | 1d | 1w | 1mo
  for_system: bist_orderflow_quant
  start: "2012-01-01"
  filters: [none, trend_sma200, htf_week_sma10]   # veya all
  exits: all                    # veya [0, 18, 22]; boş = kademeli arama (tüm çıkışlar en iyi 3 varyanta)
  sizes: all                    # pozisyon boyutu modları (kademe 3)
  side: long                    # long | short | both
  confirm: macd_cross           # isteğe bağlı: ikinci sinyal onayı (kombinasyon)
  confirm_within: [0, 3, 5]     # onay penceresi (bar)
  max_positions: 10
  status: active
  note: "neden test ediyoruz"
```

## Strateji arenası (LLM yok) — `config/arena.yaml`

Video tarzı "AI ajan + 100 canlı strateji + rejime göre geçiş" sistemi, **kural tabanlı** olarak.

```
Eleme motoru (aylık)  →  Arena (~100 strateji, her 4h kapanmış bar)  →  Rejim switcher  →  Panel + Telegram
 lab/screen.py            lab/arena.py                                  lab/switcher.py     dashboard/index.html
```

**1. Eleme motoru (`python run.py --screen`, workflow "Arena screen", her ayın 2'si):**
Her kural × tüm parametre ızgarası × her coin denenir (hepsi deneme sayılır). Her (coin, kural) için tek en iyi
nokta değil, **en sağlam bölgenin merkezi** seçilir: skor = min(kendi Sharpe, komşuların ortalama Sharpe).
Sonra adım adım elenir. İlk takıldığı adım sade Türkçe ile yazılır (ajan günlüğü).

| Adım | Kontrol (eşikler sonuçlara bakılmadan yazıldı) |
|---|---|
| S0 | En az 3 yıl veri |
| S1 | **Son 3 yıl, son 5 yıl ve tüm geçmiş** pencerelerinin hepsinde net kâr + ≥ 30 işlem |
| S2 | Kâr faktörü ≥ 1.15, 1x maks. düşüş ≥ −%40 |
| S3 | 2× maliyette hâlâ kârlı |
| S4 | Komşu ayarların ≥ %50'si kârlı (plato) |
| S5 | 1 bar geç girişte Sharpe'ın ≥ %40'ı kalır |
| S6 | Takvim yıllarının ≥ %60'ı kârlı |
| S7 | PSR ≥ 0.90 |
| Tier A | Ayrıca DSR ≥ 0.90 (tüm huni denemeleri sayılır) → rapora **önerilen hipotez YAML** olarak yazılır |

**2. aşama (her taramada, isteğe bağlı):** S1'i geçen adaylarda filtre × çıkış matrisi (6 filtre × 6 çıkış:
trend SMA200, ADX20, haftalık trend, BTC rejimi, düşük volatilite) ve iki sinyal kombosu (en sık 6 kural ailesi,
0/3/5 bar onay penceresi) denenir. Her aday için en sağlam hücre seçilir (kendisi ve komşuları birlikte iyi olmalı);
kombo, kuralın tek başına halini geçmezse aday olmaz. Bütün ek denemeler DSR'a eklenir ve aynı S1–S7 adımları
uygulanır. Kapatmak için `stage2.enabled: false` veya workflow girişi `stage2: off`.

**Zaman dilimleri:** `timeframes: [4h, 1d]`. Her biri ayrı arenadır (`decisions/arena/4h/`, `decisions/arena/1d/`),
tarama paralel iki işte çalışır. Bar uzunluğuna bağlı rejim ayarları `by_timeframe` altında.

Sonuç bir **aday listesidir**, karar değildir. Tier A adaylar `hypotheses/registry.yaml`'a eklenirse (tek coin için
`tickers: [SNX/USDT]`) normal karar kapısından geçer. Rapor: `results` dalı → `results/arena_screen_*.md` + `.csv`.

**Karne:** her strateji için 3 yıl / 5 yıl / tüm geçmiş (`report_windows_years`). Veri bir pencereyi kapsamıyorsa
"veri yok" yazılır, uzatılmaz. Yanında **perp simülasyonu**: $1000, işlem başı %10 marjin, 1x/3x/5x/10x kaldıraç,
izole marjin likidasyonu. Kaldıraç edge yaratmaz; tablo likidasyon maliyetini görünür yapar.

**2. Arena (`python run.py --arena`, workflow "Arena", her 4 saatte bir, bar kapanışından 9 dk sonra):**
En fazla 100 üye. Eleme geçenler **aktif**; boş yerler en yakın adaylarla **kontrol** üyesi olarak dolar (switcher
kullanmaz). Ayarlar katılım anında dondurulur, asla yeniden fit edilmez. Her çalışmada yeni veriyle yeniden hesaplanır,
katılım tarihinden sonraki barlar **ileri (paper) kayıt**tır. Kapanmamış bar her zaman atılır. Emeklilik: ileri düşüş
> 1.5× backtest düşüşü (her an) veya 120 gün sonra ileri Sharpe < 0.

**3. Rejim (`lab/regime.py`):** coin başına Trend ↑ / Trend ↓ / Yatay / Volatil. Geçmiş 1 yılın en oynak %20'si →
Volatil; değilse ADX ≥ 25 ve Kaufman verimlilik oranı ≥ 0.30 → Trend; diğerleri Yatay. Yeni rejim 3 bar sürmeden kullanılmaz.

**4. Switcher (`lab/switcher.py`):** her gün, her stratejinin **kendi coininin şu anki rejiminde** geçmişte nasıl
çalıştığına bakar (üstel azalan Sharpe, az kanıtta 0'a çekilir). Pozitif skorlu en iyi 5'e eşit ağırlık, coin başı
≤ %40, kalanı nakit. Her yeni barla skorlar güncellenir: kendini geliştirir. Ayar ızgarası (3 yarı ömür × 3 top-k)
raporda tamamen gösterilir.

**Kasa koruma testi (`python run.py --protect`, workflow "Protection study", her aylık taramadan sonra):**
arenadaki aktif üyelerin eşit ağırlıklı portföyünde 6 koruma kuralı test edilir: kasa düşüş sigortası, volatilite hedefi, kasa eğrisi filtresi, günlük kayıp
limiti, BTC çöküş bekçisi, felaket stopu. Ölçüm: tüm geçmiş (CAGR, Sharpe, maks. düşüş, CVaR), 6 gerçek kriz
(COVID 2020, Mayıs 2021, LUNA, FTX, Ağustos 2024, Ekim 2025) ve Monte Carlo iflas olasılığı. Bir kural sadece
komşu eşiklerin hepsinde ve her zaman diliminde kabul kurallarını geçerse açılır. Likidasyon tamponu ve coin
başı sınır matematiktir, hep açıktır. Rapor: `results/protection_*.md`, özet: `decisions/arena/<tf>/protection.json`.

**Botlar switcher'ı ne zaman kullanır?** `lab/client.py` → `arena_allocation("4h")` / `arena_allocation("1d")` boş döner, ta ki:
backtest kapısı (her pencerede eşit ağırlığı yener + 2× maliyette kârlı + düşüş ≥ −%45) **ve** ≥ 180 gün ileri
kayıtta eşit ağırlığı yenene kadar.

**Panel (telefondan):** GitHub Pages. Bir kez: Settings → Pages → Source: **GitHub Actions**. Adres:
`https://evsayar33-oss.github.io/quant_lab/`. Sekmeler: Özet (switcher, tutulanlar, ileri kayıt), Arena (100
strateji, karne + kaldıraç + rejim Sharpe'ı), Rejimler, Eleme hunisi. Panel artifact olarak yayınlanır, repo büyümez.
Repo public olduğu için panel de public'tir.

**İlk çalıştırma sırası:** Actions → "Arena screen" → Run workflow (≈ 30–90 dk). Bittikten sonra "Arena" kendi
saatinde çalışır (veya elle çalıştır).

**Dürüst sınırlar:** üyeler aynı geçmişte seçildiği için backtest ve switcher backtest'i iyimserdir; gerçek test ileri
kayıttır. Survivorship: bugünün coin listesi. Funding sabit oran, likidasyon yaklaşık. GitHub Actions zamanlaması
5–30 dk gecikebilir; bu yüzden sadece 4h/1d barlar (scalping yok).

## İsteğe bağlı çıkış ve portföy katmanları (2026-10-17'den beri)

- Hipotezde `exits:` yoksa sadece kuralın kendi çıkışı (#0) kullanılır. `exits: all` → 44 çıkışın hepsi;
  `exits: [18, 20, 28]` → sadece bunlar. Her denenen çıkış DSR deneme sayısına eklenir.
- `overlays:` yoksa portföy katmanı denenmez. `overlays: all` veya `[vt15, dd20, eqma_l]`.
- Pozisyon boyutu taraması (`sizes`) değişmedi.

## Kasa koruma teşhisi (her hipotez raporunda, her piyasada)

Her doğrulama raporuna "Kasa koruma" bölümü eklenir: son varyantın tüm geçmişi üzerinde 5 kural (kasa düşüş
sigortası, volatilite hedefi, kasa eğrisi filtresi, günlük kayıp limiti, piyasa çöküş bekçisi) piyasaya özel gerçek
krizlerde test edilir (BIST: 2013 Gezi, Ağustos 2018 kur, COVID, Mart 2021, Aralık 2021, 2023 deprem, Mart 2025 ·
ABD: 2008, 2011, 2015, 2018 Q4, COVID, 2022, Nisan 2025 · metaller/çoklu varlık · kripto). Eşikler ve kabul
kuralları `config/protection.yaml` içinde. Bu bölüm stratejiyi ve kararı DEĞİŞTİRMEZ. Bir kuralı kullanmak için
hipoteze `overlays:` olarak ekleyin; kapı ona karar verir. Kapatmak: `protection_study: false`.

## Botlara bağlama

`lab/client.py` dosyasını bot reposuna `quant_lab_client.py` adıyla kopyala:

```python
from quant_lab_client import approved, allocation
for h in approved(system="bist_orderflow_quant"):
    print(h["id"], h["timeframe"], h["targets"])
print(allocation("bist_orderflow_quant"))   # {"H001": 0.6, "H013": 0.4}
```

Kayıt alınamazsa veya 10 günden eskiyse boş döner; bot kendi varsayılanına geçer (fail-safe).

## Bilinen sınırlar (dürüst liste)

- BIST için ücretsiz geçmiş endeks üyeliği yok. Survivorship bias BIST'te kalır. ABD'de maske var ama borsadan çıkmış şirketlerin fiyatı ücretsiz kaynaklarda yok.
- Hisse 1h verisi ~2 yıl. Intraday hisse sonuçları bu yüzden kısa OOS ile sınırlı; kapı ACCEPT vermez, WATCH verebilir.
- ABD akış kalemleri yıllık 10-K'dan gelir. BIST bilanço yayın tarihi tahmini bir gecikmeyle (75/100 gün) modellenir. Bu yüzden bilanço sonrası drift bir yaklaşıktır.
- Kripto funding sabit yıllık oranla yaklaşıklanır (gerçek funding değişkendir).
- Emir defteri, kısmi dolum ve piyasa etkisi modellenmez. Slipaj sabit orandır.

## Yerel test

```bash
pip install -r requirements.txt
python tests/test_core.py      # 23 test
python tests/test_arena.py     # arena testleri
python run.py --screen --synthetic && python run.py --arena --synthetic --site site
python run.py --synthetic --rule rsi_reversal
python run.py --scan --synthetic
```

## Dosya yapısı

```
lab/data.py            veri (çoklu zaman dilimi, makro, risksiz faiz, kur, önbellek)
lab/panel.py           Panel (OHLCV + temel + makro + üyelik + bar/yıl)
lab/indicators.py      teknik indikatörler
lab/rules.py           giriş/çıkış kuralları + 19 filtre (çoklu zaman dilimi, makro)
lab/trade_engine.py    işlem motoru: stop/hedef/kısmi/breakeven/trailing/MA/zaman, boyutlandırma, limitler, MFE/MAE
lab/engine.py          ağırlık motoru (maliyet, borç, funding, üyelik)
lab/strategies/        ağırlık stratejileri: fiyat, temel, gelişmiş (pairs, ML, drift, makro)
lab/fundamentals.py    İş Yatırım + SEC EDGAR
lab/membership.py      geçmiş endeks üyeliği
lab/candidates.py      varyant üretimi (kademe 1-3) + paralel çalıştırma
lab/validation.py      karar kapısı
lab/robustness.py      sağlamlık + zamanlama + kâr maksimizasyonu çalışmaları
lab/scanner.py         keşif taraması (+ Reality Check)
lab/metrics.py         performans, risk, anlamlılık (PSR, DSR, PBO, Reality Check)
lab/charts.py          grafikler
lab/decision.py        karar kaydı + HRP dağılımı
lab/live.py            canlı takip + bozulma tespiti
lab/client.py          botlar için okuyucu (+ arena_allocation)
lab/screen.py          arena eleme motoru (huni, plato seçimi, ajan günlüğü)
lab/perp.py            karne (3y/5y/tüm) + izole marjin perp simülasyonu
lab/regime.py          coin başı rejim (trend/yatay/volatil) + histerezis
lab/arena.py           arena kadrosu, ileri kayıt, emeklilik, sinyaller
lab/switcher.py        rejime göre strateji seçen meta-strateji
lab/dashboard.py       panel verisi (data.json)
dashboard/index.html   telefon dostu panel (GitHub Pages)
config/arena.yaml      arena eşikleri (sonuçlardan önce yazıldı)
```
