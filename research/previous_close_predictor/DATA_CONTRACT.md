# DATA_CONTRACT.md — generation 4 (previous-close predictor discovery)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract, and
partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No data
rebuild in this generation.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged):
  full session data, used here for both the previous-session closing
  window (et_minute 900-959, i.e. the last 60 RTH minutes) and, via
  generation 3's unmodified `atlas.py`, the next-session cash-open targets
  (et_minute 570-629).
- `research/cash_open_atlas/src/atlas.py` (generation 3, imported by exact
  file path via `importlib`, not copied or reimplemented):
  `build_dense_bars`, `build_session_ledger` — produces `R_h`, `Q_h`,
  `closing_direction_h`, `dominant_side_h` for `h in {1,3,5,10,15,30,60}`.
  This generation uses only `h in {5,10,15,30}` of that output; h=1,3,60
  columns are computed by the reused function but not analyzed here.

## Partition (unchanged, enforced by assertion)

Development: 2018-01-03 -> 2022-12-30. Both the target-session loader and
the previous-session feature loader filter to this range; the previous-
session lookup for the earliest development session (2018-01-03) has no
predecessor in the loaded data and is naturally excluded (not a partition
breach — no 2017 or validation/holdout data is read).

## RTH close definition

The bar opening at `et_minute==959` (15:59-16:00 ET) closes at 16:00 ET
and is the official RTH close print, used as `final close` for every
window W. A session is an **early close** if its last available bar with
`et_minute<=959` has `et_minute < 959` (see RESEARCH_CHARTER.md
Assumption A2).

## What this generation adds

`research/previous_close_predictor/outputs/` (git-ignored parquet; the
session-level feature+target ledger) and
`research/previous_close_predictor/reports/tables/` (committed CSV
summaries), built by this generation's own `src/` modules, importing
generation 3's `atlas.py` unmodified for target computation.
