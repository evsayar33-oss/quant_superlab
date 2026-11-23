# Cross-repo strategy qualification: research-only, no promotion

Purpose: expose what ten accessible strategy repositories actually observe
versus what has passed independent evidence gates. They do **not** share
one strategy optimizer, alpha threshold, return target or common lookback.
All methods remain source-repo-specific. Unknown / inaccessible sources
remain UNKNOWN, never silently treated as failures or wins.

## Stages and rules

1. **OBSERVE**: collect timestamped, real, quality-checked input with explicit
   source, availability, missingness and immutable evidence reference.
2. **DESIGN**: formulate a finite, domain-relevant family of independent
   information dimensions. Only explicitly allowlisted repo-specific triggers
   and economically coherent pairs are proposed: risk filters cannot become
   stand-alone strategies, and the system does NOT blindly try all pairs.
   Generated proposals are **research ideas only**, not executions. Real raw
   features, economically coherent interactions, benchmarks,
   threshold grids, fixed calendars and negative controls must be registered
   per source repo *before seeing outcome labels*. The broad design catalogue
   is **not** itself a preregistration or backtest.
3. **DISCOVER/BACKTEST**: test all preregistered candidate cells on point-in-time
   training data (or forward-only cohorts when historical PIT data cannot
   be reconstructed), account for family multiplicity and missing series.
   Delisted failures, feature timing and matching strata cannot be removed
   merely to improve headline outcomes.
4. **OOS & COST STRESS**: temporally untouched walk-forward and multi-regime
   comparison, conservative costs, true feasible fill timing, negative controls,
   concentration and false-positive rate. PnL from sampled mark/high-low is
   never called a fill.
5. **PROSPECTIVE**: freeze implementation SHA/parameters and subsequent
   first-seen clock. Wait for genuinely matured independent future outcomes.
   Retrospective reprocessing cannot count as independent confirmation.
6. **PAPER ELIGIBILITY**: independently reproduce the evidence passport using
   the source's own market-specific gates. This module can only output
   READY_FOR_INDEPENDENT_PAPER_REVIEW, **never PAPER_ACCEPT**.
7. **LIVE REAL MONEY**: wholly separate explicit human/production authorization,
   broker execution risk, slippage and safety. This module cannot grant it.

Routine WATCH can continue to collect prospective inputs (otherwise no future
evidence can ever mature). WATCH is *not* a strategy approval. Keep legacy
PAPER_ACCEPT / lab ACCEPT / rejected results and current bot behaviour intact.

## Source-specific distinctions

- `quant_superlab` lab ACCEPT belongs only to its official hypothesis ID;
  it cannot be copied into a source bot's unrelated strategy.
- `h054_spot_bot` local PAPER_ACCEPT is simulation-only, LIVE_DENY remains.
- `federal-incentive-radar` H083 two-month rotation is distinct from five
  preregistered 20-session causal event-alpha hypotheses. NYSE SKIPPED and
  COMPLETED_RESEARCH with counts_as_forward_month=false are *not* forward months.
- `early_accumulation_radar` preimpulse association and costed marks are not
  orderflow/CVD/fill evidence; V11 and V13 are different proof stages.
- `bist_orderflow_quant` historically high backtest returns remain PIT-uncertain
  until missing listed/delisted security histories are accounted for.
- `us_f1_bot` demo and paired shadow simulations do not establish untouched
  historical member coverage or out-of-sample validity.
- `global_capital_radar` source-based capital flow hypothesis should not be
  silently replaced by price-only direction as a qualifying leading strategy.
- `tier1_quant_terminal` historical replay and independent 30-day research
  are separate evidence streams.
- `eaverse` authoritative PAPER record is in a Release, not main: no claim of
  its individual candidate readiness from a README alone.
- `islem_onerisi_alarmi` static backtest files are not a live approval.

## Usage and non-effects

Run `python -m unittest discover -s research/portfolio_qualification -p 'test_*.py' -v`.
On GitHub Actions run **Portfolio strategy qualification audit (RESEARCH ONLY)**.
The workflow pins each public status JSON to its source commit SHA and uploads
`audit.json`, `audit.md`, and `candidate_designs.json`. It does not write
a single source repository, change any workflow that produces observations,
edit the existing `decisions/registry.json`, send Telegram, or place orders.
Missing GitHub source access and cron delays are recorded explicitly.

This is **phase 1: classification, finite research-design queue, eligibility
contract and regression tests**, not completed strategy synthesis or full
historical/OOS/forward execution. Actual market-specific validation engines
must be built or extended in isolated source-repo PRs after reviewing each
strategy family and accessible data. It is unsafe to claim those runs happened.

## Private-repository boundary

`us_f1_bot` is private. The `quant_superlab` workflow's repository-scoped
`GITHUB_TOKEN` cannot read its private source files. Even if permissions
change, the audit deliberately **never fetches private files** and reports
the evidence as unavailable rather than filling it from historical numbers,
asks for an overprivileged PAT, or publishes private strategy state into this
potentially public repository's Actions artifacts. Interactive authorized
GitHub connector review can evaluate that repo separately. An UNKNOWN in this
portfolio report must never be treated as a positive or a negative proof.
