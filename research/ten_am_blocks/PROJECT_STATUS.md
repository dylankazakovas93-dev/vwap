# PROJECT_STATUS.md — 10:00 open / pre-10:00 rejection-block discovery

Branch: research/ten-am-rejection-block-discovery (base 201896d)
Research generation: independent (10:00 open mechanism + pre-10:00 wick-zone geometry)

| Stage | Status | Gate |
|---|---|---|
| Preregistration (charter/data contract/spec/decisions/limitations/registry) | COMPLETE | PASS — committed before any result-producing code |
| Data infra re-verification (hashes, data_build.py re-run) | COMPLETE | PASS — matches root DATA_CONTRACT.md exactly |
| Session ledger (RANGE_30, MEDIAN_RANGE_20, context vars, blocks) | COMPLETE | PASS |
| Module A engine (10:00 open mechanism) | COMPLETE | PASS |
| Module B engine (rejection blocks) | COMPLETE | PASS |
| Test suite (38 required test items) | COMPLETE | PASS — 31/31 test functions pass |
| ES/NQ ledgers + summary tables (dev partition) | COMPLETE | 2570 Module A events, 2916 Module B events |
| Module A classification (28 cells) | COMPLETE | 25 TEN_AM_CONTINUATION (structural caveat applies), 2 MIXED_OR_NULL, 1 UNDERPOWERED |
| Module B classification (336 cells) | COMPLETE | 8 REJECTION_BLOCK_REVERSAL_DOMINANT (ES lower PRETOUCHED only), 224 MIXED_OR_NULL, 104 UNDERPOWERED |
| TEN_AM_REJECTION_BLOCK_REPORT.md | COMPLETE | Verdict: no cross-confirmed, non-mechanical mechanism found |

No validation-partition (2023+) work follows this generation.
