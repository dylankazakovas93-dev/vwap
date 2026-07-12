# PROJECT_STATUS.md — intraday EMA21 level discovery

Branch: research/intraday-ema21-level-discovery (base 201896d)
Research generation: independent (EMA21 level-interaction discovery)

| Stage | Status | Gate |
|---|---|---|
| Preregistration (charter/data contract/spec/decisions/limitations/registry) | COMPLETE | PASS — committed before any result-producing code |
| Data infra re-verification (hashes, data_build.py re-run) | COMPLETE | PASS — matches root DATA_CONTRACT.md exactly |
| Engine build (bars, EMA, arming, outcomes, barriers, summary, BH, classification) | COMPLETE | PASS |
| Test suite (33 required test items) | COMPLETE | PASS — 27/27 test functions pass |
| ES/NQ ledgers + summary tables (dev partition) | COMPLETE | 166,737 armed excursions / 72,166 touch events; 1,440 summary cells |
| Primary classification (120 cells) | COMPLETE | 0 REJECTION_DOMINANT, 0 BREAKTHROUGH_DOMINANT, 120 MIXED_OR_NULL, 0 UNDERPOWERED |
| EMA20/21/22 specificity (40 cells) | COMPLETE | 0 EMA21_SPECIFIC, 40 GENERIC_EMA_ZONE |
| EMA21_LEVEL_DISCOVERY_REPORT.md | COMPLETE | Verdict: no supported intraday EMA21 level mechanism found in ES/NQ 2018-2022 |

No validation-partition (2023+) work follows this generation, per the
preregistered fallback (`SPEC_EMA21_LEVELS.md` §15).
