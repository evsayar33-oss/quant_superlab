# H087 — Quant Superlab institutional all-family meta-audit

This is a **read-only research record**, not a production strategy upgrade.

## Full manifest, not a fake re-run

`audit.py` enumerates **every tracked file** in the GitHub checkout
(600 files when run) and records all paths in `H087_REPO_INVENTORY.json`.
It audits archived evidence across these categories:

- Registered hypotheses, central validation gate and bots.
- Multi-asset H062/H073 and time-machine/random-entry baselines.
- H072 index/macro synthesis, H074 BTC/ETH/SOL fixed core, H076 ML, H077 vol ranges.
- H083 US event and stock rotation, H084 past-winner causal filters, H085 meta-NAV portfolios, H086 independently sourced VIX regime filters.
- Arena 4h/1d long/short/both six books, CPPI/protection, xsec funding carry.
- ICT/SMC multimillion-hypothesis report, all existing six per-asset placebo CSVs and selected NQ/SPX/XAU actual forward replay CSV.
- USD macro, paper H063–H065 and actual H052/H054 recorded 4h returns.
- GitHub Actions, terminal and market-data/provider infrastructure.

It **does not** claim to recalculate millions of original ICT, H062, H073,
ML or options trials: those are historical archived summaries, with
source and trial counts preserved. Dataset incompatibility makes arbitrary
cross-sector/cross-market signal blending methodologically invalid.

## Frozen experiment and source provenance

`FROZEN_PROTOCOL.yaml` was first committed on
`d29af1bbc757266a62296f279236027e39fbb09d` **before** running
the H087 synthesis. A subsequent edit repaired two missing YAML
booleans (syntax only). None of the candidate definitions, split dates,
costs, tests or gates were modified after H087 outcomes were viewed.

Source return data are downloaded from existing immutable GitHub
Actions archives:

- H085 original completed 14 × 25bp monthly strategy NAVs,
  run `43571747386`.
- H086 original 5 lagged daily VIX risk allocations and compounded RF,
  run `43576823624`.

All H085/H086 observations were **already exposed in previous
research**. H087 is deliberately labelled `REUSED_TEST` and
**can never be reported as a new sealed historical holdout**.

## Exhaustive registered crossover: 70 combinations

Exactly 14 H085 monthly stock rotation / allocation portfolios × 5
H086 prior-month VIX overlays, evaluated on **43 fully aligned calendar
months** February 2023–August 2026.

- Exposure for month t is the H086 allocation observed by the LAST close
  of month t-1, never inside month t.
- H085 already contains its own underlying simulated commissions;
  10bp and 20bp per one-way **additional** VIX overlay turnover added.
- Cash receives compounded Fama-French monthly RF.
- Matched benchmark is H085 net SPY monthly return, not a synthetic
  arbitrage baseline. The mixed RF/SPY proxy is a **limitation**.
- First 23 months (through 2024) used for diagnostic selection, last
  20 months used for chronological *reused-history* monitoring.

Chance detection and stress:
- Approximate 2,000-rep stationary 3-month-block familywise max-stat
  White Reality Check across the **whole 70 rule family**.
- 42 nonzero circular calendar shifts of all risk filters as
  timing placebo, maximum measured across 70 models.
- Extra fee doubling; delete the two best active months;
  compare against static risk weight estimated solely before 2025.
- Select by 2023–2024 performance and evaluate 2025–2026 without
  re-ranking. Correlated candidates are never counted as 70 independent bets.

## H052/H054 4h forward stress

From 162 dated returns each: missing/duplicate and finite-data
integrity, compounded PnL, 2,000 stationary-block bootstrap replicates
(block mean 30 four-hour bars), omit the five largest winning bars,
correlation of the two related systems and paired difference.

This is NOT the 30-day Paper Watch: H063–H065 main history is
stale and reconstructed PnL is not prospective observation.

## H056 post-hoc follow-up

Funding carry looks profitable locally: its xsec result reports
`accepted=true`, but the H054+H056 combination is `accepted=false`
and the central decision registry has **no H056 ACCEPT**.

An additional explicitly **post-hoc** sensitivity check compares the
five complete calendar years 2021–2025 (omit partial 2026):

- Base: 4/5 positive years, exact fair-year sign-null p=0.1875.
- 2x costs: 3/5, p=0.5000.
- Delist shock: 4/5, p=0.1875.

Small n, non-independent market years, historical Binance funding
proxies and unmodeled cross-exchange execution mean no statistical
certification is warranted. No live deployment.

## Reproduction

Run the GitHub Actions workflow `H087 — Full repository audit and 70-way risk synthesis`
on the H087 research branch. It runs the six offline unit tests, checks
GitHub archived sources and builds complete outputs under `results/h087/`
as a downloadable Actions artifact.

Files: inventory, family audit, H052/H054 block stress, exact H056
post-hoc sign test, all 70 crossover models, all statistical chance
diagnostics and a Turkish `H087_REPORT_TR.md`.

**No production files, central ACCEPT decisions, broker orders or
scheduled live trading actions are changed.**
