# RESEARCH_CHARTER.md — NQ Excursion-Level Timing Study (Generation 10)

Branch: `research/nq-excursion-level-timing`, base `research/simple-cash-
open-level-study` @ `4d5ee1b`. Independent, narrow follow-up: does NOT
inherit the 38-level library, synthetic controls, taxonomy conditioning,
prior highs/lows, VWAP levels, ATR levels, HMM/trend-regime labels, or
dynamic swing levels. Preserves all prior generations unchanged.

## Research classification

**Pure phenomenon discovery — timing decomposition of one narrow prior
candidate.** Generation 9 found NQ `upper_N10_mean_k0` (touch allowed
anywhere in a 120-minute activation window) continuation-dominant, but
flagged that finding as likely collapsed with correlated aliases and
untested for *when within the window* the effect actually holds. This
generation tests exactly that: whether the candidate is an immediate
cash-open mechanism, a first-30-minute mechanism, a broader late-morning
momentum threshold, a bullish-only asymmetry, an alias artifact, or null
after precise decomposition. No profitability, entries, sizing, TP/SL, or
prop-account outcomes anywhere.

## Purpose

1. Test the canonical NQ `UPPER_k0` candidate (10-session mean-only
   excursion level) and its exact `LOWER_k0` mirror, plus `k=1,2,3`
   extensions, across 11 nested activation windows and 11 post-touch
   horizons — a 2 × 8 × 11 × 11 timing surface.
2. Classify same-bar morphology, run one causal rolling continuation/
   reversal-state diagnostic, and check year-by-year stability with an
   explicit cross-year standard-deviation audit.
3. Run the identical pipeline on ES as a preregistered negative-control
   replication — interpreted separately, never used to alter NQ
   definitions.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
- Generation 9's session-mapping/dense-bar-array approach and `et_minute`
  bar-open convention inform this generation's implementation but are not
  imported directly (generation 9's `interactions.py` is scoped to 5
  horizons and different bin edges; this generation freezes its own
  11-horizon/11-activation-window ladder) — self-contained, per
  instruction not to inherit generation 9's specific level library.
- Development partition 2018-01-01 through 2022-12-31, unchanged.

## Feasibility check (before preregistration commit)

- Same touch/outcome window requirement as generation 9 (`et_minute`
  through 809, 13:29 ET) — already confirmed available in that
  generation's feasibility check; re-verified here.
- No technical conflict found between the frozen methodology and the
  repository.

## Assumptions

All frozen and enumerated verbatim in `SPEC_EXCURSION_TIMING.md`: 10-
session causal mean-only lookback (no median/EMA), 8 level_ids/instrument
(`UPPER/LOWER_k{0,1,2,3}`), a single master touch search (09:30-11:29 ET)
with nested activation-window membership derived from one first-touch
timestamp (never re-searched per window), 11 post-touch horizons, `b∈
{0.5,1,2,3}` barriers (`b=1.0` primary), Benjamini-Hochberg at 5% within
each instrument across all valid `level_id × activation_window × horizon`
primary cells, a 7-condition coherence requirement before any directional
classification, and one causal rolling-state diagnostic (prior-10-event
lookback, current session excluded).

## Falsifiers / what would make this study invalid

- Any level, touch, or outcome computation reading a bar at or after its
  own causal cutoff, or a post-touch/barrier outcome reading the touch
  bar's own H/L/C.
- The frozen inventory drifting from 8 level_ids/instrument.
- A coherence classification issued without meeting every one of its
  seven frozen conditions, or a rolling-state classification issued
  without meeting all five of its frozen conditions.
- Using ES's results to retune or reselect an NQ definition (forbidden by
  instruction; ES is a negative-control replication only).
