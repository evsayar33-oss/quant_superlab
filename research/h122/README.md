# H122 — Federal Incentive Radar isolated intelligence

Source: evsayar33-oss/federal-incentive-radar only. No branch in the
source repository is modified. H122 cannot send trades or change a
federal event, strategy parameter, threshold, ticker mapping or study clock.

## Two separate scientific tracks

1. H083: monthly low-beta and monthly ATR-volatility squeeze PAPER
   rotation with freeze/first-observed fills, source-defined SPY comparison,
   24-month completion rule and minimum 60 paper positions. On a month
   without a completed as-observed cohort, a scheduled green Action can
   have state SKIPPED. Such a run is NOT a forward result or proof of NAV.
2. Five frozen 20-session event-causal hypotheses (federal award, policy,
   prior relative strength, sector leadership, private recipient). These
   are separate from H083 rotation and the historical feed has PIT,
   survivorship and Yahoo adjusted-price limitations. A published CI
   artifact or successful research workflow is NOT an accessible verified
   net SPY-relative 20-session result until an independent source has
   provided actual eligible matured forward outcomes.

H122 reads at the exact GitHub SHA of the mutable Radar data branch:
h083_last_attempt.json, event_watch_status.json, economic_intelligence_status.json.
The optional h083_forward_status.json is read if it actually exists.
Upstream workflow run metadata is included for human triage, but a green
Actions conclusion cannot override source status SKIPPED or a missing
forward cohort file.

The data branch is an operational snapshot and may be rewritten, so H122
records both exact source SHA and SHA256 hashes for the small input JSONs.
It does not falsely label this as append-only upstream evidence. H122
stores its own tamper-evident event and notification receipts in the
dedicated Superlab research/h122-federal-evidence branch.

Initial historical skipped attempts and incomplete hypotheses are seeded
without a Telegram false positive. Future alerts can identify genuine
H083 FAILED attempts, three distinct skipped sessions since H122 bootstrap,
loss of watch data coverage, newly matured H083 months, newly published
H083 forward results, source-labelled FORWARD_VALIDATED_PAPER needing
independent lab review, or primary-source verification backlog.

Source approved_paper_rules remain informational: not quant_superlab
ACCEPT, not actual Midas broker fills. No resulting strategy is sent
to any bot or written to Quant Superlab decisions/registry.json.
Existing H083 and Alpha Discovery workflows, data and UI are unchanged.

Schedule: 03:43, 11:43 and 19:43 UTC daily (GitHub cron best-effort);
manual workflow_dispatch. Tests run before every observer. All alerts
reuse existing Quant Superlab Telegram secrets, with assigned GitHub
Issue fallback and separate delivery receipts.

Known intentional gap: independent 20-session alpha research results
are currently delivered as GitHub Actions artifacts, not structured
readable source metrics in the Radar data branch. H122 explicitly
reports NOT_AVAILABLE_AS_READABLE_SOURCE and does not invent win rate,
trades, significance or economic returns. A subsequent separately
verified export can extend the bridge once matured genuine outcomes
exist without resetting the ongoing experiments.

Test: python -m unittest discover -s research/h122 -p 'test_*.py' -v
No H119, H120, H121, H054, Tier-1 or Radar live logic changes.

## Source coverage outages (20 November 2026)

If Federal Radar explicitly publishes `ok=false` with insufficient price
coverage, zero watch candidates and `data_coverage_ok=false`, H122 now
records the actual source failure reason and coverage percentage, and emits
one transition alert when previously healthy coverage is lost. It does not
interpret a missing/partial price feed as a losing or winning strategy.
Contradictory reports, fabricated approvals, corrupt metrics and missing
required data still fail validation. The original Radar data and H083
experiment clock are never modified; no fills or retrospective metrics are
fabricated.
