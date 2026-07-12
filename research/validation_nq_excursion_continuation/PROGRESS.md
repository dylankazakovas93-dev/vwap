# PROGRESS.md — NQ upper-excursion continuation validation

- 2026-07-12: New branch created from research/nq-excursion-level-timing
  @ dba98fe. Date-range-only logistics check performed (no level, touch,
  or outcome value computed or inspected): ES processed data through
  2026-06-09, NQ through 2026-06-08 (2179/2178 total sessions since
  2018-01-03) — confirms the expected ~2026-06-07 validation end date.
  VALIDATION_CHARTER.md, VALIDATION_DATA_CONTRACT.md,
  SPEC_VALIDATION.md, DECISIONS.md, KNOWN_LIMITATIONS.md,
  PROJECT_STATUS.md committed before any 2023+ outcome was loaded or
  calculated.
- 2026-07-12: Engine adapted, reusing generation 10's levels.py/
  interactions.py/rolling_state.py formulas unmodified (build_ledger.py:
  full-history warm-up + validation-partition-only output rows, with an
  explicit assertion that no pre-2023 session enters any outcome table;
  validation_stats.py: one-sided exact binomial, Holm correction, year
  breakdown, success-criteria evaluation; validation_rolling_state.py:
  frozen state replication with pre-2023-eligible prior-state lookback
  per DECISIONS.md #9). 22 tests covering all 24 required test items,
  all passing. Committed before real 2023+ analysis, per instruction.
- 2026-07-12: Full frozen validation run on real NQ (primary) + ES
  (negative control) 2023+ data. PRIMARY RESULT: NQ UPPER_k0 (A=2,H=2,
  b=1.0) FAILS VALIDATION -- continuation-minus-reversal difference is
  -0.84pp (not the hypothesized >=+5.0pp), one-sided exact binomial
  p=0.602 (not <0.05), and yearly sign is consistent in only 2 of 4
  partitions (not >=3) -- 4 of 7 success criteria fail. Supporting
  UPPER_k1 also FAILED_VALIDATION; UPPER_k2 is directionally positive
  (+7.0pp) but DIRECTIONALLY_POSITIVE_BUT_INCONCLUSIVE after Holm
  correction (adjusted p=0.232) -- cannot rescue the failed primary per
  instruction. Negative controls (NQ lower mirrors, ES replication,
  UPPER_k3) all null, consistent with generation 10. Same-bar morphology
  for the primary cell also did not replicate (diff -2.3pp, p=0.650,
  vs. generation 10's blast-through bias). Rolling-state: 9/10 cells
  STATE_NULL; one non-primary supporting-candidate exception (NQ
  UPPER_k1: STATE_REVERSAL_SUPPORTED, p=0.023) reported honestly, not
  used to alter the verdict. No alternative timing cell was computed or
  inspected after the primary's failure, per instruction.
  NQ_EXCURSION_VALIDATION_REPORT.md committed. No further research
  generation begun.
