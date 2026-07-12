# PROJECT_STATUS.md — generation 8 (cash-open level interaction study)

Branch: research/cash-open-level-interactions
Base: research/cash-open-level-library @ 3c734ca
Research generation: 8 (unconditional predetermined-level interaction study, Part 2B-1)

| Stage | Status | Gate |
|---|---|---|
| Feasibility check | COMPLETE | PASS — no technical conflict found; scipy/statsmodels installed |
| Preregistration (charter/spec/data contract/decisions/limitations) | COMPLETE | PASS — commit 1f2609f, before any result-producing code |
| Engine build | COMPLETE | interactions.py, build_ledger.py, families.py, secondary.py, run_analysis.py |
| 36 required tests | COMPLETE | 34/34 test functions pass, covering all 36 required items |
| Real-data ledgers (ES+NQ) | COMPLETE | ES 49058, NQ 48982 unit rows; commit e71c0bc (code), outputs git-ignored |
| Family A / Family B primary results | COMPLETE | Family A: 55/76 Bonferroni survivors (see critical caveat); Family B: 0/76 (all underpowered) |
| Secondary grid / year stability / null inventory | COMPLETE | full grids in reports/tables/, no omissions |
| Report | COMPLETE | LEVEL_INTERACTION_REPORT.md, critical synthetic-control matching-artifact caveat disclosed |

## Required outputs checklist (per spec §21) — all complete

- [x] real/synthetic event ledgers (ES, NQ) — outputs/{es,nq}_{levels,events,outcomes,barriers}.parquet
- [x] eligibility and exclusion summary — reports/tables/eligibility_exclusion_summary.csv
- [x] touch-rate table — reports/tables/touch_rate_table.csv
- [x] first-touch timing table — reports/tables/first_touch_timing_table.csv
- [x] cluster/co-touch table — reports/tables/cluster_co_touch_table.csv
- [x] Primary Family A complete results — reports/tables/primary_family_a_results.csv
- [x] Primary Family B complete results — reports/tables/primary_family_b_results.csv
- [x] primary-family sample-coverage table — reports/tables/primary_family_sample_coverage.csv
- [x] full secondary-outcome grid — reports/tables/secondary_*.csv
- [x] barrier-order table — reports/tables/barrier_order_table.csv
- [x] year-stability table — reports/tables/year_stability_table.csv
- [x] complete null inventory — reports/tables/family_{a,b}_null_inventory.csv
- [x] insufficient-sample inventory — reports/tables/family_{a,b}_underpowered_inventory.csv
- [x] implementation-limitation report — KNOWN_LIMITATIONS.md #12-13, LEVEL_INTERACTION_REPORT.md critical caveat
- [x] LEVEL_INTERACTION_REPORT.md
- [x] reproducible RUN_REGISTRY.csv
