# KNOWN_LIMITATIONS.md — generation 3

1. This is a descriptive atlas only; no statistic here should be read as
   a predictor, filter, or trading signal. Any apparent asymmetry or
   concentration is reported as a fact about the historical sample, not as
   evidence of a persistent or exploitable effect.
2. Development partition only (2018-2022); results may not generalize to
   the validation (2023-2024) or holdout (2025-> end) periods, which are
   untouched by design.
3. Primary-sample gating requires all 30 bars 09:30-09:59 present; sessions
   with any gap in that window (e.g., certain holiday half-days, data
   irregularities) are excluded outright, not imputed. The excluded-session
   count and reasons are logged, not hidden.
4. U_h and D_h are running extremes from a single fixed origin (O); they
   are not independent across nested horizons (U_30 >= U_15 by
   construction) — this monotonicity is expected and reported as a
   sanity check, not a finding.
5. Q_h and E_h are undefined (not zero) when U_h+D_h=0 (price never moved
   from O through horizon h); this occurs rarely at h=1 and is reported
   per horizon.
6. Roll-week sessions are not excluded (consistent with generation 1's
   policy).
7. No cost, slippage, or execution assumption is relevant to this
   generation — there is no trade being described.
