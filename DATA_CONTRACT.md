# DATA_CONTRACT.md

## Raw data identity

Databento GLBX.MDP3, schema `ohlcv-1m`, parent symbology (`ES.FUT`, `NQ.FUT`),
CSV + zstd, pretty prices/timestamps, `map_symbols=true`. Files live in
`data/raw/` (git-ignored, immutable). SHA256 hashes are recorded in
`research/vwap_shock/reports/raw_data_hashes.txt` and reproduced here:

```
a3f9eaa234b28cb7d86f2022f347d8f2a719790cf8879439945565a03265abe4  es2018.ohlcv-1m.csv.zst  (2018-01-01 -> 2019-12-31)
12ddd7a83d577c85b3043f41e827571f20c6c9800cc824b752af5a1ca36d4e1f  es2023.ohlcv-1m.csv.zst  (2020-01-01 -> 2023-12-30)
1a41db6e86537419b1987e40e2ae19c20ad159263989a0d3571a8a6a8d1ea21b  es2026.ohlcv-1m.csv.zst  (2024-01-01 -> 2026-06-08)
e55c17379a26e04760c6eb331a3300959ce5067779fdf3df097e3c4762f70e52  nq2018.ohlcv-1m.csv.zst  (2018-01-01 -> 2019-12-30)
738b657513aca8d5130936e96c2dcef3b5571fe979702cdf1b12022375aaf5ff  nq2020.ohlcv-1m.csv.zst  (2020-01-01 -> 2020-12-30)
5012a9f1685175a7a4d83d5999e37f06abf084f0035c25279e1d01f3ae030750  nq2021.ohlcv-1m.csv.zst  (2021-01-01 -> 2022-12-30)
fbc646a1be1e854e8aa187290ed74d5b58471367385a97197000267b51a72219  nq2023.ohlcv-1m.csv.zst  (2023-01-01 -> 2024-12-30)
4a56638dad7a79c8d0d42a28da2a2bab58273fb0b8274f47bf54da05b7dc7cad  nq2025.ohlcv-1m.csv.zst  (2025-01-01 -> 2026-06-07)
```

## Schema and semantics

Columns: `ts_event, rtype, publisher_id, instrument_id, open, high, low,
close, volume, symbol`. `ts_event` is UTC nanoseconds and marks the **bar
open** (Databento OHLCV convention: the bar aggregates [ts_event,
ts_event + 1min)). A bar timestamped t is therefore complete only at
t + 1min; all "as of close of bar t" logic uses this convention.

## Sessions, timezone, DST

- Exchange sessions defined in `America/New_York` (handles DST); raw
  timestamps are UTC and converted per bar.
- Globex session: 18:00 ET -> 17:00 ET next day; maintenance halt bars
  with ET time in [17:00, 18:00) are excluded (70 ES / 38 NQ stray rows).
- `session_date` = calendar date of `ET + 6h` (Sunday 18:00 ET belongs to
  Monday's session).
- RTH (cash) window: 09:30-16:00 ET. Holiday early closes appear naturally
  as short sessions and are retained, not repaired.

## Contract selection (causal)

- Outright quarterly contracts only (`^(ES|NQ)[HMUZ][0-9]$`); calendar
  spreads dropped (599,117 ES / 412,911 NQ rows).
- Front month for session s = volume leader of session s-1 (prior completed
  session only; no lookahead). First session (2018-01-02) dropped for lack
  of a prior session. 33 rolls per root, mid-expiry-month, as expected.
- No back-adjustment is applied. Returns and lookback features are computed
  within a single (session, contract); windows spanning a roll or session
  boundary yield null features, never spliced prices.

## Processed artifacts

`data/processed/{es,nq}_front_1m.parquet` — one row per front-month bar:
`ts_event, session_date, et_minute, symbol, roll, open, high, low, close,
volume`. Produced deterministically by `research/vwap_shock/src/data_build.py`.
Audit counters in `research/vwap_shock/reports/stage0_audit.json`.

Quality results: 0 impossible OHLC rows, 0 duplicate (ts, symbol) rows after
archive-overlap dedup, 0 zero-volume front-month bars, median 1379/1380 bars
per session; short sessions: 2020-03-16 (COVID halt), 2025-11-28 (early
close), 2026-06-09/08 (data end), plus NQ holiday sessions.

## Partitions (reserved before any strategy results were viewed)

| Partition   | Sessions                     | Use |
|---|---|---|
| development | 2018-01-03 -> 2022-12-30     | Stage 2 phenomenon study, all discovery |
| validation  | 2023-01-03 -> 2024-12-31     | later nested selection/verification only |
| holdout     | 2025-01-02 -> end of data    | FINAL UNTOUCHED; not to be read by analysis code until Stage 6 unlock |

Minute-of-day causal baselines may only use sessions strictly earlier than
the bar being normalized and never cross a partition boundary from the right
(a development bar may use earlier development sessions only; validation
bars may use trailing history that includes development sessions, which is
causal and allowed).
