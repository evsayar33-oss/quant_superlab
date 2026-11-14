# H086 — Five frozen VIX/market-risk hypotheses on independent sources

**Freeze audit:** [PREREGISTRATION.yaml](PREREGISTRATION.yaml) was committed in
a standalone GitHub commit *before any H086 model result or external source*
was downloaded (commit `b150a28c7ad238e5148dc206bb49b2ce6e93e976`).

Sources:
- Kenneth R. French Dartmouth Data Library: *F-F Research Data Factors [Daily]*,
  CRSP US value-weight market excess return and daily RF.
- Cboe: publicly published daily VIX Index closes.
These are independent of H083's Yahoo/US event ledger and H085's derived
strategy NAVs. The data are historical, not fresh prospective paper data.

Pre-registered five hypotheses: shock defense; VIX level band; 21-day capped
vol targeting; one-year relative VIX median risk-off; VIX plus adverse market
momentum. No fitting or threshold optimization.

Discovery 1990–2009, validation 2010–2018, locked historical holdout 2019–Aug
2026. Daily signals are strictly lagged to the prior close. Return on cash is
RF and returns of invested capital use Mkt-RF+RF. All returns are in fractions,
and one-way exposure turnover pays 10 bp and a 20 bp stress scenario.

Strict multiple-testing corrected paired monthly stationary-block bootstrap and
11 threshold gates per preregistered model. The effect is measured against
a passive 1x **CRSP market proxy**, not a directly investable SPY portfolio.

No part of this branch changes production decisions, bot execution,
historical H083/H085 data or strategy parameters. Even a historical pass
would require point-in-time vintage data, broker-realistic ETF simulation
and genuinely prospective forward records before anyone trades it.

Run:
```sh
PYTHONPATH=research/h086:. python -m pytest -q research/h086/test_h086.py
python research/h086/h086_run.py --output results/h086
```

The GitHub Actions workflow automatically executes the offline regression
tests, then independently downloads the sources, and uploads the full evidence.
Data-source failure is a visible **failed experiment**, never replaced with
fabricated prices or Yahoo substitutes.
