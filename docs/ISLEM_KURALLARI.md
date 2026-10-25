# İşlem ve para yönetimi kuralları (laboratuvarın kanıtıyla)

Bu dosya, bir stratejiyi kârlı yapan veya batıran kuralları tek yerde toplar. Her kuralın yanında kanıtı vardır.

## 1. Kazanma oranı ve RR birlikte okunur
- Beklenti = kazanma oranı × ortalama kazanç − kayıp oranı × ortalama kayıp.
- Başa baş kazanma oranı = 1 / (1 + RR). 1:1 → %50, 1:2 → %33, 1:3 → %25.
- **Kural:** bir strateji ancak kazanma oranı başa baş oranının açıkça üstündeyse kârlıdır (marj). Her rapor bu marjı yazar (`lab/perp.trade_stats` → `wr_margin`).
- **Kanıt:** hedef uzadıkça kazanma oranı düşer. islem ICT araması: 1:4–1:6 RR'de kazanma %20–29, başa baş ile aynı; kilitli dönemde −0,06R. H077: kazanma %50–60, başa baş %47–58.
- **Sonuç:** RR seçimi tek başına kâr yaratmaz; girişin kalitesi (avantaj) gerekir.

## 2. Her işlemde risk sabit ve küçük
- **Kural:** işlem başı risk kasanın %0,5–1'i (stop mesafesine göre pozisyon büyüklüğü). `lab/trade_engine.SizeCfg("atr_risk", 0.01)`.
- **Kanıt:** islem Stage A — boyutlandırma ortalamanın işaretini değiştirmedi; avantajsız sistemi kurtarmadı, ama düşüşü sınırladı.

## 3. Stopsuz işlem yok
- **Kural:** her işlemin girişte belli bir stopu vardır.
- **Kanıt:** H077 stopsuz ayarlarında tek işlem kaybı −%12 (endeks) ile −%30 (kripto). Videodaki "ortalama kayıp $0" kısa bir seçilmiş dönemdi.

## 4. Kaldıraç kenar yaratmaz
- **Kural:** kaldıraç sadece kanıtlı (ACCEPT) bir kuralda ve önceden yazılmış düşüş sınırıyla. 
- **Kanıt:** H072 A0: 2x endeks 1929–32'de −%98. H070 kaldıraç testi: Sharpe sabit, düşüş kaldıraçla büyür.

## 5. Trend filtresi düşüşü azaltır, getiriyi değil
- **Kural:** long sistemlerde SMA200 / momentum filtresi kuyruk riskini keser.
- **Kanıt:** H072 A3: ABD piyasası 1928–2026 düşüş −%84 → −%57; getiri farkı 1966 sonrası küçük. H054/H074: kriptoda düşüş yarıya iner.

## 6. Kasa koruma kuralları
- Test edilenler: kasa düşüş sigortası, volatilite hedefi, kasa eğrisi filtresi, günlük kayıp limiti, BTC çöküş bekçisi, felaket stopu (`lab/protect.py`, `config/protection.yaml`).
- **Kanıt:** komşu eşiklerde ve tüm zaman dilimlerinde kabul kuralını geçen olmadı; sadece aritmetik kurallar (likidasyon tamponu, coin başı sınır) her zaman açık.

## 7. Maliyet ve funding
- **Kural:** her backtest 2x maliyette de kârlı olmalı. Perp'te funding hesaba katılır.
- **Kanıt:** Bitget funding (2026-10, yıllık): SPX %11, XAU %12, XAG %15, BTC %7. SPX al-tut perp ile %6,4 → %1,2.

## 8. Seçim şansı
- **Kural:** binlerce denemeden seçilen "en iyi" kural kanıt değildir; DSR, kilitli dönem ve zaman makinesi şarttır.
- **Kanıt:** H062 73.005 deneme → 0; H073 29.912 deneme → 0; H073 ek analizi: en iyi 10 kural yükselen piyasada al-tutu 130 kesimin 9'unda geçti.

## 9. Bot sadece ACCEPT ile işlem yapar
- `decisions/registry.json` → `verdict: ACCEPT`. Bugün: H052, H054.
