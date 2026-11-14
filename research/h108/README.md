# H108 — Dependence-aware inference and aggregate cost hurdle

Follow-up to H107's negative H106 results. Reads H106 SHA-256-verified trade ledgers; computes aggregate gross-to-cost break-even bps rather than averaging trade-level break-even thresholds, and fixed-seed 2,000-replicate weekly calendar-block bootstrap intervals. Reports full-history and matched trade-window venue results. This is a diagnostic of the **existing fixed hypothesis**, not parameter tuning or new alpha discovery.

Weekly resampling preserves same-week trade clusters but cannot remove cross-venue dependence, market nonstationarity or multiple-testing bias. All alpha gates remain false. No production/H089 changes.

Merge only after H108 research workflow and CI both succeed; dispatch H108 manually on main.
