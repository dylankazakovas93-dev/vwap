# KNOWN_LIMITATIONS.md — generation 5

1. Discovery-stage, standalone-feature screening only. No result here is a
   strategy, model, or tradable edge; combinations (with each other, with
   generation 4's previous-close features, or across ES/NQ) are explicitly
   out of scope.
2. Development partition only (2018-2022); validation/holdout untouched.
3. VWAP-derived features (Sec. 4) require >=30 overnight bars; sessions
   with a materially shortened overnight (rare, e.g. data gaps) will have
   these features undefined, not imputed.
4. Sec. 6 relationship variables require a non-early-close predecessor
   session (same exclusion as generation 4, ~3.5% of sessions); Sec. 3-5
   features do not depend on the predecessor and are unaffected.
5. `return_acceleration_W` at W=60 requires 120 minutes of pre-open data
   (two full 60-minute windows before 09:30); on sessions with a short
   overnight this may be undefined more often than smaller W's version.
6. 720 elementary tests are run; the declared Bonferroni correction is
   conservative given expected feature redundancy (the 5 pre-open windows
   in particular are highly overlapping); an effective-N sensitivity is
   reported alongside, per SPEC_OVERNIGHT.md Sec. 11.
7. Roll-week sessions are not excluded (consistent with prior generations'
   policy).
8. No macro/news calendar is used to stratify overnight behavior
   (consistent with prior generations).
