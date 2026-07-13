# DATA_CONTRACT.md — generation: sweep-and-failure discovery

## Inherited (unchanged, re-verified)

Root `DATA_CONTRACT.md` applies unchanged. This generation re-hashed all
8 raw archives against the root's recorded SHA256 list and re-ran
`research/vwap_shock/src/data_build.py` unmodified; counters matched the
root document exactly (ES: 2,968,335 front-month bars / 2,179 sessions;
NQ: 2,963,298 bars / 2,178 sessions).

Source: `data/processed/{es,nq}_front_1m.parquet`, one row per
front-month 1-minute bar: `ts_event, session_date, et_minute, symbol,
roll, open, high, low, close, volume`. This generation works directly on
1-minute bars.

## Partition (this generation)

Development only: `session_date` in `[2018-01-03, 2022-12-30]`, enforced
by one explicit filter applied immediately after loading the parquet. ES
and NQ processed as fully separate primary series end-to-end (per
`RESEARCH_CHARTER.md` A5); ES-NQ pairing is a secondary diagnostic only.

## Causal level ledger (new this generation)

One row per `(instrument, session_date)` with:

- `PREV_RTH_HIGH`/`PREV_RTH_LOW`: from the immediately previous *valid*
  session's 09:30-15:59 ET bars (390 one-minute bars required complete);
  `None`/session excluded from previous-RTH-level events if unavailable
  (e.g. the first valid session of the partition, or after a data gap).
- `OVERNIGHT_HIGH`/`OVERNIGHT_LOW`: from the current session's
  18:00-09:29 ET bars (930 one-minute bars required complete); session
  excluded from overnight-level events if unavailable.
- Search window: `09:30-15:59 ET` (RTH), 390 one-minute bars, required
  complete for a session to host any event (root `DATA_CONTRACT.md`
  already guarantees a 09:30 bar exists every development session; a
  gap elsewhere in RTH excludes that session from the event search, not
  imputed).

## Causal scales (new this generation)

- `ATR20_T`: mean 1-minute `TR` over the 20 completed bars strictly
  before candidate event bar `T` (root front-month series, continuous,
  not reset at 09:30 — a bar's `TR` may reference the immediately prior
  bar even if that bar is in the overnight session, since `TR` is a
  property of the continuous 1-minute recursion, exactly as in the prior
  EMA21 generations' `ATR20`).
- Causal clock-minute volume percentile: for instrument x exact ET
  minute, the empirical percentile of the candidate bar's volume within
  the trailing 60 *valid* prior sessions' volume observations at that
  same exact minute (all 60 required present).

## Processed artifacts (this generation, git-ignored under `outputs/`)

- `outputs/{es,nq}_level_ledger.csv`
- `outputs/{es,nq}_armed_episodes.csv`
- `outputs/{es,nq}_interaction_events.csv`
- `outputs/{es,nq}_outcomes.csv`
- `outputs/{es,nq}_barriers.csv`
- `outputs/pairwise_confirmation.csv`

Large ledgers are git-ignored; every summary table needed to audit
conclusions is committed under `reports/tables/`.
