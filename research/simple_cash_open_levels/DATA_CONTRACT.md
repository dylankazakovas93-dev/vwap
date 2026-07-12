# DATA_CONTRACT.md — generation 9 (simple cash-open level study)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract,
and partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No
data rebuild in this generation.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
  Columns used: `ts_event, session_date, et_minute, open, high, low,
  close, volume`.
- No other generation's code is imported. This generation is
  self-contained (per instruction not to inherit the 38-level library,
  synthetic-control design, taxonomy conditioning, or prior interaction
  results). Session-mapping conventions (`session_date` resolving the
  Globex midnight wrap, `et_minute` bar-open timestamp) follow generation
  1's established contract, re-implemented locally where needed (dense
  bar arrays with volume, causal VWAP/SD).

## Partition (unchanged, enforced by assertion)

Development: 2018-01-01 through 2022-12-31. Validation (2023-2024) and
holdout (2025+) are never read by this generation.

## Bar windows used

- Family A1 (overnight VWAP): all bars of session `s` with `et_minute <
  570` (the processed data's own Globex-overnight-leg convention for that
  `session_date`), through the completed 09:29 bar.
- Family A2 (prior-RTH VWAP): the immediately preceding session's full RTH
  window, `et_minute` 570-959 inclusive, only if that session is not an
  early close.
- Family B (09:30 excursion): the single `et_minute==570` bar of each of
  the previous N (5/10/20) valid prior sessions only — no other bar.
- Touch search: `et_minute ∈ [570, 689]` (09:30-11:29 ET), 120 bars.
- Outcome window: `et_minute ∈ [570, 809]` (09:30-13:29 ET) — bars
  `T+1..T+120` for any touch bar `T≤689` fall within this range, still
  within ordinary RTH (`et_minute≤959`).

## What this generation adds

`research/simple_cash_open_levels/outputs/` (git-ignored parquet; level/
event/outcome/barrier ledgers) and `research/simple_cash_open_levels/
reports/tables/` (committed CSV tables), built by this generation's own
`src/` modules.

## Explicitly out of scope

No synthetic controls, no taxonomy conditioning, no profitability,
entries, exits, sizing, TP/SL optimization, or 2023+ access anywhere in
this generation's outputs.
