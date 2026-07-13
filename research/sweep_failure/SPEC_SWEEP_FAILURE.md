# SPEC_SWEEP_FAILURE.md — formal specification

Single source of truth for formulas/thresholds used by `src/`. Where this
spec and code disagree, this spec wins and the code has a bug.

## 1. Causal levels (exactly four)

`PREV_RTH_HIGH`/`PREV_RTH_LOW`: max/min of the immediately previous
*valid* session's 09:30-15:59 ET highs/lows. `OVERNIGHT_HIGH`/
`OVERNIGHT_LOW`: max/min of the current session's 18:00-09:29 ET
highs/lows. No other reference level. Upper levels: `PREV_RTH_HIGH`,
`OVERNIGHT_HIGH` (outside = above). Lower levels: `PREV_RTH_LOW`,
`OVERNIGHT_LOW` (outside = below).

## 2. Causal volatility scale

`TR_t = max(High_t-Low_t, |High_t-Close_{t-1}|, |Low_t-Close_{t-1}|)`.
`ATR20_T` = mean `TR` over the 20 completed bars strictly before `T`
(`T-20..T-1`); require 20 complete and `ATR20_T > 0`. The breach or
confirmation bar never enters the scale.

## 3. Search window and strata

Search only 09:30-15:59 ET. Touch-time strata (by interaction bar `T`'s
ET minute): `OPEN` 09:30-10:29, `MID_MORNING` 10:30-11:59, `MIDDAY`
12:00-13:59, `AFTERNOON` 14:00-15:59, plus `ALL_RTH`. Events and complete
outcomes stay within the current RTH session (no outcome reads past
15:59 of the same session).

## 4. Arming and rearming (per level, per session)

Armed only after 3 consecutive completed 1-minute bars lie entirely
inside: upper level, `High_bar < level` for each; lower level, `Low_bar
> level` for each. After an event OR control episode is consumed
(classified into one of the terminal classes below, or the episode
simply ends without a qualifying interaction), disarm; a fresh 3-bar run
is required before the next episode. At most one classification per
armed episode. All event/arming state resets at the RTH session boundary
(09:30); no level or arming state carries from one session to the next.

## 5. First interaction and breach requirement

After arming, the first later bar whose range reaches the level is the
interaction bar `T`. Tick-normalized equality (0.25 tick) is used for
`==` comparisons. **`TOUCH_WITHOUT_BREACH`**: upper, `High_T == level`
and bar does not trade above; lower, `Low_T == level` and bar does not
trade below. **`BREACH`**: upper, `High_T >= level + 0.25`; lower,
`Low_T <= level - 0.25`. The first breach bar is `B` (`B == T` when the
very first interaction bar is already a breach; a bar that merely
touches without breaching is `TOUCH_WITHOUT_BREACH` and terminal — it
does not "become" a breach on a later bar within the same episode,
because the touch bar already consumed the episode, per §4).
`BREACH_MAGNITUDE`: upper `High_B - level`; lower `level - Low_B`;
normalized by `ATR20_B`. Breach-magnitude bands (fixed, preregistered):
`0_TO_0.25_ATR`, `0.25_TO_0.50_ATR`, `0.50_TO_1.00_ATR`, `ABOVE_1.00_ATR`.

## 6. Failed breach

Counting the breach bar `B` as minute one: `FAILED_BREACH_1MIN` if
`Close_B` is back inside (upper: `Close_B < level`; lower: `Close_B >
level`); `FAILED_BREACH_2MIN` if the first inside close is at `B+1`;
`FAILED_BREACH_3MIN` if the first inside close is at `B+2`. The first
qualifying inside-close bar is confirmation bar `C` (`C==B`, `B+1`, or
`B+2` respectively). No earlier bar in the episode may already have
qualified (mechanically true since we take the *first* qualifying bar).

## 7. Successful breach control

`SUCCESSFUL_BREACH_CONTROL`: a valid breach occurred; no completed close
returns inside during `B`, `B+1`, or `B+2`; at least one of those three
bars closes on the outside side (rules out a degenerate all-exactly-at-
level case). Event anchor = close of `B+2`.

## 8. Delayed failure control

