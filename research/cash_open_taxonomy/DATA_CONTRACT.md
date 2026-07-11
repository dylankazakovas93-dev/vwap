# DATA_CONTRACT.md — generation 6 (cash-open path taxonomy)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract,
and partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No
data rebuild in this generation.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
- `research/cash_open_atlas/src/atlas.py` (generation 3, imported by exact
  file path via `importlib`): only `build_dense_bars` is reused, for its
  dense per-session `tau`-indexed bar arrays; this generation's own path
  variables (`u(t)`, `d(t)`, `Q(t)`, bar-0 morphology, taxonomy classes)
  are computed independently, not imported.

## Partition (unchanged, enforced by assertion)

Development: 2018-01-03 -> 2022-12-30. Validation (2023-2024) and holdout
(2025-> end) are never read by this generation.

## Bar window used

`tau = 0..59` (09:30-10:29 ET), matching the atlas's secondary-horizon
ceiling — no bar beyond 10:30 ET is used anywhere in this generation.

## What this generation adds

`research/cash_open_taxonomy/outputs/` (git-ignored parquet; the
session-level taxonomy ledger) and
`research/cash_open_taxonomy/reports/tables/` (committed CSV summaries),
built by this generation's own `src/` modules.
