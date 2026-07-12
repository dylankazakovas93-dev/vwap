# KNOWN_LIMITATIONS.md — generation 8 (cash-open level interaction study)

1. Unconditional phenomenon-discovery study only; no result here is a
   signal, strategy, trade, or proof of order flow/absorption/stop-
   hunting/dealer positioning. No entries, exits, sizing, TP/SL
   optimization, fitted MAE/MFE exits, or prop simulation anywhere.
2. Development partition only (2018-2022); validation/holdout untouched.
3. Not conditioned on the cash-open taxonomy (generation 6) — deliberately
   deferred, per instruction not to begin taxonomy-conditional analysis in
   this generation.
4. Touch search is restricted to 09:30-09:59 ET only; a level that would
   only be touched later in the session (10:00 ET onward) is recorded as
   untouched in this generation, by design, not by data limitation.
5. `directional_close_recross` requires strict close inequality; a close
   exactly at the level contributes to neither the continuation nor
   rejection side of that test (DECISIONS.md #6).
6. Family B's confidence interval on the Hodges-Lehmann estimate is a
   seeded percentile bootstrap, not the exact nonparametric CI
   (DECISIONS.md #11) — disclosed, not presented as exact.
7. Co-touch and cluster flags evaluate the raw touch condition against
   every other level's value at a specific bar; this is O(level²) per
   session (38×37 pairwise checks) but computationally trivial at this
   scale — no sampling or approximation is used.
8. Different `level_id`s touched in the same session are not
   statistically independent observations (shared subsequent price path);
   this is disclosed, not corrected for beyond the secondary family's
   Benjamini-Hochberg treatment — the two primary families do not attempt
   a cross-level_id dependence correction (Dylan's spec does not request
   one for the primary families).
9. Barrier and label thresholds are frozen and never selected by result;
   the diagnostic sensitivity grids ({0.5,1.0,1.5} for labels) are
   reported but never substituted for the primary `1.0` threshold.
10. `scipy`/`statsmodels` were installed into the runtime environment for
    this generation (Wilcoxon signed-rank, exact binomial/McNemar); no
    project dependency-lock file exists to record this formally.
11. As in generation 7, roll-week sessions are not excluded (consistent
    with prior generations' policy).
12. **Critical, verified during this generation's analysis**: generation
    7's synthetic control caps its draw at `[bucket_lo, bucket_lo+1.0)`
    for the open-ended `[2.0,∞)` normalized-distance bucket, while the
    real level's actual distance in that bucket is unbounded (verified:
    ES `prior_low`, mean real distance 23.1 scale-units vs. mean
    synthetic 2.5, max real 126.5). This makes Family A's touch-rate
    comparison mechanically biased (not a market effect) for the 17
    level_ids that predominantly land in that bucket (see
    `LEVEL_INTERACTION_REPORT.md`'s critical caveat). Not fixed here, per
    instruction to reuse generation 7's control unmodified; disclosed as
    the dominant interpretive limitation of this generation's Family A
    results.
13. Family B (paired D_5) reached zero confirmatory cells across all 76
    (instrument, level_id) tests — `real_isolated=1` and
    `synthetic_isolated=1` co-occurred in only 1 of 49058 ES unit-rows.
    This is a structural consequence of 38 densely-spaced levels sharing
    a `0.10·side_scale` isolation threshold, verified by passing tests,
    not a computation defect — but it means this generation cannot speak
    to the paired post-touch-path question at all for this level library.
