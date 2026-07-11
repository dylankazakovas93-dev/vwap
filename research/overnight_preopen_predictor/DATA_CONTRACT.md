# DATA_CONTRACT.md — generation 5 (overnight/pre-open predictor discovery)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract,
and partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No
data rebuild in this generation.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged):
  used for the overnight window (all bars strictly before the session's
  09:30 bar, taken chronologically by `ts_event`), the pre-open windows
  (`et_minute` in `[570-W, 569]`, W in {5,10,15,30,60}), and the prior-RTH
  reference values (previous valid session's own RTH open/close/high/low).
- `research/cash_open_atlas/src/atlas.py` (generation 3, imported by exact
  file path via `importlib`, not copied or reimplemented): produces
  `R_h`, `Q_h` for `h in {1,3,5,10,15,30,60}`; this generation uses only
  `h in {5,10,15,30}`.

## Partition (unchanged, enforced by assertion)

Development: 2018-01-03 -> 2022-12-30. The loader filters to this range
and asserts the boundary; validation/holdout are never read. The previous-
valid-RTH-session lookup for the earliest development session has no
predecessor in the loaded data and is naturally excluded (not a partition
breach).

## Futures-session / RTH boundary (verified, inherited)

Globex session anchor 18:00 ET; maintenance halt bars (`et_minute` in
[1020,1080)) already excluded from the base parquet. The 09:30 ET bar
(`et_minute==570`) opens the RTH day; the bar at `et_minute==959` closes
at 16:00 ET (official RTH close). DST is resolved per-bar by the
inherited `America/New_York` conversion (verified against real 2021
spring-forward/fall-back transition dates in generation 3's test suite;
reused here, not re-derived).

## What this generation adds

`research/overnight_preopen_predictor/outputs/` (git-ignored parquet; the
session-level feature+target ledger) and
`research/overnight_preopen_predictor/reports/tables/` (committed CSV
summaries), built by this generation's own `src/` modules.
