# PR #11 — Quant Superlab operational reliability

This PR fixes monitoring infrastructure, not investment performance or algorithmic alpha. Strategy selection rules, ACCEPT decisions, H083 research and live order behavior remain unchanged.

## Audit of forward-data provenance

- `decisions/watch/history.csv` is the **recomputed** historical NAV table. It was not originally appended for each prospective trading session. It is not independently observed forward PnL and should not be used as such.
- A successful new daily run appends an **actual first-seen snapshot** to `decisions/watch/observations.csv`, including timestamp, last closed bar and current positions. It records the NAV field explicitly as reconstructed from historical prices, **not** as prospective realized PnL.
- Missed dates are not backfilled. Completing 30 calendar days is not equivalent to proving alpha. A trustworthy forward return ledger and sufficient out-of-sample trading evidence are still needed.

## Deployment and verification

1. Require green CI on this PR. CI now includes Paper Watch, funding/client operational tests and additional research tests.
2. Merge then manually run **Paper watch H063-H065** with `daily`; confirm updated `decisions/watch/observations.csv` and preserved `history.csv`.
3. Manually run **Arena (paper, every 4h)**. Six timeframe/side scopes are isolated. The default schedule runs 4h scopes every four hours and 1d scopes near UTC midnight. Inspect each matrix job and confirm dashboard publishing.
4. Validate runtime `QUANT_LAB_URL` and `QUANT_LAB_ARENA_URL` overrides in every downstream bot; copied client files in other repositories do not auto-update. Expired strategy approvals stay fail-closed.
5. Check negative funding cache JSON under `data/cache/`, retried after 7–30 days. 404 is not interpreted as zero funding. Cross-venue funding proxies may still be unreliable.

## Residual risks

- External market-data outages, missing contract archives, GitHub runner delays, incomplete history and per-job 45-minute timeouts remain possible. No zero-failure guarantee is made.
- Arena is split to prevent one job using up all six scopes' budget, but any individual job can still time out. The dashboard deploy job requires all matrix jobs to complete and at least one valid new JSON file.
- A daily Paper Watch snapshot is an observation, not an execution-quality trading fill. The original acceptance gate must still be passed before a strategy can be live.
