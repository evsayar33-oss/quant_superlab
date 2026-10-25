# quant_superlab — tek repo, tek test sırası

Bu repo üç projeyi birleştirir:

| Klasör | Kaynak | Görev |
|---|---|---|
| `/` (kök: `lab/`, `config/`, `hypotheses/`, `decisions/`, `run.py`) | [quant_lab](https://github.com/evsayar33-oss/quant_lab) | **Karar merkezi.** 68 kural, 47 ağırlık stratejisi, 60+ indikatör, karar kapısı, arena, zaman makinesi, sentez (H072), varlık kitabı (H073), çekirdek kural (H074), öğrenen model (H076). |
| `ict/` | [islem_onerisi_alarmi](https://github.com/evsayar33-oss/islem_onerisi_alarmi) | **ICT/SMC laboratuvarı.** FVG, OB, BB, MB, RB, PB, VB blokları, çoklu zaman dilimi konfluens, kilitli 2 yıl, Stage A–D. |
| `terminal/` | [OpenTerminal](https://github.com/ErTasselli/OpenTerminal) (MIT) | **Veri terminali.** Ücretsiz veri sağlayıcıları, grafik, tarayıcı, makro, takvim. Yeni: `/api/lab` lab kararlarını gösterir. |
| `bots/core3_bot/` | bu çalışma | Bitget spot botu (H054 kuralı; SOL için H075 bekleniyor). |

Sonuçlar ve dürüst özet: [`SENTEZ_RAPORU.md`](SENTEZ_RAPORU.md), [`VARLIK_STRATEJI_KITABI.md`](VARLIK_STRATEJI_KITABI.md).
Bugüne kadar karar kapısından geçen tek kural ailesi: H052/H054 (BTC+ETH trend + oynaklık hedefi).

## Zorunlu test sırası

Her yeni fikir aynı sırayla geçer. Atlanan adım = karar yok. Ayrıntı: [`PIPELINE.md`](PIPELINE.md).

1. **Ön kayıt** — kabul kuralı, deneme sayısı, alt dönemler sonuçlardan önce yazılır ve commit edilir.
2. **Veri** — ücretsiz kaynak, ileriye bakma yok, survivorship notu.
3. **Keşif** — sadece kilitli dönemden önceki veri; 2x maliyet; plato; 1 bar gecikme.
4. **Şans testi** — DSR (tüm denemeler sayılır), PBO, Reality Check.
5. **Kilitli dönem** — son 2 yıl, bir kez okunur.
6. **Zaman makinesi** — aynı seçim geçmiş kesimlerde tekrarlanır (en az 2/3 içeride).
7. **Karar kapısı** — `python run.py --hypothesis Hxxx` → `decisions/registry.json`.
8. **İleri kayıt** — arena / paper / live tracking; bozulan strateji DEGRADED olur.
9. **Bot** — sadece ACCEPT. `lab/client.py` → `approved()`.

## Hızlı başlangıç

```bash
pip install -r requirements.txt
python tests/test_core.py                 # lab testleri
(cd ict && python -m pytest -q)           # ICT lab testleri
cd terminal && npm install && npm test    # terminal testleri
npm run dev                               # terminal: http://localhost:3000, API: :4000 (/api/lab/registry)
```

## Kurallar

`CLAUDE.md` ve `AGENTS.md` geçerlidir: kapı eşikleri gevşetilmez, her fikir yeni hipotez id alır, veri ve araçlar ücretsizdir.
Eski quant_lab belgesi: [`docs/QUANT_LAB.md`](docs/QUANT_LAB.md). ICT belgesi: [`ict/README.md`](ict/README.md).
