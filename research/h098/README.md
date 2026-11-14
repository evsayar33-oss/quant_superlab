# H098 — Independent venue, execution-cost sensitivity and prospective candidate evidence

**Research-only, fail-closed.** Does not change H089, trading execution, accepted-alpha registry or any production decisions.

## What actually runs

- Fetches finalized OKX BTC/ETH 15m and 1H USDT perpetual bars as the primary source; independently requests Binance USD-M futures and Bybit linear perpetual bars. Each provider has a distinct read-only adapter with strict UTC bar alignment, candle validation, duplicate-conflict rejection, missing-data reporting and SHA-256 source artifacts.
- Exact-time OHLC comparison between venues, including price deviations and data gaps. Re-runs H095 event detector on independent-venue candles and reports exact timestamp/type/direction event concordance. **Candle or event agreement is not strategy return replication.**
- Re-fetches OKX public funding history and records raw observed settlements separately. The sign of a funding debit is modeled for long/short unit-notional sensitivity, but settlement coverage and mark/notional path are not verified. **Funding is not yet applied as an exact trade expense.**
- Three explicit **hypothetical** roundtrip cost scenarios: low 4 fee + 2 spread + 2 slippage + 0 impact bps; medium 8 + 5 + 5 + 2; stress 16 + 12 + 12 + 10. These are **assumptions, not measured exchange fees or fills**. An illustrative long return sensitivity is saved; no execution-level NAV is claimed.
- Creates source-hashed candidate event snapshots per run. Scheduled daily at **07:17 UTC** and also manual via Actions. GitHub artifacts retained 90 days. **Snapshots are not independently immutable or cross-run first-seen reconciled**, so the prospective evidence gate stays false.

## Usage

```bash
python -m unittest discover -s research/h098 -p 'test_*.py' -v
python research/h098/run.py --pages 8 --out results/h098
```

After green checks, merge and run Actions → **H098 — Independent venue and cost evidence (read-only)** → Run workflow on `main`. Inspect `summary.json`, source hashes, venue comparison results, observed funding records and snapshots in `h098-venue-cost-prospective-*`.

## What remains NOT verified

- Actual exchange-specific historical fee tiers, bid/ask quotes, execution slippage, funding settlement coverage, price impact, leverage/liquidations and position-dependent cost application.
- Independent *strategy* replication (trade entry/exit outcomes across venues) and dependence-robust statistical significance (e.g. block-bootstrap SPA).
- Long-term immutable first-seen journal, prospective realized outcomes, independent live fill audit and portfolio capital NAV.
- Point-in-time macro/fundamental data.
- Provider geoblocks, HTTP 403/429 or downtime are explicitly marked `NOT_VERIFIED_PROVIDER_ERROR`. **A green workflow can mean no independent venue was accessible**; inspect comparison statuses before interpreting it. Primary OKX failures fail the workflow.

No alpha is accepted, regardless of candle or event agreement. These gates require future evidence, not merely successful CI.
