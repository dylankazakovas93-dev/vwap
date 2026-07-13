# DATA_CONTRACT.md — generation: EMA21 session-and-horizon decomposition

## Inherited (unchanged, re-verified)

Root `DATA_CONTRACT.md` (raw data identity, schema, session/DST, causal
front-month selection, partitions) and the base generation's
`research/ema21_levels/DATA_CONTRACT.md` (5-minute construction pattern)
both apply unchanged. This generation re-hashed all 8 raw archives
against the root's recorded SHA256 list and re-ran
`research/vwap_shock/src/data_build.py` unmodified; counters matched the
root document exactly (ES: 2,968,335 front-month bars / 2,179 sessions;
NQ: 2,963,298 bars / 2,178 sessions).

Source: `data/processed/{es,nq}_front_1m.parquet`, one row per
front-month 1-minute bar: `ts_event, session_date, et_minute, symbol,
roll, open, high, low, close, volume`.

## Partition (this generation)

Development only: `session_date` in `[2018-01-03, 2022-12-30]`, enforced
by one explicit filter applied immediately after loading the parquet,
identical in mechanism to the base generation's guard. ES and NQ
processed as fully separate series end-to-end.

## Five-minute bar construction (reused pattern, continuous full-session only)

Only the continuous (full, including overnight) 5-minute bar frame is
built this generation — there is no RTH-only variant, since every session
leg (Asia/London/New York) is itself a slice of the continuous sequence.
Bucketing: `[HH:00,HH:05), [HH:05,HH:10), ...` on `et_minute`, one row per
`(session_date, bucket_start_min)`, requiring all 5 constituent 1-minute
bars present (dropped otherwise, logged). OHLCV aggregation identical to
the base generation: `open`=first, `high`=max, `low`=min, `close`=last,
`volume`=sum.

## Session leg assignment (new this generation)

Every continuous 5-minute bar is tagged by `bucket_start_min` (ET minute
of day) into exactly one of:

- `ASIA`: `bucket_start_min` in `[1080, 1439]` (18:00-23:59 ET) or
  `[0, 179]` (00:00-02:59 ET) — both ranges carry the *same*
  `session_date` (root convention, `DECISIONS.md` #3), so grouping by
  `(session_date, "ASIA")` already yields one continuous, correctly
  ordered (by `ts_event`) leg spanning the midnight wrap.
- `LONDON`: `[180, 509]` (03:00-08:29 ET).
- `NEW_YORK`: `[570, 959]` (09:30-15:59 ET).
- `EXCLUDED`: `[510, 569]` (08:30-09:29 ET) and `[960, 1079]`
  (16:00-17:59 ET) — these bars still exist in the continuous EMA21
  recursion (the EMA is never reset) but never arm, touch, or host an
  outcome bar.

A "session-leg instance" is one `(session_date, leg)` pair with `leg !=
EXCLUDED`; bars within it are ordered by `ts_event` and given a 1-indexed
local rank used for the touch-time bucket (`SPEC_SESSION_HORIZONS.md`
§5). Event arming, touch detection, and all post-touch outcome/barrier
windows are scoped strictly to one session-leg instance's own bar
sequence.

## Processed artifacts (this generation, git-ignored under `outputs/`)

- `outputs/{es,nq}_5m_full.parquet` — continuous 5m bars + EMA21/ATR20/level
- `outputs/{es,nq}_armed_excursions.csv`
- `outputs/{es,nq}_touch_events.csv`
- `outputs/{es,nq}_outcomes_barriers.csv`

Large ledgers are git-ignored; every summary table needed to audit
conclusions is committed under `reports/tables/`.
