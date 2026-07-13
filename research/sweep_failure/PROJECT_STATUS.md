# PROJECT_STATUS.md — sweep-and-failure discovery

Branch: research/sweep-and-failure-discovery (base 201896d)
Research generation: independent (mechanical sweep-and-failure rotation study)

| Stage | Status | Gate |
|---|---|---|
| Preregistration (charter/data contract/spec/decisions/limitations/registry) | COMPLETE | PASS — committed before any result-producing code |
| Data infra re-verification (hashes, data_build.py re-run) | COMPLETE | PASS — matches root DATA_CONTRACT.md exactly |
| Causal level ledger + ATR20 + volume percentile infra | COMPLETE | PASS |
| Event engine (arming, interaction, breach/failure/control classes) | COMPLETE | PASS |
| ES-NQ confirmation, outcomes, barriers | COMPLETE | PASS |
| Permutation test + BH + classification + year stability | COMPLETE | PASS |
| Test suite (38 required test items) | COMPLETE | PASS — 32/32 test functions pass |
| ES/NQ ledgers + summary tables (dev partition) | COMPLETE | 17,972 armed episodes, 12,138 events |
| Primary classification (40 cells) | COMPLETE | 29 FAILED_BREACH_ROTATION_SUPPORTED (anchor-confound caveat applies), 11 UNDERPOWERED, 0 MIXED_OR_NULL, 0 BREAKOUT_SUPPORTED |
| SWEEP_FAILURE_REPORT.md | COMPLETE | Verdict: no confound-free sweep-and-failure mechanism found |

No validation-partition (2023+) work follows this generation.
