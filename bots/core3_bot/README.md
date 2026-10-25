# core3_bot — BTC + ETH + SOL, H054 çekirdek kuralı, Bitget SPOT

Kaynak araştırma: [quant_lab](https://github.com/evsayar33-oss/quant_lab) → `VARLIK_STRATEJI_KITABI.md`, H054 (ACCEPT), H074, H075 (SOL, karar kapısında).

## Kural (değiştirmeyin — `bot/signal.py`)
Her varlık için, kapanmış 4 saatlik barda:
1. Kapanış > son 200 günün ortalaması **ve** 30/90/180 günlük getirilerden en az biri pozitif → long.
2. Pozisyon = min(1; 0,40 / son 30 gün yıllık oynaklık) × (kasanın 1/3'ü).
3. Hedef mevcut pozisyondan 0,10'dan fazla farklıysa işlem yapılır. Aksi halde beklenir.
4. Short yok, kaldıraç yok, sadece spot (funding yok).

## Emir türü
En iyi alış/satış fiyatına **limit emir** (spread ödenmez, kayma olmaz; fiyat orta fiyattan en çok %0,2 uzakta).
60 sn'de dolmazsa iptal edilir ve bir kez yeni fiyatla tekrar verilir. Kalan kısım **piyasa emri** ile tamamlanır (yedek).

## Bileşik getiri
Bot her çalışmada pozisyonları **toplam kasaya** (USDT + coinlerin güncel değeri) göre hesaplar.
Kâr ve zarar otomatik olarak sonraki pozisyonlara yansır (bileşik büyüme). Ayrı bir ayar gerekmez.

## Minimum kasa
- Bitget spot en küçük emir: 1 USDT. Bot 5 USDT altındaki emirleri atlar.
- En küçük düzeltme = 0,10 × kasa/3. Bu en az 5 USDT olmalı → **teknik minimum 150 USDT**.
- **Önerilen: en az 500 USDT.** Küçük kasada yuvarlama ve komisyon (%0,1) oransal olarak büyür.
- Kaybetmeyi göze alabileceğiniz tutarı yatırın: geçmişte en büyük düşüş yaklaşık −%25, gelecekte daha büyük olabilir.

## Kurulum (telefondan)
1. Bu klasörü yeni bir repoya kopyalayın (ör. `core3_bot`). Repo **private** olsun.
2. Bitget → API Yönetimi → yeni anahtar: **sadece Spot Trade izni, çekim (withdraw) KAPALI**, IP kısıtı mümkünse açık.
3. Repo → Settings → Secrets and variables → Actions → Secrets: `BITGET_KEY`, `BITGET_SECRET`, `BITGET_PASSPHRASE`.
4. Settings → Actions → General → Workflow permissions → **Read and write**.
5. İlk 2–4 hafta **kuru çalıştırma**: `LIVE` değişkenini tanımlamayın. Actions günlüğünde planı izleyin.
6. Canlıya geçiş: Variables → `LIVE` = `1`.
7. Acil durdurma: `state/STOP` adında boş bir dosya ekleyin (bot hiçbir işlem yapmaz).

## Kurallar
- SOL, quant_lab H075 ACCEPT almadan canlıya alınmamalı. O zamana kadar `config.yaml` → `assets: [BTC, ETH]` (= H054).
- `bot/signal.py` quant_lab `lab/core.py` ile aynıdır; `tests/test_bot.py` her çalışmada bunu kontrol eder. Test kırılırsa bot çalışmaz.
- Bitget yerine başka spot borsa: `bot/run.py` içindeki veri ve emir kısmı değişir; kural aynı kalır.
