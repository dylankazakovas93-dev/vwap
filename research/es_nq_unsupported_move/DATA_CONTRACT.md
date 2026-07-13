# DATA_CONTRACT.md — generation: ES-NQ unsupported move discovery

## Inherited (unchanged, re-verified)

Root `DATA_CONTRACT.md` applies unchanged. This generation re-hashed all
8 raw archives against the root's recorded SHA256 list and re-ran
`research/vwap_shock/src/data_build.py` unmodified; counters matched the
root document exactly.

Source: `data/processed/{es,nq}_front_1m.parquet`, one row per
front-month 1-minute bar: `ts_event, session_date, et_minute, symbol,
roll, open, high, low, close, volume`.

## Partition (this generation)

Development only: `session_date` in `[2018-01-03, 2022-12-30]` for
*both* instruments' underlying parquet before synchronization, enforced
by one explicit filter applied immediately after loading each parquet.
Validation (2023 onward) is never read.

## Synchronization (new this generation)

`sync.py` performs an exact inner join of ES and NQ 1-minute bars on
`ts_event` (UTC nanosecond bar-open timestamp, per root convention). Any
minute present in one instrument's parquet but not the other's is
dropped from *both* — no forward fill, no synthetic bar. `session_date`
and `et_minute` are taken from the joined row (ES and NQ share identical
values for both, by construction of the root front-month series, since
both use the same UTC->ET conversion and `session_date = date(ET+6h)`
convention; a test asserts this rather than assuming it). Synchronization
coverage (raw bar counts per instrument, joined bar count, dropped-count
per instrument, coverage ratio) is logged to
`outputs/sync_coverage.json` and summarized in `reports/tables/`.

## Session legs (reused from `research/ema21_session_horizon/`)

`ASIA` (18:00-02:59 ET), `LONDON` (03:00-08:29 ET), `NEW_YORK`
(09:30-15:59 ET); `EXCLUDED` (08:30-09:29 and 16:00-17:59 ET). A
"session-leg instance" is one `(session_date, leg)` pair with `leg !=
EXCLUDED`; synchronized bars within it are ordered by `ts_event` and
given a 1-indexed local rank.

## Five-minute synchronized returns (new this generation)

Per instrument, per leg instance, at local rank `t >= 5`: `return_t =
Close_t / Close_{t-5} - 1`. Requires bars at local ranks `t-5..t` all
present in the synchronization join (guaranteed within one leg instance
by construction, since the instance itself is built from already-joined
bars).

## Causal normalization and regression (new this generation)

Per exact `(leg, et_minute)` clock slot (where `et_minute` is the window
*endpoint* bar's ET minute), using the 60 chronologically prior *valid*
leg instances at that same slot (excluding the current occurrence):
return mean, return standard deviation, return z-score (per instrument,
independently); OLS regression `NQ_return = alpha + beta*ES_return +
residual`; predicted NQ return, residual, residual standard deviation
(of the *historical* residual series at that slot, itself computed
causally per historical occurrence), residual z-score. All three
(mean/std, alpha/beta, residual-std) explicitly exclude the current
occurrence and require exactly 60 valid prior occurrences — no shorter-
history fallback (`RESEARCH_CHARTER.md` A3).

## Processed artifacts (this generation, git-ignored under `outputs/`)

- `outputs/synchronized_bars.parquet` — joined ES/NQ 1-minute bars with leg/rank
- `outputs/returns_normalized.parquet` — per-instrument 5-min returns, z-scores, regression outputs
- `outputs/events.csv`, `outputs/outcomes.csv`, `outputs/attribution.csv`
- `outputs/sync_coverage.json`

Large ledgers are git-ignored; every summary table needed to audit
conclusions is committed under `reports/tables/`.