`DELAYED_FAILURE_CONTROL`: no close returns inside during `B..B+2`; the
first inside close occurs during `B+3` through `B+9`. Confirmation bar
`C` = that first inside-close bar. (A breach with no inside close through
`B+9` is retained in the ledger as `NEITHER_RESOLVED_WITHIN_10MIN` —
not a failure, not the successful-breach control's fixed 3-bar window,
not a delayed failure — for completeness/null-retention, but is not a
primary/secondary comparison group per the task's four listed classes.)

## 9. Touch control

`TOUCH_WITHOUT_BREACH` uses interaction bar `T` as the event bar.
Sub-split (diagnostic only): `TOUCH_CLOSE_INSIDE` (`Close_T` strictly
inside) vs. `TOUCH_CLOSE_AT_LEVEL` (`Close_T` tick-equal to level). Never
pooled with `FAILED_BREACH_*`.

## 10. Same-bar morphology (breach bar `B`)

Upper: `FAILURE_PROXY` if `Close_B < level`; `OUTSIDE_CLOSE_PROXY` if
`Close_B > level`; `NEUTRAL` if tick-equal. Lower: mirrored. Also stored:
candle range, body/range ratio, breach-side wick, breach-side
wick/range ratio, volume, volume percentile (§12), close distance from
level. Permanent caveat: "One-minute OHLCV confirms that both prices
traded during the minute but does not establish the true intrabar
sequence."

## 11. Causal volume normalization

For instrument x exact ET minute, percentile of the breach bar's volume
within the trailing 60 *valid* prior sessions' volume at that same exact
minute (all 60 required). Strata: `HIGH_VOLUME` (percentile >= 0.80),
`NORMAL_VOLUME` (0.20-0.80), `LOW_VOLUME` (< 0.20). Diagnostic only,
never primary eligibility.

## 12. Previous-test count

Count of earlier *armed* episodes at the same level (same instrument,
session, level type) that reached an interaction (`TOUCH_WITHOUT_BREACH`
or any breach-derived class) before the current episode, within the same
RTH session. `FIRST_TEST` (0), `SECOND_TEST` (1), `THIRD_PLUS_TEST`
(>=2). The current episode is never counted in its own total.

## 13. ES-NQ confirmation (secondary diagnostic)

For each event (keyed by breach/interaction timestamp), inspect the
paired instrument's homologous level type (e.g. ES `PREV_RTH_HIGH` event
pairs with NQ `PREV_RTH_HIGH`). `CONFIRMED_BREACH`: paired instrument
breaches its homologous level in the same direction within event
timestamp ±1 minute. `PARTIAL_CONFIRMATION`: paired instrument touches
(without breaching) in that window. `UNCONFIRMED_BREACH`: neither.
Attached as a column on every event; never used to filter or merge
ES/NQ primary event streams (`RESEARCH_CHARTER.md` A5).

## 14. Post-event outcomes

Legal outcomes begin at: `C+1` for failed/delayed-failure classes; after
`B+2` (i.e. `B+3`) for `SUCCESSFUL_BREACH_CONTROL`; `T+1` for
`TOUCH_WITHOUT_BREACH`. The interaction/breach/confirmation bars never
enter outcomes. Horizons: 5, 10, 15, 30, 60 minutes, each requiring the
full window inside the same RTH session (no partial-window fallback).

## 15. Oriented outcomes (mirrored, anchored at the causal level)

Upper: `ROTATION_EXC_H = max(0, level - min(Low[anchor+1:anchor+H]))`;
`BREAKOUT_EXC_H = max(0, max(High[anchor+1:anchor+H]) - level)`;
`SIGNED_CLOSE_H = level - Close_{anchor+H}` (positive = rotation away).
Lower: mirrored so positive `SIGNED_CLOSE_H` always means rotation away.
Normalized by `ATR20` (computed at the anchor bar): `ROTATION_EXC_ATR`,
`BREAKOUT_EXC_ATR`, `SIGNED_CLOSE_ATR`. `DOMINANCE = (ROT_ATR -
BRK_ATR)/(ROT_ATR+BRK_ATR)`, NA when both zero. Also recorded: return to
the level (any bar in the window with range touching `level`), close
through the level again, max consecutive bars spent back outside.

## 16. Barrier-first outcomes

