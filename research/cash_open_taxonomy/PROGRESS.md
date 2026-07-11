# PROGRESS.md — generation 6 (cash-open path taxonomy)

- 2026-07-11: New branch created from research/cash-open-target-atlas @
  201896d. RESEARCH_CHARTER.md, DATA_CONTRACT.md, SPEC_TAXONOMY.md
  (Revision 3, final), DECISIONS.md, KNOWN_LIMITATIONS.md,
  PROJECT_STATUS.md committed before any development-partition result was
  viewed.
- 2026-07-11: Engine built (taxonomy.py: causal scale, path primitives,
  same-bar proxy family + ambiguity band, same-bar subsequent-path
  4-category classification, ordinary 6-class taxonomy, excursion ladder;
  build_ledger.py: orchestration via generation-3 build_dense_bars
  file-path import). 15 passing tests (causal scale, no-lookahead,
  incomplete-bar handling, bar-0 invariant, ambiguity band, all 4
  same-bar subsequent-path branches, ordinary classes incl. reversal
  timing, ladder order/ties/monotonicity, one-row-per-session, ES/NQ
  separation). Ledgers: ES 1269, NQ 1267 sessions (250/205 same-bar
  dual-sided at h=1). Full diagnostics run (12 registry rows):
  class-frequency, same-bar-h1 and subsequent-path frequency, ambiguous-
  bar counts, 3x3 sensitivity grid, ladder reach rates + ties, same-bar
  morphology stats. Findings: taxonomy is coherent and adequately
  populated at every horizon for 5/6 ordinary classes + the full same-bar
  family; morphology stats validate the proxy labels' assumed shape;
  DELAYED_EXPANSION_AFTER_INITIAL_BALANCE (class 6) is empty at the
  chosen tau_c=1.0/N=15 defaults - flagged, not hidden. Year-by-year
  stable across 2018-2022. TAXONOMY_REPORT.md committed.
