# PROGRESS.md — generation 9 (simple cash-open level study)

- 2026-07-12: New branch created from research/cash-open-target-atlas @
  201896d (independent of generations 6-8: no 38-level library,
  synthetic-control design, or taxonomy conditioning inherited).
  Feasibility check performed before any preregistration commit: raw
  data confirmed to cover et_minute 570-809 (09:30-13:29 ET, needed for
  a touch as late as 11:29 plus a full 120-minute post-touch horizon);
  scipy/statsmodels already available. No technical conflict found.
  RESEARCH_CHARTER.md, DATA_CONTRACT.md, SPEC_SIMPLE_LEVELS.md,
  DECISIONS.md, KNOWN_LIMITATIONS.md, PROJECT_STATUS.md committed before
  any result-producing code.
- 2026-07-12: Engine implemented exactly per SPEC_SIMPLE_LEVELS.md
  (levels.py: Family A1/A2 overnight/prior-RTH VWAP, Family B 09:30-
  excursion 72-level construction; interactions.py: touch search,
  orientation, same-bar morphology, raw/oriented post-touch outcomes,
  barriers, close-recross; build_ledger.py: per-instrument orchestration;
  stats.py: BH correction, behavior/same-bar classification, year
  stability, coincident-level alias detection). 31 tests covering all 43
  required test items, all passing. Committed (5b43853) before real-data
  analysis, per instruction.
- 2026-07-12: Real ES/NQ ledgers built (111026/110854 level rows) and
  full analysis run. Both VWAP families (overnight and prior-RTH, 7
  rungs each) are null on both instruments -- no directional
  classification anywhere. Family B: 21/516 (instrument x level_id x
  primary horizon) cells classify CONTINUATION_DOMINANT, all NQ, all
  upper-side, all k=0 (center-only); 0 REVERSAL_DOMINANT; 0
  UNDERPOWERED. Same-bar morphology: 5 level_ids (ES/NQ, all
  lower-side k=0) classify SAME_BAR_REVERSAL_BIASED; 0
  SAME_BAR_BLAST_THROUGH_BIASED. CRITICAL FINDING: coincident-level audit
  shows all nine NQ upper_N{5,10,20}_{mean,median,ema}_k0 land within one
  tick of each other in 168/~1290 sessions -- the 21 "significant" cells
  are very likely a small number of independent discoveries (perhaps one)
  tested under many correlated aliases, not 21 separate confirmations.
  No level shows both coherent same-bar morphology and coherent
  post-touch dominance (the two flagged sets are on opposite sides and
  disjoint). Year stability verified directly for the flagship result
  (positive in all 5 years, no 2020 dominance). Full tables written with
  no omissions. SIMPLE_LEVEL_STUDY_REPORT.md committed. No further
  generation begun.
