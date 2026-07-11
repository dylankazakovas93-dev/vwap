# PROGRESS.md — generation 4 (previous-close predictor discovery)

- 2026-07-11: New branch created from research/cash-open-target-atlas @
  201896d. RESEARCH_CHARTER.md, DATA_CONTRACT.md, SPEC_PREDICTOR.md,
  DECISIONS.md, KNOWN_LIMITATIONS.md, PROJECT_STATUS.md committed before
  any development-partition result was viewed.
- 2026-07-11: Engine built (prev_close_features.py: 6 windows x 5 raw + 3
  normalized features; build_ledger.py: previous-session mapping, early-
  close exclusion, target reuse via generation-3 atlas.py file-path
  import). 9 passing tests (early-close flag, exact window/ret mapping,
  no-target-info-leakage, weekend mapping, predecessor-early-close
  exclusion, non-negativity/bounds, undefined-on-zero-range, causal
  trailing normalization, ES/NQ separation). Ledgers: ES 1240/1286, NQ
  1236/1284 primary rows (45/47 excluded for early-close predecessor,
  matching CME's published early-close calendar). Full 480-test standalone
  screen run (62 registry rows). Zero cells survive Bonferroni
  (alpha=0.05/480); effective-N sensitivity shows the 30 features are
  highly redundant (effective ~2.4-2.5 of 30). Strongest raw evidence: NQ
  last-60min normalized return / signed efficiency vs next-session Q_5
  (rho~-0.10, fades to null by h=15-30, partly driven by 2020); ES
  range_ratio vs Q_5 stable but small across all 6 windows (rho~0.06-0.07).
  Verdict: no standalone predictor clears the preregistered bar.
  PREDICTOR_SCREEN_REPORT.md committed.
