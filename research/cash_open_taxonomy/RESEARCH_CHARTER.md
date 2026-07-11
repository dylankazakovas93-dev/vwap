# RESEARCH_CHARTER.md — Cash-Open Path Taxonomy (Generation 6)

Branch: `research/cash-open-path-taxonomy`, base `research/cash-open-target-atlas`
@ `201896d`. Preserves generations 1 (`research/vwap_shock`), 2
(`research/cash_open_discovery`), 3 (`research/cash_open_atlas`), 4
(`research/previous_close_predictor`), and 5
(`research/overnight_preopen_predictor`) unchanged.

## Research classification

**Descriptive taxonomy construction, Part 1 only.** This generation builds
and characterizes a frozen classification of the 09:30→horizon path shape.
It does **not** test level reactions, does not compute profitability,
does not define entries/exits, and does not access 2023-01-01 onward. Any
resemblance between a class label and a "signal" must not be read as one —
this is a descriptive census of path shapes, exactly as generation 3's
atlas was a descriptive census of continuous targets.

## Purpose

1. Define, causally and precisely, a compact parent taxonomy of six
   multi-bar path shapes plus a separate same-bar (bar-0) morphology-proxy
   family, using excursion scales derived **only from each prior session's
   own 09:30 candle** (not from any later horizon or session-end value).
2. Track a full normalized excursion ladder (0.5/1.0/1.5/2.0 units,
   upside and downside kept separate) with first-crossing bar, crossing
   order, and same-bar ties.
3. Report class frequencies, ambiguity counts, and threshold-crossing
   diagnostics for ES and NQ separately, on the 2018-2022 development
   partition, and give a plain interpretation of whether the taxonomy is
   coherent and adequately populated.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
- `research/cash_open_atlas/src/atlas.py` (generation 3, unchanged):
  `build_dense_bars`, dense per-session `tau=0..N` bar arrays, `tau=h-1`
  convention. Reused here for bar-array construction, not for its R/Q
  targets (this generation defines its own path variables).
- Development partition 2018-01-03 -> 2022-12-30, unchanged.

## Design history (for audit trail)

This specification is Revision 3 of a three-round design conversation:
- Revision 1: initial six-class taxonomy; same-bar dual-threshold events
  routed to an "ambiguous, excluded" flag.
- Revision 2: same-bar dual-sided candles promoted to a first-class,
  permanently-caveated morphology proxy (`SAME_BAR_BULLISH_REVERSAL_PROXY`
  / `SAME_BAR_BEARISH_REVERSAL_PROXY` / `SAME_BAR_DUAL_SIDED_AMBIGUOUS`),
  with a frozen ambiguity band; proposed (but not yet approved) extending
  the proxy's closing side into an assumed initial direction for h>1
  classification.
- **Revision 3 (this document, final, authorized for implementation)**:
  the h>1 extension is rejected as internally inconsistent (the proxy's
  closing side is the *resulting* direction of a possible prior opposite
  excursion, not a fresh initial direction) — see `SPEC_TAXONOMY.md`
  Sec. 3.3. Same-bar cohorts are tracked as a **permanently separate**
  cohort at every horizon, with their own four-category subsequent-path
  classification. The full excursion ladder is restored as a first-class,
  always-computed output, not subsumed by the sensitivity grid.

## Assumptions

Carried from Revisions 1-2 (`scale_U`/`scale_D` trailing-median causal
normalization, `τ_c=1.0` commitment threshold, `τ_b=0.15` ambiguity band,
`τ_d=0` dominance threshold, minimum 20 prior sessions), all detailed in
`SPEC_TAXONOMY.md`.

## Falsifiers / what would make this taxonomy incoherent

- A class-frequency table where one or more of the six parent classes, or
  the same-bar proxy family, is empty or near-empty (below the reporting
  floor) at every horizon — would indicate the thresholds are miscalibrated
  for this instrument/sample, not that the taxonomy is wrong per se.
- Morphology descriptive stats for `SAME_BAR_BULLISH_REVERSAL_PROXY` that
  do NOT show the expected shape (e.g., no elevated lower-wick proportion)
  — would indicate the proxy label does not track what it claims to.
- Excursion-ladder threshold reach rates that are not monotonically
  decreasing in threshold level (0.5 reached more often than 1.0, than
  1.5, than 2.0) — would indicate a computation error, not a market fact,
  since this is a coded near-tautology (reaching 2.0 implies having passed
  0.5) and any violation is a bug to fix before reporting further.
