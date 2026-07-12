# DATA_CONTRACT.md — generation 8 (cash-open level interaction study)

Inherits raw-data identity, hashes, session/timezone/DST/roll contract,
and partitions from `../../DATA_CONTRACT.md` (generation 1) unchanged. No
data rebuild in this generation.

## Sources

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
  Columns used: `ts_event, session_date, et_minute, open, high, low,
  close, volume`.
- `research/cash_open_levels/src/build_levels.py::build_instrument` and
  `research/cash_open_levels/src/levels.py` (generation 7, imported by
  exact file path, unmodified): produces, per instrument, `fam1` (`open`,
  `scale_U`, `scale_D`, `scale_U_mad`, `scale_D_mad`, all 14 family-1
  levels), `fam2`/`fam3`/`fam4` (raw level values), `long` (one row per
  session×level_id, all 38 level_ids), `synth` (matched synthetic control,
  `value_synth`, one row per session×level_id, seed `20260711`).
- `research/cash_open_taxonomy/src/taxonomy.py::build_scale_tables`
  (generation 6, transitively reused via generation 7, unmodified): the
  causal exact-60-valid-session trailing scale, no fallback.

No new control-generation method is introduced. `V_synth` is read
directly from generation 7's `synth` output; this generation never
redraws or recomputes a synthetic value independently.

## Partition (unchanged, enforced by assertion)

Development: 2018-01-01 through 2022-12-31. Validation (2023-2024) and
holdout (2025+) are never read by this generation.

## Bar windows used

- Touch search: `et_minute ∈ [570, 599]` (09:30-09:59 ET), 30 bars.
- Outcome window: `et_minute ∈ [570, 614]` (09:30-10:14 ET), 45 bars —
  bars `T+1..T+15` for any touch bar `T≤599` fall within this range.
- No bar at or after a level's causal-availability cutoff (generation 7's
  per-family gates, unchanged) is used to construct that level's own
  value. No bar beyond `et_minute=614` is used anywhere in this
  generation.

## What this generation adds

`research/cash_open_level_interactions/outputs/` (git-ignored parquet;
per-session-level-arm event ledgers) and
`research/cash_open_level_interactions/reports/tables/` (committed CSV
tables), built by this generation's own `src/` modules.

## Explicitly out of scope

No profitability, entries, exits, sizing, TP/SL optimization, fitted
MAE/MFE exits, prop simulation, or taxonomy-conditional analysis anywhere
in this generation's outputs.
