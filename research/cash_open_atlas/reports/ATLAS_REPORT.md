# Cash-Open Target Atlas — Report (Generation 3)

Branch: `research/cash-open-target-atlas`, base commit `1d39d8e`.
Development partition only (2018-01-03 -> 2022-12-30). **Purely
descriptive — no predictor, rule, entry, exit, level, band, pivot,
reclaim, TP/SL, MAE/MFE, or sizing is defined or implied anywhere below.**
All values are unconditional historical statistics of the sample.

## Sample

| instrument | total dev sessions | primary-valid (09:30-09:59 complete) | secondary-valid (09:30-10:29 complete) | excluded (reason) |
|---|---|---|---|---|
| ES | 1291 | 1286 | 1285 | 3 incomplete primary window; 1 additional incomplete secondary-only |
| NQ | 1291 | 1284 | 1283 | 3 incomplete primary window; 1 additional incomplete secondary-only |

Missing-session exclusions are outright exclusions (no imputation),
logged in `outputs/{es,nq}_missing_sessions.csv`.

## Anomaly/invariant check (all pass)

Zero violations across the full development sample for: `U_h >= 0`,
`D_h >= 0`, `Q_h` bounded to `[-1,1]` when defined, and `U_h`/`D_h`
monotone non-decreasing across nested primary horizons. `Q_h`/`E_h` were
never undefined in this sample (`U_h+D_h==0` did not occur for any
session/horizon) — reported as observed, not assumed.

## Findings (descriptive only)

**R (close-to-open drift).** Mean `R_h` is small in both points and in
economic terms at every horizon, and mostly statistically indistinguishable
from zero by day-block bootstrap CI: ES ranges from -0.01 to +0.33 points
(CI excludes zero only at h=1: [0.16, 0.46]); NQ ranges from +0.29 to +1.88
points (CI excludes zero at h=1 [0.88,2.29], h=3 [0.26,2.86], and h=30
borderline). Medians are near zero throughout. Q10/Q90 widen steadily with
h (ES: ±2.5 at h=1 to ±13-17 at h=60; NQ: ±13-17 at h=1 to ±60-83 at
h=60), i.e. dispersion grows with horizon as expected of an accumulating
random walk, while the central tendency stays close to flat.

**Closing direction (UP/DOWN/NEUTRAL).** Frequencies hover close to 50/50
at every horizon, both instruments (ES 43.5-52.4% UP depending on h; NQ
45.6-53.6% UP), with NEUTRAL (exact tie) shrinking from ~5.4%/0.8% at h=1
(ES/NQ) to ~1% or less by h=30-60 as more bars make an exact-zero close
increasingly unlikely.

**Dominant excursion side (Q_h) — the one small, consistent tilt.** Mean
`Q_h` is small but **positive with a CI excluding zero at h=1 and h=3 in
BOTH instruments** (ES h=1: 0.054 [0.022,0.084]; ES h=3: 0.034
[0.001,0.064]; NQ h=1: 0.049 [0.018,0.084]; NQ h=3: 0.049 [0.017,0.081]),
meaning the running high tends to slightly exceed the running low's
distance from the open in the first 1-3 minutes, on average across the
sample. This tilt shrinks toward (and statistically through) zero by
h=15-60 (ES mean Q_60 = -0.014 [-0.049,0.020]; NQ mean Q_60 = -0.003
[-0.036,0.037]). The same pattern appears in the **upper/lower symmetry**
table: mean `U_h` exceeds mean `D_h` with a CI excluding zero at h=1 and
h=3 for both instruments (ES h=1: +0.26 [0.10,0.43]; NQ h=1: +0.98
[0.24,1.80]), fading to overlapping CIs by h=15+ and even reversing sign
(not significantly) at h=60. This is reported as a fact about this
five-year sample's first few minutes, not as a mechanism or a persistent
property.

**Initial/final agreement.** The h=1 closing direction agrees with the
later-horizon closing direction more often than the 50% neutral baseline
at every horizon, decaying smoothly from h=3 to h=60: ES 65.6% (h=3) ->
53.6% (h=60); NQ 69.7% (h=3) -> 57.3% (h=60). Both instruments show the
same monotone decay shape.

**Concentration.** The top decile of sessions (by |R_h| or by U_h+D_h)
contributes roughly 24-35% of the total across all horizons and both
instruments (e.g. ES top-10% share of |R_h|: 32.6-34.9%; of U_h+D_h:
24.5-25.8%) — consistent with fat-tailed but not degenerate/single-day-
dominated behavior, stable across horizons.

**Year-by-year (see `year_by_year.csv`).** Every year 2018-2022 has >=20
sessions for every horizon/metric cell (no reporting-floor violations);
mean R and mean Q both show ordinary year-to-year variation with no
single year producing an outsized share of either the small R drift or
the small Q tilt (full table committed, not reproduced here for space).

**Cross-instrument correlation (ES vs NQ, same session, same horizon).**
Substantial positive Spearman correlation at every horizon for both R and
Q, rising with h: R from 0.70 (h=1) to 0.82 (h=60); Q from 0.62 (h=1) to
0.74 (h=60) — ES and NQ cash-open behavior co-moves strongly, as expected
of two correlated equity-index futures.

**Cross-horizon correlation (within instrument).** `R_1` vs `R_60`
Spearman is modest (ES 0.16, NQ 0.19) — the first minute's direction is a
weak but nonzero predictor-shaped correlate of the 60-minute closing
direction in a purely descriptive sense (matches the initial/final
agreement finding above). `Q_1` vs `Q_60` is somewhat higher (ES 0.32, NQ
0.37) — the first minute's dominant side correlates more with the
1-hour dominant side than closing direction does. Full 5x7 matrix (R,U,D,
Q,E across 7 horizons) committed in `correlation_matrix.csv`.

## Limitations

See `KNOWN_LIMITATIONS.md`. In particular: this is 2018-2022 ES/NQ only;
the small early-horizon Q/U-D tilt and the initial/final agreement decay
are sample statistics, not validated out-of-sample, and must not be acted
upon as if they were. No claim is made about validation (2023-2024) or
holdout (2025-> end) periods, which were not touched.

## Artifacts

`RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_ATLAS.md`, `DECISIONS.md`,
`KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`, `PROGRESS.md`,
`RUN_REGISTRY.csv` (35 registered configurations); `src/{atlas,
build_ledger, run_analysis, analysis_utils}.py`; `tests/test_fixtures.py`
(8 tests, including a real-data DST-transition check); session ledgers
`outputs/{es,nq}_atlas_ledger.parquet` (git-ignored, reproducible) and
missing-session logs `outputs/{es,nq}_missing_sessions.csv`; summary tables
in `reports/tables/*.csv` (summary_stats, direction_frequencies,
initial_final_agreement, year_by_year, upper_lower_symmetry,
concentration, correlation_matrix, cross_instrument_correlation,
anomaly_inventory).
