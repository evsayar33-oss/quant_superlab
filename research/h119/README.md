# H119 — Autonomous Alpha Discovery / quant_superlab research bridge

## What is new

H119 is a **read-only integration between two separate repositories**:

* early_accumulation_radar continues the original V8–V13 anomaly discovery,
  cost-stressed strategy research and real first-seen prospective cohorts.
* quant_superlab H119 pulls **commit-pinned and SHA-linked research evidence**
  from V12 BIST/US, V13 BIST/US and V13 crypto perpetual futures. It checks
  the same rule/horizon search counts, economic selection gates, evidence
  continuity and forward-trial lock/decision records before accepting anything
  as an **unapproved research hypothesis**.
* All event records, original source commit IDs, first-seen milestones and
  delivery receipts stay in the isolated
  research/h119-autonomous-evidence branch, in research_evidence/h119/.
  This branch is distinct from main and existing PAPER branches.

Current source search scope: 16 equity patterns × 4 holding horizons × two
markets = 128; crypto 23 patterns × two directions × two horizons = 92.
Total **220 strategy variants** re-checked from the published V13 source
reports. These are research variants, **not 220 confirmed trade strategies**.

The source itself generates the new hypotheses and the source's prospective
trial ledgers test them. H119 does not invent fills, silently backfill
unknown observations, refit thresholds or make candidate parameters executable.
It does not yet reproduce the complete OHLCV trials locally with native
quant_superlab strategy engine. When a variant cannot be materialized under
lab/candidates.py from verified point-in-time data, the official validation
gate is **NOT_RUN**. No fake DSR, PBO, Reality Check, walk-forward or full
risk-adjusted verdict is written.

## Why separate from the original lab decision gate?

Quant_superlab lab/validation.py already requires an established
walk-forward/OOS validation, DSR, PBO/Reality Check, 2× costs, minimum history,
random-entry and parameter stability. H119 deliberately **does not modify**
GATE, hypotheses/registry.yaml, decisions/registry.json, lab/client.py,
any live bot, H054 or H089/H111/H115/H118 paper records.

A V13 strategy with modelled costs beating its matched control is only a
COSTED_RESEARCH_CANDIDATE. A newly locked independent trial is
FUTURE_TRIAL_FROZEN. If it later meets its prospective research conditions,
it becomes POSITIVE_FORWARD_RESEARCH, **not ACCEPT**. An actual quant_superlab
ACCEPT is monitored separately from decisions/registry.json, and only that
existing official decision (not imported V13 data) can produce
NEW_LAB_ACCEPT.

These categories prevent promotion by headline win rate or one seemingly
profitable lookback. This is a research bridge, **not a turnkey order-bot**.

## Notifications: Telegram first, GitHub issue fallback

Workflow reuses the existing secrets:

* TELEGRAM_TOKEN and CHAT_ID (primary)
* TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (alternative names)

When a strictly new milestone occurs, H119 sends a short Turkish Telegram
message explaining source, market, rule, direction, horizon and verification
status. An unsuccessful Telegram send, or missing secrets, attempts to create
an independently visible **GitHub Issue fallback**, with permanent event
fingerprint and linkable audit history. A successful delivery is stored in a
separate SHA-linked receipts.jsonl; retry does not intentionally resend
already acknowledged events. GitHub issue subscriptions and Telegram delivery
depend on the user's GitHub/Telegram account configuration; GitHub Issue
creation alone does not guarantee a push notification on the phone.

The FIRST run sends exactly one setup/channel test message to verify
notification connectivity, not a fictitious profit discovery. Historical
H052/H054 ACCEPT decisions are seeded, **not announced as newly discovered**.

Only important milestone messages are sent:
1. Cost-positive screened research candidate
2. Frozen prospective profit trial
3. Positive future-costed research decision (still not executable PnL)
4. Newly registered official lab ACCEPT
5. Removal of a prior ACCEPT (risk-relevant change)
6. One-time setup test

There are **no routine hourly 'nothing found' messages**. Batch limit is
eight events per poll; undelivered events stay queued.

## Scheduled operation and reports

GitHub Actions:
H119 — Autonomous Alpha Discovery, Validation Bridge and Telegram Milestones

On first merge to main, an automatic **path-limited push bootstrap** runs.
It also runs every four hours (01:37, 05:37, 09:37, 13:37, 17:37, 21:37 UTC)
and can run via workflow_dispatch.

The GitHub token for this repo needs contents:write and issues:write for the
state branch and fallback issues. The source repo is public and fetched
READ-ONLY via branch commit SHA pinned to each run; no cross-repo secrets
or extra API credentials are necessary.

CI also checks regression tests from research/h119 and the repository's
existing tests/test_core.py, so the integration cannot silently relax the
lab gate. Failed or rewritten upstream source branches block the scan. A
failed GitHub Actions run does not erase valid research.

Outputs:
* Actions artifact h119-autonomous-research-<runid>
* results/h119/report/report.json and report.md in artifact
* research/h119-autonomous-evidence: manifest.json, events.jsonl,
  receipts.jsonl, latest.json

## Limitations

This integration does **not** automatically rewrite research hypotheses into
tradable bot code or replace full quant_superlab validation. For BIST/US the
source universe does not prove historical PIT membership or delistings. Crypto
perpetual returns are quote-snapshot hypothetical marks; funding, margin,
liquidation, market impact and actual fills are not independently proven.
Repeated-symbol and multiple-testing residual uncertainty remains.

Profit-seeking research is possible and continuously monitored; **positive
modelled results are not guarantees of independently executable alpha**.
