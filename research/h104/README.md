# H104 — Long-history coverage and fixed H103 replication

Extends **Gate USDT perpetual** 1H candles with deterministic UTC timestamp windows (180 days default), and **OKX USDT swap** native 1H via up to 60 historical pages. No synthetic backfills, no spot substitutions, no parameter optimization. Strict duplicate-conflict detection, gap accounting, bounded pagination, SHA-256 bar and ledger files. Replicates exactly H103's two fixed strategy families, 1H and strictly complete 4H, fixed cost assumptions. Coverage differs by provider; missing windows are reported and never presented as complete.

Research-only: no production/H089 changes, no alpha approval. Even a positive result is not prospective OOS, funding/execution verified, or multiplicity adjusted.

Merge after successful PR CI and H104 evidence; manually dispatch H104 on main.
