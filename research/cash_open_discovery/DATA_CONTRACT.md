# DATA_CONTRACT.md — generation 2 (cash-open discovery)

Inherits the raw-data identity, hashes, session/timezone/DST/roll contract
and partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. This
file records only what is specific to this generation.

## Source

`data/processed/{es,nq}_front_1m.parquet` (built by generation 1's
`research/vwap_shock/src/data_build.py`; not rebuilt here — raw data and the
front-month causal mapping are immutable and already audited in Stage 0).
Columns used: `ts_event, session_date, et_minute, symbol, roll, open, high,
low, close, volume`.

## Bar timestamp convention (verified)

`ts_event` marks bar OPEN. The bar at `et_minute == 570` is the 09:30:00 ET
-> 09:31:00 ET bar; its `open` field is the verified cash-open price `O` for
that session. Its `close` field is the price as of 09:31 ET (the bar's
completion), i.e. the earliest point at which the 09:30 bar is fully known.

## DST

et_minute is derived from `ts_event.tz_convert("America/New_York")` per bar
(generation 1, `src/data_build.py`); this already resolves DST per-session
automatically. 09:30 ET is always et_minute 570 on every session regardless
of the day's UTC offset. No separate DST branch is introduced in this
generation.

## Futures-session / maintenance boundary (verified)

Generation 1 established and this generation reuses: Globex session anchor
18:00 ET; maintenance halt bars with ET time in [17:00, 18:00) are excluded
from the base parquet already (0.002%/0.001% of raw rows, ES/NQ). The
"verified futures-session end" for the prior-session-direction module
(final 10 completed minutes before the boundary) is therefore et_minute in
[1019-9, 1019] i.e. the last 10 bars with et_minute <= 1019 (16:59 ET,
since the last tradeable minute before the 17:00-18:00 halt is the bar
opening at 16:59 ET, closing at 17:00 ET).

## Partitions (unchanged, inherited, enforced by assertion)

Development: 2018-01-03 -> 2022-12-30 (1291 sessions/instrument). Validation
2023-2024 and holdout 2025-> end remain untouched; this generation's loader
filters to development only and asserts the boundary, identically to
generation 1.

## What this generation adds (own artifacts, not touching generation 1's)

`research/cash_open_discovery/outputs/` (git-ignored parquet/csv) and
`research/cash_open_discovery/reports/tables/` (committed CSV summaries),
built by this generation's own `src/` modules.
