# PROGRESS.md

- 2026-07-10: Session start. Raw ES (3 files) + NQ (5 files) Databento
  ohlcv-1m archives received; hashes recorded. Stage 0 build+audit run:
  outright filter, ET session construction, causal front-month mapping,
  quality checks — all clean (see reports/stage0_audit.json). Partitions
  reserved (DATA_CONTRACT.md).
- 2026-07-10: Stage 1 preregistration committed: SPEC_LOCKED.md,
  VALIDATION_PROTOCOL.md, DECISIONS.md #1-9, KNOWN_LIMITATIONS.md.
- 2026-07-10: Stage 2 engine implementation begun (features, events,
  analysis) with deterministic test fixtures.
- 2026-07-10: Stage 2 complete. Engine + 8 fixtures pass; ES/NQ ledgers
  (~101-103k events each, k1z3) and preregistered analysis run on dev
  partition. Findings: displacement alone directionally uninformative
  (cont 0.483/0.488); no feature recovers continuation >=2 ticks; VWAP
  acceptance sort is anchor leakage (causal post-decision null); volume/
  inefficiency lean weakly to REVERSAL; cash-open reversal pocket only.
  Verdict REVISE HYPOTHESIS. 42 analysis configs registered. No TP/SL,
  no validation/holdout access. STAGE2_FINDINGS.md + STAGE2_GATE.md.
