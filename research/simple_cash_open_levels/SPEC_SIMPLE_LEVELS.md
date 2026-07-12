# SPEC_SIMPLE_LEVELS.md — Simple Cash-Open Level Study (Generation 9)

Final frozen methodology, transcribed from Dylan's specification.
Implemented exactly as given — no redesign, no additional level families,
no synthetic controls. Branch `research/simple-cash-open-level-study`,
base `research/cash-open-target-atlas` @ `201896d`.

## Objective

Determine whether anchored VWAP deviation levels or historical 09:30-
excursion levels contain repeatable information about ES/NQ cash-open
price paths. No level is assumed a priori to be reversal or continuation;
same-bar morphology and post-touch path are classified independently.

## Family A — anchored VWAP deviation levels (14/instrument)

**A1, overnight VWAP** (7 levels): window = all bars of session `s` with
`et_minute<570` through the completed 09:29 bar. `p_i=(H_i+L_i+C_i)/3`;
`VWAP_ON = Σ(Vol_i·p_i)/ΣVol_i`; `SD_ON = sqrt(max(0, Σ(Vol_i·p_i²)/ΣVol_i
− VWAP_ON²))`. Valid only if ≥30 overnight bars and total volume > 0.
Levels: `ON_VWAP_{m3,m2,m1,0,p1,p2,p3} = VWAP_ON + j·SD_ON`, `j∈{-3,-2,
-1,0,1,2,3}`. All fixed before the 09:30 bar opens.

**A2, prior-RTH VWAP** (7 levels): window = the immediately preceding
session's full RTH (`et_minute` 570-959), only if that session is not an
early close (no substitution to a more distant predecessor). Same
`VWAP_PR`/`SD_PR` formulas over that window. Levels: `PR_VWAP_{m3,...,p3}
= VWAP_PR + j·SD_PR`. No other VWAP anchor.

## Family B — historical 09:30-candle excursion levels (72/instrument)

For prior valid session `i`: `U_i = High_0930,i − Open_0930,i`,
`D_i = Open_0930,i − Low_0930,i` (the single 09:30 candle only — never a
later bar, later-session max/min, session-end data, overnight range, or
current-session realized volatility). U and D kept separate.

Lookbacks `N∈{5,10,20}`, exactly the previous N valid 09:30 candles, no
expanding/partial-window fallback. Centers: `mean`, `median`, `EMA`
(`ewm(span=N, adjust=False).mean()`, final value, `alpha=2/(N+1)`, not
retuned). One shared raw sample SD per side/lookback (`ddof=1`) used
across all three center variants (isolates the center-estimator effect).

Current-session level (`O` = current 09:30 open), for `N∈{5,10,20}`,
`CENTER∈{mean,median,EMA}`, `k∈{0,1,2,3}`:
`UPPER_(N,CENTER,k) = O + CENTER_U(N,CENTER) + k·SD_U(N)`
`LOWER_(N,CENTER,k) = O − CENTER_D(N,CENTER) − k·SD_D(N)`
→ 36 upper + 36 lower = 72 level_ids. Aliases (different formulas
producing numerically coincident prices) are never silently deduplicated
— all rows retained, coincidences reported (§19).

## Final inventory: 7 + 7 + 72 = 86 level_ids/instrument, locked by test.

No ATR levels, prior highs/lows, overnight highs/lows, midpoints, opening
ranges, round numbers, synthetic controls, taxonomy labels, paired-level
swaps, or dynamic swing levels are added.

## Orientation

`UPPER_LEVEL` if `level_value ≥ O_0930 + 0.25` (1 tick); `LOWER_LEVEL` if
`level_value ≤ O_0930 − 0.25`; else `AT_OPEN_AMBIGUOUS` (retained for
touch-frequency reporting only, excluded from directional stats).

## Touch search

