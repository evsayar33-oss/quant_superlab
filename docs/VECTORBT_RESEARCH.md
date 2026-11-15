# vectorbt independent research (optional; no strategy approval)

This tool is an **exploratory engine-parity check**, not an alternative to
`run.py --hypothesis`, `lab.validation`, DSR/PBO, PIT, or the two-year locked period.
It neither reads nor writes `decisions/registry.json`. No live trading endpoint.

## Setup (free, optional)

```bash
pip install -r requirements-research-ui.txt
streamlit run dashboard/vectorbt_research.py
```

Use a local historical CSV containing `Date,Close` columns. CSV is preferred
to implicit downloads so the test's input data is auditable. You may also run:

```bash
python -m lab.adapters.vbt_research data/example.csv --fast 5 51 5 --slow 50 251 10 --fee 0.001 --slippage 0.0005 --out results/vbt_research
python -m pytest -q tests/test_vbt_research.py
```

Outputs: one CSV row per **valid** fast < slow trial with net total return,
maximum drawdown, Sharpe, number of orders, maximum **full-path equity**
disagreement and a parity flag. JSON provides explicit assumptions, total
number of tested combinations and overall engine agreement. Every attempt must
be accounted for in downstream multiple-testing corrections, including
discarded combinations from other research runs. Use this research to **find
accounting bugs**, not to cherry-pick the best in-sample Sharpe.

## Execution consistency

- Both engines start with the same initial cash and source close prices.
- SMA crossover after **close t** produces an order at **close t+1** (one-bar
  signal shift). This avoids same-bar execution at an unknowable close signal.
- All-in, long-only, fee and proportional price slippage on both buy and sell.
- An independent cash/units ledger computes the full equity path; vectorbt
  calculates the same under matching settings.
- `max_equity_gap_pct_of_initial` must be below the chosen tolerance for
  every grid cell. A mismatch is **FAIL**, never silently averaged away.

This is *not* equivalent to the production trade engine's next-open execution
with intrabar stops; comparison of dissimilar fills is misleading. A parity
PASS only proves accounting agreement under these specific assumptions. Shared
data sources, corporate-action adjustments, survivorship, sampling bias, market
impact, PIT availability, OOS performance, and real fills remain **unverified**.

**Promotion path:** explicitly register a hypothesis, run the existing
independent out-of-sample and time-machine checks as required by
`PIPELINE.md`. The standalone exploratory results never grant ACCEPT.

## CI / security

The optional UI processes uploaded CSV in memory; it does not fetch data or
push anything to the registry. No secrets required. Parameter grids capped at
500 valid combinations to constrain accidental heavy scans. If you run the UI
on an internet-accessible host, restrict access and resource limits before
letting others upload files.
