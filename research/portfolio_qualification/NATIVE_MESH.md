# Repo-native Evidence Mesh — stage 1 of autonomous strategy research

This layer is the missing **data-first** bridge for the ten repositories
currently accessible through the GitHub integration. It does **not** claim
that adding an observer proves any of the hypotheses profitable.

Each repository launches the same pinned and independently tested open-source
`research.portfolio_qualification.mesh` module **inside its own checkout**.
All source inputs are explicitly enumerated and tied to actual repo-native
records, incl. source-branch ref/SHA and SHA-256 of the original source.
No private source is exported to quant_superlab: private `us_f1_bot` runs
and retains its observations **inside its own private Actions**.

### Lifecycle

1. Existing repo-native ingestion/scans keep producing genuine source data.
   No broken/blocked API is fabricated, no missing candle interpolation,
   no reset of existing PAPER clocks or old historical returns.
2. Mesh independently reads those real repo reports and commits a unique
   source-content fingerprint into `research/strategy-mesh-evidence` inside
   **each source repo**. Identical status files DO NOT become new observations.
   Existing SHA chain is verified before append; backward as-of timestamps
   block the append; same as-of revisions are labeled and never counted as
   new prospective measurements.
3. Domain-specific **research diagnostics** run. These include BIST
   historical first-half-selected challenger vs published second half,
   F1 existing paired shadow session maturity, ICT selected-rule holdout
   diagnosis, real V13 pending vs matured research observations, H083
   period guard, 30-day Tier-1 replay distinction and capital-flow
   independent-method sample coverage. They are exploratory unless
   independently verified. No cross-asset league table of incomparable
   CAGR or selected winner is created.
4. Each repo's economic grammar from `catalog.json` produces a FINITE
   design-only queue of valid single-source hypotheses and complementary
   feature pairs, not a blind Cartesian parameter grid. A design is not
   a preregistered strategy, historical backtest, prospective trade or
   PAPER_ACCEPT.
5. When enough actual first-seen observations accumulate, the next
   repo-specific research PR must implement the matched controls, costs,
   true execution timing, independent OOS and frozen forward gates under
   that repo's original logic. The mesh cannot auto-skip these gates.

### Explicitly outside scope

- No new execution orders, trading Telegram, PAPER trades, production
  parameter changes, fake win rates, data backfill or alteration of
  `quant_superlab/decisions/registry.json`.
- No assumption that V11/V13 or the five H083 event-alpha tests are the
  same research question as existing H054 or H083 PAPER.
- No publishing private F1 trades or ledger to a public repository.
- GitHub Actions cron may be delayed; a green job or a new hash-chained
  report is not a profitable test.

### Run locally

`python -m unittest discover -s research/portfolio_qualification -p 'test_*.py' -v`

`python -m research.portfolio_qualification.mesh --repo quant_superlab --root . --out out/native_mesh`

`--ledger` is optional in dry-run and required in committed scheduled
source collection. A research branch mutation never changes main.

### Dedicated source workflows

Each source checkout should use a pinned SHA of this module and keep
research branch observations private to itself. Eaverse Release-held PAPER
data require a separate local release download; if absent the system
fails closed. No access-token privilege expansion is necessary.

### V2 source-cadence correction (Nov 23)

The first release exposed a material evidence-timing gap: Tier1 live
observations, signed-trade samples and the 30-day microstructure study are
written to its separate `state` branch, not stale main; its historical
replay results are on `reports`. The V2 bridge reads both at their actual
commit SHAs. It runs two fixed, descriptive 4-hour prospective checks on
real completed Tier1 observations: signed spot taker direction, and the same
sign only when a five-minute-fresh book imbalance agrees. The experimental
clock is the **actual observed-at timestamp**, not the truncated bar hour.
No dynamic threshold search, real fills, return guarantee, funding claims or
PAPER authorization is generated.

BIST now uses the published `data/engine_state_v3.json:last_run.utc` and
latest closed BIST session as its live source clock, separate from the
October static variant report. Eaverse uses the Release's `published_at`
and actual entries count, rather than an unknown or invented market time.
H054 preserves its separate band-30 PAPER evidence and does not interpret it
as LIVE permission. The Quant Lab also audits the independent H119/H120
source-observer timestamps without interpreting WATCH as official ACCEPT.

All V2 source-spec changes require the source workflows to be deliberately
re-pinned to this new module SHA. The old V1 evidence remains readable;
changed source fingerprints are additional provenance, not retroactive
alpha or duplicated hypothetical trades.
