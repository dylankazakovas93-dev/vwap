# PROGRESS.md — ES-NQ unsupported move discovery

- 2026-07-13: New branch and research directory created from `201896d`.
  Preregistration committed: `RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`,
  `SPEC_UNSUPPORTED_MOVE.md`, `DECISIONS.md`, `KNOWN_LIMITATIONS.md`,
  `PROJECT_STATUS.md`, `PROGRESS.md` (this file), initial
  `RUN_REGISTRY.csv` — before any synchronization, normalization,
  regression, event, or outcome code was written.
- 2026-07-13: Engine built (sync, returns, regression, leadership,
  events, outcomes, attribution, permutation, classification, summary,
  pipeline) and 17 test functions written covering all 35 required test
  items -- all pass. First pipeline run completed in ~6 minutes but
  revealed a bug: the causal residual path was capped at the primary
  horizon (15) instead of the largest secondary horizon (30), so
  `outcome_h30` was always empty. Fixed (commit `5899a4f`) and re-ran.
  Corrected run: 1,749,931 synchronized ES/NQ bars (99.75%/99.91%
  coverage), 3,867 leg instances, 25,603 events (1,133 EXTREME, 24,470
  MODERATE), 19 leader ties. Primary comparison (12 cells): 0
  EXTREME_CONVERGES_MORE_SUPPORTED, 11 MIXED_OR_NULL, 1 UNDERPOWERED --
  effect sizes range -17.2pp to +7.9pp with no consistent direction and
  no cell surviving BH correction, coherently null across all four
  adjacent horizons (5/10/15/30) and stable (as a null) across years.
  `ES_NQ_UNSUPPORTED_MOVE_REPORT.md` committed with this verdict: the
  extremity hypothesis is null.
