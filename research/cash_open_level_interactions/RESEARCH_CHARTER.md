# RESEARCH_CHARTER.md — Cash-Open Level Interaction Study (Generation 8, Part 2B-1)

Branch: `research/cash-open-level-interactions`, base `research/cash-open-
level-library` @ `3c734ca`. Preserves generations 1-7 unchanged.

## Research classification

**Unconditional phenomenon-discovery study of predetermined-level
interactions.** Tests whether a named predetermined level produces a
different post-touch price path from a generic matched synthetic level
with comparable side, normalized distance, and exposure. This is the
final frozen methodology specified by Dylan; it is implemented exactly as
given, without redesign, alternative proposals, or scope reinterpretation.

Not a strategy, not a profitability study, not a taxonomy-conditional
study. No entries, exits, sizing, TP/SL optimization, fitted MAE/MFE
exits, or prop simulation anywhere in this generation. No 2023+ access.

## Purpose

1. For each of the 38 frozen level_ids (per instrument, per
   `research/cash-open-level-library` @ `3c734ca`), compare touch rate and
   post-touch price path between the named (`REAL`) level and its
   generation-7 matched synthetic control (`SYNTHETIC`).
2. Two independently Bonferroni-corrected primary confirmatory families:
   Family A (paired touch rate, McNemar) and Family B (paired `D_5`,
   Wilcoxon signed-rank, isolated touches only).
3. Full secondary/exploratory grid (all other outcomes/horizons/cohorts),
   year stability, and complete null reporting.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
- `research/cash_open_levels/src/{levels,build_levels}.py` (generation 7,
  unchanged, reused by exact file-path import): `LEVEL_COLUMNS` (38
  level_ids/instrument: family1=22, family2=7, family3=5, family4=4),
  `build_instrument` (real levels + synthetic controls), `build_family1`
  (causal `scale_U`/`scale_D`/`O_0930`).
- `research/cash_open_taxonomy/src/taxonomy.py` (generation 6, unchanged,
  reused transitively via generation 7): `build_scale_tables`, the exact
  60-valid-session causal trailing scale, no expanding-window fallback.
- Generation 7's synthetic control verified in this generation to be
  deterministic, instrument/side/distance-bucket-matched, and unrelated to
  any named structural price (re-derivation check: identical
  `value_synth` across two independent calls with the frozen seed
  `20260711` and identical inputs).
- Development partition 2018-01-01 through 2022-12-31, unchanged.

## Feasibility check (performed before any preregistration commit)

- Raw processed parquet contains `ts_event, session_date, et_minute, open,
  high, low, close, volume` — sufficient for the touch/outcome window.
- Every checked development session has all 30 bars `et_minute∈[570,599]`
  and, where flagged `outcome_window_complete`, all 45 bars through
  `et_minute=614` (10:14 ET).
- `scipy`/`statsmodels` were not present in the environment and were
  installed (no project dependency-lock file exists to update).
- No technical conflict was found between the frozen methodology and the
  existing repository; implementation proceeded as specified.

## Assumptions

All frozen and enumerated in `SPEC_LEVEL_INTERACTIONS.md`, verbatim from
Dylan's final specification: touch window 09:30-09:59 ET, outcome ladder
`h∈{1,3,5,10,15}` through 10:14 ET, orientation from level-vs-09:30-open
with `τ_b=0.15` ambiguity band, cluster distance `0.10·side_scale`,
primary label threshold `1.0`, barrier ladder `k∈{0.5,1.0,1.5,2.0}`,
Family A/B sample floors (100 mutual/20 discordant; 50 pairs/20 non-zero
differences), two independent Bonferroni families of 76 tests each.

## Falsifiers / what would make this study invalid

- Any touch or outcome computation reading a bar at or after the level's
  own causal-availability cutoff, or reading the touch bar's own H/L/C
  into a post-touch outcome — a leakage bug, caught by the frozen-window
  and touch-bar-exclusion tests before any real-data run.
- The frozen inventory drifting from 22/7/5/4/38 — caught by the
  inventory-lock regression test (carried forward from generation 7,
  re-verified here).
- A supported classification issued without surviving the correct,
  independently-corrected Bonferroni family and sample floor.
