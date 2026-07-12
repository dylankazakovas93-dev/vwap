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
- 2026-07-12: Engine implemented exactly per SPEC_LEVEL_INTERACTIONS.md
  (interactions.py: eligibility, touch search, orientation, touch-bar
  diagnostics, raw/normalized outcomes, close-recross, labels, barriers;
  build_ledger.py: real/synthetic ledger construction reusing generation
  7's build_levels.py/levels.py unmodified, cluster/co-touch/isolation
  pass; families.py: Family A McNemar + Family B Wilcoxon/Hodges-Lehmann;
  secondary.py: BH-corrected exploratory grid; run_analysis.py:
  orchestration). 34 tests covering all 36 required test items, all
  passing. Committed (e71c0bc) before real-data analysis, per instruction.
- 2026-07-12: Real ES/NQ ledgers built (49058/48982 unit rows) and full
  analysis run. Family A: 55/76 (instrument, level_id) cells survive
  Bonferroni (alpha=0.05/76) on paired touch-rate difference. Family B:
  0/76 cells reach the confirmatory floor (real_isolated=1 AND
  synthetic_isolated=1 co-occurred in only 1/49058 ES unit-rows given 38
  densely-spaced levels) -- reported as uniformly underpowered, not
  omitted. CRITICAL FINDING during analysis: generation 7's synthetic
  control caps its draw at [bucket_lo, bucket_lo+1.0) for the open-ended
  [2.0,inf) distance bucket, while the real level's distance there is
  unbounded (verified: ES prior_low, mean real distance 23.1 vs mean
  synthetic 2.5, max real 126.5) -- this makes most of Family A's
  "significant" results, for the 17 level_ids that predominantly land in
  that bucket, very likely a matching-artifact rather than a genuine
  market phenomenon. Disclosed prominently in LEVEL_INTERACTION_REPORT.md
  and KNOWN_LIMITATIONS.md #12-13; not fixed, per instruction to reuse
  generation 7's control unmodified. Full secondary grid, year stability,
  and null/underpowered inventories written with no omissions. No
  taxonomy-conditional analysis begun.
