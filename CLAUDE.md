# Task Observer activation

Invoke the `task-observer` skill before the FIRST tool call of every session, and before writing or proposing a plan.

- Workspace folder (pinned): `/home/claude/quant_lab/.claude`
- Observation log: `/home/claude/quant_lab/.claude/skill-observations/observation-log/`
- Substitute this path for `[ABSOLUTE PATH]` in every skill snippet. Keep it in double quotes. Run snippets with bash.
- Commit new observation files to the repo so they persist between sessions.

# quant_lab rules

This repo is the decision center for every trading bot of the owner.

- A bot acts on a strategy only when `decisions/registry.json` has `verdict: ACCEPT` for it (read through `lab/client.py`).
- Every new idea is a hypothesis: add it to `hypotheses/registry.yaml` with a new id. Never reuse an id.
- Never loosen `validation.GATE` to make a hypothesis pass. Any gate change needs a line in `hypotheses/CHANGELOG.md` with the reason.
- New weight strategies go in `lab/strategies/` with `@strategy(...)`; new entry/exit rules go in `lab/rules.py` with `@rule(...)`; new indicators in `lab/indicators.py`. Every one needs a parameter grid and a source. Signals and weights must use data up to close t only.
- Fundamentals must stay point-in-time (publication date / SEC filed date). Never use a value before it was public.
- A scan result is a lead, never a decision. Only `run.py --hypothesis` / `--all` writes `decisions/registry.json`.
- Run `python tests/test_core.py` before every commit. All tests must pass.
- Data and tools must be free (no paid API). The owner works only from an Android phone and GitHub Actions.

# Gerçekçilik kuralı (sahibin isteği — tüm çalışmalar)

Sahibe canlıda en iyi çalışacak sonuç lazım, testte en iyi görüneni değil.
- Kabul kuralını sonuçlara bakmadan ÖNCE yaz (alt dönemlerin hepsinde geçmeli, komşu ayarlarda da geçmeli, yüksek maliyette de geçmeli).
- Çok deneme = şans riski (aşırı uyum). Deneme sayısını söyle; tek en iyi noktayı değil, düz/sağlam bölgeyi seç.
- Daha iyisi kurala göre çıkmazsa açıkça yaz: "daha iyisi bulunamadı" veya "canlıda aynısı olmayabilir, bu yüzden önermiyorum".
- Zayıf yönleri (geride kalınan dönemler, test edilemeyen veriler, tek sektöre bağımlılık) her raporda yaz.

# Seçim süreçleri için zaman makinesi kuralı (2026-10-17)

- Binlerce aday arasından seçim yapan her süreç (eleme motoru, "en iyi N" portföyleri, switcher, yeni tarama
  yöntemleri) gerçek paraya aday olmadan önce zaman makinesi testinden geçmelidir (`lab/timemachine.py`,
  workflow "Time machine test"). Ölçüt: kesim tarihlerinin en az `timemachine.min_inside`'ında (varsayılan 2/3)
  ileri kayıt beklenen aralıkta kalmalı. Ayar: `config/arena.yaml` → `timemachine` (enabled ile açılıp kapanır).
- Tek bir hipotez için gerekmez: karar kapısının walk-forward'ı aynı işi tek strateji için yapar.
- Neden: 2026-10-17'de arena portföyleri backtest'te çok iyi görünüp 6 replay'in 6'sında beklenen aralığın
  altında kaldı; backtest sırası ile ileri sıra arasında ilişki ~0 çıktı.
