# PROGRESS.md — generation 5 (overnight/pre-open predictor discovery)

- 2026-07-11: New branch created from research/cash-open-target-atlas @
  201896d. RESEARCH_CHARTER.md, DATA_CONTRACT.md, SPEC_OVERNIGHT.md,
  DECISIONS.md, KNOWN_LIMITATIONS.md, PROJECT_STATUS.md committed before
  any development-partition result was viewed.
- 2026-07-11: Engine built (overnight_features.py: overnight path, frozen
  VWAP+dispersion, 5 pre-open windows x 6 feature types incl. acceleration,
  prior-RTH relationship variables; build_ledger.py: target reuse via
  generation-3 atlas.py file-path import). 9 passing tests (no-lookahead,
  exact pre-open window mapping, real-data DST/weekend session mapping,
  one-row-per-session, zero-range/path undefined, causal VWAP min-bars +
  no-lookahead, target/instrument separation, causal trailing
  normalization). Ledgers: ES 1286/1286, NQ 1284/1284 primary rows
  (matches generation-3 atlas counts exactly, since Sec.3-5 need no
  predecessor); Sec.6 relationship variables valid for 1242/1240 rows (44
  excluded for early-close predecessor). Full 720-test standalone screen
  run (92 registry rows). Zero cells survive Bonferroni (alpha=0.05/720);
  effective-N sensitivity: ~4.2 of 45 features effectively independent.
  Strongest raw evidence: NQ/ES above_below_prior_close and ES
  overnight_return vs R_10 (rho~-0.10, fades by h=15-30, 2020-driven,
  2019 sign-flip); separate smaller ES-only range-vs-Q_5 pattern. Verdict:
  no standalone predictor clears the preregistered bar.
  OVERNIGHT_SCREEN_REPORT.md committed.
