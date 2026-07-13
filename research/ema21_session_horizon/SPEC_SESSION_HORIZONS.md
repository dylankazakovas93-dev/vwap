# SPEC_SESSION_HORIZONS.md — formal specification

Single source of truth for formulas/thresholds used by `src/`. Where this
spec and code disagree, this spec wins and the code has a bug.

## 1. Indicator

`FULL_SESSION_EMA21` only: `ewm(span=21, adjust=False)` on continuous
chronological 5-minute closes (all sessions, including overnight),
carried with no reset anywhere in the recursion. No EMA20/EMA22, no SMA,
VWAP, MACD, RSI, or any other period/indicator.

## 2. Frozen level

For 5-minute bar `t`: `EMA_LEVEL_t = EMA` computed through the close of
bar `t-1`. Bar `t`'s own close never enters the level used to test bar
`t`'s own touch. Warm-up: 60 completed bars minimum (unchanged from base
generation), evaluated on the full continuous sequence.

## 3. Session legs and event-state reset

Three fixed ET windows plus one excluded complement (`DATA_CONTRACT.md`):
`ASIA` (18:00-02:59), `LONDON` (03:00-08:29), `NEW_YORK` (09:30-15:59);
excluded: 08:30-09:29 and 16:00-17:59. The EMA21 recursion itself is
never reset. Event-arming state **is** reset at the start of every
session-leg instance (`(session_date, leg)` pair): the 3-bar arming
window, touch detection, and post-touch outcome/barrier windows only ever
look at bars within that same leg instance. An event may not arm in one
leg instance and touch in another; a horizon may not read bars from the
next leg instance or from an excluded interval.

## 4. Arming and touch (per session-leg instance, chronological order)

Identical mechanics to the base generation's 3-bar rule
(`research/ema21_levels/SPEC_EMA21_LEVELS.md` §4), scoped to one leg
instance's local bar sequence:

- Armed from above: previous 3 completed bars (within the same leg
  instance) each have `Low_bar > frozen_EMA_for_that_bar`.
- Armed from below: previous 3 completed bars (within the same leg
  instance) each have `High_bar < frozen_EMA_for_that_bar`.
- First later bar `T` (same leg instance) with `Low_T <= EMA_LEVEL_T <=
  High_T` is a touch; approach side = `FROM_ABOVE`/`FROM_BELOW`.
