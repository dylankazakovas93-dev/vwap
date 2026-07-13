# SPEC_TEN_AM_BLOCKS.md — formal specification

Single source of truth for formulas/thresholds used by `src/`. Where this
spec and code disagree, this spec wins and the code has a bug.

## 1. Session ledger and causal scales

Pre-10:00 window: 1-minute bars `et_minute` in `[570,599]` (09:30-09:59),
exactly 30 bars, required complete. `RANGE_30 = High_{0930-0959} -
Low_{0930-0959}`; require `RANGE_30 > 0`. `MEDIAN_RANGE_20` = median of
the 20 chronologically prior *valid* sessions' `RANGE_30` (`DECISIONS.md`
#3); require all 20. All excursion/signed-close outputs are stored both
in raw points, normalized by `RANGE_30`, and normalized by
`MEDIAN_RANGE_20` — never one chosen over the other post hoc.

Post-10:00 interaction window: 1-minute bars `et_minute` in `[600,659]`
(10:00-10:59), exactly 60 bars for the full-window search; a session
short of the full 60 simply truncates the achievable activation windows
(§7) and horizons (§8) — never a partial-window guess.

## 2. Module A — 10:00 open mechanism

`O_1000` = open of the `et_minute==600` bar. Tick size 0.25 (ES, NQ).

`BULLISH_1000` if `Close_1000 >= O_1000 + 0.25`; `BEARISH_1000` if
`Close_1000 <= O_1000 - 0.25`; else `NEUTRAL_1000`.

Permanent caveat: "One-minute OHLCV does not establish the intrabar
order of the 10:00 candle."

Outcomes begin at 10:01 (`et_minute==601`). `BULLISH_1000`: continuation
= above `O_1000`, reversal = below. `BEARISH_1000`: continuation =
below `O_1000`, reversal = above. Per horizon: signed close displacement
(`Close_{T+H} - O_1000` signed so positive=continuation), continuation
excursion, reversal excursion (mirrored max-based formulas, same
structure as Module B §5), dominance (same formula as §5), return
through `O_1000` (any bar `T+1..T+H` with `Low<=O_1000<=High`), first
completed close through the opposite side of `O_1000`. Barriers `b in
{0.25, 0.50, 1.00} x RANGE_30` around `O_1000`; 4-way outcome
`CONTINUATION_FIRST`/`REVERSAL_FIRST`/`SAME_BAR_TIE`/`NEITHER`, same
same-bar-tie discipline as §6.

`NEUTRAL_1000` sessions are retained in the ledger (continuation/
reversal direction is undefined for them and they do not enter Module A's
directional summary cells, but they are counted and reported, never
silently dropped).

## 3. Module B — pre-10:00 rejection blocks (pure OHLCV geometry)

**Upper block**: `H_BAR` = the last (most recent, by time) bar in the
30-bar pre-10:00 window whose own `High` equals `RANGE_30`'s high
endpoint (`DECISIONS.md`/`RESEARCH_CHARTER.md` A3 — ties broken by
recency). `UPPER_BLOCK_LOW = max(Open_H_BAR, Close_H_BAR)`,
`UPPER_BLOCK_HIGH = High_H_BAR`, zone `[UPPER_BLOCK_LOW,
UPPER_BLOCK_HIGH]`.

**Lower block**: `L_BAR` = the last bar in the window whose own `Low`
equals `RANGE_30`'s low endpoint. `LOWER_BLOCK_LOW = Low_L_BAR`,
`LOWER_BLOCK_HIGH = min(Open_L_BAR, Close_L_BAR)`, zone
`[LOWER_BLOCK_LOW, LOWER_BLOCK_HIGH]`.

Require zone width `>= 0.25` (one tick); otherwise `BLOCK_INVALID` for
that side (excluded from all interaction search, retained in the
definition ledger with a reason code). No other block type is defined.

## 4. Freshness, open location

**Freshness**: scan the pre-10:00 bars strictly after the block-forming
bar (`H_BAR`/`L_BAR`) through 09:59; `PRETOUCHED` if any later pre-10:00
bar's `[Low,High]` range overlaps the zone at all, else `PRISTINE`.

**10:00 open location** (upper): `APPROACH_SIDE` if `O_1000 <
UPPER_BLOCK_LOW`; `OPEN_INSIDE` if `UPPER_BLOCK_LOW <= O_1000 <=
UPPER_BLOCK_HIGH`; `ALREADY_BEYOND` if `O_1000 > UPPER_BLOCK_HIGH`.
Lower (mirrored): `APPROACH_SIDE` if `O_1000 > LOWER_BLOCK_HIGH`;
`OPEN_INSIDE` if inside; `ALREADY_BEYOND` if `O_1000 < LOWER_BLOCK_LOW`.
All three states are retained and reported; the clean first-interaction
analysis (primary test, §9) uses `APPROACH_SIDE` only.

