# PROGRESS.md — generation 3 (cash-open target atlas)

- 2026-07-11: New branch and research directory created from 1d39d8e.
  RESEARCH_CHARTER.md, DATA_CONTRACT.md, SPEC_ATLAS.md, DECISIONS.md,
  KNOWN_LIMITATIONS.md, PROJECT_STATUS.md committed before any
  development-partition result was viewed.
- 2026-07-11: Engine built (atlas.py: horizon-to-bar mapping, R/U/D/Q/E,
  derived labels) with 8 passing tests (causality, exact mapping, one-row-
  per-session, primary/secondary gating independence, non-negativity,
  Q-bounds, real-data DST transition check). Ledgers built: ES 1286/1291,
  NQ 1284/1291 primary-valid sessions; secondary (60-bar) valid 1285/1283.
  Full descriptive analysis run (35 registered configurations): summary
  stats, direction/dominant-side frequencies, initial/final agreement,
  year-by-year, upper/lower symmetry, concentration, correlation matrices,
  cross-instrument correlation, anomaly inventory — zero invariant
  violations. Key descriptive facts: mean R near zero at all horizons
  (small, CI-significant only at h=1); mean Q slightly positive at h=1,3
  in both instruments (fades to ~0 by h=15-60); initial/final agreement
  decays from ~65-70% (h=3) to ~53-57% (h=60); ES/NQ same-session
  correlation strong (R: 0.70-0.82, Q: 0.62-0.74). All descriptive only;
  no predictor/rule proposed. ATLAS_REPORT.md committed.
