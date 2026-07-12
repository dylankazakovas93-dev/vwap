# RESEARCH_CHARTER.md — Simple Cash-Open Level Study (Generation 9)

Branch: `research/simple-cash-open-level-study`, base `research/cash-open-
target-atlas` @ `201896d`. Independent generation: does NOT inherit the
38-level library, synthetic-control design, taxonomy conditioning, or
prior interaction results from generations 6-8. Preserves all prior
generations unchanged.

## Research classification

**Pure phenomenon discovery, unconditional and non-directional.** No
level is assumed a priori to be a reversal or continuation level — every
level classifies independently as continuation-dominant, reversal-
dominant, mixed, null, or underpowered, separately for same-bar
morphology and for post-touch path. No entries, exits, sizing, TP/SL
optimization, profitability, or taxonomy conditioning anywhere. Does not
claim evidence of order flow, absorption, participant inventory, dealer
positioning, stop hunting, or queue behavior — this is a description of
one-minute OHLCV price paths only.

## Purpose

1. Determine whether anchored VWAP deviation levels (overnight-session
   VWAP±{1,2,3}σ, prior-RTH VWAP±{1,2,3}σ) or historical single-candle
   09:30 excursion levels (5/10/20-session lookback × mean/median/EMA
   center × 0-3 native-SD rungs, upside/downside separate) contain
   repeatable information about ES/NQ cash-open price paths.
2. Measure same-bar candle morphology (reversal-proxy vs blast-through-
   proxy) and subsequent continuation/reversal excursions independently
   — a level may show either, both, or neither.
3. Report every result, including nulls and underpowered cells, with
   Benjamini-Hochberg correction and 2018-2022 year-by-year stability.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
- `research/cash_open_atlas/src/atlas.py` (generation 3, unchanged):
  informs this generation's session-mapping/dense-bar-array approach and
  `et_minute`/`tau` convention, but is NOT imported directly — its
  `tau_max` ceiling (59) is far short of what this generation needs (touch
  search through `et_minute=689`, outcomes through `et_minute=809`), so
  this generation writes its own dense-bar-array builder (with volume,
  which `atlas.py`'s builder does not carry) rather than extending or
  modifying generation 3's file.
- Development partition 2018-01-01 through 2022-12-31, unchanged.

## Feasibility check (before preregistration commit)

- Raw processed parquet has bars through `et_minute=809` (13:29 ET) for
  ordinary RTH sessions — sufficient for a touch as late as 11:29 ET
  (`et_minute=689`) plus a full 120-minute post-touch horizon.
- `scipy`/`statsmodels` already present in this environment (installed in
  an earlier generation's session).
- No technical conflict found between the frozen methodology and the
  repository.

## Assumptions

All frozen and enumerated verbatim in `SPEC_SIMPLE_LEVELS.md`: overnight/
prior-RTH VWAP formulas, exact-N (5/10/20) causal 09:30-excursion lookback
with no expanding-window fallback, frozen mean/median/EMA(`adjust=False`)
centers sharing one raw sample SD (`ddof=1`), orientation from level-vs-
09:30-open with a 1-tick (`0.25`) band, touch window `et_minute∈[570,689]`
only, outcome horizons `{5,15,30,60,120}` (primary `{30,60,120}`) starting
strictly at `T+1`, barrier ladder `b∈{0.5,1,2,3}` native-SD units,
Benjamini-Hochberg at 5% within `(instrument, primary horizon)` for the
1.0-SD barrier test and within `instrument` for same-bar morphology.

## Falsifiers / what would make this study invalid

- Any excursion or VWAP formula reading a bar at or after its own causal
  cutoff (09:30 open for Family B; 09:29 close for Family A1; prior RTH
  close for Family A2), or a post-touch outcome reading the touch bar's
  own H/L/C.
- The frozen inventory drifting from 7+7+72=86 level_ids/instrument.
- A `CONTINUATION_DOMINANT`/`REVERSAL_DOMINANT` classification assigned
  without meeting every one of its four frozen conditions (rate
  threshold, corrected significance, signed-median-close sign, 4-of-5-
  year stability).
