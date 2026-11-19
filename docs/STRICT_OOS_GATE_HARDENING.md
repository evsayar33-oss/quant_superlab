# Central lab gate: strict nested OOS and risk-path hardening (2026-11-19)

## Why this change

Prior to this change, staged rule candidates selected stage-2 exit and
stage-3 sizing *seeds* from full-history returns and then applied a
walk-forward to the globally curated variant pool. Even though fold
scoring used earlier data only, stage inclusion itself had future
information. OOS rule trade counts were also taken from the FINAL
variant's ledger, not the variant actually selected in each test fold.

## New gate semantics

- At every outer test fold, candidate stage-2 exits, stage-3 sizing and
  overlays are generated only from earlier train-window rankings.
- Variant returns can be precomputed as a causal speed cache; the
  provenance of the *candidate pool* and selection is train-only.
- Train and test time windows, chosen variant, eligible stage count and
  genuine within-fold completed trades are recorded for every test fold.
- Trials attempted in either staged diagnostics or nested selection
  are included in the multiple-testing accounting.
- The final all-history top-variant sweep remains labelled **exploratory**
  and is not used to create OOS alpha claims.
- Old full-history-selected OOS Sharpe is retained as a DIAGNOSTIC
  comparison, not as a gate input.
- Cross-boundary trades inherited from an earlier model are excluded
  from the completed OOS trade count. Model switches without a fully
  verified transition fill model cannot automatically earn ACCEPT.
- Required PBO, White Reality Check and rule diagnostics cannot be
  silently missing while granting ACCEPT.

Existing hypothesis entries and model weights are unchanged.
Historical ACCEPT decisions are not silently rewritten. This change
governs validations *after* merge, and any previously reported strategy
needs independent revalidation before being upgraded to LIVE.

## Monte Carlo interpretation

Two different simulations were already present and remain separate:

1. OOS block bootstrap samples alternative return paths and estimates
   Sharpe-positive frequency, 5th percentile CAGR, and drawdown. The
   estimator now uses a circular stationary bootstrap with uniform
   starting indices and an explicit simulation-method tag.
2. Rule trade-order shuffle reorders the same realized trade returns.
   With compounding, terminal wealth is order-invariant; this shuffle
   is ONLY a sequence/drawdown stress test, never an estimate of
   possible new trading profits. Its JSON now flags that limitation.

Neither method simulates exchange orders or guarantees future profits.

## What this does NOT solve

- The original return generator must be causal and historically PIT;
  a present-day survivor universe cannot be made historical-PIT by
  adding a statistical gate.
- Transaction prices are still modelled using per-market fee/slippage
  assumptions. No live executable fills or market impact are inferred.
- A historical price-time feed does not prove quote arrival time.
- A strategy switch across a walk-forward boundary still requires a
  dedicated execution replay. Until proven, strict validation fails
  closed on a potential ACCEPT, rather than charging zero and passing.
- 30-day PAPER observation windows do not replace adequate multi-regime
  independent OOS evidence.

## Operational rollout

This is a CENTRAL LAB-ONLY change. No code is edited in
early_accumulation_radar, tier1_quant_terminal, h054_spot_bot or
federal-incentive-radar. H119–H122 source adapters/append-only evidence
branches, live/PAPER bot engines and their original experiment clocks
continue untouched.

Verification:
- python -m pytest -q tests/test_strict_oos.py
- python tests/test_core.py
- Quant Superlab CI (other research suites and Typescript bot/terminal CI)

A green CI verifies algorithm contracts, not that any specific
strategy has passed the newly more conservative ACCEPT gate.
