# SPEC_EMA21_LEVELS.md — formal specification

This document is the single source of truth for formulas and thresholds
used by `src/`. Where this spec and code disagree, this spec wins and the
code has a bug.

## 1. EMA session definitions (two, kept separate)

- `RTH_EMA`: computed from RTH 5-minute bar closes only (09:30-15:59 ET),
  state carried continuously across valid RTH sessions (no reset at
  09:30), overnight bars never enter it.
- `FULL_SESSION_EMA`: computed from continuous chronological 5-minute
  closes across the full Globex session including overnight, carried
  continuously across session boundaries; touches evaluated only on RTH
  bars.

Never blended or selected post-hoc; every table reports both.

## 2. EMA inventory

For each session definition: EMA20, EMA21, EMA22, via
`ewm(span=n, adjust=False)` on completed-bar closes, warm-up >= 60
completed bars before eligibility (`DECISIONS.md` #4). EMA20/EMA22 are
specificity controls, not additional hypotheses.

## 3. Causally frozen level

For 5-minute bar `t`: `LEVEL_t = EMA_{t-1}` (EMA value after bar `t-1`'s
close; bar `t`'s own close never enters the EMA used to test bar `t`).
`LEVEL_T` is frozen at the touch bar and never recomputed with later data
for any subsequent same-bar or post-touch statistic.

## 4. Event arming and consumption

State machine per instrument x EMA-session-definition x span, evaluated
bar-by-bar in chronological order (RTH bars only, in session order):

- **Armed from above**: previous 3 completed bars each have
  `Low_bar > frozen_EMA_for_that_bar`.
- **Armed from below**: previous 3 completed bars each have
  `High_bar < frozen_EMA_for_that_bar`.
- Once armed, the next bar `T` with `Low_T <= LEVEL_T <= High_T` is a
  touch; approach side = `FROM_ABOVE`/`FROM_BELOW` per which arming fired.
- After a touch, the event immediately disarms; a fresh 3-bar one-sided
  run is required before the next event. At most one touch event per
  armed excursion.
- If a bar breaks the 3-bar one-sided condition without touching (e.g. a
  4th consecutive bar on the same side, or price reverses back to the
  same side without touching), arming simply persists/re-evaluates on the
  latest 3 bars — arming is a rolling condition on the last 3 bars, not a
  single latching flag, so it is re-checked every bar until a touch
  consumes it. A gap that lands the price on the *opposite* side without
  a qualifying touch re-starts the 3-bar count on the new side.

Session boundaries do not reset EMA state, but the 3-bar arming window
only ever compares bars within the same continuous bar sequence used for
that EMA definition (RTH bars for `RTH_EMA`; all bars, RTH+overnight, for
`FULL_SESSION_EMA` — though only RTH bars are eligible to be the touch bar
`T` itself, per section 1).

Stored per event: instrument, session date, year, EMA session definition,
EMA span, touch time, approach side, frozen EMA value, previous close,
pre-touch distance (in price and in ATR units), pre-touch ATR, the 3
arming bars (OHLC + frozen EMA each), event/exclusion reason codes.

## 5. Pre-touch ATR normalization

`TR_t = max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)`
`ATR20_t` = arithmetic mean of `TR` over the previous 20 completed bars.
`ATR_EVENT = ATR20` through bar `T-1` (never includes bar `T`). Events
with `ATR_EVENT` missing or <= 0 are excluded from all normalized
statistics (reason code `ATR_INVALID`) but retained in the raw ledger.

## 6. Same-bar morphology (descriptive only)

`FROM_ABOVE`: `Close_T > LEVEL_T` -> `SAME_BAR_REJECTION_PROXY`;
`Close_T < LEVEL_T` -> `SAME_BAR_BREAKTHROUGH_PROXY`; equal -> `SAME_BAR_NEUTRAL`.
`FROM_BELOW`: mirrored (`<` -> rejection, `>` -> breakthrough).

Stored: touch-bar OHLCV, `Close_T - LEVEL_T`, close location in range,
body/range ratio, upper/lower wick ratios, morphology label.

**Permanent caveat** (restated in every report that cites this section):
"One-minute source data aggregated to five-minute OHLCV confirms that the
EMA level traded during the bar but does not establish the true intrabar
sequence."

## 7. Post-touch outcomes

Measurement starts strictly at `T+1`; bar `T`'s own H/L/C never enter
post-touch excursions. Horizons (5-minute bars): 1,2,3,5,10,20 (=5,10,15,
25,50,100 minutes). A horizon requires the full window of bars to exist
(no partial-window fallback); otherwise excluded (`HORIZON_INCOMPLETE`).

`FROM_ABOVE` (rejection=up/back to approach side, breakthrough=down/through):
```
REJECTION_EXC_H    = max(0, max(High[T+1:T+H]) - LEVEL_T)
BREAKTHROUGH_EXC_H = max(0, LEVEL_T - min(Low[T+1:T+H]))
SIGNED_CLOSE_H     = Close_{T+H} - LEVEL_T      # positive = rejection
```
`FROM_BELOW` (rejection=down/back, breakthrough=up/through):
```
REJECTION_EXC_H    = max(0, LEVEL_T - min(Low[T+1:T+H]))
BREAKTHROUGH_EXC_H = max(0, max(High[T+1:T+H]) - LEVEL_T)
SIGNED_CLOSE_H     = LEVEL_T - Close_{T+H}      # positive = rejection
```
Normalized by `ATR_EVENT`: `REJECTION_EXC_ATR_H`, `BREAKTHROUGH_EXC_ATR_H`,
`SIGNED_CLOSE_ATR_H`. `DOMINANCE_H = (REJ_ATR - BRK_ATR)/(REJ_ATR + BRK_ATR)`,
`NA` when both excursions are exactly 0. Also record whether price traded
at `LEVEL_T` again strictly after bar `T` within the ledger's max horizon.

## 8. Barrier-first outcomes

Barriers `b in {0.5, 1.0}` ATR, checked bar-by-bar from `T+1` through the
20-bar ledger horizon (barrier tests are evaluated on the same underlying
path regardless of the "horizon" grouping used for excursion outcomes —
each `(horizon, barrier)` combination in section 10 restricts the search
window to `T+1 .. T+H`).

`FROM_ABOVE`: rejection barrier = `LEVEL_T + b*ATR_EVENT`; breakthrough
barrier = `LEVEL_T - b*ATR_EVENT`.
`FROM_BELOW`: rejection barrier = `LEVEL_T - b*ATR_EVENT`; breakthrough
barrier = `LEVEL_T + b*ATR_EVENT`.

Per bar, a barrier is "reached" if the bar's High/Low range crosses it
(direction-appropriate: rejection barrier reached if bar's excursion in
the rejection direction reaches/exceeds it; symmetrically for
breakthrough). Outcome per event x horizon x barrier:
`REJECTION_FIRST`, `BREAKTHROUGH_FIRST`, `SAME_BAR_TIE` (both barriers
first reached within the same bar — intrabar order is never inferred),
`NEITHER` (neither reached within the horizon). Recorded: reached flags,
first-reach bar index for each barrier, and the 4-way outcome.

## 9. Time-of-day strata (fixed, preregistered)

`OPEN` 09:30-10:29, `MID_MORNING` 10:30-11:59, `MIDDAY` 12:00-13:59,
`AFTERNOON` 14:00-15:59, plus `ALL_RTH` (union). Stratum is assigned from
the touch bar's ET time. No narrower filter is created after viewing
results.

## 10. Required summary cells

For every `instrument x EMA_session_definition x EMA_span x
approach_side x time_stratum x horizon`, `src/summary.py` reports:
eligible armed excursions, touch events, touch rate, same-bar
rejection/breakthrough count+rate, same-bar rejection-minus-breakthrough
difference, exact two-sided binomial p-value (vs 0.5) for the same-bar
split, median `SIGNED_CLOSE_ATR_H`, median `REJECTION_EXC_ATR_H`, median
`BREAKTHROUGH_EXC_ATR_H`, median `DOMINANCE_H`, P(rejection excursion >
breakthrough excursion), P(breakthrough > rejection), post-touch retouch
rate, 0.5-ATR and 1.0-ATR barrier-first rates (rejection-first,
breakthrough-first, tie, neither), exact binomial p-value among
non-tied/non-neither first-hit outcomes, raw and BH-adjusted p-values
(section 12), and a `sample_status` flag (`OK` / `UNDERPOWERED`). Every
cell is retained, including null and underpowered ones — none are
dropped from `reports/tables/full_exploratory_results.csv`.

## 11. Year stability (2018-2022, all five years, no cherry-picking)

Per principal effect (same-bar rejection-minus-breakthrough,
0.5-ATR and 1.0-ATR rejection-first-minus-breakthrough-first,
median signed close, directional sign), reported per year with event
count. Flags: sign reversal across adjacent years, 2020 concentration
(one year contributing disproportionately), one-year dominance, years
below the 10-event floor. All five years are always computed together;
never five independently-selected hypotheses.

## 12. Multiple testing

**Primary family**: 1.0-ATR rejection-first vs. breakthrough-first,
horizon = 5 bars (25 minutes). Benjamini-Hochberg at q=0.05, applied
*separately within each* `instrument x EMA_session_definition x
time_stratum`, across the 6 members `{EMA20,EMA21,EMA22} x
{FROM_ABOVE,FROM_BELOW}`.

**Secondary/exploratory families** (each its own separate BH pass,
clearly labeled exploratory in `reports/tables/`): all other horizons;
same-bar morphology splits; 0.5-ATR barrier splits.

**Primary minimum sample**: >=50 touch events, >=20 non-tied first-hit
outcomes, >=4 of 5 years with >=10 events.
**Primary minimum material effect**: |rejection-first - breakthrough-first| >= 5pp.

## 13. Classification

Per primary cell:
- `REJECTION_DOMINANT` / `BREAKTHROUGH_DOMINANT` require, jointly: (1)
  minimum sample met; (2) |effect| >= 5pp; (3) BH-adjusted q < 0.05; (4)
  median `SIGNED_CLOSE_ATR_5` has the matching sign; (5) directional sign
  agrees in >=4 of 5 years.
- `MIXED_OR_NULL`: minimum sample met but conditions 2-5 not jointly
  satisfied.
- `UNDERPOWERED`: minimum sample not met.

Specificity, per instrument x EMA_session_definition x approach_side x
time_stratum cell:
- `EMA21_SPECIFIC` iff EMA21 receives a directional classification, EMA20
  and EMA22 do **not** receive the same directional classification in the
  same cell, and EMA21's |effect| exceeds both neighbors' |effect| by
  >=5pp.
- `GENERIC_EMA_ZONE`: EMA20, EMA21, EMA22 show materially similar
  direction and magnitude (all three directionally classified the same
  way, or all three `MIXED_OR_NULL`, with pairwise |effect| differences
  < 5pp).
- Otherwise: `INCONCLUSIVE_SPECIFICITY` (e.g. only one neighbor matches,
  or spans disagree in direction without a clean generic pattern).

No claim that "algorithms specifically watch EMA21" is made anywhere
unless `EMA21_SPECIFIC` holds for that cell.

## 14. Prohibited analyses (hard constraint, enforced by code review + tests)

No other EMA period; no SMA, VWAP, MACD, RSI, volatility filters, trend
regime filters, weekday/month/economic-release conditioning; no
profitability, entries, exits, stop/target combinations; no 2023+ data
access; no combination with any prior cash-open variable. A null EMA21
result is not rescued by any post-hoc filter search.

## 15. Fallback statement

If no cell in either instrument reaches `EMA21_SPECIFIC` with a directional
classification, the final report states verbatim: "No supported intraday
EMA21 level mechanism was found in ES/NQ five-minute OHLCV during
2018-2022." No further validation or new generation is started in that
case.
