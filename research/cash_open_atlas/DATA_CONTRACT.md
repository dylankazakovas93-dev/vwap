# DATA_CONTRACT.md — generation 3 (cash-open target atlas)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract, and
partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No data
rebuild in this generation.

## Source

`data/processed/{es,nq}_front_1m.parquet`. Columns used: `ts_event,
session_date, et_minute, open, high, low, close`. `ts_event` = bar OPEN;
`et_minute` is DST-resolved per bar (verified in generation 1).

## Partition (unchanged, enforced by assertion)

Development: 2018-01-03 -> 2022-12-30. This generation's loader filters to
this range and asserts the boundary; validation/holdout are never read.

## Session window used here

Only `et_minute` in [570, 629] (09:30-10:29 ET, i.e. tau=0..59 relative to
the 09:30 bar) is read from the base parquet for this generation — no
overnight, pre-open, or afternoon data is needed for a cash-open atlas.

## What this generation adds

`research/cash_open_atlas/outputs/` (git-ignored parquet; the session-level
ledger) and `research/cash_open_atlas/reports/tables/` (committed CSV
summaries), built by this generation's own `src/` modules (no imports from
generation 1 or 2's `src/`, to keep this branch self-contained).
