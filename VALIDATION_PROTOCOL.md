# VALIDATION_PROTOCOL.md

## Partitions

See DATA_CONTRACT.md. Development 2018-2022, validation 2023-2024, final
untouched holdout 2025-01 -> data end. Stage 2 code reads the development
partition only; the loader asserts this. Holdout rows are never loaded by
analysis code until a Stage 6 unlock is recorded in DECISIONS.md with
Dylan's explicit authorization.

## Dependence handling (Stage 2)

Events cluster in time. All Stage 2 confidence intervals use a session-block
bootstrap: resample session dates with replacement (500 draws, seed
20260710) and recompute the statistic from all events in the drawn sessions.
No IID t-tests are used as primary evidence.

## Placebo / matched null

For each event, candidate placebo bars are development-partition non-event
bars (|z_mod| < 1.5) in the same session segment, ET minute within ±15, and
the same ATR30 decile (deciles fit on development data causally by trailing
expanding quantiles). One placebo sampled per event without replacement
where possible, fixed seed. Placebos get identical forward measurement with
direction assigned by the sign of their own bar return (and, as a second
null, random ±1 with fixed seed).

## Multiplicity

Every executed analysis configuration is a row in RUN_REGISTRY.csv (hard cap
150 for Stages 2-4; failures count). Stage 2 conclusions require the same-
signed effect in BOTH instruments and at both z thresholds — cross-instrument
consistency is the primary guard against selection within this stage.
Formal DSR/PBO/CPCV apply at Stages 4-5 (not authorized yet); the label
horizon for purging there is 180 minutes (max forward window) plus a
1-session embargo.

## Stage gates

- Stage 0 PASS: data audit clean or fully explained; partitions reserved.
- Stage 1 PASS: SPEC_LOCKED.md + this file committed before development
  results viewed.
- Stage 2 PASS to entry-freeze proposal: preregistered "signal exists"
  criterion in SPEC_LOCKED.md met; otherwise REVISE / REJECT / UNDERPOWERED
  verdict with evidence.
