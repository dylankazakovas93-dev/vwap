# DATA_CONTRACT.md — generation: 10:00 open / pre-10:00 rejection-block discovery

## Inherited (unchanged, re-verified)

Root `DATA_CONTRACT.md` (raw data identity, schema, session/DST, causal
front-month selection, partitions) applies unchanged. This generation
re-hashed all 8 raw archives against the root's recorded SHA256 list and
re-ran `research/vwap_shock/src/data_build.py` unmodified; counters
matched the root document exactly (ES: 2,968,335 front-month bars /
2,179 sessions; NQ: 2,963,298 bars / 2,178 sessions).

Source: `data/processed/{es,nq}_front_1m.parquet`, one row per
front-month 1-minute bar: `ts_event, session_date, et_minute, symbol,
roll, open, high, low, close, volume`. This generation works directly on
1-minute bars — there is no 5-minute aggregation step.

## Partition (this generation)

Development only: `session_date` in `[2018-01-03, 2022-12-30]`, enforced
by one explicit filter applied immediately after loading the parquet, ES
and NQ processed as fully separate series end-to-end.

## Session ledger (new this generation)

One row per `(instrument, session_date)` with:

- the 30 pre-10:00 one-minute bars (`et_minute` 570-599) — session
  excluded from the ledger if any of the 30 are missing;
- `RANGE_30 = High_{0930-0959} - Low_{0930-0959}`; session excluded
  from normalized analysis if `RANGE_30 <= 0` (flat/degenerate window);
- the 60 post-10:00 one-minute bars (`et_minute` 600-659) — used by
  Module B's interaction search; a session missing any of the 60 simply
  yields no first interaction within the full 60-minute window (and a
  correspondingly shorter maximum activation window), never a partial
  guess;
- `MEDIAN_RANGE_20`: median `RANGE_30` of the 20 chronologically prior
  **valid** sessions (`DECISIONS.md` #3); sessions before the 20th valid
  prior session are excluded from `MEDIAN_RANGE_20`-normalized outputs
  only (raw-point and `RANGE_30`-normalized outputs are unaffected).

## Processed artifacts (this generation, git-ignored under `outputs/`)

- `outputs/{es,nq}_session_ledger.parquet` — one row per session:
  `RANGE_30`, `MEDIAN_RANGE_20`, context variables, block definitions.
- `outputs/{es,nq}_module_a_outcomes.csv`
- `outputs/{es,nq}_module_b_interactions.csv`
- `outputs/{es,nq}_module_b_outcomes.csv`
- `outputs/{es,nq}_module_b_barriers.csv`

Large ledgers are git-ignored; every summary table needed to audit
conclusions is committed under `reports/tables/`.
