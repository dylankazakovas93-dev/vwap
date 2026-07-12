# SPEC_EXCURSION_TIMING.md — NQ Excursion-Level Timing Study (Generation 10)

Final frozen methodology, transcribed from Dylan's specification.
Implemented exactly as given — no redesign, no additional level
families, no threshold changes. Branch `research/nq-excursion-level-
timing`, base `research/simple-cash-open-level-study` @ `4d5ee1b`. NQ is
primary; ES is a preregistered negative-control replication, interpreted
separately and never used to alter NQ definitions.

## Canonical historical excursion input

Prior valid session `i`, single 09:30 candle only: `U_i = High_0930,i −
Open_0930,i`, `D_i = Open_0930,i − Low_0930,i`. Exactly the previous 10
valid sessions, no expanding/partial fallback. `MEAN_U_10`, `MEAN_D_10`
(arithmetic mean only — no median, no EMA), `SD_U_10`, `SD_D_10` (sample
SD, `ddof=1`).

## Frozen level inventory — 8/instrument

`O` = current 09:30 open. For `k∈{0,1,2,3}`: `UPPER_k = O + MEAN_U_10 +
k·SD_U_10`; `LOWER_k = O − MEAN_D_10 − k·SD_D_10`. `UPPER_k0` = canonical
continuation candidate; `LOWER_k0` = its causal mirror; `k=1/2/3` test
whether farther extensions are continuation, reversal/exhaustion, mixed,
or null. Locked by regression test.

## Master touch search

Once per `(instrument, session_date, level_id)`, `et_minute∈[570,689]`
(120 bars). First touch only; later retouches create no additional
observation. Nested activation windows `A∈{1,2,3,4,5,10,15,20,30,60,120}`
minutes are derived from the single first-touch elapsed-bar count
(`first_touch_elapsed_bar ≤ A`) — never independently re-searched.
Mutually exclusive first-touch bins: `BAR_0930, MINUTE_2, MINUTE_3,
MINUTE_4, MINUTE_5, MINUTES_6_TO_10, MINUTES_11_TO_15, MINUTES_16_TO_20,
MINUTES_21_TO_30, MINUTES_31_TO_60, MINUTES_61_TO_120`.

## Same-bar morphology (touch bar only, never enters post-touch outcomes)

Upper: `Close_T<level`→`SAME_BAR_REVERSAL_PROXY`; `Close_T>level`→
`SAME_BAR_BLAST_THROUGH_PROXY`; `==`→`SAME_BAR_NEUTRAL`. Lower: mirrored.
Permanent caveat: 1-minute OHLCV does not establish true intrabar
high/low ordering.

## Post-touch outcomes (start strictly at T+1; touch bar H/L/C excluded)

Horizons `H∈{1,2,3,4,5,10,15,20,30,60,120}`, no partial-window fallback.
Raw (`close_H`, `raw_close_displacement`, `raw_up/down_excursion`,
`post_touch_retouch`) and oriented (`CONT_EXC_H`, `REV_EXC_H`,
`SIGNED_CLOSE_H`, each `/native_sd` where valid; `DOMINANCE_H`, NA if
both excursions zero), mirrored upper/lower per the frozen formulas.
Barrier-first: `b∈{0.5,1.0,2.0,3.0}` native-SD units (`b=1.0` primary),
`CONTINUATION_FIRST/REVERSAL_FIRST/SAME_BAR_TIE/NEITHER`, tie whenever
both reached in the same bar (never inferred). Directional close-recross
distinct from simple retouch (continuation-side close must occur before
a later rejection-side close).

## Timing surface

One row per `instrument × level_id × activation_window(11) × outcome_
horizon(11)` — 2×8×11×11 = 1936 primary cells max (fewer where a level
is invalid). Every metric in §15 of Dylan's specification, every cell
retained including null/underpowered.

## Multiple testing

BH at 5%, separately within each instrument, across all valid `level_id
× activation_window × horizon` primary (`b=1.0`) cells. Same-bar
morphology: BH at 5% within each instrument across `8 levels × 11
activation windows`. ES interpreted as a separate negative-control
family, its own BH, never pooled with NQ.

## Coherence requirement (timing-region classification)

All seven conditions required (§17 of Dylan's specification): ≥1
BH-surviving primary cell; |cont−rev diff|≥5pp; median `SIGNED_CLOSE_SD_H`
same direction; same direction in ≥2 adjacent activation windows AND ≥2
adjacent horizons; year sign consistent in ≥4/5 years; ≥50 touched events
and ≥20 non-tied barrier observations per supporting cell. Classification:
`COHERENT_OPEN_CONTINUATION`, `COHERENT_OPEN_REVERSAL`,
`LATE_MORNING_CONTINUATION_ONLY`, `LATE_MORNING_REVERSAL_ONLY`,
`ISOLATED_SIGNIFICANT_CELL`, `MIXED_OR_NULL`, `UNDERPOWERED`. `OPEN` iff
the coherent region includes an activation window ≤30 minutes;
`LATE_MORNING_ONLY` iff every supported window is >30 minutes.

## Same-bar classification

`SAME_BAR_REVERSAL_BIASED`/`SAME_BAR_BLAST_THROUGH_BIASED`/
`SAME_BAR_MIXED`/`SAME_BAR_UNDERPOWERED` — ≥50 non-neutral touch bars,
|diff|≥5pp, BH q<0.05, sign consistent ≥4/5 years, support across ≥2
adjacent activation windows.

## Year-by-year stability

Every timing-surface cell reported per year 2018-2022 (touches, cont/rev
rates and diff, median signed close, same-bar rates), plus mean/SD of the
five annual effects, within-one-cross-year-SD flag per year, count of
years with the pooled sign, max/min annual effect, 2020-largest-year flag,
>35%-of-touches-in-one-year flag. No five separate confirmatory year
tests.

## Causal rolling-state test (one frozen secondary experiment)

Per instrument × level_id: events touched within 30 minutes with a
complete 30-minute horizon and a non-tied/non-neither `b=1.0` result,
ordered chronologically. Prior state from the immediately preceding 10
such events (strictly prior sessions only): `CONTINUATION_STATE` (≥6/10
`CONTINUATION_FIRST`), `REVERSAL_STATE` (≥6/10 `REVERSAL_FIRST`),
`MIXED_STATE` otherwise, `STATE_UNAVAILABLE` if <10 prior events. Current
event's own 30-min/`b=1.0` outcome compared by prior state: counts, rates,
continuation-rate difference, Fisher exact p, BH q (within instrument
across 8 level_ids), year-by-year. Classification `STATE_PERSISTENCE_
SUPPORTED`/`STATE_REVERSAL_SUPPORTED`/`STATE_NULL`/`STATE_UNDERPOWERED`
per the five frozen minimums (§20). Causal diagnostic only, not a trading
rule.

## Duplicate/alias audit

Per session: exact duplicates and within-one-tick clusters among the 8
level values; % sessions with aliases, % touches in alias clusters, most
common alias pairs, and whether any supported finding consists only of
duplicated physical prices. Formula aliases never counted as independent
confirmation.
