# H083 — Two-track US stock trading research (Midas execution)

**Research only. Not authorized for live trading, auto-orders or production signals.**

H083 tests previously untried **entry and exit styles** with source-causal signals,
fixed per-order Midas commissions and portfolios with finite capital.

**Track A: 34 event-conditioned strategies**: 5/20/60-session next-open hold,
3-session delay, next-close confirmation, 20-day breakout, RSI(2) pullback,
3-day dip, positive 20-day momentum, 50-day trend, beta <=1, liquid>=5m USD
proxy dollar turnover, prior SPY regime, sector relative strength, factory
investment theme, ATR2 stop/ATR3 target, close-based trailing ATR stop.

**Track B: 10 distinct weekly/monthly technical stock rotation strategies**:
weekly 3m momentum, weekly 50MA trend, monthly 12-1 momentum, monthly breakout,
monthly RSI(2) pullback, monthly low beta, monthly strong sector, monthly low
volatility squeeze, risk-on momentum/cash, market-relative strength.
At most five equally ticketed cash equity positions, no margin or short selling.

### Universe

H081 source-date-eligible **619 individual records** (120 source tickers)
are frozen in `H081_eligible_snapshot.csv` with SHA256 in the report; 60-day
ticker event cooldown precedes evaluation. No use of the earlier 217
**measured** event subset to avoid survivorship-by-availability selection.
Unobservable/delisted securities are **reported missing**, not given synthetic
returns. Rotation ticker eligibility begins **only after the first historically
available event for that ticker**. Dataset as-of 2026-11-11 to avoid incomplete
current US trading day.

### Fair performance comparison

- **Midas** $1.50 per buy and $1.50 per sell, base $2,000 stock ticket.
- Additional 5 basis points each side for **market execution friction** (not
  an extra Midas commission); can be sensitivity tested by changing parameters.
- SPY benchmark held for **identical trading intervals**, with same fee and
  friction when comparing individual trades.
- Monthly/weekly rotation NAV includes commissions, proceeds, unused cash,
  mark-to-market, terminal close liquidation; compare to fully invested SPY
  buy/hold baseline (not equal market beta).
- Global fixed period boundaries (2025-07-31, 2026-06-02) and **exit-date purge**.
- Monthly clustered one-sided test, **Benjamini-Hochberg q <= .10** across all
  34 Track A rules; another family of 10 Track B rules corrected separately.
- Separate **10-rule rotation-family** overfit audit: stationary-block White
  Reality Check, 8-block CSCV PBO (70 partitions), approximate Deflated Sharpe
  Ratio. These are diagnostic estimates on **already exposed** historical data,
  NOT forward/untouched holdout proof or release clearance.
- Execution stress audit: 0/5/15/30bp each side applied to frozen realized
  trade ledgers. This is an approximate stress, not a fresh cash-rebalanced run.
- Concentration audit: profit contributions by top one/two tickers, and
  full-account SPY buy-and-hold NAV with identical fee/impact assumptions.
- **All historical results already exposed in H078–H082**, including 2026;
  `REUSED_TEST` is not a sealed out-of-sample test.

### Limitations and blockers for approval

- Frozen feed omits historically unavailable publication times for 1,945
  federal events; these remain in the coverage findings, not eligible signals.
- Yahoo corporate-action-adjusted daily prices are NOT independently
  point-in-time audited; survivorship, delistings and adjustment bias can remain.
- Sector maps and security history in source feed are not externally
  point-in-time audited; ADR/OTC/Midas tradability must be verified.
- Beta/volume signals use historical prices, not inaccessible current financials.
  Historical fundamental quality and 2026 current Unusual Whales snapshots
  are NOT retroactively imputed.
- Daily bars cannot guarantee that real market/stop orders fill at modeled prices.
  Stop-before-target and gap-through-stop use conservative assumptions.
- A watch signal is exploratory, not certified profitable; production needs
  prospective untouched walk-forward/paper monitoring and economic validation.

### Run

```
python -m pytest -q research/h083/test_h083.py research/h083/test_h083_robustness.py
python research/h083/run_h083.py \
  --events research/h083/H081_eligible_snapshot.csv \
  --output results/h083
```

The branch-local H083 GitHub Actions workflow performs the same steps and
uploads all results, errors, exclusions and daily NAV in its artifact.
This module does not alter `lab/event_study.py`, existing workflows or live bots.
