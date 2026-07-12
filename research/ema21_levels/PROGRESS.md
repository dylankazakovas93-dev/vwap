# PROGRESS.md — intraday EMA21 level discovery

- 2026-07-12: New branch and research directory created from `201896d`.
  Re-hashed all 8 raw archives against root `DATA_CONTRACT.md` (exact
  match) and re-ran `research/vwap_shock/src/data_build.py` unmodified
  (audit counters identical to root). Preregistration committed:
  `RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_EMA21_LEVELS.md`,
  `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
  `PROGRESS.md` (this file), initial `RUN_REGISTRY.csv` — before any
  5-minute bar, EMA, event, or outcome code was written.
- 2026-07-12: Engine built (`src/five_min_bars.py`, `ema.py`, `events.py`,
  `outcomes.py`, `summary.py`, `classification.py`, `pipeline.py`) and 27
  test functions written covering all 33 required test items (partition
  guard, ES/NQ separation, deterministic aggregation, RTH/full-session EMA
  construction, adjust=False EMA formula, no-daily-reset, frozen-level
  causality, 3-bar arming from above/below, first-touch-only + mandatory
  rearming, causal ATR20, same-bar morphology both sides, T+1-start
  outcomes, mirrored rejection/breakthrough formulas, complete-horizon
  requirement, 0.5/1.0-ATR barrier ordering + tie/neither handling, time
  strata, year accounting, BH family membership, EMA21-specific and
  generic-zone classification, null-cell retention) — all pass.
  Full ES/NQ 2018-2022 pipeline run: 166,737 armed excursions / 72,166
  touch events across instrument x session_definition x span x side; 1,440
  summary cells, 120 primary cells, 40 specificity cells written to
  `reports/tables/`. Result: 0/120 primary cells directionally classified
  (all `MIXED_OR_NULL`, none `UNDERPOWERED`); 0/40 specificity cells
  `EMA21_SPECIFIC` (all 40 `GENERIC_EMA_ZONE`). Fixed one bug found during
  the run (ALL_RTH year-stability rows never matched because touch events
  never carry the literal "ALL_RTH" stratum label — `classification.py`
  now pools across strata explicitly for that row). Documented a known,
  non-fatal per-stratum `touch_rate` >1.0 artifact (excursion-start-vs-
  touch-time stratum attribution mismatch; does not affect ALL_RTH figures
  or the primary classification) in `KNOWN_LIMITATIONS.md`/`DECISIONS.md`.
  `EMA21_LEVEL_DISCOVERY_REPORT.md` committed with the final verdict: no
  supported intraday EMA21 level mechanism found in ES/NQ 2018-2022.
