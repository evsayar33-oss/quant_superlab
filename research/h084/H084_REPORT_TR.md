# H084 — Yalnızca kazanan hisse adaylarını seçme denemesi

**12 Kasım 2026 · H083 dondurulmuş verisi · kazananlar önceden bilinmeden test · yeni piyasa verisi yok.**

## Yönetici kararı

**20 araştırma varyantının hiçbiri kârlılığı veya SPY üzeri alpha avantajını güvenilir biçimde kanıtlamadı.**
İki eski rotasyon portföyüne eklenen 12 filtre içinde **hiçbir filtre**, bütün veride orijinal portföyden daha fazla toplam USD kâr sağlamadı. Üç tarih bölümünün tamamında hem pozitif ilave kâr hem de en az beş yeni gözlem üreten filtre bulunmadı.

Bu sonuç geçmişten kazanan hisseleri kusursuz ayıklamanın mümkün olduğu anlamına gelmez. Tam tersine, kazanan görünümünü geriye dönük bilmeden, önceki tamamlanmış işlemlerle ölçmenin güçlüğünü ortaya koyar.

## 1. Gerçek H083 nakit alım-satımının kazanan-hafıza filtreleri

Standart 10.000 USD hesap, yaklaşık 2.000 USD/pozisyon. Mevcut H083 işlemlerinin maliyet sonrası PnL değerleri kullanılır: 1,50 USD alış + 1,50 USD satış ve taraf başına 5 bp gerçekleşme sapması **önceki H083 hesabında zaten dahil**. Bu tabloda ikinci kez komisyon düşülmez.

| Portföy | Önceden bilinebilir seçim filtresi | Alınan işlem | Kazanma oranı | Net USD | Orijinale fark | BH q (isabet artışı) |
|---|---|---:|---:|---:|---:|---:|
| monthly_low_beta | Filtre yok | 103 | %49.5 | +6,009 | +0 | 1.000 |
| monthly_low_beta | En az iki diğer model de tutuyor | 24 | %29.2 | +2,209 | -3,800 | 1.000 |
| monthly_low_beta | En az üç diğer model de tutuyor | 16 | %37.5 | +2,991 | -3,018 | 1.000 |
| monthly_low_beta | Aynı sistemde önceki işlem kazançlı | 31 | %41.9 | -694 | -6,703 | 1.000 |
| monthly_low_beta | Diğer sistemlerde son tamamlanmış işlem kazançlı | 33 | %48.5 | -493 | -6,502 | 1.000 |
| monthly_low_beta | Aynı sistemde önceki 2 işlem kazançlı | 8 | %50.0 | +115 | -5,893 | 0.948 |
| monthly_low_beta | Çoklu model + geçmiş kazanan | 5 | %20.0 | -846 | -6,854 | 1.000 |
| monthly_vol_squeeze | Filtre yok | 141 | %54.6 | +5,175 | +0 | 1.000 |
| monthly_vol_squeeze | En az iki diğer model de tutuyor | 68 | %55.9 | +4,478 | -697 | 0.948 |
| monthly_vol_squeeze | En az üç diğer model de tutuyor | 50 | %52.0 | +2,436 | -2,739 | 1.000 |
| monthly_vol_squeeze | Aynı sistemde önceki işlem kazançlı | 44 | %63.6 | +2,670 | -2,504 | 0.948 |
| monthly_vol_squeeze | Diğer sistemlerde son tamamlanmış işlem kazançlı | 48 | %58.3 | +4,151 | -1,023 | 0.948 |
| monthly_vol_squeeze | Aynı sistemde önceki 2 işlem kazançlı | 20 | %60.0 | +1,149 | -4,026 | 1.000 |
| monthly_vol_squeeze | Çoklu model + geçmiş kazanan | 30 | %63.3 | +4,116 | -1,059 | 0.948 |

En küçük çoklu-test düzeltmeli q = **0.948**. Test edilen filtrelerin hiçbirinde anlamlı pozitif isabet oranı kanıtı yok.

### Dönemsel dayanıklılık

2023 başlangıçlı H083 portföyünün üç yeniden kullanılan tarih aralığında seçilen filtrelerin orijinale göre USD farkı:

| Kural | Filtre | Keşif farkı | Doğrulama farkı | Yeniden kullanılmış son bölüm farkı |
|---|---|---:|---:|---:|
| monthly_low_beta | consensus_2 | +18 | -2,997 | -821 |
| monthly_low_beta | last_same_rule_win | -3,810 | -3,139 | +246 |
| monthly_low_beta | last_any_rule_win | -3,604 | -2,862 | -36 |
| monthly_low_beta | consensus2_prior_win | -3,254 | -2,779 | -821 |
| monthly_vol_squeeze | consensus_2 | -409 | -749 | +461 |
| monthly_vol_squeeze | last_same_rule_win | -1,143 | -1,170 | -192 |
| monthly_vol_squeeze | last_any_rule_win | +268 | -1,050 | -242 |
| monthly_vol_squeeze | consensus2_prior_win | -154 | -1,263 | +358 |

