# PROGRESS.md — sweep-and-failure discovery

- 2026-07-13: New branch and research directory created from `201896d`.
  Re-hashed all 8 raw archives against root `DATA_CONTRACT.md` (exact
  match) and re-ran `research/vwap_shock/src/data_build.py` unmodified
  (audit counters identical to root). Preregistration committed:
  `RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_SWEEP_FAILURE.md`,
  `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
  `PROGRESS.md` (this file), initial `RUN_REGISTRY.csv` — before any
  level-ledger, event, or outcome code was written.
- 2026-07-13: Engine built (levels, volume, events, outcomes,
  confirmation, permutation, summary, classification, pipeline) and 32
  test functions written covering all 38 required test items -- all
  pass. Full ES/NQ 2018-2022 pipeline run (1m43s): 17,972 armed
  episodes, 12,138 events. Primary comparison (40 cells, FAILED_BREACH
  pooled vs. SUCCESSFUL_BREACH_CONTROL, permutation test, 10,000 perms,
  seed 20260713): 29 FAILED_BREACH_ROTATION_SUPPORTED, 11 UNDERPOWERED,
  0 MIXED_OR_NULL, 0 BREAKOUT_SUPPORTED -- a uniform, ~70-80pp effect in
  every tested cell, p pinned at the permutation floor everywhere.
  Investigated this uniformity/magnitude before writing it up as a
  finding: found that TOUCH_WITHOUT_BREACH (close-inside sub-class,
  never breached at all) shows a similarly elevated rotation rate
  (75.5%), and that failure delay/breach magnitude show only mild,
  non-monotonic variation -- both consistent with the effect being
  dominated by each class's own anchor position (inside vs. outside the
  level) relative to the level-anchored symmetric barriers, rather than
  genuine new post-failure information (documented in `DECISIONS.md` #9
  and `KNOWN_LIMITATIONS.md` #12). `SWEEP_FAILURE_REPORT.md` committed
  with this caveat stated prominently and a nuanced verdict.
