# PROGRESS.md — EMA21 session-and-horizon decomposition

- 2026-07-13: New branch and research directory created from `7853a9c`.
  Re-hashed all 8 raw archives against root `DATA_CONTRACT.md` (exact
  match) and re-ran `research/vwap_shock/src/data_build.py` unmodified
  (audit counters identical to root). Preregistration committed:
  `RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_SESSION_HORIZONS.md`,
  `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
  `PROGRESS.md` (this file), initial `RUN_REGISTRY.csv` — before any
  session-mapping, EMA, event, or outcome code was written.
- 2026-07-13: Engine built (`src/five_min_bars.py`, `ema.py`,
  `sessions.py`, `events.py`, `outcomes.py`, `summary.py`,
  `classification.py`, `pipeline.py`) and 28 test functions written
  covering all 35 required test items — all pass. Full ES/NQ 2018-2022
  pipeline run (2m49s): 41,995 armed excursions / 38,550 touch events
  across ASIA/LONDON/NEW_YORK x ES/NQ; 1,080 summary cells; 432 primary
  cells (9 UNDERPOWERED, 423 MIXED_OR_NULL, 0 directionally classified);
  12 session-mechanism cells, all `NO_COHERENT_SESSION_MECHANISM`.
  `EMA21_SESSION_HORIZON_REPORT.md` committed with the final verdict: no
  supported Asia, London, or New York EMA21 mechanism found.
