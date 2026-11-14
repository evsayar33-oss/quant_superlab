# H086 — Independent-source pre-registered final research audit

**Run date:** 2026-11-14  |  **Research verdict: 0/5 historical approval gates passed. NO LIVE AUTHORIZATION.**

## Provenance and freeze integrity

- The [hypothesis preregistration](../research/h086/PREREGISTRATION.yaml) was
  first committed as `b150a28c7ad238e5148dc206bb49b2ce6e93e976`
  **before** H086 source acquisition and any results.
- Frozen original source: Dartmouth Kenneth R. French F-F Research Data Factors
  [Daily] (Fama-French CRSP market proxy) + Cboe VIX Index daily closes.
  No H083 or H085 Yahoo event/rotation inputs used.
- Data source SHA-256:
  - F-F archive: `96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89`
  - Cboe VIX CSV: `d4e2b1199951501b7757814b6e1c2356394922a7ea8ef16d85c3a4596e6e2c2d`
- Combined: **9,233** daily sessions, 1990-01-02 to **2026-08-31**.
  Exactly four missing original VIX daily matches forward-filled by *one
  trading session*, within the **1%** missing-data ceiling. No asset
  returns were synthesized.
- Data available at fetch: factors through 2026-09-30, VIX through 2026-11-13.
  Analysis cutoff 2026-08-31 was frozen in advance.
- Exploratory 1990–2009, validation 2010–2018, chronological one-shot
  **historical** holdout 2019–August 2026. This is not a prospective
  future observation or revision-vintage point-in-time source.

## Fully frozen strategy comparison

All return numbers are net of **10 basis points per one-way position
turnover**, including the initial position. Passive benchmark is always
invested in Fama-French CRSP market, earning RF on cash only when not
invested. The passive benchmark CAGR in the historical holdout: **17.44%**.

| Frozen hypothesis | Discovery excess CAGR | Validation excess CAGR | Holdout CAGR | Holdout excess CAGR | Max drawdown | 20bp stress excess CAGR | Holm-adjusted approximate p | Passed gates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H086A — volatility shock defense | -3.97 pp | -4.42 pp | +14.44% | -3.00 pp | -33.54% | -4.17 pp | 1.000 | 4/11 |
| H086B — VIX ≥ 25 risk band | -1.48 pp | -1.43 pp | +14.17% | -3.27 pp | -24.01% | -3.95 pp | 1.000 | 5/11 |
| H086C — 21d realized-vol target | -0.96 pp | -2.59 pp | +12.93% | -4.51 pp | -16.59% | -4.95 pp | 1.000 | 5/11 |
| H086D — VIX > 252d median | -1.88 pp | -4.75 pp | +12.58% | -4.86 pp | -18.37% | -6.00 pp | 1.000 | 5/11 |
| H086E — VIX + adverse momentum | -1.04 pp | -3.54 pp | +13.66% | -3.78 pp | -26.56% | -4.39 pp | 1.000 | 5/11 |
| **Passive market factor** | — | — | **+17.44%** | — | **-34.22%** | — | — | — |

Here **pp** means percentage points of annualized compounded return.
Every model lost to the passive market on annualized returns in each
of discovery, validation and holdout. None passed the 2019–2022 AND
2023–2026 positive-relative-return subperiod gates. All failed the
20bp cost-stress benchmark comparison. None met the Holm-adjusted
p <= 0.05 familywise requirement. The paired stationary-block
bootstrap used **92** historical holdout months, 2,000 replicates
and a three-month mean block length. Its probabilities are approximate,
not an exact proof of alpha.

## What did improve?

The **H086C** capped volatility target had a maximum holdout
drawdown of **-16.59%** versus the passive proxy **-34.22%**,
with a higher Sharpe estimate (**1.052** versus **0.905**).
That is *drawdown reduction*, NOT positive excess CAGR or evidence
of independent trading alpha: H086C earned +12.93% annualized while
the passive market earned +17.44%. Average H086C market exposure
was only **78.8%**, so lower downside partly reflects less stock risk.
An equal-risk, fully funded, investable ETF/broker execution comparison
would be needed to test practical value.

## Regret and release controls

- **New ACCEPT decisions = ZERO.** No changes to the live registry,
  production strategies, order routing, leverage or capital allocations.
- Do not search new thresholds on the now-exposed H086 historical holdout
  and represent a subsequent better result as sealed OOS.
- Market series is the academic CRSP proxy, not an exchange-traded SPY
  portfolio. VIX is an index observation, not a VIX futures return.
  Dividend accounting, ETF tracking, actual spreads and liquidity can differ.
- Historical external archives may be revised and are not as-of-vintage
  evidence. Even a retrospectively passing model would still need
  a genuine prospective, timestamped paper experiment before deployment.
- Lower drawdown may justify **separate future risk-budget research**,
  but no claim of new profitable alpha is supported today.

## Reproduction

- Successful [GitHub Actions H086 run](https://github.com/evsayar33-oss/quant_superlab/actions/runs/43576823624):
  **8/8 causality, parsing, cost and source integrity tests passed**,
  full independent-source study completed, results artifact uploaded.
- Evidence ZIP in that run contains `H086_DAILY_RETURNS.csv`,
  `H086_GATES.csv`, `H086_COMPLETE_RESULTS.json` and
  `H086_FINAL_REPORT.md`. Full losing outcomes and every gate are retained.
- Operational PR #13 and the earlier H085 results remain independent
  studies; H086 performs no follow-on optimization after observing its holdout.
