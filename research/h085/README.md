# H085 — Strategy derivatives from independent archived H083 research

Research-only exploration, NOT a new ACCEPT hypothesis. No live orders, alerting,
production bot changes, revenue promises or historical-results reclassification.

**Frozen input:** original successful H083 GitHub Actions artifact (run 43225656166).
Original rotation and event ledger SHA-256 values are independently verified by
the H085 workflow. H083 and H084 already exposed all 2023–2026 results, so
**no part of this analysis is a sealed holdout**.

## New ideas, frozen before results

- 6 prior-performance top-three/top-five rotation meta portfolios over completed
  rolling 3, 6 or 9 months.
- 2 SPY-regime cash controls, based only on prior 3 fully completed months.
- 2 inverse-volatility allocations based on 6 or 9 completed months.
- 2 50%-equal/50%-winner blends, a breadth-driven cash filter, plus EW10.
- 5 causal event-conditioners using **completed past outcomes only** and 90/180/365-day
  historical window requirements. Reported event trade PnL is not a funded NAV.
- Incremental 25bp and 50bp meta allocation turnover stress in addition to
  already-paid H083 rotation commissions. NAV blends are proxies: scaling
  original fixed Midas commissions is not exact, so an order-level replay is
  mandatory before any deployment.

The report includes losing variants, data coverage, the fraction allocated
to cash, benchmark SPY and an exploratory stationary-bootstrap max-mean test
across all registered variants. Any p-value on this already reused history
is descriptive and **cannot clear** the existing approval gate.

## Reproduce

```sh
PYTHONPATH=research/h085:. python -m pytest -q research/h085/test_h085.py
python research/h085/h085.py --h083-results results/h083 --output results/h085
```

On this research branch, `.github/workflows/h085.yml` runs both test and
frozen-history study automatically on push and uploads all outputs as an
Actions artifact. Existing production logic remains untouched.
