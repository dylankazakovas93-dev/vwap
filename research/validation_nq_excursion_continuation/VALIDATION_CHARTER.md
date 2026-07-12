# VALIDATION_CHARTER.md — NQ Upper-Excursion Continuation Validation

Branch: `validation/nq-upper-excursion-continuation`, base `research/nq-
excursion-level-timing` @ `dba98fe`. **This is validation, not
discovery.** The frozen candidate, its exact activation windows,
horizons, barriers, and success criteria were fixed by generation 10's
development-sample findings before any 2023+ data was loaded or
calculated. No redesign, no additional timing cells, no new filters, no
parameter optimization, no other research generation begins after this
one.

## What is being validated

Generation 10 (development partition 2018-2022) found: NQ upper
historical-09:30-excursion levels `UPPER_k0`/`k1`/`k2`, touched within
2-5 minutes of 09:30, showed continuation-dominant post-touch paths
(`COHERENT_OPEN_CONTINUATION`); the lower mirror and ES were null;
`UPPER_k3` was null; the causal rolling continuation/reversal-state
variable was null. This generation tests whether that exact,
frozen phenomenon replicates on untouched 2023+ data.

## Scope

- **Primary hypothesis** (one test, no multiplicity correction): NQ
  `UPPER_k0`, activation `A=2`, horizon `H=2`, barrier `b=1.0`,
  one-sided exact binomial (`continuation_first_rate >
  reversal_first_rate`).
- **Supporting candidates** (Holm-corrected together, cannot rescue a
  failed primary): NQ `UPPER_k1` (`A=2,H=1`), NQ `UPPER_k2` (`A=5,H=2`).
- **Negative controls** (reported, never used to alter the primary
  hypothesis): NQ `LOWER_k0/k1/k2` (exact mirrors), ES `UPPER_k0/k1/k2`
  (exact replication), NQ `UPPER_k3` (frozen null-extension check).
- **Secondary diagnostics**: same-bar morphology (NQ `UPPER_k0`, `A=2`,
  primary), rolling direction-state replication (frozen from generation
  10, no new lookback/threshold).
- **Explicitly prohibited**: any other activation window, horizon,
  barrier, lookback, center estimator, volatility/trend/weekday/month/
  economic-release filter, prior-close/overnight/taxonomy feature,
  feature combination, or profitability/trading-rule outcome.

## Validation partition

2023-01-01 through the latest audited data (~2026-06-07/08/09,
confirmed by a date-range-only check before this preregistration
commit — no level, touch, or outcome value was computed or inspected).
2023, 2024, 2025 are complete calendar years; 2026 is explicitly
partial. 2018-2022 data is used **only** to construct the first causal
levels (10-session warm-up) — no 2018-2022 session enters any
validation outcome, touch, or statistic.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
  Confirmed via a date-only check (no outcome/value inspected): ES data
  through 2026-06-09, NQ through 2026-06-08, 2179/2178 total sessions.
- Generation 10's engine (`research/nq_excursion_level_timing/src/`) is
  reused wherever possible for level construction, touch search, and
  outcome/barrier formulas — same frozen formulas, no reimplementation
  drift. The rolling-state test reuses the identical frozen logic.

## Falsifiers / what would make this validation invalid

- Any 2018-2022 session appearing in a validation-partition outcome row.
- Any inspection of a non-frozen timing cell, lookback, or filter before
  or after seeing the primary result.
- Reinterpreting a failed success criterion, or searching for an
  alternative "winner" after the primary candidate fails.
- Using a supporting-candidate or negative-control result to alter the
  primary candidate's definition or classification.
