# Bağımsız araştırma köprüsü: Eaverse V7 → quant_superlab (RESEARCH ONLY)

Bu entegrasyon, gerçek Binance Vision SHA doğrulamasından sonra Eaverse'in
kendi içinde oluşturduğu 32 adayın **aynı haftalarda hizalanmış ve
maliyet-stresli** getiri matrisini, kendi kaynak kanıt dalından alır.

## Çalışan ölçüm

- 8 varlığın her biri `research/eaverse-v7-{symbol}-evidence` dalının
  **baş commit SHA**'sına sabitlenir; ilk ve yeni paralel SHA-zincirli
  `studies.jsonl` / `statistical_trials.jsonl` doğrulanır.
- Yalnız kaynak/politika SHA, 64 kayıtlı varyant, 32 uzun aday,
  8 varlıkta 256 uzun aile yükü ve kaynak strateji kimliği eşleşirse
  kanıt incelenir.
- Kayıtlı kazanmayan 32 varyant dahil, tek haftalık takvim üzerinde
  kullanılan tüm return yolları yeniden doğrulanır. PBO 8-blok/70
  bölmeyle **bağımsız plain-Python yeniden hesaplanır**. DSR aynı
  keşif-seçimi ve ayrı doğrulama haftalarıyla yeniden hesaplanır.
- Kaynak PBO/DSR sayısı uyuşmazsa, haftalık verinin hash'i bozuksa,
  geçmişte seçilen varyant kayıttan farklıysa veya kaynak eski/süresi
  geçmişse kaynak **SOURCE_NOT_REPRODUCED** olarak reddedilir.
- Çıktı, mevcut
  `research.portfolio_qualification.gate.review` kanıt pasaportuna
  bağlanır. "Yeterli" olmayan bilgiler sahte TRUE'ya çevrilmez.

## Hayati sınır

Bu, merkezî onay motoru `lab.validation.validate`'in koşup tüm
gereken testleri geçmesi değildir. Eaverse V7'nin fiyat akışı geriye dönük
araştırmadır; bugünkü source indirme zamanı gerçek 2023 ilk gözlem saatini
yeniden yaratmaz. Spot veri üzerinde short emir, gerçek fill, likidite,
sermaye kısıtları, BIST/US delist-aware PIT fiyatı, katı bağımsız ileri
dönem, 3y OOS ve ileri PAPER henüz bağımsız yeniden ispatlanmış değildir.

Merkezî `lab.validation.GATE`, `decisions/registry.json`,
H054/H118/H119/H120 veya diğer çalışan stratejiler değişmez.
`central_lab_accept=false`, `paper_approved=false`,
`live_allowed=false` kalır; kaynak başarı etiketleri
ve haber bültenleri canlı işlem izni olamaz.

**Genelleştirme:** Diğer 9 kaynağın status/eksik kanıt denetimi
`research/portfolio_qualification/audit.py` tarafından zaten yapılır.
Bir diğer araştırmanın bu tekrar-doğrulama mekanizmasına katılması için
çalıştırılabilir şeffaf PIT fiyat/olay/gerçek zaman/cost/strateji
sözleşmesi ve bağımsız prospective kanıt sağlaması gerekir.
İsim benzerliği ya da README iddiasıyla tüm araştırmalar otomatik
`ACCEPT` yapılmaz. Kaynak bazında yeni adapter gerekir.

## Ücretsiz periyodik çalışma

Mevcut `Portfolio strategy qualification audit (RESEARCH ONLY)`
workflow'unda günde bir defa, sadece main/manual/schedule çalışmasında
public GitHub kaynaklarına salt okunur bağlanır. 8 varlık için tüm
denetimler SHA kanıtlı JSON artifact'e girer. PR'da sadece
adversarial offline test yürütülür. İlave ücret, harici API anahtarı,
write izni, ek cron, Telegram veya emir yoktur.
