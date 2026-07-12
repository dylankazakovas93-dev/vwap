# PROJECT_STATUS.md — generation 7 (cash-open level library)

Branch: research/cash-open-level-library
Base: research/cash-open-path-taxonomy @ 796ad3f
Research generation: 7 (level construction only, Part 2A)

| Stage | Status | Gate |
|---|---|---|
| Preregistration (charter/spec/data contract/decisions/limitations) | COMPLETE | PASS — committed before any development-partition result was viewed (commit e2ef210) |
| Engine build + required tests | COMPLETE | PASS — 21/21 tests pass (7 added in the Revision 3 correction, 2 added in the Revision 4 correction) |
| Level ledgers (dev partition, ES+NQ) | COMPLETE | ES 1291, NQ 1289 sessions in library; **38** level_ids/instrument (corrected, up from 24) |
| Missingness / dedup / clustering / coverage / overlap diagnostics | COMPLETE | see LEVELS_REPORT.md (rerun post-correction) |
| Report | COMPLETE | Level construction only; no reaction/return/outcome/profitability computed |
| Implementation-fidelity correction (Revision 3) | COMPLETE | 14 approved level_ids added (family1 quantiles, family2 ±3σ, family3 mid/vwap, family4 mid/open); `prior_settlement_open` retracted as never-approved |
| Documentation arithmetic correction (Revision 4) | COMPLETE | Family 1 count corrected 14→22, total corrected 30→38; implementation was already correct, only prose was wrong; 2 count-lock regression tests added |
