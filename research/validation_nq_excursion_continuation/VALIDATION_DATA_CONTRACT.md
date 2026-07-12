# VALIDATION_DATA_CONTRACT.md — NQ upper-excursion continuation validation

Inherits raw-data identity, hashes, session/timezone/DST/roll contract
from `../../DATA_CONTRACT.md` (generation 1) unchanged. No data rebuild.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
  Columns used: `ts_event, session_date, et_minute, open, high, low,
  close, volume`.
- `research/nq_excursion_level_timing/src/{levels,interactions,
  rolling_state}.py` (generation 10, imported/reused wherever possible
  for the frozen formulas — level construction, touch search, outcome/
  barrier definitions, rolling-state logic). This generation's own `src/`
  restricts execution to exactly the named frozen cells and the 2023+
  partition; it does not modify generation 10's formulas.

## Partition (enforced by assertion)

- **Warm-up only** (never a validation outcome row): all sessions
  through 2022-12-31, used exclusively to construct the causal 10-session
  `MEAN_U_10`/`MEAN_D_10`/`SD_U_10`/`SD_D_10` inputs for the first
  2023 sessions.
- **Validation partition**: 2023-01-01 through the latest audited session
  (confirmed 2026-06-08/09 by a date-range-only check, no outcome
  inspected). 2023, 2024, 2025 are complete calendar years; 2026 is
  explicitly labelled partial in every output.
- No session dated before 2023-01-01 may appear in any validation
  outcome, touch-event, or statistic row.

## What this generation adds

`research/validation_nq_excursion_continuation/outputs/` (git-ignored
parquet; frozen validation level/touch/outcome ledgers, warm-up-inclusive
level construction but validation-only outcome rows) and
`research/validation_nq_excursion_continuation/reports/tables/`
(committed CSV tables).

## Explicitly out of scope

No other timing cell, lookback, center estimator, filter, or
profitability/trading-rule outcome anywhere in this generation's outputs.
No research generation begins after this one.
