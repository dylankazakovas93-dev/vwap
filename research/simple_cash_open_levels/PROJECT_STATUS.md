# PROJECT_STATUS.md — generation 9 (simple cash-open level study)

Branch: research/simple-cash-open-level-study
Base: research/cash-open-target-atlas @ 201896d
Research generation: 9 (simple predetermined level study, independent of generations 6-8)

| Stage | Status | Gate |
|---|---|---|
| Feasibility check | COMPLETE | PASS |
| Preregistration | COMPLETE | PASS — commit 7039473, before any result-producing code |
| Engine build | COMPLETE | levels.py, interactions.py, build_ledger.py, stats.py, run_analysis.py |
| 43 required tests | COMPLETE | 31/31 test functions pass, covering all 43 required items |
| Real-data ledgers (ES+NQ) | COMPLETE | ES 111026, NQ 110854 level rows; commit 5b43853 (code) |
| Behavior classification / year stability | COMPLETE | 21/516 CONTINUATION_DOMINANT (NQ upper k=0 only), 0 REVERSAL_DOMINANT |
| Report | COMPLETE | SIMPLE_LEVEL_STUDY_REPORT.md; coincident-level aliasing caveat disclosed |

## Required outputs checklist (per spec §21) — all complete

- [x] ES/NQ level ledgers — outputs/{es,nq}_levels.parquet
- [x] ES/NQ first-touch event ledgers — outputs/{es,nq}_events.parquet
- [x] full post-touch outcome ledger — outputs/{es,nq}_outcomes.parquet
- [x] full barrier-first ledger — outputs/{es,nq}_barriers.parquet
- [x] level inventory table — reports/tables/level_inventory_table.csv
- [x] level availability table — reports/tables/level_availability_table.csv
- [x] touch-rate table — reports/tables/touch_rate_table.csv
- [x] touch-timing table — reports/tables/touch_timing_table.csv
- [x] same-bar morphology table — reports/tables/same_bar_morphology_table.csv
- [x] post-touch outcome table — reports/tables/post_touch_outcome_table.csv
- [x] barrier-order table — reports/tables/barrier_order_table.csv
- [x] year-stability table — reports/tables/year_stability_{barrier,touch}_table.csv
- [x] behavior-classification table — reports/tables/behavior_classification_table.csv
- [x] coincident-level/alias table — reports/tables/coincident_level_{alias_table,top_collisions}.csv
- [x] null inventory — reports/tables/{behavior,same_bar}_null_inventory.csv
- [x] underpowered inventory — reports/tables/{behavior,same_bar}_underpowered_inventory.csv
- [x] SIMPLE_LEVEL_STUDY_REPORT.md
- [x] reproducible RUN_REGISTRY.csv
