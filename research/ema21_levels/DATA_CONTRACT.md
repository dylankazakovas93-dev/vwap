# DATA_CONTRACT.md — generation: intraday EMA21 level discovery

## Inherited (unchanged, re-verified)

Root `DATA_CONTRACT.md` governs raw data identity, schema, session/DST
handling, causal front-month contract selection, and partitions. This
generation re-hashed all 8 raw archives against the root's recorded
SHA256 list and re-ran `research/vwap_shock/src/data_build.py` unmodified;
the resulting audit counters matched the root document exactly (see
`RESEARCH_CHARTER.md` "Facts"). No raw or processed file from generation 1
was edited.

Source for this generation: `data/processed/{es,nq}_front_1m.parquet`,
one row per front-month one-minute bar, columns `ts_event, session_date,
et_minute, symbol, roll, open, high, low, close, volume`.

## Partition (this generation)

Development only: `session_date` in `[2018-01-03, 2022-12-30]`. Enforced
by a single explicit filter (`src/five_min_bars.py::filter_development`)
applied immediately after loading the parquet and before any 5-minute bar,
EMA, event, or outcome computation. No code path in this generation reads
`session_date > 2022-12-30`. Test #1/#2 assert this both by construction
(the filter) and by scanning the emitted ledgers.

ES and NQ are processed as fully separate series end-to-end (separate
5-minute bar frames, separate EMA state, separate event/outcome ledgers,
never pooled into a single arming/touch stream) — test #3.

## Five-minute bar construction (new, this generation)

`src/five_min_bars.py` builds two 5-minute frames per instrument from the
1-minute parquet:

1. **RTH bars**: 1-minute bars with `et_minute` in `[570, 959]` (09:30
   through 15:59 inclusive start-minute), grouped into 5-minute buckets
   `floor(et_minute/5)*5`, one bucket per `(session_date, bucket_start)`.
   A bucket is emitted only if all 5 constituent one-minute bars are
   present (`count==5`); otherwise dropped and logged
   (`outputs/{es,nq}_incomplete_5m_bars.csv`). OHLCV aggregation:
   `open`=first, `high`=max, `low`=min, `close`=last, `volume`=sum.
2. **Full-session bars**: every 1-minute bar (all `et_minute`, all
   sessions, in chronological `ts_event` order), same 5-minute bucketing
   applied to `ts_event` (bucketed on the minute-of-day within each
   session's own clock, consistent with bucket boundaries used for RTH),
   same complete-bucket requirement.

Both frames are deterministic functions of the audited 1-minute parquet;
no randomness, no imputation, no partial-bar carry-forward.

## Processed artifacts (this generation, git-ignored under `outputs/`)

- `outputs/{es,nq}_5m_rth.parquet`, `outputs/{es,nq}_5m_full.parquet`
- `outputs/{es,nq}_ema_ledger.parquet` — EMA20/21/22 x {RTH,FULL} per bar
- `outputs/{es,nq}_armed_excursions.csv`
- `outputs/{es,nq}_touch_events.csv`
- `outputs/{es,nq}_post_touch_outcomes.csv`
- `outputs/{es,nq}_barrier_outcomes.csv`

Large ledgers are git-ignored (`research/ema21_levels/.gitignore`); every
summary table needed to audit conclusions is committed under
`reports/tables/`.
