# AGENTS.md — rules for ANY AI or person who runs tests in this repo

This repo is the decision center for the owner's trading bots. Read `CLAUDE.md` for the full rules.
The short version, which every tool (Claude, ChatGPT, Gemini, Copilot, ...) must follow:

1. **A scan or screen result is a lead, never a decision.** Only `python run.py --hypothesis <id>` / `--all`
   writes `decisions/registry.json`. Bots act only on `verdict: ACCEPT`.
2. **Time machine check after every selection test.** Any process that picks winners from many candidates
   (arena screen, top-N books, switcher, new scan methods) must pass the `Time machine test` workflow
   (`lab/timemachine.py`, same timeframe AND same side) before it is a real-money candidate.
   Pass = forward record inside the expected band in at least `timemachine.min_inside` (2 of 3) cutoffs.
   Why: on 2026-10-17 and 2026-10-19 the arena picks looked great in backtest and fell below the band in
   almost every replay; backtest rank vs forward rank correlation was ~0. Fixed literature rules (K1/K2,
   H054) passed 3/3.
3. **Write the acceptance rule BEFORE looking at results** (sub-periods, neighbour settings, 2x costs).
   Report the number of trials. Pick a flat robust region, not the single best point.
4. **Never loosen `validation.GATE`.** A gate change needs a line in `hypotheses/CHANGELOG.md`.
5. **New idea = new hypothesis id** in `hypotheses/registry.yaml`. Never reuse an id.
6. **No look-ahead.** Signals use data up to close t only (swing points are known k bars later).
   Fundamentals are point-in-time.
7. **Free data and tools only.** The owner works from an Android phone + GitHub Actions.
8. **Run `python tests/test_core.py` before every commit.**
9. **Directions:** arena / screen / time machine run three books per timeframe: `both` (one book trades
   long and short), `long` only, `short` only (`config/arena.yaml` → `sides`, CLI `--side`,
   folders `decisions/arena/<tf>`, `<tf>_long`, `<tf>_short`). Compare a direction only with the time
   machine of the SAME direction.
10. **Always write the weak points** (lost periods, untestable data, single-sector dependence) and say
    "no better result found" when the rule says so.

- Win rate alone means nothing. Every screen report shows win rate, payoff (avg win / avg loss), breakeven win rate = 1/(1+payoff), the margin (win rate - breakeven) and net expectancy per trade (`lab/perp.trade_stats`). Read the margin, not the win rate.

- H054 bot parity: `h054_spot_bot/bot/signal.py` is a copy of the H054 rule in `lab/core.py`. `tests/test_core.py::test_h054_bot_parity_fixture` fails when `lab/core.py` changes. Then run `python tests/make_parity_fixture.py`, copy `tests/fixtures/h054_parity.json` to `h054_spot_bot/tests/fixtures/`, and update `bot/signal.py`. Never trade live while the two tests disagree.
