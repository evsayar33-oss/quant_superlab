# H105 — Matched-window cross-venue robustness

Reads H104 bars and trade ledgers, verifies SHA-256 for all consumed inputs, compares OKX and Gate within their shared UTC candle window, and reports sample sizes, assumed 20 bps net R, and deterministic naive-bootstrap descriptive intervals. This is an **audit of H104 evidence**, not an additional independent strategy discovery test. It does not alter H103/H104 parameters, production, or H089.

Important: the common-window filter does not recompute indicators from an identical common warm-up period. Venue observations are dependent. Bootstrap intervals ignore serial dependence and multiple comparisons. Even positive paired results do not validate alpha, real execution, funding or prospective OOS.

Merge only after PR CI and H105 evidence pass. Dispatch H105 on main to regenerate H104 data and the paired audit.
