# PROGRESS.md — generation 10 (NQ excursion-level timing study)

- 2026-07-12: New branch created from research/simple-cash-open-level-
  study @ 4d5ee1b. Self-contained (does not import generation 9's `src/`
  or any other prior generation's level library/synthetic-control/
  taxonomy code). Feasibility reconfirmed from generation 9's own check
  (same touch/outcome window requirements, et_minute through 809).
  RESEARCH_CHARTER.md, DATA_CONTRACT.md, SPEC_EXCURSION_TIMING.md,
  DECISIONS.md, KNOWN_LIMITATIONS.md, PROJECT_STATUS.md committed before
  any result-producing code.
- 2026-07-12: Engine implemented exactly per SPEC_EXCURSION_TIMING.md
  (levels.py: 8 mean-only 10-session excursion levels/instrument;
  interactions.py: master touch search, nested activation-window
  derivation, same-bar morphology, post-touch/barrier outcomes,
  close-recross; build_ledger.py: per-instrument orchestration; stats.py:
  timing surface, BH correction, year stability, alias audit;
  classification.py: 7-condition coherence + same-bar classification;
  rolling_state.py: causal prior-10-event state diagnostic). 35 tests
  covering all 42 required test items, all passing. Committed (5a357de)
  before real-data analysis, per instruction.
- 2026-07-12: Real NQ (primary) + ES (negative control) ledgers built and
  full 1936-cell timing surface computed. NQ UPPER_k0/k1/k2 classify
  COHERENT_OPEN_CONTINUATION (anchored at activation windows 2/2/5
  minutes -- genuinely cash-open-proximate, not late-morning-only);
  UPPER_k3 and all LOWER_* levels MIXED_OR_NULL except LOWER_k1 (one
  ISOLATED_SIGNIFICANT_CELL, correctly not promoted). ES: all 8 levels
  null -- clean negative-control replication. Year stability verified
  directly for UPPER_k0's anchor cell (positive in all 5 years,
  2022 not 2020 is the largest-magnitude year). Rolling causal state
  test: all 16 cells STATE_NULL -- no persistence or mean-reversion in
  the touch-outcome sequence. Alias audit: NQ 0% alias rate -- the
  coherent finding is confirmed not a duplicated-price artifact. Fixed a
  real gap found during review: the yearly-stability export table
  initially lacked activation_window/horizon identifying columns
  (the classification logic itself was unaffected, since each
  classification call used an unambiguous single (A,H) query) --
  corrected and table regenerated. Full tables written with no
  omissions. EXCURSION_LEVEL_TIMING_REPORT.md committed. No further
  generation begun.
