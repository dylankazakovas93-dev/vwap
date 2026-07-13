# PROJECT_STATUS.md — ES-NQ unsupported move discovery

Branch: research/es-nq-unsupported-move-discovery (base 201896d)
Research generation: independent (cross-instrument causal dislocation study)

| Stage | Status | Gate |
|---|---|---|
| Preregistration (charter/data contract/spec/decisions/limitations/registry) | COMPLETE | PASS — committed before any result-producing code |
| Data infra re-verification (hashes, data_build.py re-run) | COMPLETE | PASS — matches root DATA_CONTRACT.md exactly |
| Sync + normalization + regression engine | COMPLETE | PASS |
| Leader/laggard + event/control + rearming engine | COMPLETE | PASS |
| Outcome + attribution + session-leadership diagnostic | COMPLETE | PASS (one bug found and fixed: outcome_h30 cap, see DECISIONS.md/PROGRESS.md) |
| Permutation test + BH + classification + year stability | COMPLETE | PASS |
| Test suite (35 required test items) | COMPLETE | PASS — 17/17 test functions pass |
| ES/NQ ledgers + summary tables (dev partition) | COMPLETE | 1,749,931 synchronized bars; 25,603 events |
| Primary classification (12 cells) | COMPLETE | 0 EXTREME_CONVERGES_MORE_SUPPORTED, 11 MIXED_OR_NULL, 1 UNDERPOWERED |
| ES_NQ_UNSUPPORTED_MOVE_REPORT.md | COMPLETE | Verdict: extremity hypothesis is null |

No validation-partition (2023+) work follows this generation.
