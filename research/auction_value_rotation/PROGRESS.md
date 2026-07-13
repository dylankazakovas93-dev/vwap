# PROGRESS.md — auction value reacceptance and rotation engine

- 2026-07-13: New branch and research directory created from `201896d`.
  Confirmed `data/processed/{nq,es}_front_1m.parquet` span 2018-01-03
  through 2026-06-08/09 (2026 present in the underlying file; a hard,
  tested partition filter ensures it is never read by this generation).
  Preregistration committed: `RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`,
  `SPEC_AUCTION_VALUE.md`, `DECISIONS.md`, `KNOWN_LIMITATIONS.md`,
  `PROJECT_STATUS.md`, `PROGRESS.md` (this file), initial
  `RUN_REGISTRY.csv` — before any profile, event, outcome, or control
  code was written.
- 2026-07-13: Built and unit-tested the full engine (profiles, mappings,
  event state machine, outcomes, controls, permutation/BH,
  classification — 71 tests). Running on real NQ data caught and fixed
  two real bugs (`LEG_EXPECTED_BARS["ASIA"]` wrong, which had silently
  zeroed mappings 1/3; `MATCHED_INSIDE_STATE`'s failure-condition
  fallback, which had inflated effects to an implausible 35-48pp).
  Ran the full 3,456-cell development grid: 1 qualifying candidate
  family (`M2_LONDON_TO_NY`, short, `R1_ONE_CLOSE`, 6 parameter rows,
  all 12 criteria). `CANDIDATE_MANIFEST.md` committed and pushed
  separately, before `oos_pipeline.py` existed. Ran OOS exactly once on
  2019/2021/2023/2025: all 6 rows FAIL (primary row's effect shrank
  from +17.4pp development to +2.6pp OOS, p=0.83). Final verdict: NULL.
  Wrote `AUCTION_VALUE_ROTATION_REPORT.md`. ES not evaluated (no
  surviving NQ finding to confirm). 2026 never read.
