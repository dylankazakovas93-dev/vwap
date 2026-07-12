# PROJECT_STATUS.md — generation 10 (NQ excursion-level timing study)

Branch: research/nq-excursion-level-timing
Base: research/simple-cash-open-level-study @ 4d5ee1b
Research generation: 10 (timing decomposition; NQ primary, ES negative control)

| Stage | Status | Gate |
|---|---|---|
| Feasibility check | COMPLETE | PASS |
| Preregistration | COMPLETE | PASS — commit 38b0617, before any result-producing code |
| Engine build | COMPLETE | levels.py, interactions.py, build_ledger.py, stats.py, classification.py, rolling_state.py, run_analysis.py |
| 42 required tests | COMPLETE | 35/35 test functions pass, covering all 42 required items |
| Real-data ledgers (NQ + ES) | COMPLETE | NQ 10296, ES 10312 level rows; commit 5a357de (code) |
| Timing surface / coherence classification | COMPLETE | NQ UPPER_k0/k1/k2 COHERENT_OPEN_CONTINUATION; all else MIXED_OR_NULL/ISOLATED; ES fully null |
| Rolling causal state test | COMPLETE | All 16 cells STATE_NULL |
| Report | COMPLETE | EXCURSION_LEVEL_TIMING_REPORT.md |

## Required outputs checklist (per spec §23) — all complete

- [x] NQ level ledger — outputs/nq_levels.parquet
- [x] ES negative-control level ledger — outputs/es_levels.parquet
- [x] first-touch event ledgers — outputs/{nq,es}_events.parquet
- [x] full timing-surface table — reports/tables/timing_surface_table.csv
- [x] same-bar morphology table — reports/tables/same_bar_surface_table.csv
- [x] post-touch outcome table — reports/tables/post_touch_outcome_table.csv
- [x] barrier-first table — reports/tables/barrier_first_table.csv
- [x] yearly stability table — reports/tables/yearly_stability_table.csv
- [x] rolling-state table — reports/tables/rolling_state_table.csv
- [x] timing-region classification table — reports/tables/timing_region_classification_table.csv
- [x] same-bar classification table — reports/tables/same_bar_classification_table.csv
- [x] alias/duplicate table — reports/tables/alias_duplicate_table.csv, alias_top_collisions.csv
- [x] complete null inventory — reports/tables/timing_region_null_inventory.csv, same_bar_null_inventory.csv
- [x] underpowered inventory — reports/tables/timing_region_underpowered_inventory.csv, same_bar_underpowered_inventory.csv
- [x] EXCURSION_LEVEL_TIMING_REPORT.md
- [x] reproducible RUN_REGISTRY.csv
