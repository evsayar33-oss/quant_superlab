# H110 — One PR, one rerun, realistic execution-cost reassessment

Reprices **all 144 original H109 trade ledgers**, preserving trade entries, stops, exits, risk units, regimes and chronological splits. Does **not** reoptimize signals or manufacture missing market data.

Fee reference: OKX published regular futures 0.02% maker and 0.05% taker per fill (2/5 basis points). Gate fees depend on contract and tier; **2/5 is an unverified Gate assumption**, not claimed as a confirmed fee. Published fees are not account-specific or guaranteed historical.

- Taker+taker fee: 10 bps roundtrip. With assumed roundtrip slippage 2, 6, 10 bps, model costs 12, 16, 20 bps. These are assumptions, not observed execution.
- Maker+maker 4 bps and maker+taker 7 bps: **hypothetical sensitivity only**. Next-open entry and stop-first exit cannot assert maker fill probability.
- Funding and spread history are missing; none is silently modeled as verified.
- All 72 paired candidates, 144 venue trials, full/validation/tail metrics and profile-by-profile comparisons are reported.
- Ranking requires two-venue sample adequacy, positive 12/16 bps, historical tail and validation positive at 16 bps, plus 20 bps stress. A positive outcome is WATCHLIST ONLY; alpha acceptance remains false.
- Original H109 fixed cost 40/80 bps stress remains visible in H109 report; it is no longer the sole candidate screening gate.

## Procedure
Merge **only after CI and evidence are both green**. Then dispatch `H110 — Realistic cost reassessment` on main **once**. Download `h110-cost-reassessment` artifact containing `summary.json`, `trials.json`, `matrix.csv`, `committee.md`.

No changes to H089, production, orders or portfolio NAV. No prospective alpha validation.
