# KNOWN_LIMITATIONS.md — ES-NQ unsupported move discovery

1. Purely descriptive causal-dislocation study; no profitability, entry,
   exit, sizing, or prop-account simulation logic anywhere. Path
   convergence is not trading profitability.
2. Development partition only (2018-2022, ES/NQ); 2023+ never read.
3. The regression orientation (`NQ_return = alpha + beta*ES_return +
   residual`) is frozen and never re-oriented per event; a residual
   defined the opposite way (`ES` as the dependent variable) would not
   necessarily produce the same z-scores or event set — this generation
   only tests the one frozen orientation, as instructed.
4. The resolution-attribution materiality threshold (`0.25 * |r0|`,
   `DECISIONS.md` #4) is one reasonable, frozen choice; a different
   threshold would reclassify some `PARTIAL_OR_MIXED` events into
   `LEADER_REVERSAL`/`LAGGARD_CATCHUP`/`JOINT_CONVERGENCE` or vice
   versa. Not re-tuned after viewing results.
5. Permutation-test matching strata use `leg x leader_instrument x
   leader_direction x clock_hour` (`DECISIONS.md` #6); leader-z and
   residual-z bands are recorded and reported per event but not used as
   additional shuffle keys, to avoid degenerate (near-empty) matched
   strata. A stricter six-key stratification was not run.
6. The 60-prior-valid-session requirement for causal normalization and
   regression means events cannot be evaluated in the earliest part of
   the development partition at any given clock slot until 60 valid
   occurrences accumulate; early-2018 sessions are systematically
   under-represented in the earliest calendar weeks at each clock slot,
   though this does not bias any single event's own causal estimate.
7. `RESIDUAL_PATH(h)` reuses the frozen event-time `alpha`/`beta`
   applied to increasingly long cumulative-return windows as `h` grows;
   this is an explicit simplification instructed by the task ("do not
   refit... during the outcome window"), not a claim that a 5-minute-
   scale regression coefficient is the "correct" scale for a 20-minute
   cumulative return.
8. `SAME_BAR_AMBIGUOUS` and `INCOMPLETE_HORIZON` events receive no
   resolution-attribution category by design (intrabar order is never
   inferred; incomplete horizons cannot be attributed at all) — they are
   retained in the full event ledger and counted, but excluded from the
   primary comparison's resolved-non-ambiguous denominator.
9. Multiple-testing correction (BH) controls false discovery within the
   declared primary family (`leg x leader_instrument x
   leader_direction`); it does not correct across the primary family and
   every secondary/diagnostic table jointly.
10. Contract-roll weeks are not specially excluded, consistent with the
    root front-month series' policy of no back-adjustment.
11. Both ES and NQ synchronization requires bars present in both
    instruments' audited parquet at exact matching timestamps; any
    period where one instrument has systematically thinner 1-minute
    coverage than the other (e.g. very early in the partition, or during
    a roll) reduces the synchronized sample for that period, which is
    logged in `outputs/sync_coverage.json` and summarized in
    `reports/tables/` rather than hidden.
