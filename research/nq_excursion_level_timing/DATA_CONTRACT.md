# DATA_CONTRACT.md — generation 10 (NQ excursion-level timing study)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract,
and partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No
data rebuild in this generation.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
  Columns used: `ts_event, session_date, et_minute, open, high, low,
  close, volume`.
- No other generation's code is imported (self-contained, per instruction
  not to inherit generation 9's 86-level library or any earlier
  generation's synthetic controls/taxonomy/prior-highs-lows/VWAP/ATR/HMM/
  swing-level logic). Session-mapping conventions (`session_date`
  resolving the Globex midnight wrap, `et_minute` bar-open timestamp)
  follow generation 1's established contract, re-implemented locally.

## Partition (unchanged, enforced by assertion)

Development: 2018-01-01 through 2022-12-31. Validation (2023-2024) and
holdout (2025+) are never read by this generation.

## Bar windows used

- Family input (09:30 excursion): the single `et_minute==570` bar of each
  of the previous 10 valid prior sessions only — no other bar.
- Master touch search: `et_minute ∈ [570, 689]` (09:30-11:29 ET), 120
  bars, searched once per `(instrument, session_date, level_id)`; nested
  activation-window membership (`A∈{1,2,3,4,5,10,15,20,30,60,120}`) is
  derived from that single first-touch timestamp, never re-searched.
- Outcome window: `et_minute ∈ [570, 809]` (09:30-13:29 ET) — bars
  `T+1..T+120` for any touch bar `T≤689` fall within this range, still
  within ordinary RTH (`et_minute≤959`).

## What this generation adds

`research/nq_excursion_level_timing/outputs/` (git-ignored parquet;
level/event/outcome/barrier ledgers, NQ primary + ES negative control)
and `research/nq_excursion_level_timing/reports/tables/` (committed CSV
tables), built by this generation's own `src/` modules.

## Explicitly out of scope

No synthetic controls, no taxonomy conditioning, no prior highs/lows, no
VWAP levels, no ATR levels, no HMM/trend-regime labels, no dynamic swing
levels, no profitability, entries, sizing, TP/SL, or prop-account
outcomes, and no 2023+ access anywhere in this generation's outputs.
