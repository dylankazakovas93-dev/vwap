# PROGRESS.md — 10:00 open / pre-10:00 rejection-block discovery

- 2026-07-13: New branch and research directory created from `201896d`.
  Re-hashed all 8 raw archives against root `DATA_CONTRACT.md` (exact
  match) and re-ran `research/vwap_shock/src/data_build.py` unmodified
  (audit counters identical to root). Preregistration committed:
  `RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_TEN_AM_BLOCKS.md`,
  `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
  `PROGRESS.md` (this file), initial `RUN_REGISTRY.csv` — before any
  session-ledger, Module-A, or Module-B code was written.
- 2026-07-13: Engine built (session ledger, Module A, Module B, summary,
  classification, pipeline) and 31 test functions written covering all
  38 required test items -- all pass. Full ES/NQ 2018-2022 pipeline run:
  2570 Module A events, 2916 Module B events. Module A: 25/28 cells
  `TEN_AM_CONTINUATION`, all 4 instrument x candle_state mechanisms
  `TEN_AM_CONTINUATION` -- but flagged with a structural open-vs-close
  anchoring caveat (`DECISIONS.md` #10) rather than reported as a clean
  discovery. Module B: 8/336 cells `REJECTION_BLOCK_REVERSAL_DOMINANT`
  (all ES lower-block PRETOUCHED), 1 coherent mechanism (ES lower
  PRETOUCHED), not replicated in NQ. `TEN_AM_REJECTION_BLOCK_REPORT.md`
  committed with a nuanced verdict: no cross-confirmed, non-mechanical
  mechanism found.
