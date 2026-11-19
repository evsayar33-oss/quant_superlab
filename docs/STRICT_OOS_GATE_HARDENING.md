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
- A position can legitimately span walk-forward reporting windows.
  A closed trade contributes once to OOS statistics if the same model
  was actually selected for the trade's entire lifetime.
- Selecting a new model at a fold boundary is a normal strategy operation,
  not an automatic failure. The first OOS bar's cached turnover cost is
  replaced with its cost-accounted rebalance from the previously held
  portfolio, preserving intra-bar entry/exit turnover.
- This is a historical **simulated** handoff using the existing costs,
  not evidence of broker-verified fills or order-book queue priority.
- Required PBO and White Reality Check must have sufficient statistical
  data when multiple variants were evaluated. Full-history diagnostic
  delay, random entry, and neighbouring-parameter checks remain visible
  but cannot act as hard gates against a different stitched OOS policy.

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
- Handoff costs are calibrated to the existing proportional commission
  and slippage model; true bid/ask depth, partial fills and execution
  timing require a broker or recorded order-book replay. The result
  must never be called exchange-realized PnL.
- Statistical parameters and regularization must not be selected using
  OOS outcomes. Train-only fold selection still applies.
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

## Fairness correction: 2026-11-19

The first strict OOS patch contained an overly conservative
`cross_boundary_trades == 0 and model_switches == 0` approval
condition. That would reject almost any adaptive model whose valid
trade crossed a calendar fold boundary or that changed parameters
over time. This was removed: actual simulated portfolio handoff turnover
is debited in the test return path, including same-bar churn. The
PAPER / source / LIVE engine is not changed.

In addition, retrospective full-history staged variant sweeps are no
longer run or counted *again* as trials that were not available to the
fold-by-fold candidate selector. Only fold-authorized candidate
configurations enter the selection-related trial burden.

Original diagnostic robustness tests remain available for research,
but do not veto the actually tested stitched OOS policy when they
were measured on a different last-selected model over all history.
