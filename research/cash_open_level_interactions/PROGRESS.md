# PROGRESS.md — generation 8 (cash-open level interaction study)

- 2026-07-12: New branch created from research/cash-open-level-library @
  3c734ca. Feasibility check performed before any preregistration
  commit: confirmed raw data has required columns/bar coverage for the
  09:30-09:59 touch window and 09:30-10:14 outcome window; confirmed
  generation 7's synthetic control is deterministic and reproducible from
  the frozen seed (re-derivation check, two independent calls, identical
  `value_synth`); installed scipy/statsmodels (absent from environment,
  no project dependency-lock file to update). No technical conflict
  found with Dylan's frozen methodology. RESEARCH_CHARTER.md,
  DATA_CONTRACT.md, SPEC_LEVEL_INTERACTIONS.md, DECISIONS.md,
  KNOWN_LIMITATIONS.md, PROJECT_STATUS.md committed before any
  result-producing code.
