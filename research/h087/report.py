"""H087 complete Turkish source-grounded report generator (all failures visible)."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"results"/"h087"
a=json.loads((OUT/"H087_AUDIT.json").read_text())
v=json.loads((OUT/"H087_LIVE_STRESS.json").read_text())
t=json.loads((OUT/"H087_STAT_TESTS.json").read_text())
rows=pd.read_csv(OUT/"H087_SYNTHESIS_70.csv")


def pct(x):
    return "—" if x is None else f"{x*100:+.2f}%"


family=a["family_results"]
assets=a["arena"]
inv=json.loads((OUT/"H087_REPO_INVENTORY.json").read_text())
lines=[
"# H087 — Quant Superlab bütüncül sentez ve şans kontrolü",
"",
"**Kanıt sınıfı: daha önce açılmış tarihsel veriler üzerinde yeniden test (REUSED_TEST); yeni, gizli veya ileri tarihli veri değildir.**",
"",
"## 1. Kapsam ve kaynaklar",
"",
f"- Git üzerinde envanteri çıkarılan izlenen dosya: **{inv['tracked_files']}**.",
"- Her dosyanın tam yolu `H087_REPO_INVENTORY.json` içinde. Kod, belge, sonuç ve bot/terminal altyapıları sınıflandırıldı.",
"- H062, H073, H072, H074, H076, H077, H083–H086, ICT/SMC, CPPI, Arena, risk, cross-section, forward live ve watch kayıtları denetlendi.",
"- Tam dosya envanteri, bütün dosyaların satır satır kod doğrulaması demek değildir; bu çalışmada veri ve strateji kararı üreten kayıtlar sayısal olarak denetlendi.",
"- Bağımsız olmayan deneme sayıları toplanıp bağımsız istatistiksel örnek gibi kullanılmadı.",
"",
"## 2. Önceden yayımlanmış aday eleme sonuçları",
"",
"| Araştırma ailesi | Arşivdeki deneme | Bulgular |",
"|---|---:|---|",
f"| H062 dev tarama | {family['H062']['trials']:,} | D4 aday {family['H062']['d4_candidates']}, finalist {family['H062']['finalists']}; nihai kazanan {family['H062']['winners']} |",
f"| H073 varlık kitabı | {family['H073']['trials']:,} | İş sayısı {family['H073']['jobs']}; final kabul yok |",
f"| H072 endeks/makro | {family['H072']['trials']:,} | Blok A nihai kabul {family['H072']['block_a_final']} |",
f"| H076 MLBook | {family['H076']['trials']} | Orijinal raporda onay kapısı tekrar kontrol edilmeli |",
f"| H077 VolRange | {family['H077']['trials']} | Önceki raporda yeni onay yok |",
f"| ICT/SMC | Çok milyonlu arama (ayrı metrik) | OOS/yer tutucu/placebo testleri ve kaynak sınırlamaları aşağıda |",
"",
f"- H062 time machine survivors: {family['H062']['time_machine_survivors']}; bunlardan rastgele giriş ve al-tut bazlı sınamaları geçen {family['H062']['random_entry_baseline_passers']} varsa bile **nihai DSR/başarı izni değildir**.",
f"- Karar defteri güncellemesi: {a['decision_registry']['source_updated']}; durum dağılımı: `{a['decision_registry']['verdict_counts']}`.",
"",
"## 3. Yeniden test edilen 70 disiplinler arası kombinasyon",
"",
"- H085'in daha önce denenmiş **14 maliyetli hisse rotasyon portföyü**, H086'nın **beş gecikmeli VIX risk katmanı** ile birleştirildi.",
"- Yalnızca ilgili takvim ayından **önceki ay sonunda bilinen VIX ağırlığı** kullanıldı; ayın gerçekleşmiş getirisi sinyale girmedi.",
"- Önceki H085 25bp işlemsel maliyeti korundu, üzerine risk katmanı dönüşlerine 10bp ve 20bp ek tek yönlü maliyet uygulandı.",
f"- Veri kesişimi: **{t['full_month_count']} ay**, {t['input_provenance']['start']}–{t['input_provenance']['end']}. Ön kontrol {t['early_month_count']} ay, sonraki yeniden kullanılan test {t['late_month_count']} ay.",
f"- SPY karşılaştırması, sonraki dönemde toplam **{pct(t['late_spy_total'])}**.",
f"- 70 kombinasyondan SPY üstünde toplam getiri: **{t['number_above_SPY_late']}/70**. İki kat maliyette: **{t['number_above_SPY_late_2x']}/70**.",
f"- Yerel koşulların hepsini geçen: **{t['number_meeting_local_gates']}/70**.",
f"- Familywise durağan blok-bootstrap p değeri: **{t['familywise_bootstrap']['familywise_p']}**.",
f"- Tüm risk zamanlamasını kaydırma placebo p değeri: **{t['phase_shift_placebo']['placebo_p']}**, kaydırma sayısı: {t['phase_shift_placebo']['exact_nonzero_circular_shifts']}.",
f"- Sadece 2023–2024 döneminde belirlenen 'en iyi' aday: `{t['pre_2025_selected_id']}`, 2025–2026 göreli toplam fark: **{pct(t['pre_2025_selected_late_excess'])}**.",
"",
"**Kombinasyonların tamamı araştırma adayıdır; canlı ya da gerçek bağımsız ileri performans değildir.**",
"",
"### 3.1 En yüksek görünen beş kombinasyon (önceden açılmış veriye göre sıralanmış, seçim değildir)",
"",
"| Portföy + risk filtresi | Son dönemde net toplam | SPY'den fark | 2x maliyette SPY'den fark | Ort. risk ağırlığı |",
"|---|---:|---:|---:|---:|",
]
for _,r in rows.sort_values("late_active_gap",ascending=False).head(5).iterrows():
    lines.append(f"| `{r['id']}` | {pct(r['late_net_return'])} | {pct(r['late_active_gap'])} | {pct(r['late_2x_cost_active_gap'])} | {pct(r['mean_exposure'])} |")
lines += [
"",
"### 3.2 Başarısızlığa dayanıklılık testleri",
"",
"- **White-style familywise maximum:** 70 model aynı anda sınandı; kazananın sıradan p değerine bakılmadı.",
"- **VIX zamanlama kaydırması:** risk ağırlıklarının seri yapısı korunup farklı tarihlere yerleştirildi; şansa uygun sıralama değişikliği kontrol edildi.",
"- **En iyi iki ay silme:** bir modeli taşıyan iki olağanüstü ay çıkınca üstünlük devam ediyor mu kontrol edildi.",
"- **Yüksek komisyon:** 10/20bp tek yönlü ek overlay dönüş maliyetleri.",
"- **Sabit maruziyet kontrolü:** 2025 öncesindeki ağırlık ortalaması kullanıldı; piyasanın daha az alınmasının kendi başına avantaj olup olmadığı denetlendi.",
"- **Zamansal seçim testi:** 2025+ dönemi görmeden 2023–2024'e göre aday seçildi, sonraki dönem raporlandı.",
"- Veriler önceki H083/H085/H086 çalışmalarıyla zaten açığa çıktığından, bu aşamalar **bağımsız, mühürlü dış örneklem kanıtı** değildir.",
"",
"## 4. Forward live kayıtlarının yeniden analizi",
"",
"| Kayıt | 4h bar sayısı | Tarih aralığı | Birikimli getiri | En iyi beş bar çıkarılınca | Blok-bootstrap pozitif ortalama p |",
"|---|---:|---|---:|---:|---:|",
]
for k,r in v["models"].items():
    lines.append(f"| {k} | {r['bars']} | {r['start']} – {r['end']} | {pct(r['cum_return'])} | {pct(r['return_excluding_five_best_bars'])} | {r['block_bootstrap']['p_positive_mean']:.3f} |")
lines += [
"",
f"- H052/H054 getiri korelasyonu: **{v['correlation']:.4f}**. İki isim aynı dayanak ve mantığı paylaştığından iki bağımsız başarılı örnek gibi sayılamaz.",
f"- H054–H052 farkı, blok-bootstrap pozitif ortalama p: **{v['paired_delta_H054_minus_H052']['p_positive_mean']:.3f}**.",
"- Geçmiş H063–H065 fiyat serileri yeniden hesaplanan NAV olabilir; bugünkü forward getiri olarak geriye dönük doldurulmaz.",
"",
"## 5. ICT/SMC şans ve genellenebilirlik",
"",
f"- `ict/results/cross_asset.csv` içinde {a['ict']['cross_asset_rows']} kayıt; olumlu görünen satır {a['ict']['positive_cross_asset_rows_not_independent_alpha']}. Bu satırlar bağımsız hipotez denemesi değil, arama sürecinin sonucu.",
"- Orijinal araştırma 100 milyonun üzerinde korelasyonlu parametre/varlık denemesini belgeliyor; geçerli bir FWER için yalnızca en son olumlu satırları seçmek doğru olmaz.",
"- Per-varlık placebo çıktılarını aşağıdaki tabloda eksiksiz gösteriyorum. Az sayıda placebo olduğundan p=0.05 gibi kesin anlamlılık sonucu çıkarılamaz.",
"",
"| Varlık | Gerçek OOS expectancy (R) | Placebo sayısı | Gerçek placebo'ların hepsinden yüksek mi? |",
"|---|---:|---:|---|",
]
for z in a["ict"]["asset_placebo"]:
    lines.append(f"| {z['asset']} | {z['real_oos_exp']:+.4f} | {z['placebo_rows']} | {'Evet' if z['real_exceeds_all_placebos'] else 'Hayır'} |")
lines += [
"",
"## 6. Arena ve gerçek karar uygulaması",
"",
"| Arena anahtarı | Aktif | Control | Switcher yaşı (gün) | usable |",
"|---|---:|---:|---:|---|",
]
for k,r in a["arena"].items():
    lines.append(f"| {k} | {r['active']} | {r['control']} | {r['switcher_age_days']:.1f} | {r['switcher_usable']} |")
lines += [
"",
f"- Repo ana paper state tarihi: {a['paper_watch']['date']}; doğrudan saklanan ilk gözlem dosyası: {a['paper_watch']['has_first_seen_committed']}.",
"- Gecikmiş Arena kaydı ve eksik paper gözlemlerinden geleceğe dair kârlılık türetilemez.",
"- Bot, terminal ve veri entegrasyonları birer uygulama altyapısıdır; bir yazılım testinin başarılı olması işlem stratejisinin istatistiksel üstünlüğünü kanıtlamaz.",
"",
"## 7. Yönetim kararı ve sonuçların kanıt seviyeleri",
"",
f"- **Yeni canlı ACCEPT = {t['new_live_accepts']}.** H087 hiçbir trading sistemini değiştirmez.",
"- Güvenilir bulgular: repo içi karar defteri ve tarihli sonuçlar, maliyet stresi, gerçek kayıtların betimleyici dağılımı.",
"- Sınırlı bulgular: işleme uygun günlük tick fiyatları, delisted/PIT, gerçek market impact, karşılaştırılabilir portföy NAV bulunmadan farklı platform sinyallerini aynı sepet gibi üretmek.",
"- Şansa karşı testler olasılık tahminidir. Seçim sonrası, önceden kullanılmış veride sıfıra yakın şans olasılığı iddiası **kanıt değildir**.",
"- Eğer seçilen bir kombinasyon tarihsel göstergelerde başarılı görünürse bile, değiştirilemeyen yeni tarihli 6–12 aylık prospektif zaman damgalı izleme gerekir.",
"- Yeni sonuçlar 'şans eseri olabilir' standardıyla değerlendirildi; veriye göre yeni parametre eşikleri ayarlanmadı.",
"",
"## Yeniden üretim ve tam kayıtlar",
"",
"- `research/h087/FROZEN_PROTOCOL.yaml`: sonuçlardan önce kaydedilmiş kapsam ve eşikler.",
"- `H087_SYNTHESIS_70.csv`: 70/70 modelin bütün kayıp ve kazanımları.",
"- `H087_STAT_TESTS.json`: çoklu test, zaman kaydırma, 2x maliyet, anomali silme.",
"- `H087_REPO_INVENTORY.json`: Git'teki izlenen tüm dosyaların tam listesi.",
"- `H087_AUDIT.json`: araştırma ailesi, kaynak, karar, arena ve ICT durumları.",
"- `H087_LIVE_STRESS.json`: 4h ileri kayıtları ve bağımlılık testleri.",
]
(OUT/"H087_REPORT_TR.md").write_text("\n".join(lines)+"\n")
print(f"H087 report created: {len(lines)} lines")