## 2. Olayın kazanan hissede tekrarlanması

20 günlük `baseline/20/time` işlemlerinden sınırları aşan `PURGED` işlemler atılınca **196** olay-hisse işlemi kalır. Her aday sadece **aynı hisse/sektör/haber türüne ait, geçmişte tamamen sonuçlanmış** işlemlerin kazanç işaretini kullanır. Sonucu bilinmeyen şirketler önceden kazanan ilan edilmez.

| Önceden bilinen koşul | Örnek | Pozitif işlem | Ortalama hisse net | SPY üzeri ortalama |
|---|---:|---:|---:|---:|
| all | 196 | %48.5 | %+0.81 | %+0.11 |
| prior_ticker_win | 52 | %46.2 | %+0.54 | %+0.44 |
| prior_ticker_excess | 49 | %44.9 | %+0.94 | %+1.04 |
| prior_sector_winrate | 27 | %37.0 | %-0.52 | %-0.80 |
| prior_category_winrate | 65 | %47.7 | %+1.35 | %+0.77 |
| prior_ticker_sector | 4 | %25.0 | %+6.39 | %+5.97 |

Özellikle `prior_ticker_excess` geçmiş SPY üstünlüğüne göre seçim yaparken, son kullanılabilir 31 olaya ait bölümde 8 işlemden ortalama SPY üzeri **negatif %0,09** verdi. Bu çok küçük ve önceden görülen örnekleme göre alpha olarak kabul edilemez.

## 3. Sonuç neden kolayca kanıtlanamıyor?

- Bazı kazananlarda tek büyük pozitif işlem tüm strateji getirisini taşıyor. Çok sıkı kazanan filtresi, o işlem daha yaşanmadan hissenin alınmasını engelliyor.
- Yüksek kazanma oranı tek başına yeterli değil; ortalama kazanç / ortalama zarar, pozisyon maruziyeti ve aylar arasında süreklilik önemlidir.
- Birden fazla kural aynı yatırım faktörlerine (momentum/trend) bakabildiğinden **konsensüs bağımsız bilgi kanıtı değildir**.
- Tarihsel veri H083 içinde daha önce görülmüş olduğu için H084 sonuçları yeni bir bağımsız holdout değildir.
- Kazananları sonra seçmek *look-ahead bias* üretir; kod her zaman `exit_date < entry_date` şartı uygular.
- Seçilmeyen işlemler yerine başka hisse seçilmedi. Filtre sonrasında portföy günlük NAV ve tam yeniden dengeleme / maruziyet karşılaştırması yoktur.
- Kaynak H083 Yahoo ayarlı OHLCV ve tarihsel şirket evreni/delist/veri kalitesi sınırlamalarını aynen devralır.

## 4. Ne yapmalıyız?

**Üretim önerisi: yeni filtrelerin hiçbiri canlı al/sat sinyaline eklenmemeli.** Radar üzerinde H083’ün zaten birleştirilmiş iki `WATCH_ONLY_UNVALIDATED` izleme yaklaşımı korunmalı.
Sonraki aşama geçmişte başka 20 filtre aramak değil, kuralları sabitleyip 6–12 aylık gerçek ileriye dönük kâğıt işlemlerde maliyet, maruziyet ve SPY’a göre performansı ölçmektir.

**Bu çalışma mümkün olan bütün stratejilerin test edildiği anlamına gelmez.** Yalnızca mevcut H083 işlemlerinin üzerine eklenen kazanan-hafıza, model-konsensüs ve olay-hafıza yöntemlerinin olumsuz/kararsız sonuçlarını belgeler.

## Kaynak ve çoğaltılabilirlik

- Dondurulmuş girdi: H083 2026-11-12 sonuç arşivi içindeki iki CSV.
- Kaynak kodu: `h084_winners.py`; testler: `test_h084.py`.
- Araştırma CSV dosyaları: `results/` altında; kod hiçbir broker hesabını çağırmaz.
- Akademik motivasyon: George & Hwang (2004), 52-hafta zirvesi ve momentum; Zhang, Cai & Keasey (2014), pratik maliyetlerin olay stratejisinde alpha’yi silebileceği.
- 52-hafta zirvesine uzaklık için **yeni fiyat temelli bir backtest yapılmadı**; motivasyon kaynak göstermenin testin yerine geçmesine izin verilmez.