`b in {0.25, 0.50, 1.00} x ATR20` anchored at the causal level (not at
the anchor bar's price). Upper: rotation barrier `= level - b*ATR20`;
breakout barrier `= level + b*ATR20`. Lower: mirrored. 4-way outcome
`ROTATION_FIRST`/`BREAKOUT_FIRST`/`SAME_BAR_TIE`/`NEITHER`; intrabar
order never inferred for a tie.

## 17. Primary hypothesis and stratified permutation test

Primary event = `FAILED_BREACH_1MIN`+`FAILED_BREACH_2MIN`+
`FAILED_BREACH_3MIN` pooled (subclasses retained separately for
diagnostics). Primary outcome: horizon=15min, barrier=0.50xATR20,
rotation-first vs. breakout-first. Primary comparison: `FAILED_BREACH`
(pooled) vs. `SUCCESSFUL_BREACH_CONTROL`, reported by instrument x level
type x level side x touch-time stratum.

**Matched stratified permutation test**: match within instrument x
level type x time stratum x breach-magnitude band x prior-test-count
category x side. Within each matching stratum, shuffle the
failed/successful labels only (never across strata), recompute the
rotation-first-rate difference, repeat >=10,000 times with a fixed
deterministic seed (`DECISIONS.md` records the seed value), and compute
a two-sided permutation p-value as the fraction of permuted statistics
at least as extreme as the observed one (with the standard `+1` in
numerator/denominator to avoid a zero p-value). BH at 5% applied across
the primary comparison family (all `instrument x level_type x side x
time_stratum` cells).

## 18. Secondary comparisons (each a separately labeled, exploratory BH family)

`FAILED_BREACH` vs. `TOUCH_WITHOUT_BREACH`; vs. `DELAYED_FAILURE_CONTROL`;
`FIRST_TEST` vs. repeated tests; `HIGH_VOLUME` vs. `NORMAL`/`LOW_VOLUME`;
`CONFIRMED_BREACH` vs. `UNCONFIRMED_BREACH`; failure delay 1 vs. 2 vs. 3;
breach-magnitude bands; same-bar failure (`FAILED_BREACH_1MIN`) vs. later
failure (`2MIN`/`3MIN` pooled). No isolated subgroup is promoted absent
its own sample floor and corrected significance.

## 19. Year stability

Per primary cell, reported separately for 2018-2022: failed/successful
counts, rotation-first rate, breakout-first rate, difference, median
signed close, effect sign. Flags: sign reversal, 2020 concentration
(>=50% of pooled events from 2020), one-year dominance, years below a
10-event floor.

## 20. Classification

Primary cell -> `FAILED_BREACH_ROTATION_SUPPORTED` /
`..._BREAKOUT_SUPPORTED` require jointly: (1) >=100 failed breaches; (2)
>=100 successful-breach controls; (3) >=50 non-tied primary barrier
outcomes in *each* state; (4) |state difference| >=5pp; (5) BH q<0.05;
(6) median-signed-close contrast (failed minus successful) agrees in
sign with the rotation-first-rate difference; (7) same sign in >=4 of 5
years; (8) support (same direction, nominal significance not required)
at >=1 horizon adjacent to 15 minutes (10 or 30 minutes) in addition to
15 minutes itself. Otherwise `MIXED_OR_NULL` (floors 1-3 met) or
`UNDERPOWERED` (floors 1-3 not met). A volume/confirmation/previous-test
*incremental* claim additionally requires: >=50 events per subgroup,
>=5pp incremental effect over the pooled primary cell, its own corrected
(BH-adjusted, secondary-family) significance, and same contrast sign in
>=3 of 5 years.

## 21. Fallback statement

If nothing coherent survives, the final report states verbatim: "No
supported sweep-and-failure rotation mechanism was found at previous-RTH
or overnight extremes in ES/NQ one-minute OHLCV during 2018-2022." No
further validation or new generation follows.

## 22. Prohibited (unchanged pattern)

No ICT terminology used as evidence, no stop-hunting/liquidity-
engineering/dealer-positioning claim, no trading strategy, no
threshold optimization after viewing results, no 2023+ access, no other
reference level (no opening range, swing point, VWAP, order block, or
previous-week level), no combination with any other generation's
variables.
