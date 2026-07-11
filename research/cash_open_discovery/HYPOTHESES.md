# HYPOTHESES.md

## Facts (established, not assumed)

- Bar timestamp = bar OPEN (Databento ohlcv-1m convention); bar at et_minute
  m covers [m, m+1) ET and completes/closes at m+1.
- 09:30 ET bar exists in the base series (et_minute == 570); its `open`
  field is the verified cash-open price O.
- America/New_York conversion (used to derive et_minute) already resolves
  DST automatically per bar; no separate DST branch is required — 09:30 ET
  is always et_minute 570 regardless of the UTC offset that day.
- Development partition = 2018-01-03 to 2022-12-30 (1291 sessions/instrument
  ES and NQ), inherited unchanged from generation 1's DATA_CONTRACT.md.
  Validation (2023-2024) and holdout (2025-> end) remain untouched.
- Generation 1's exploratory cash-open observation used a bar-shock
  z-score trigger unrelated to this generation's opening-scale definition;
  it is background motivation only, not a preregistered prior for this test.

## Assumptions (declared, not yet demonstrated)

- A1: A robust same-elapsed-minute displacement scale, estimated from prior
  RTH sessions only, is a reasonable causal proxy for "statistically
  abnormal" opening displacement (mirrors the minute-of-day robust scale
  already used and tested in generation 1).
- A2: A 60-minute research window per side (outer-excursion search 09:30-
  10:30; reclaim search bounded to 60 minutes after the outer excursion) is
  a defensible bound for an "opening episode" without being tuned to the
  data. Declared before any table is viewed (see SPEC_DISCOVERY.md).
- A3: Comparing reclaimed vs. held excursions at common post-excursion
  checkpoints (5/10/15 minutes) is a fair matched-comparison design; held
  episodes are direction-aligned to the hypothetical reclaim direction
  (lower excursion -> long convention; upper excursion -> short convention)
  purely to make the comparison apples-to-apples, not because a held
  episode has "chosen" a direction.
- A4: No verified macro/news calendar is available in this environment;
  ordinary-day vs. news-day stratification is out of scope and logged as a
  limitation, not approximated.

## Falsifiable hypotheses

### Lower failed excursion -> LONG-direction outcome
- H-L1: After a lower excursion beyond O - A*S reclaims to at or above
  O - B*S (decision at reclaim-bar close, outcome from next bar open),
  forward returns are positive (upward) on average, beyond what a held
  (non-reclaimed) excursion of matched magnitude A shows at the same
  post-excursion checkpoint.
- H-L2: Faster reclaim (shorter minutes-to-reclaim) is associated with
  stronger subsequent upward movement (monotone or stable, not one cell).
- H-L3: Full reclaim (B=0) shows a stronger/different effect than 50%
  reclaim (B=0.5A).

### Upper failed excursion -> SHORT-direction outcome
- H-U1/H-U2/H-U3: mirror images of H-L1-3 for the upper side.

### Cross-cutting
- H-X1: The reclaim effect is not simply "large opening moves reverse" —
  held excursions of the same A must NOT show the same forward effect as
  reclaimed ones, or the reclaim event carries no information beyond
  magnitude.
- H-X2: Overnight positioning/path proxies and prior-session final-10-minute
  variables may predict which side is reached first and whether the
  excursion reclaims, tested as explanatory (not required-filter) variables.

## Null / falsifiers preregistered

- N1: Held vs. 50%-reclaimed vs. fully-reclaimed excursions (matched on A,
  direction, checkpoint) show forward outcomes with overlapping session-
  block bootstrap CIs -> reclaim adds no information; REJECT/REVISE.
- N2: The effect (if any) is driven by a small number of sessions/years
  (concentration diagnostic) -> WEAK/UNDERPOWERED, not PHENOMENON SUPPORTED.
- N3: A later-session placebo using identical excursion/reclaim logic shows
  a comparably sized effect -> the phenomenon is not specific to the cash
  open; REVISE.
