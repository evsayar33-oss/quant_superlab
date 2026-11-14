# P11 post-merge real-provider diagnostic (read-only)

This diagnostic does NOT dispatch the actual production Watch/Arena scheduler,
send Telegram, commit to main, send broker orders or alter any strategy verdict.

The Actions job tests `python -m lab.watch daily` on a throwaway checkout
with real Yahoo inputs; asserts that `observations.csv`, `state.json`
and reconstructed `history.csv` are produced without duplicates and that
the latest closed bar is not stale.

The independent sources job checks canonical GitHub client registry,
recent Bitget/OKX-fallback public BTC/ETH OHLCV, a bounded BTC funding archive,
and the six existing Arena roster/switcher files. It explicitly separates
source availability from successful Arena end-to-end completion.

Failures (including upstream rate limits) are preserved in Actions logs and
must not be hidden. Results upload even if a job fails. Production main is
unchanged until the user explicitly approves any future fix PR.
