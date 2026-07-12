# SPEC_VALIDATION.md — NQ Upper-Excursion Continuation Validation

Final frozen methodology, transcribed from Dylan's specification.
Implemented exactly as given — no redesign, no additional cells, no
threshold changes. Branch `validation/nq-upper-excursion-continuation`,
base `research/nq-excursion-level-timing` @ `dba98fe`.

## Frozen level construction (unchanged from generation 10)

`U_i = High_0930,i − Open_0930,i`, `D_i = Open_0930,i − Low_0930,i`
(single 09:30 candle of prior valid session `i` only). Exactly the
previous 10 valid sessions, arithmetic mean only (no median/EMA), sample
SD `ddof=1`, no partial-window fallback. `UPPER_k = O_0930 + MEAN_U_10 +
k·SD_U_10`, `LOWER_k = O_0930 − MEAN_D_10 − k·SD_D_10`, `k∈{0,1,2,3}`.

## Primary validation hypothesis (one test, no multiplicity correction)

NQ `UPPER_k0`, activation `A=2` (legal first touch on the 09:30 or 09:31
candle only), horizon `H=2` completed post-touch bars, barrier `b=1.0·
SD_U_10`. Outcomes begin strictly at `T+1`; touch bar H/L/C never enter a
post-touch outcome. Continuation barrier `level_value + 1.0·SD_U_10`;
reversal barrier `level_value − 1.0·SD_U_10`. Outcomes:
`CONTINUATION_FIRST/REVERSAL_FIRST/SAME_BAR_TIE/NEITHER`, tie whenever
both reached in the same bar (never inferred). `SAME_BAR_TIE`/`NEITHER`
excluded from the directional test but their rates reported. Primary
statistic: `continuation_first_rate − reversal_first_rate`; **one-sided**
exact binomial (`H_a: continuation > reversal`), since the frozen
directional hypothesis is specifically that direction.

## Primary success criteria — ALL required for `VALIDATED`

1. ≥100 total touches within `A=2`.
2. ≥50 non-tied barrier-first outcomes.
3. `continuation_first_rate − reversal_first_rate ≥ +5.0pp`.
4. one-sided exact binomial `p < 0.05`.
5. median `SIGNED_CLOSE_SD_H` at `H=2` is positive.
6. same directional sign in ≥3 of {2023, 2024, 2025, partial 2026}.
7. no single year contributes >50% of all validation touches.

Classification (assigned once, never reinterpreted after viewing data):
`VALIDATED`, `DIRECTIONALLY_POSITIVE_BUT_INCONCLUSIVE`,
`FAILED_VALIDATION`, `UNDERPOWERED`, `IMPLEMENTATION_INVALID`.

## Frozen supporting candidates (Holm-corrected together; cannot rescue a failed primary)

- Supporting 1: NQ `UPPER_k1`, `A=2`, `H=1`, `b=1.0`.
- Supporting 2: NQ `UPPER_k2`, `A=5`, `H=2`, `b=1.0`.

Same continuation/reversal definitions and the same seven success
criteria, evaluated after Holm-adjusting the two supporting p-values
together (family of 2). They may support the primary interpretation
narratively; they may never override a `FAILED_VALIDATION`/
`UNDERPOWERED` primary result.

## Frozen negative controls (reported only, never used to alter the primary hypothesis)

- NQ lower mirrors: `LOWER_k0` (`A=2,H=2`), `LOWER_k1` (`A=2,H=1`),
  `LOWER_k2` (`A=5,H=2`).
- ES replication: `UPPER_k0` (`A=2,H=2`), `UPPER_k1` (`A=2,H=1`),
  `UPPER_k2` (`A=5,H=2`).
- NQ `UPPER_k3`, `A=5`, `H=2` — frozen null-extension check.

## Same-bar morphology (supporting evidence only, not a substitute for post-touch validation)

Primary diagnostic: NQ `UPPER_k0`, `A=2`. Upper: `Close_T<level`→
reversal proxy; `Close_T>level`→blast-through proxy; `==`→neutral.
Report non-neutral count, blast-through/reversal rates and difference,
exact binomial p, yearly rates. Permanent caveat: 1-minute OHLCV does not
establish true intrabar order.

## Year-by-year reporting

2023, 2024, 2025, partial 2026 reported separately for every frozen
candidate/control (eligible sessions, touches, non-tied outcomes,
cont/rev rates and diff, median signed close in native-SD units,
same-bar rates), plus pooled effect, mean/SD of annual effects, count of
years with the pooled sign, max/min annual effect, one-year->50%-of-
touches flag. No separate confirmatory year tests.

## Rolling direction-state replication (frozen from generation 10, secondary)

Touches within 30 minutes of 09:30, complete 30-minute `b=1.0` result,
ties/neither excluded. Prior state from the immediately preceding 10
such events (strictly earlier sessions): `CONTINUATION_STATE` (≥6/10
continuation-first), `REVERSAL_STATE` (≥6/10 reversal-first),
`MIXED_STATE` otherwise, `STATE_UNAVAILABLE` if <10 prior. Current
event's outcome compared by prior state: counts, rates, difference,
Fisher exact p, year-by-year. Supported only if ≥20 observations in each
directional state, |diff|≥10pp, Fisher `p<0.05`, sign consistent in ≥3
validation partitions. Never used to filter or rescue the primary
candidate. This is a causal diagnostic, not a trading rule.

## Prohibited (per Dylan's instruction, never computed or inspected)

Any other activation window, horizon, barrier, 09:30 lookback, median/EMA
center, volatility/trend/weekday/month/economic-release filter,
prior-close/overnight-predictor/taxonomy feature, feature combination, or
profitability/trading-rule outcome. No interactive 2023+ inspection
before the preregistration commit (observed: none occurred — only a
date-range check was performed, no outcome value).