`et_minute∈[570,689]` (09:30-11:29 ET, 120 bars) only. First touch per
`(instrument, session_date, level_id)`; later retouches create no
additional observation. `touch_by_{30,60,120}` flags; timing bins
`BAR_0930, MINUTES_2_TO_5, MINUTES_6_TO_15, MINUTES_16_TO_30,
MINUTES_31_TO_60, MINUTES_61_TO_120`. Permanent caveat: intrabar H/L/C
sequence is never established by 1-minute OHLCV.

## Same-bar morphology (touch bar only, never enters post-touch outcomes)

Upper: `Close_T<level_value`→`SAME_BAR_REVERSAL_PROXY`;
`Close_T>level_value`→`SAME_BAR_BLAST_THROUGH_PROXY`;
`Close_T==level_value`→`SAME_BAR_NEUTRAL`. Lower: mirrored.

## Post-touch outcomes (start strictly at `T+1`; touch bar H/L/C excluded)

Horizons `h∈{5,15,30,60,120}` (primary `{30,60,120}`), no partial-window
fallback (touch as late as 689 → 120-min outcome may reach `et_minute=
809`, still within RTH). Raw: `Close_h`, `raw_close_displacement`,
`raw_up_excursion`, `raw_down_excursion`, `post_touch_retouch` (a repeat
touch, explicitly not a directional recross). Oriented (upper/lower
mirrored per §13 of the frozen spec): `CONT_EXC_h`, `REV_EXC_h`,
`SIGNED_CLOSE_h` (positive = continuation), each in raw points and
`/native_sd` where `native_sd>0`; `DOMINANCE_h = (CONT_EXC_SD_h −
REV_EXC_SD_h)/(CONT_EXC_SD_h+REV_EXC_SD_h)`, NA if both zero. Raw
outcomes retained even when `native_sd==0`; normalized outcomes excluded
in that case.

## Barrier-first outcomes

`b∈{0.5,1.0,2.0,3.0}` native-SD units; continuation/reversal barrier
prices mirrored per orientation (§14). Outcomes: `CONTINUATION_FIRST`,
`REVERSAL_FIRST`, `SAME_BAR_TIE`, `NEITHER` — same-bar tie whenever both
barriers are first reached in the same 1-minute bar (never inferred
order).

## Directional close-recross

Distinct from `post_touch_retouch`: requires a completed post-touch bar
to first close on the continuation side, THEN a later completed bar to
close on the reversal side (§15, mirrored by orientation).

## Multiple testing

Main 1.0-SD barrier-first test: Benjamini-Hochberg at 5%, separately
within each `(instrument, primary horizon)`, across every valid level_id.
Same-bar morphology: BH at 5%, separately by instrument, across all
level_ids. Raw p-values, adjusted q-values, and all null cells retained.

## Behavior classification (per instrument × level_id × primary horizon)

Floors: ≥50 first-touch events, ≥20 non-tied 1.0-SD barrier-first
outcomes, ≥4 calendar years with ≥10 touches. `CONTINUATION_DOMINANT`/
`REVERSAL_DOMINANT` require all four frozen conditions (§17); else
`MIXED_OR_NULL` if adequately powered, else `UNDERPOWERED`. Same-bar
morphology classified separately and independently (a level may blast
through same-bar and reverse over 60 minutes, or the reverse) — never
combined into one forced narrative.

## Coincident levels (§19)

Exact and within-one-tick duplicates across formulas are identified and
reported (aliases per physical level, most common collisions, % of touch
events in multi-alias clusters) but never deduplicated or required to be
isolated — every formula-specific row is retained.

## Final interpretation

Reports separately: (1) overnight-VWAP behavior, (2) prior-RTH-VWAP
behavior, (3) 09:30-excursion behavior by lookback/center/rung/side, (4)
2018-2022 stability, (5) whether results are duplicated parameterizations
of the same physical level, (6) whether any level shows coherent same-bar
morphology AND coherent post-touch dominance. If no level family shows
stable, adequately powered directional behavior, the report states the
frozen null sentence verbatim (§22) — never overgeneralized beyond this
specific data/mechanism.