## 5. Block interaction and activation windows

Search 10:00-10:59 (60 one-minute bars) in chronological order for the
first bar whose `[Low,High]` range overlaps any part of the zone at all
(any overlap, not full containment). At most one first-interaction bar
`T` per `(session, block side)`. Nested activation windows are derived
from that single `T` (never searched independently per window):
`WITHIN_10AM_CANDLE` (`T` is `et_minute==600`), `WITHIN_5MIN` (`T -
600 <= 5`... i.e. `T` in `[600,605)`), `WITHIN_10MIN`, `WITHIN_15MIN`,
`WITHIN_30MIN`, `WITHIN_60MIN` (`T` in `[600,660)`, i.e. anywhere in the
search window) — each window is a superset of the narrower ones by
construction (`T` either falls in the 5-minute bucket or it doesn't; the
10/15/30/60-minute flags are simply `T-600 < {10,15,30,60}` evaluated
once from the same `T`).

## 6. Same-bar block morphology (interaction bar `T`, closing side proxy)

Upper (approached from below): `REVERSAL_PROXY` if `Close_T <
UPPER_BLOCK_LOW`; `BREAKTHROUGH_PROXY` if `Close_T > UPPER_BLOCK_HIGH`;
`INSIDE_UNRESOLVED` if `UPPER_BLOCK_LOW <= Close_T <= UPPER_BLOCK_HIGH`.
Lower (approached from above): `REVERSAL_PROXY` if `Close_T >
LOWER_BLOCK_HIGH`; `BREAKTHROUGH_PROXY` if `Close_T < LOWER_BLOCK_LOW`;
`INSIDE_UNRESOLVED` if inside. Operational proxy only — "Do not claim
the true intrabar order is known," restated in the report.

## 7. Post-interaction block outcomes

Legal outcomes begin strictly at `T+1`; bar `T`'s own H/L/C never enter
them. Horizons (minutes = bars, 1-minute bars): 1, 3, 5, 10, 15, 30, 60.
Require the full `T+1..T+H` window to exist in the 1-minute parquet
(no partial-window fallback; `HORIZON_INCOMPLETE` otherwise — this can
legitimately extend past 11:00 ET into later RTH bars, since Module B's
*outcome* horizons are not capped at 10:59, only the *interaction
search* is).

**Upper**: `REV_EXC_H = max(0, UPPER_BLOCK_LOW - min(Low[T+1:T+H]))`;
`BRK_EXC_H = max(0, max(High[T+1:T+H]) - UPPER_BLOCK_HIGH)`.
`SIGNED_CLOSE_H = UPPER_BLOCK_LOW - Close_{T+H}` if `Close_{T+H} <
UPPER_BLOCK_LOW`; `= UPPER_BLOCK_HIGH - Close_{T+H}` if `Close_{T+H} >
UPPER_BLOCK_HIGH`; else `0` with `CLOSE_INSIDE_ZONE=1`. Positive =
rejection below the block, negative = breakthrough above.

**Lower**: `REV_EXC_H = max(0, max(High[T+1:T+H]) - LOWER_BLOCK_HIGH)`;
`BRK_EXC_H = max(0, LOWER_BLOCK_LOW - min(Low[T+1:T+H]))`.
`SIGNED_CLOSE_H = Close_{T+H} - LOWER_BLOCK_HIGH` if `Close_{T+H} >
LOWER_BLOCK_HIGH`; `= Close_{T+H} - LOWER_BLOCK_LOW` if `Close_{T+H} <
LOWER_BLOCK_LOW`; else `0` with `CLOSE_INSIDE_ZONE=1`. Positive =
rejection above the block, negative = breakthrough below.

Normalize `REV_EXC_H`/`BRK_EXC_H`/`SIGNED_CLOSE_H` by both `RANGE_30`
and `MEDIAN_RANGE_20` (both stored, never chosen between).
`DOMINANCE_H = (REV_EXC_H - BRK_EXC_H)/(REV_EXC_H + BRK_EXC_H)` (on the
`RANGE_30`-normalized values; NA when both are zero). Retouch = any bar
`T+1..T+H` whose range overlaps the zone again.

## 8. Block barrier-first outcomes

`b in {0.25, 0.50, 1.00} x RANGE_30`, searched `T+1..T+H`. **Upper**:
reversal barrier `= UPPER_BLOCK_LOW - b*RANGE_30`; breakthrough barrier
`= UPPER_BLOCK_HIGH + b*RANGE_30`. **Lower**: reversal barrier `=
LOWER_BLOCK_HIGH + b*RANGE_30`; breakthrough barrier `= LOWER_BLOCK_LOW
- b*RANGE_30`. 4-way outcome `REVERSAL_FIRST`/`BREAKTHROUGH_FIRST`/
`SAME_BAR_TIE`/`NEITHER`; intrabar order never inferred for a tie. Path
measurements only, not trade exits.