- Touch consumes and disarms the event; a fresh 3-bar one-sided run
  (still within the same leg instance) is required before the next
  event. At most one touch per armed excursion. (As in the base
  generation, the straddling touch bar automatically fails both
  one-sided conditions, so re-arming naturally requires fresh bars —
  `research/ema21_levels/DECISIONS.md` #5.)

## 5. Touch-time buckets (elapsed bars since the leg instance's own first bar)

1-indexed local bar rank `r` within the leg instance (`DATA_CONTRACT.md`):
`SESSION_0_TO_30`: `r` in 1-6; `SESSION_30_TO_60`: `r` in 7-12;
`SESSION_60_TO_120`: `r` in 13-24; `SESSION_120_PLUS`: `r >= 25`. Also
report `ALL_SESSION` (union of all four). Buckets are mutually exclusive,
not nested.

## 6. Causal ATR20

Identical formula to the base generation: `TR_t = max(High_t-Low_t,
|High_t-Close_{t-1}|, |Low_t-Close_{t-1}|)` on the full continuous
sequence (TR/ATR are not leg-scoped — they are a property of the
continuous bar recursion, exactly like the EMA itself); `ATR20_t` =
mean of the previous 20 completed bars; `ATR_EVENT` = `ATR20` through
`T-1`. Positive `ATR_EVENT` required for normalized outcomes.

## 7. Same-bar morphology

Identical formulas/labels to the base generation
(`SAME_BAR_REJECTION_PROXY` / `SAME_BAR_BREAKTHROUGH_PROXY` /
`SAME_BAR_NEUTRAL`), same permanent caveat: "Five-minute OHLCV confirms
that the EMA traded during the bar but does not establish the true
intrabar high/low sequence."

## 8. Post-touch horizons

1, 2, 3, 4, 6, 9, 12, 18, 24 bars (5/10/15/20/30/45/60/90/120 minutes).
Measurement starts strictly at `T+1`; bar `T`'s own H/L/C never enter
outcomes. **A horizon is legal only if all of `T+1..T+H` lie within the
same session-leg instance as `T`** — if the leg instance ends (session
close, or the leg simply runs out of bars for that day) before `T+H`, the
horizon is excluded for that event (`HORIZON_INCOMPLETE`), never
partially computed and never allowed to read into `EXCLUDED` bars or the
next leg instance.

## 9. Oriented outcomes (mirrored, identical structure to base generation)

`FROM_ABOVE`: `REJECTION_EXC_H = max(0, max(High[T+1:T+H]) - EMA_LEVEL_T)`;
`BREAKTHROUGH_EXC_H = max(0, EMA_LEVEL_T - min(Low[T+1:T+H]))`;
`SIGNED_CLOSE_H = Close_{T+H} - EMA_LEVEL_T` (positive = rejection).
`FROM_BELOW`: `REJECTION_EXC_H = max(0, EMA_LEVEL_T - min(Low[T+1:T+H]))`;
`BREAKTHROUGH_EXC_H = max(0, max(High[T+1:T+H]) - EMA_LEVEL_T)`;
`SIGNED_CLOSE_H = EMA_LEVEL_T - Close_{T+H}` (positive = rejection).
Normalized by `ATR_EVENT`: `*_ATR_H`. `DOMINANCE_H = (REJ_ATR -
BRK_ATR)/(REJ_ATR + BRK_ATR)`, NA when both are zero. Retouch = any bar
`T+1..T+H` with `Low<=EMA_LEVEL_T<=High`.

## 10. Barrier-first outcomes

`b in {0.5, 1.0}` ATR, searched `T+1..T+H` within the leg instance only
(never past it — if the horizon itself is `HORIZON_INCOMPLETE`, the
corresponding barrier outcome for that horizon is also excluded). Barrier
definitions and 4-way outcome (`REJECTION_FIRST` / `BREAKTHROUGH_FIRST` /
`SAME_BAR_TIE` / `NEITHER`) identical to the base generation
(`research/ema21_levels/SPEC_EMA21_LEVELS.md` §8); intrabar order is
never inferred for a same-bar tie.

## 11. Required result surface

For every `instrument x session x touch_time_bucket x approach_side x
horizon`: eligible armed excursions, touch events, same-bar
rejection/breakthrough rate, same-bar rejection-minus-breakthrough
difference, median signed close (ATR), median rejection/breakthrough
excursion (ATR), median dominance, P(rejection exc > breakthrough exc),
P(breakthrough exc > rejection exc), retouch rate, 0.5-ATR and 1.0-ATR
rejection-first/breakthrough-first/tie/neither rates, exact binomial
p-value among non-tied first-hit events, BH-adjusted q-value, sample
status. Every cell retained, including null/underpowered ones.

## 12. Primary outcome and multiple testing

Primary: `1.0 ATR` rejection-first vs. breakthrough-first (all 9
horizons — unlike the base generation, the primary family here spans
every horizon, not one fixed horizon, because horizon-dependence is
itself part of this generation's question). Benjamini-Hochberg at q=0.05
applied separately within each `instrument x session`, across all
members `{touch_time_bucket} x {approach_side} x {horizon}` = 4 x 2 x 9
= 72 tests per family (6 families: 2 instruments x 3 sessions).
`ALL_SESSION` touch-time-bucket cells are a separate, exploratory,
labeled family (they overlap/duplicate the four disjoint buckets and
would violate BH's exchangeability-within-family assumption if pooled
with them). Same-bar morphology and 0.5-ATR barrier families are
secondary/exploratory, each its own separate BH pass.

**Minimum sample**: >=50 touch events, >=20 non-tied first-hit outcomes.
**Minimum material effect**: |rejection-first - breakthrough-first| >= 5pp.

## 13. Cell classification

`REJECTION_DOMINANT`/`BREAKTHROUGH_DOMINANT` require jointly: (1) min
sample; (2) |effect|>=5pp; (3) BH q<0.05 (within its `instrument x
session` primary family); (4) median signed close (ATR) has the matching
sign; (5) same directional sign in >=4 of 5 years. Otherwise
`MIXED_OR_NULL` (sample met, conditions 2-5 not jointly satisfied) or
`UNDERPOWERED` (sample not met).

## 14. Session-level mechanism classification

Per `instrument x session x approach_side`, roll the disjoint
touch-time-bucket x horizon cell classifications (from §13, restricted to
the 4 disjoint touch-time buckets, `ALL_SESSION` excluded from this
rollup) into one label:
`{ASIA,LONDON,NEW_YORK}_{REJECTION,BREAKTHROUGH}_MECHANISM` or
`NO_COHERENT_SESSION_MECHANISM`. A directional session-level label
requires: at least one directionally classified cell, corroborated by
>=2 *adjacent* horizons (adjacency in the ordered horizon list
1,2,3,4,6,9,12,18,24) carrying the *same* direction at the *same*
touch_time_bucket, **and** >=2 adjacent touch-time buckets (in the
ordered list `0_TO_30, 30_TO_60, 60_TO_120, 120_PLUS`) carrying the same
direction at some shared horizon — unless the finding is confined
entirely to `SESSION_0_TO_30` (single-bucket exception, explicitly
allowed by the task), in which case the adjacent-bucket requirement is
waived but the adjacent-horizon requirement still applies — **and**
>=4-of-5-year sign agreement pooled across the corroborating cells. A
single isolated significant cell, with no adjacent-horizon or
adjacent-bucket support, is never promoted; it is reported as-is in the
full result surface and flagged in the report as isolated.

## 15. Fallback statement

If no `instrument x session x approach_side` reaches a directional
session-level mechanism label, the final report states verbatim: "No
supported Asia, London or New York EMA21 rejection or breakthrough
mechanism was found in ES/NQ five-minute OHLCV during 2018-2022." No
further validation or new generation is started in that case.

## 16. Prohibited (unchanged)

No other EMA period, no SMA/VWAP/MACD/RSI, no volatility/trend/weekday/
month/economic-release filters, no profitability, entries, exits, sizing,
TP/SL, no 2023+ access, no combination with any prior generation's
variables. A null result is not rescued by a post-hoc filter search.
