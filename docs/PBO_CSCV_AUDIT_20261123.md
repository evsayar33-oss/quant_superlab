# CSCV PBO sampling-coverage audit (research only)

The central `lab.metrics.pbo` remains unchanged. Its default 16-block
CSCV partitions comprise C(16,8)=12,870 combinations, of which 1,839
are evaluated using deterministic stride 7. The added `pbo_coverage`
field in each new hypothesis validation report discloses the actual
partition count, how the sample was chosen, usable observations, and
whether partially missing return cells were filled with zero.

This is a **sampling coverage disclosure**, not a confidence interval or
another ACCEPT filter. Overlapping CSCV folds are dependent; do not treat
the partition count as an independent sample size, interpret PBO as a
probability of future trading losses, or claim historical returns are
broker fills. Full enumeration would be computationally expensive for
large variant matrices on free GitHub runners.

No change to `validation.GATE`, `lab.metrics.pbo`, registered decisions,
historical research, PAPER, LIVE, strategies, scheduled workflows,
bot execution, or central voting rules.

Run: `python -m unittest tests/test_pbo_coverage.py -v`.
