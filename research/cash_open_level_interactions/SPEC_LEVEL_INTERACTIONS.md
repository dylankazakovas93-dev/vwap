# SPEC_LEVEL_INTERACTIONS.md — Cash-Open Level Interaction Study (Generation 8, Part 2B-1)

Final frozen methodology, transcribed verbatim from Dylan's specification.
Implemented exactly as given — no redesign, no alternatives, no scope
reinterpretation. Branch `research/cash-open-level-interactions`, base
`research/cash-open-level-library` @ `3c734ca` (38 level_ids/instrument:
family1=22, family2=7, family3=5, family4=4).

## 1. Level inventory

Read from the frozen `LEVEL_COLUMNS` in generation 7's `levels.py`,
imported by exact file path, never re-typed by hand. Locked by regression
test (`test_frozen_inventory_22_7_5_4_38`). `mult_U_1.0`/`mult_D_1.0`
remain the sole p50 aliases; no separate p50 level_id; no
`prior_settlement_open`; `overnight_high_dev_vwap`/`overnight_low_dev_vwap`
remain diagnostic distances, not levels.

## 2. Study unit and arms

Base unit: `(instrument, session_date, level_id)`. Two arms: `REAL`
(`V_real`, the named level) and `SYNTHETIC` (`V_synth`, generation 7's
already-computed matched control — no new control-generation method).
Verified deterministic/reproducible from the frozen seed `20260711` and
inputs (re-derivation check in `RESEARCH_CHARTER.md`); seed and provenance
stored on every synthetic row.

## 3-14. Session variables, eligibility, touch search, orientation,
touch-bar diagnostics, outcome window, raw/normalized outcomes,
close-recross, labels, barriers, clusters/isolation

Implemented exactly as specified by Dylan (touch window 570-599 ET only;
outcome ladder h∈{1,3,5,10,15} through et_minute 614; orientation from
`V − O_0930` vs 09:30 open with `τ_b=0.15`, never from the touch bar;
touch-bar H/L/C excluded from all outcomes; corrected upper/lower
MFE/MAE; `Q_h` NA on zero denominator; `post_touch_retouch` distinct from
`directional_close_recross`; labels at `{0.5,1.0,1.5}` with `1.0` primary,
never selected by result; barriers at `k∈{0.5,1.0,1.5,2.0}` compared
directly, `SAME_BAR_BARRIER_TIE` when order can't be inferred; cluster
distance `0.10·side_scale`; named/synthetic isolation and pair-separation
exactly as defined). See `research/cash_open_level_interactions/src/
interactions.py` for the executable formulas — this document defers to
that code's docstrings for the literal formula text to avoid transcription
drift; `DECISIONS.md` records every implementation-level judgment call
(storage format, CI method, tie-breaking) not fully pinned by the frozen
spec text.

## 15-16. Primary confirmatory families

**Family A** (touch rate, McNemar): all mutually touch-eligible sessions,
not filtered by isolation. Floors: ≥100 mutually eligible sessions, ≥20
discordant pairs. Bonferroni across `2 instruments × 38 level_ids = 76`.

**Family B** (paired `D_5`, Wilcoxon signed-rank): both arms touched, same
session, same 5-minute bucket, both normalized-outcome-eligible, same
non-ambiguous orientation, `real_isolated=1`, `synthetic_isolated=1`,
`pair_separated=1`. Floors: ≥50 valid pairs, ≥20 non-zero differences.
Bonferroni across `76`, corrected independently from Family A.

## 17. Secondary analyses

All other outcomes/horizons/cohorts (unpaired `D_5`, `D_h≠5`, MFE/MAE/Q,
retouch, close-recross, labels, barriers/order, clustered, co-touched,
touch-bar-dual-sided, raw point outcomes, `AT_OPEN_AMBIGUOUS`) — fully
reported including nulls, Benjamini-Hochberg within each
`(instrument, outcome, horizon)` family across the 38 level_ids, never
promoted to confirmatory.

## 18-19. Year stability and event consumption

Descriptive only, no per-year confirmatory tests. At most one real and
one synthetic first-touch event per `(instrument, session_date,
level_id)`; later same-session/same-arm touches suppressed; different
level_ids remain separate, non-independent rows; no bootstrap
within-session resampling.

## 20-22. Tests, outputs, interpretation

36 required tests (§20 of Dylan's specification) must all pass before any
real-data analysis runs. Required outputs enumerated in
`PROJECT_STATUS.md`/`LEVEL_INTERACTION_REPORT.md`. Final classification
per level_id: `SUPPORTED_TOUCH_RATE_DIFFERENCE`,
`SUPPORTED_PAIRED_POST_TOUCH_DIFFERENCE`, `SUPPORTED_BOTH`,
`WEAK_EXPLORATORY_ONLY`, `NULL`, `UNDERPOWERED`, `IMPLEMENTATION_INVALID`
— a supported classification requires surviving the correct Bonferroni
family and sample floor. No result is ever called a strategy,
profitable, an entry, a rejection/continuation trade, or proof of order
flow/absorption/stop-hunting/dealer positioning.
