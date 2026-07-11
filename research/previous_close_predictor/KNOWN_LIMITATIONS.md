# KNOWN_LIMITATIONS.md — generation 4

1. Discovery-stage, standalone-feature screening only. No result here is a
   strategy, model, or tradable edge; interactions and combinations are
   explicitly out of scope and deferred to a possible future generation.
2. Development partition only (2018-2022); validation (2023-2024) and
   holdout (2025-> end) are untouched and results may not generalize.
3. Early-close predecessor sessions are excluded outright from the primary
   analysis (count reported separately, not imputed); this slightly
   shrinks the sample relative to the full atlas target set.
4. Trailing baselines require 20+ prior valid sessions; the first ~20-60
   development sessions per instrument have undefined normalized features
   and are excluded from those specific cells (not imputed).
5. 480 elementary tests are run; the declared Bonferroni correction is
   conservative (windows and features are correlated, not independent),
   and an effective-N sensitivity is reported alongside as a check, per
   SPEC_PREDICTOR.md Sec. 9.
6. `close_location_W` and `signed_efficiency_W` are undefined (not zero)
   when `range_W==0` or the path sum is zero respectively; occurrence
   counts are reported per window.
7. Roll-week sessions are not excluded (consistent with prior generations'
   policy).
8. No macro/news calendar is used to stratify previous-session behavior
   (consistent with prior generations; not acquired here either).
