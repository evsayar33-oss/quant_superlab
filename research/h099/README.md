# H099 — Independent venue strategy trade-proxy replication

H098 established **12/20** successful independent **candle** comparison sets (Gate, Bitget, MEXC), but did not replicate strategy entry/exit outcomes. H099 advances that specific gap, without accepting alpha.

## Fixed research protocol

- Independently fetch closed BTC/ETH USDT perpetual 15m and 1H bars from OKX and each of Binance, Bybit, Gate, Bitget and MEXC. 4H parent bars are strictly derived from complete 1H groups.
- Re-run H095 detectors and H096 causal parent-conditioned signal setup **on each venue's own candles**. Use the same fixed 1R target, 20 bps assumed roundtrip cost, next-open entry, 24-bar maximum hold, stop-first proxy. Evaluate six event families × two sides × two parent cohorts, **without optimizing on the independent venue**.
- Pair trades **only** when entry UTC timestamp, event family and side are identical. Report missing matches, matched mean net R and independent-venue matched win fraction, plus deterministic moving-block-bootstrap descriptive confidence intervals when n >= 30.
- Output source SHA-256 manifests, per-venue 24-configuration matrices and explicit inaccessible provider reasons. Real-data job **fails** if no independent comparison set succeeds.
- **No portfolio NAV, fills, fee-tier measurement, funding debit application, live prospective proof or corrected multiple-testing significance.** Bootstrap is descriptive and does not establish alpha.

## Important methodological limitation

H096 `setup()` currently requires a recent confirmed higher-timeframe parent event even in cohort `all`. H099 deliberately reuses H096 unmodified to preserve exact replication comparability. Therefore `all` is **not truly unconditional**. Fixing this should be a separate, versioned methodological correction with historical baseline comparison; do not silently relabel these results.

Cross-venue proxy trade agreement is not independent realized execution profitability. The same broad crypto market influences all venues; venue independence does not equal statistical independence. The evidence gate remains fail-closed.

## Run

```bash
python -m unittest discover -s research/h099 -p 'test_*.py' -v
python research/h099/run.py --pages 8 --out results/h099
```

After all PR checks pass: merge, then Actions → **H099 — Independent trade-proxy replication (read-only)** → Run workflow on `main`. Download the artifact and inspect `summary.json` for `independent_trade_comparison_sets`, per-configuration `matched_n`, and `alpha_accepted=false`. H089 and production files are unchanged.
