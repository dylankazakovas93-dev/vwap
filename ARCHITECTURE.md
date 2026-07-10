# ARCHITECTURE.md

```
data/raw/                      immutable Databento csv.zst (git-ignored; hashes committed)
data/processed/                front-month parquet per root (deterministic build)
research/vwap_shock/
  src/data_build.py            Stage 0: outright filter, session construction,
                               causal front-month selection, audit counters
  src/features.py              Stage 2: causal feature engine (minute-of-day
                               baselines, ATR, lookback families, VWAP/bands)
  src/events.py                event grid, forward outcomes, first passage,
                               acceptance, candidate + outcome ledgers
  src/analysis.py              quantile response maps, nested increments,
                               placebo matching, session-block bootstrap
  tests/                       deterministic fixtures (hand-calculated)
  reports/                     stage gate reports, audit json, summary tables
  outputs/                     ledgers (parquet, git-ignored) + committed CSV summaries
RUN_REGISTRY.csv               every executed analysis configuration
```

Pipeline order: data_build -> features -> events -> analysis. Each step is
deterministic (fixed seeds recorded in SPEC_LOCKED.md) and reads only the
development partition during Stage 2 (enforced by an assertion in the
loader). Reproduction commands are listed in each stage gate report.

Causality invariants enforced in code and covered by tests:
- every feature uses bars <= t (completed) and baselines from strictly
  earlier sessions;
- lookback windows never cross session or contract boundaries;
- acceptance decisions use only completed bars after t and are timestamped
  at their decision bar;
- forward outcomes start at open(t+1) or open(decision+1);
- holdout/validation sessions are filtered out before any feature or event
  computation in Stage 2.
