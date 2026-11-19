# H120 — Tier-1 Quant Terminal ↔ Quant Superlab (Isolated Intelligence)

H120 reads ONLY evsayar33-oss/tier1_quant_terminal, and never
evsayar33-oss/early_accumulation_radar. Existing H119, H054,
H089, H111, H115, H118 or Tier-1 production code remain unchanged.

## Independent scope and methodology

Tier-1 is a non-executing, six-asset SPX / NQ / XAU / XAG / BTC / ETH
decision-support terminal. Its own real-time factor model, risk/stop,
entry and direction methodologies are not interchangeable with Early
Radar anomaly/perpetual-strategy research.

Tier-1 already publishes prospective, first-seen directional observations
on its own independent audit/30d-evidence branch. H120 reads its
independent_audit/summary.json and ledger.json at a pinned source commit SHA.
It does NOT rely on the mutable, force-pushed Tier-1 operational state
branch as independent proof.

When separately published, H120 will also ingest final research-only
decisions from audit/study-decisions and audit/sentiment-superlab.
Unfinished/missing studies remain unfinished/missing; no deadline or
historical labels are made up.

Each poll checks SHA ancestry (fail closed on upstream rewrite),
publication versus first-seen UTC chronology, underlying audit row
count versus headline n, independent asset qualification, reference
baseline, multiple-test significance, price stress, source liveness
and official expiry decision provenance.

## Research-only qualification (not ACCEPT)

The fixed diagnostic 4h and 24h candidates require at least
100 independent graded observations, 30 entry-allowed observations,
verified asset independence, Bonferroni-12 p <= 0.05, at least
5 percentage points directional uplift versus always-long,
positive assumed 40-bps stress mean, and no unresolved missing-label
excess. Otherwise verdict is NOT_ENOUGH_INDEPENDENT_EVIDENCE.
Even after this filter, a candidate is only a
REPLICATION_LEAD_REQUIRES_NATIVE_LAB_TEST, NEVER an ACCEPT.

A native Tier-1-specific implementation with PIT-safe data,
realistic fills and costs, DSR/PBO/White Reality Check, adequate
out-of-sample periods, and a Time Machine is still prerequisite.
H120 does not call the official lab approval engine or modify its gate.

All per-asset raw performance statistics are labelled overlapping
and not independent. Hit rate without entry allowance is not PnL.

## Autonomous service and Telegram

H120 — Tier-1 Independent Intelligence Bridge runs every six hours:
01:49, 07:49, 13:49, 19:49 UTC, with optional workflow_dispatch.
A workflow path-filtered push triggers the first run on merge.

The engine writes SHA-linked evidence only to the independent
research/h120-tier1-evidence branch of quant_superlab, with:
tier1_h120/events.jsonl, receipts.jsonl, manifest.json and latest.json.
It does not update main, the Tier-1 source, model memory, bot, UI,
state, reports or other PAPER histories.

Only a sealed FINAL study decision, a qualified independent
replication lead, or an audit interruption longer than 24 hours
triggers a new alert. Existing quant_superlab Telegram secrets
TELEGRAM_TOKEN and CHAT_ID are reused; alternate names supported.
If Telegram fails, an assigned GitHub Issue is attempted, with
delivery receipts recorded after acknowledgement. There are no
routine empty-result messages.

## Preserve ongoing experiment windows

Tier-1 production model LOGIC_VERSION 2026.10.23-v2 is locked through
November 23, 2026. The independent BTC/ETH sampled-trade research
(through December 14, 2026) and six-asset sentiment research
(through December 15, 2026, plus grace) continue unmodified.

No Tier-1 model direction, stop, signal, workflow or state branch is
edited by this integration. No Early Radar hypothesis enters Tier-1.

The existing audit uses delayed Yahoo and bar-close proxies, not
executable quotes. Positive hypothetical mean return is not a
realized execution profit statement. The 30-day observation interval
alone is not enough for official institutional validation.

Regression tests:
python -m unittest discover -s research/h120 -p 'test_*.py' -v
The PR also checks python tests/test_core.py.
