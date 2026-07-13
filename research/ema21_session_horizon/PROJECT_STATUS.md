# PROJECT_STATUS.md — EMA21 session-and-horizon decomposition

Branch: research/ema21-session-horizon-surface (base 7853a9c)
Research generation: independent decomposition (session x touch-timing x horizon)

| Stage | Status | Gate |
|---|---|---|
| Preregistration (charter/data contract/spec/decisions/limitations/registry) | COMPLETE | PASS — committed before any result-producing code |
| Data infra re-verification (hashes, data_build.py re-run) | COMPLETE | PASS — matches root DATA_CONTRACT.md exactly |
| Engine build (sessions, EMA21, arming, outcomes, barriers, summary, BH, classification) | COMPLETE | PASS |
| Test suite (35 required test items) | COMPLETE | PASS — 28/28 test functions pass |
| ES/NQ ledgers + summary tables (dev partition) | COMPLETE | 41,995 armed excursions / 38,550 touch events; 1,080 summary cells |
| Primary classification (432 cells) | COMPLETE | 0 REJECTION_DOMINANT, 0 BREAKTHROUGH_DOMINANT, 423 MIXED_OR_NULL, 9 UNDERPOWERED |
| Session-level mechanism classification (12 cells) | COMPLETE | 12/12 NO_COHERENT_SESSION_MECHANISM |
| EMA21_SESSION_HORIZON_REPORT.md | COMPLETE | Verdict: no supported Asia/London/New York EMA21 mechanism found |

No validation-partition (2023+) work follows this generation, per the
preregistered fallback (`SPEC_SESSION_HORIZONS.md` §15).
