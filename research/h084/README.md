# H084 — Winner memory: independent GitHub Actions verification

This PR independently reimplements the 14 rotation cash-veto selections and
six event winner-memory selections from the completed H084 local study.
It downloads the successful H083 Actions artifact (run 43225656166),
verifies SHA-256 checksums of both frozen trade ledgers, tests strict
`exit_date < entry_date` causality, and checks counts and selected net PnL
against the previously published H084 local report.

This is an **independent verification**, not a copy of the full original
H084 source or its bootstrap/permutation routines. Statistical inference
remains the original local report's exploratory result; this workflow
verifies the 20 selector counts, key cash PnLs and event sample sizes.

All results are **REUSED_TEST**, never an independent sealed holdout.
The Midas fixed commissions and 5bp/side friction are already in H083 PnL;
the script does not double-charge them.

There is no approved alpha and no changes to Radar, production trading,
Telegram or any broker execution system.
