# Test sırası (zorunlu)

| Adım | Ne | Komut / dosya | Geçme şartı |
|---|---|---|---|
| 0 | Hipotez | `hypotheses/registry.yaml` (yeni id), `config/<çalışma>.yaml` | Kurallar commit edildi, sonuç yok |
| 1 | Veri | `lab/data.py`, `lab/assetdata.py`, `ict/ictlab/data.py` | Ücretsiz, nedensel; testler geçer |
| 2 | Keşif | `run.py --scan`, `lab.assetbook`, `lab.mega`, `ict` `scripts/rule_search.py` | 2x maliyette kâr, plato, gecikme |
| 3 | Şans | DSR / PBO / Reality Check (`lab/metrics.py`) | DSR ≥ 0,90 (çalışmaya göre 0,95) |
| 4 | Kilitli dönem | son 2 yıl, tek okuma | 2x maliyette pozitif |
| 5 | Zaman makinesi | `lab/timemachine.py`, `lab.assetbook` kesimleri | ≥ 2/3 kesim içeride |
| 6 | Karar kapısı | `python run.py --hypothesis Hxxx` | `validation.GATE` → ACCEPT |
| 7 | İleri kayıt | `run.py --live`, `--arena`, `lab/watch.py` | Bozulma yok |
| 8 | Bot | `bots/`, `lab/client.py` | Sadece ACCEPT |

Bir tarama sonucu her zaman bir **aday**dır, karar değildir. Deneme sayısı her raporda yazılır.
