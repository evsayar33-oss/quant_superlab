# claude-trading-skills: ücretsiz anahtarlar ve çıkarılanlar

Kaynak: https://github.com/tradermonty/claude-trading-skills (MIT). 61 skill `.claude/skills/` altında.
Bu skill'ler ipucu üretir; karar yalnız `decisions/registry.json` + `validation.GATE` ile verilir.

## Tek ücretsiz anahtar: FMP
- Adres: https://site.financialmodelingprep.com/developer/docs (ücretsiz kayıt, günde 250 çağrı).
- GitHub Actions: repo Settings → Secrets → `FMP_API_KEY`. Telefonda: GitHub uygulaması → Settings → Secrets.
- Anahtar isteyenler: canslim-screener, vcp-screener, pead-screener, earnings-calendar, earnings-trade-analyzer, ftd-detector,
  ibd-distribution-day-monitor, market-top-detector, macro-regime-detector (yfinance yedeği var), pair-trade-screener,
  options-strategy-advisor, downtrend-duration-analyzer, kanchi-dividend-sop, theme-detector, value-dividend-screener,
  dividend-growth-pullback-screener, 4 Stockbee skill'i, signal-postmortem.
- Günde 250 çağrı sınırı: büyük taramalar (tüm S&P 500, 40+ hisse CANSLIM) bir günde bitmeyebilir; küçük listeyle çalıştırın.
- FINVIZ Elite (ücretli) isteğe bağlıdır; yoksa skill bu adımı atlar. Alpaca gerekmez.

## Anahtarsız çalışanlar
backtest-expert, residual-edge-analyzer, market-breadth-analyzer, uptrend-analyzer, sector-analyst, crypto-regime-analyzer,
exposure-coach, position-sizer, futures-position-sizer, drawdown-circuit-breaker, pre-trade-discipline-gate,
trader-memory-core, weekly-performance-digest, trade-performance-coach, edge-* hattı, finviz-screener (URL açar),
grafik görüntüsü isteyenler: breadth-chart-analyst, technical-analyst.

## Çıkarılan 13 skill (neden)
| Skill | Neden |
|---|---|
| mt5-robot-tester | Windows + MetaTrader 5 gerekir |
| portfolio-manager | Alpaca broker MCP sunucusu gerekir |
| parabolic-short-trade-planner | Canlı 5 dk veri + borç/SSR kontrolü, telefondan çalışmaz |
| cot-contrarian-detector | COT uç noktası FMP Premium+ ister (ücretli) |
| news-reaction-failure-analyzer, contrarian-setup-gate | COT hattının parçaları; COT olmadan işlevsiz (repo'da ücretsiz `lab/cot.py` var) |
| institutional-flow-tracker | 13F verisinin ücretsiz katmanda çalıştığı doğrulanamadı |
| economic-calendar-fetcher | Uç nokta ücretsiz anahtarda 402 verebilir |
| us-undervalued-growth-screener | Toplu veri için ücretli FMP planı ister, 250 çağrı yetmez |
| manifoldbt-backtester | Ek Rust motoru ve Commons Clause lisansı; repo'nun kendi motoru var |
| skill-designer, skill-idea-miner, skill-integration-tester | Kaynak reponun kendi geliştirme hattı; bu repoda işlevi yok |

## Zayıf yönler
- Skill'leri çalıştırmadım; "ücretsiz" bilgisi skill dosyalarındaki ifadeye dayanır. FMP ücretsiz katmanı değişebilir.
- FMP çıkış tarihi/fiyat verisi nokta-zamanlı (PIT) değildir; temel veri kullanan skill sonuçları CLAUDE.md PIT kuralına uymaz, yalnız ipucu sayılır.
