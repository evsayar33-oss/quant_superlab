# H102 — Economic edge decomposition and candidate preregistration

Research-only follow-up to H101. This does **not** optimize thresholds, change H089 or production, approve alpha, or claim a new profitable strategy.

## Scope
1. Regenerate H101 read-only evidence at the current market-data retrieval timestamp. Preserve the source manifest and trade-ledger SHA-256 hashes.
2. Verify ledger hashes and linear consistency of assumed 20/40/80 bps cost conversions. Fail closed on corrupt ledgers, non-finite prices, nonpositive initial risk or mismatched cost columns.
3. For each observed symbol/timeframe/venue/configuration cell, decompose mean **gross R**, 20/40/80 bps net R, cost drag, and implied break-even *round-trip* bps. Report median holding duration and stop/target/time exits.
4. Mark cells with fewer than 30 trades or fewer than 30 historical-tail trades as descriptive and insufficient; no significance or acceptance inference. Report eligible-cell family counts without winner selection.
5. Register **untested hypotheses only**: medium-term trend following, volatility-expansion breakout, cross-asset relative strength. None are implemented or represented as successful.

## Methodological limits
This is an economic diagnosis, not an independent alpha discovery or statistically valid multiple-testing correction. Exchange observations and overlapping signals are dependent. The last 30% of reused history is not prospective OOS. Cost inputs are assumed, not verified realized spread, impact, slippage, fees or funding. A positive gross result is not a tradable edge. An implied negative break-even cost means the gross mean is already negative.

## Run
```bash
python -m unittest discover -s research/h102 -p 'test_*.py' -v
python research/h101/run.py --pages 8 --out results/h101
python research/h102/audit.py --source results/h101 --out results/h102/diagnostics.json
```
Merge only after CI is green. Then manually run **H102 — Economic edge diagnostics (read-only)** on main and inspect the artifact. Production and H089 are untouched.