## 9. Pre-10:00 context variables and fixed strata

`R_30 = Close_0959 - Open_0930`; `U_30 = High_{0930-0959} - Open_0930`;
`D_30 = Open_0930 - Low_{0930-0959}`; `Q_30 = (U_30-D_30)/(U_30+D_30)`;
`CLOSE_LOCATION_30 = (Close_0959 - Low_{0930-0959})/RANGE_30`. Also
stored: block width, block width/`RANGE_30`, block-forming candle
wick/range and body/range ratios, block-forming candle time, distance
from `O_1000` to the block, freshness, 10:00 open location state.

Fixed strata (preregistered, no post-hoc thresholds): `PRE10_UP`
(`R_30>0`)/`PRE10_DOWN`(`R_30<0`)/`PRE10_FLAT`(`R_30==0`);
`CLOSE_LOW`(`<=0.25`)/`CLOSE_MIDDLE`(`0.25-0.75`)/`CLOSE_HIGH`(`>=0.75`);
`UP_DOMINANT`(`Q_30>=1/3`)/`BALANCED`(`|Q_30|<1/3`)/`DOWN_DOMINANT`
(`Q_30<=-1/3`); `PRISTINE`/`PRETOUCHED`. `MOMENTUM_INTO_BLOCK` (upper) iff
`PRE10_UP` and `CLOSE_HIGH` and `UP_DOMINANT`; (lower) iff `PRE10_DOWN`
and `CLOSE_LOW` and `DOWN_DOMINANT`; else `NOT_MOMENTUM_INTO_BLOCK`. No
further combinations are created after viewing results.

## 10. Required result surfaces

**Module A**: for every `instrument x candle_state x context_stratum x
horizon`, continuation vs. reversal outcomes (same structural fields as
Module B's list below, adapted to continuation/reversal naming).
**Module B**: for every `instrument x block_side x activation_window x
context_stratum x horizon`: valid blocks, first interactions, interaction
rate, same-bar reversal/breakthrough/unresolved rate, median signed
close, median reversal/breakthrough excursion, median dominance, P(rev
exc > brk exc), P(brk exc > rev exc), retouch rate, each barrier-first
distribution (reversal-first/breakthrough-first/tie/neither rate), raw
p-value, BH-adjusted q-value, sample status. Every cell retained,
including null/underpowered ones.

## 11. Primary tests and multiple testing

**Module A primary**: 10:00 candle state x context stratum, horizon=15
min, barrier=0.50xRANGE_30, continuation-first vs. reversal-first.
**Module B primary**: activation window = `WITHIN_30MIN`, `APPROACH_SIDE`
opens only, horizon=15 min, barrier=0.50xRANGE_30, reversal-first vs.
breakthrough-first, upper/lower separate, `PRISTINE`/`PRETOUCHED`
reported separately (not pooled). BH at q=0.05 applied separately within
each `instrument x module`. All other activation windows, horizons,
barriers, and context strata are exploratory, each its own separately
labeled BH family.

**Minimum sample**: >=50 interactions, >=20 non-tied first-hit outcomes.
**Minimum material effect**: |directional difference| >= 5pp.

## 12. Classification

Cell-level (5 joint conditions: sample, >=5pp, BH q<0.05, matching
median-signed-close sign, >=4/5-year sign agreement): Module A ->
`TEN_AM_CONTINUATION`/`TEN_AM_REVERSAL`/`TEN_AM_MIXED_OR_NULL`/
`UNDERPOWERED`; Module B ->
`REJECTION_BLOCK_REVERSAL_DOMINANT`/`..._BREAKTHROUGH_DOMINANT`/
`MIXED_OR_NULL`/`UNDERPOWERED`. A "coherent conditional mechanism"
(reported alongside the cell table, not a new label) additionally
requires support across >=2 adjacent horizons (ordered list
1,3,5,10,15,30,60) and, for Module B, >=2 adjacent activation windows
(ordered list `10AM_CANDLE,5MIN,10MIN,15MIN,30MIN,60MIN`) unless confined
entirely to `WITHIN_10AM_CANDLE`, in which case the adjacent-window
requirement is waived but adjacent-horizon support still required. One
isolated significant cell is never promoted.

## 13. Fallback statement

If nothing coherent survives in either module, the final report states
verbatim: "No supported 10:00-open or mechanically defined pre-10:00
rejection-block mechanism was found in ES/NQ one-minute OHLCV during
2018-2022." No further validation or new generation follows.

## 14. Prohibited (unchanged pattern)

No ICT terminology/narrative claims (order-flow, absorption,
dealer-positioning, liquidity-sweep), no profitability, entries, exits,
sizing, TP/SL, no 2023+ access, no unrestricted threshold search beyond
the fixed strata in §9, no combination with any other generation's
variables. A null result is not rescued by a post-hoc filter search.
