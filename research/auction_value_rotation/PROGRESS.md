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
