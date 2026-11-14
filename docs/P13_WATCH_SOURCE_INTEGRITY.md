# P13 — Paper Watch source integrity (2026-11-14)

A real, read-only GitHub Actions Paper Watch job succeeded after PR #11
but logged:

```text
['GC=F']: OperationalError('database is locked')
[data] WARNING no 1d data for: ['GC=F']
```

Metal H063/H064 NAV was calculated on 4 of 5 fixed metal futures. A
green workflow therefore contained a **changed-universe** result.

This patch uses serial yfinance data downloads, retries incomplete batches
and individual missing symbols, and fails Paper Watch closed whenever
any asset in its pre-registered class universe is absent. The error is
visible instead of publishing an incomparable historical NAV.

No parameters, leverage, existing approvals or live orders are changed.
Should Yahoo remain inaccessible, explicit failure is safer than silently
substituting GLD or another non-equivalent market.

The read-only real-provider source job is separate from actual scheduled
production verification. Merge and then verify one successful daily
Paper Watch execution with all frozen instruments present.
