# DATA_CONTRACT.md — generation: auction value reacceptance and rotation engine

## Inherited (unchanged, re-verified)

Root `DATA_CONTRACT.md` applies unchanged. This generation re-hashed all
8 raw archives against the root's recorded SHA256 list and re-ran
`research/vwap_shock/src/data_build.py` unmodified; counters matched the
root document exactly.

Source: `data/processed/{nq,es}_front_1m.parquet`, one row per
front-month 1-minute bar: `ts_event, session_date, et_minute, symbol,
roll, open, high, low, close, volume`. Confirmed range (read-only
inspection, no downstream use of 2026 rows): `session_date` 2018-01-03
through 2026-06-08 (NQ) / 2026-06-09 (ES).

## Partitions (hard-enforced, tested)

| Partition | Years | Use |
|---|---|---|
| Development | 2018, 2020, 2022, 2024 | grid sweep, candidate selection |
| OOS (locked) | 2019, 2021, 2023, 2025 | evaluated once, only for frozen candidates, only after `CANDIDATE_MANIFEST.md` is committed and pushed |
| Holdout | 2026 (partial year present in source) | never read by this generation |

`src/data.py::filter_partition(df, years)` is the single choke point
every pipeline entry point calls immediately after loading each parquet;
`years` is always an explicit literal list from the table above, never
a range or "everything except holdout." A test asserts no row with
`session_date.year == 2026` (or outside the requested partition) ever
reaches downstream code, and every pipeline stage logs the exact min/max
`ts_event` it read to `outputs/timestamp_boundaries.json`.

## Session definitions (reused where audited, else frozen per task fallback)

- `ASIA`: 18:00-02:59 ET (audited convention, reused from
  `research/ema21_session_horizon/`).
- `LONDON`: 03:00-08:29 ET (audited convention, reused —
  `RESEARCH_CHARTER.md` "Assumptions" explains why this is used instead
  of the task's own fallback of 03:00-09:29 ET).
- `NEW_YORK_RTH`: 09:30-15:59 ET (audited convention, reused).
- Timezone/DST handled via the root parquet's `et_minute` column, which
  is already computed DST-safely from `ts_event` (UTC) via
  `America/New_York` conversion in `research/vwap_shock/src/data_build.py`
  — re-verified, not re-derived.
- Half-days: sessions with materially fewer than the expected bar count
  for their leg are **excluded outright** (not specially supported),
  consistent with "incomplete sessions excluded."

## Profile artifacts (new this generation, git-ignored under `outputs/`)

- `outputs/{asia,london,ny}_profiles.parquet` — one row per completed
  session-leg profile: POC/VAH/VAL (per profile-model x bin-width x
  VA% variant), profile timestamp, completion timestamp, expiry
  timestamp.
- `outputs/profile_validation_samples.csv` — hand-checkable synthetic
  and real-session profile examples (committed, small).
- `outputs/excursion_acceptance_ledger.parquet` — the master per-
  excursion, per-acceptance-rule ledger (`RESEARCH_CHARTER.md` A2).
- `outputs/event_ledger.parquet`, `outputs/control_ledger.parquet`,
  `outputs/outcome_ledger.parquet`.

Large ledgers are git-ignored; every summary table needed to audit
conclusions is committed under `reports/tables/`.
