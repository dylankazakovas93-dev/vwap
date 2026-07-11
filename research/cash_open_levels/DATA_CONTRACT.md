# DATA_CONTRACT.md — generation 7 (cash-open level library)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract,
and partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No
data rebuild in this generation.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
  Columns used: `ts_event`, `session_date`, `et_minute`, `open`, `high`,
  `low`, `close`, `volume`.
- `research/cash_open_taxonomy/src/taxonomy.py` (generation 6, imported by
  exact file path via `importlib`): only `build_scale_tables` is reused,
  for family 1's causal exact-60-valid-session trailing median/MAD scale.
  No other generation-6 code (path classification, same-bar proxy, ladder)
  is used — this generation does not condition on the taxonomy.

## Partition (unchanged, enforced by assertion)

Development: 2018-01-03 -> 2022-12-30. Validation (2023-2024) and holdout
(2025-> end) are never read by this generation.

## Bar windows used

- Family 1: 09:30 ET bar only (`et_minute == 570`), plus the causal
  60-session trailing history of that same field (via `build_scale_tables`).
- Families 2 and 4: the overnight window, defined as all bars of session
  `s` with `et_minute < 570` (the processed data's Globex-overnight-leg
  convention for that session_date), ordered by `ts_event` ascending.
- Family 3: the immediately preceding session's full RTH window
  (`et_minute` 570-959 inclusive).
- No bar at or after 09:30 ET of session `s` is used by any family for
  session `s`'s own levels (verified by mutate-after-boundary tests).

## What this generation adds

`research/cash_open_levels/outputs/` (git-ignored parquet; the per-
session, per-level real-level and synthetic-control tables) and
`research/cash_open_levels/reports/tables/` (committed CSV diagnostic
summaries), built by this generation's own `src/` modules.

## Explicitly out of scope

No touch/reaction detection, subsequent-return computation, taxonomy-
class-conditional statistics, or profitability/entry/exit logic is
computed, stored, or reported anywhere in this generation's outputs.
