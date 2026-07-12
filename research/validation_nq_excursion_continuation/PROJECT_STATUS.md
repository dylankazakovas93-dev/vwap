# PROJECT_STATUS.md — NQ upper-excursion continuation validation

Branch: validation/nq-upper-excursion-continuation
Base: research/nq-excursion-level-timing @ dba98fe

| Stage | Status | Gate |
|---|---|---|
| Date-range logistics check (no outcome computed) | COMPLETE | PASS |
| Preregistration | COMPLETE | PASS — commit 43969a5 |
| Engine adaptation (frozen cells only) | COMPLETE | reuses generation 10's levels.py/interactions.py/rolling_state.py unmodified |
| 24 required tests | COMPLETE | 22/22 test functions pass, covering all 24 required items |
| Validation ledgers (NQ + ES, 2023+ only) | COMPLETE | NQ 7056, ES 7072 level rows; no pre-2023 session in any outcome (asserted) |
| Primary/supporting/negative-control results | COMPLETE | Primary FAILED_VALIDATION; see report |
| Same-bar / year stability / rolling-state | COMPLETE | same-bar did not replicate; rolling-state mostly null |
| Report | COMPLETE | NQ_EXCURSION_VALIDATION_REPORT.md |

## Required outputs checklist (per spec §14) — all complete

- [x] frozen validation level ledger — outputs/{nq,es}_levels.parquet
- [x] frozen touch-event ledger — outputs/{nq,es}_events.parquet
- [x] frozen post-touch outcome ledger — outputs/{nq,es}_outcomes.parquet
- [x] primary validation result table — reports/tables/primary_validation_result.csv
- [x] supporting-candidate result table — reports/tables/supporting_candidate_result.csv
- [x] negative-control result table — reports/tables/negative_control_result.csv
- [x] same-bar morphology table — reports/tables/same_bar_morphology_table.csv
- [x] yearly stability table — reports/tables/{primary,supporting,negative_control,same_bar}_year_table.csv
- [x] rolling-state replication table — reports/tables/rolling_state_replication_table.csv
- [x] null and underpowered inventory — reports/tables/null_and_underpowered_inventory.csv
- [x] NQ_EXCURSION_VALIDATION_REPORT.md
- [x] reproducible RUN_REGISTRY.csv

## Final classification: FAILED_VALIDATION (primary candidate)

No further research generation begins after this one, per instruction.
