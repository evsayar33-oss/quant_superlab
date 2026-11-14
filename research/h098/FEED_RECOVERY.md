# H098 independent market feed recovery

H098 now attempts **five separate USDT perpetual venues**: Binance USD-M, Bybit linear, Gate USDT futures, Bitget USDT futures and MEXC contract futures. It does not replace a failed perpetual feed with spot prices, an OKX mirror, a synthetic bar or a cached stale snapshot.

The original Binance and Bybit public REST endpoints remain configured. HTTP 403/451/429, network failures, malformed provider responses and incomplete bars are recorded **per venue, symbol and timeframe** in `results/h098/summary.json` under `venue_health` and `comparisons`. All sources are retained with venue identity, original request URL, market type and SHA-256.

An independent source counts only after fetching finalized valid OHLC, at least 30 exact UTC-aligned overlapping bars with OKX and a successful comparison. If every venue fails, the summary explicitly reports `DEGRADED_NO_INDEPENDENT_VENUE`; a green workflow is a healthy **diagnostic execution**, not verified independent market evidence.

No public market-data endpoint can be guaranteed reachable from every GitHub-hosted runner. If the five sources are all blocked, the next step is an approved stable-egress data service or permitted third-party market-data feed, not spoofing location, hiding HTTP errors or declaring success.

This patch does not alter H089, production trading, H098 daily 07:17 UTC schedule, historical alpha gates or cost assumptions. To run after merge: Actions → H098 — Independent venue and cost evidence (read-only) → Run workflow on main. Inspect `independent_venue_status`, `gates.cross_venue_candle_comparisons` and `venue_health`.
