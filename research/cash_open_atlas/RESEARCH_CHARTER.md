# RESEARCH_CHARTER.md — Cash-Open Target Atlas (Generation 3)

Branch: `research/cash-open-target-atlas`, base commit `1d39d8e`.
Preserves generations 1 (`research/vwap_shock`) and 2
(`research/cash_open_discovery`) unchanged.

## Research classification

**Descriptive atlas, not a hypothesis test.** Per QUANT_RESEARCH_OS.md
Sec. 4.2 this generation's objective is: *characterize the empirical
distribution of ES/NQ cash-open price action across fixed horizons*. It is
explicitly **not**: establishing whether a signal exists, selecting an
entry/exit rule, or estimating a filter's effect. There is no predictor,
no trading rule, no entry, no level, no VWAP band, no pivot, no reclaim
logic, no k-parameter, no TP/SL, no MAE/MFE, no PF/Sharpe, no sizing, no
prop simulation anywhere in this generation. Any resemblance of a
descriptive statistic to a "signal" must not be read as one.

## Purpose

Build a session-level ledger of five continuous targets (R, U, D, Q, E) at
seven fixed horizons after the 09:30 ET cash open, for ES and NQ
separately, on the development partition (2018-2022), and report their
unconditional distributions, symmetry, concentration, cross-horizon
correlation, and year-by-year stability — nothing more.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged):
  causal front-month bars, `ts_event` = bar OPEN, `et_minute` = ET minute
  of day (DST-resolved per bar), `session_date` = calendar date of ET+6h.
- 09:30 ET bar exists every development session at `et_minute==570`.
- Development partition: 2018-01-03 -> 2022-12-30 (1291 sessions/instrument
  ceiling), validation (2023-2024) and holdout (2025-> end) untouched.

## Assumptions

- A1: "h-th candle" in the task's horizon table means the one-minute bar
  whose OPEN is `09:30 + (h-1)` minutes, i.e., array position `tau=h-1`
  when bars are indexed from `tau=0` at 09:30. Verified against every
  stated example (h=1->09:30 candle, h=3->09:32 candle, ..., h=60->10:29
  candle); see SPEC_ATLAS.md Sec. 2 for the derivation table.
- A2: Session inclusion in the primary sample requires all 30 bars
  `tau=0..29` (09:30-09:59 inclusive) present with no gaps — a single
  session-level gate applied uniformly to every primary horizon, so the
  primary sample size does not shrink as h grows within {1,3,5,10,15,30}.
- A3: The secondary h=60 target requires all 60 bars `tau=0..59` present
  (09:30-10:29) and is evaluated independently — its own missingness never
  removes a session from the primary (h<=30) sample.

## Falsifiers / anomaly triggers (descriptive, not predictive)

Not applicable in the hypothesis-testing sense (Sec. 4.2 classification).
This generation instead commits to reporting, as a "null and anomaly
inventory": any horizon/instrument/year combination with an implausible
value (Q outside [-1,1], negative U or D, non-monotone U/D growth across
nested horizons, unexplained missingness), rather than silently dropping
or smoothing it.
