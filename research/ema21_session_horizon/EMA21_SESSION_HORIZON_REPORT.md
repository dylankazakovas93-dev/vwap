# EMA21 Session-and-Horizon Decomposition Report

Generation: EMA21 session-and-horizon decomposition (base `7853a9c`)
Branch: `research/ema21-session-horizon-surface`
Partition: development only, ES + NQ, 2018-01-03 -> 2022-12-30. 2023
onward was never read.

Descriptive level-interaction study, `FULL_SESSION_EMA21` only. No
entries, exits, sizing, TP/SL, or profitability claim anywhere.

## Event volume

| Instrument | Session | Armed excursions | Touch events |
|---|---|---|---|
| ES | ASIA | 9,029 | 8,390 |
| ES | LONDON | 5,743 | 5,175 |
| ES | NEW_YORK | 6,355 | 5,881 |
| NQ | ASIA | 8,925 | 8,273 |
| NQ | LONDON | 5,738 | 5,128 |
| NQ | NEW_YORK | 6,205 | 5,703 |

Total: 41,995 armed excursions, 38,550 touch events, 0 ATR_INVALID
exclusions. Same-bar morphology pooled: 19,669 `SAME_BAR_REJECTION_PROXY`
vs. 18,881 `SAME_BAR_BREAKTHROUGH_PROXY` (51.0% vs. 49.0%) — same-bar
rejection rate is ~50-51% in every session (Asia 50.3%, London 50.9%, New
York 50.3%), i.e. materially flat.

## Primary result: 1.0-ATR rejection-first vs. breakthrough-first, all 9 horizons

432 primary cells (`instrument x session x touch_time_bucket x
approach_side x horizon`; `reports/tables/primary_result_table.csv`).
Touch-event counts per cell ranged 70-3,587. 9/432 cells (2.1%) were
`UNDERPOWERED` (below 50 touches or 20 non-tied first-hit outcomes); the
remaining 423 were tested. **0/432 cells directionally classified —
all 423 tested cells are `MIXED_OR_NULL`.**

153/432 cells (35%) had |rejection-first minus breakthrough-first| >=
5pp — larger and more frequent than the base generation's coarse RTH
study, because these cells are far smaller (session x bucket x horizon
slices touch events much more finely, which mechanically inflates both
noise and apparent effect size). Only 2/432 cells reached BH-adjusted
q < 0.05 within their `instrument x session` family, and neither survived
the remaining joint conditions:

- ES `NEW_YORK` `SESSION_120_PLUS` `FROM_BELOW` H=2: rejection-first +6.2pp
  (n=1,976, q=0.010) — but median signed close is *negative* (opposite
  sign), so it fails the sign-agreement condition.
- NQ `ASIA` `SESSION_60_TO_120` `FROM_ABOVE` H=1: breakthrough-first
  +11.4pp (n=483, q=0.006) — but only 3-of-5 years agree in sign, failing
  the year-stability condition.

## Session-level mechanism classification

12 `instrument x session x approach_side` combinations
(`reports/tables/session_mechanism_table.csv`). **All 12 are
`NO_COHERENT_SESSION_MECHANISM`.** With zero cells directionally
classified in the first place, no session could accumulate the required
adjacent-horizon / adjacent-touch-time-bucket / 4-of-5-year support.

## Strongest individual cells (isolated, not session-level findings)

- **Strongest rejection lean**: ES `NEW_YORK` `SESSION_0_TO_30`
  `FROM_BELOW`, H=6: rejection-first +22.1pp (n=77, q=0.43, year
  agreement 3/5) — a small-sample, non-significant, isolated cell.
- **Strongest breakthrough lean**: ES `LONDON` `SESSION_0_TO_30`
  `FROM_ABOVE`, H=3-4: breakthrough-first -22.4pp (n=107, q=0.20, year
  agreement 4/5) — same caveats; not adjacent-horizon-corroborated at a
  significant level.
- **Strongest/cleanest nulls**: same-bar rejection rates within 0.3pp of
  50/50 in Asia and New York pooled across all buckets; e.g. NQ
  `NEW_YORK` `ALL_SESSION` `FROM_ABOVE` H=6 sits within a couple of
  points of 50/50 with q>0.9 (full detail in
  `reports/tables/full_exploratory_results.csv`).

## Approach-side differences

No qualitative asymmetry between `FROM_ABOVE` and `FROM_BELOW` beyond
sampling noise — both sides produce the same pattern of small,
inconsistent, mostly sub-significant tilts across sessions.

## Horizon findings

Mean effect size does not grow or shrink monotonically with horizon in
any session; the two nominally-significant cells above sit at short
(H=1) and short-to-medium (H=2) horizons respectively, but neither
generalizes to adjacent horizons in the same touch-time bucket, so there
is no coherent "effect appears/disappears at horizon X" pattern to
report.

## First 30 minutes vs. later

Mean effect by touch-time bucket (pooled, H=6 shown as representative):
`SESSION_0_TO_30` -3.4pp, `SESSION_30_TO_60` +1.9pp, `SESSION_60_TO_120`
-2.8pp, `SESSION_120_PLUS` +0.9pp — no consistent concentration in the
first 30 minutes of any session; if anything the first-30-minute bucket
is noisier (smallest samples) rather than systematically stronger.

## RTH vs. full-session context

This generation uses `FULL_SESSION_EMA21` exclusively. New York's mean
effect here (+0.7pp at H=6, pooled) is consistent with the base
generation's `FULL_SESSION_EMA` finding for New York RTH (small,
sub-5pp, non-significant tilt) — the two generations agree qualitatively
even though this one further subdivides New York by touch-time bucket
and adds Asia/London.

## Year stability

Both nominally-significant cells above failed on either sign-agreement
or year-agreement, and inspection of `reports/tables/year_stability.csv`
shows no systematic 2020-only concentration or single-year dominance
driving the small pooled tilts — the noise is broadly spread across
2018-2022, consistent with sampling variation rather than a real,
time-varying mechanism.

## ES vs. NQ agreement

Comparing matched `session x touch_time_bucket x approach_side` cells at
H=6, ES and NQ agree on the sign of the rejection-minus-breakthrough
effect in 75% of cells (18/24) — similar to the base generation's 73%,
consistent with a shared, small, non-actionable tilt rather than two
independently strong signals.

## Final report questions

1. **Does EMA21 behave differently in Asia, London and New York?** Not
   materially — same-bar rejection rates sit within a point of 50% in all
   three sessions, and no session reaches a directional mechanism
   classification; pooled mean effects differ slightly (London mean
   slightly negative, New York/Asia near zero) but none of this survives
   the joint classification bar.
2. **Does it act as rejection or breakthrough after approach from
   above?** Neither, consistently — small, sign-inconsistent tilts only.
3. **Does it act as rejection or breakthrough after approach from
   below?** Same answer as above; no asymmetry between sides.
4. **Is any effect confined to the first 30 minutes of a session?** No —
   `SESSION_0_TO_30` is not systematically stronger than the other
   buckets; it is smaller-sample and noisier, not more effect-laden.
5. **At what post-touch horizons does any effect appear or disappear?**
   No coherent appearance/disappearance pattern; the only two
   nominally-significant cells sit at different, non-adjacent-corroborated
   horizons and fail other classification conditions.
6. **Is any result stable across 2018-2022?** There is no classified
   effect to test for stability; the marginal cells that came close both
   failed the year-stability or sign-consistency condition directly.
7. **Does ES agree with NQ?** Loosely (75% same-sign at matched cells),
   consistent with shared noise/small tilt rather than strong agreement
   on a real effect.
8. **Is there any coherent session-specific candidate worth validating on
   2023+?** No — 0/432 primary cells directionally classified, 0/12
   session-level mechanisms found.

## Verdict

No supported Asia, London or New York EMA21 rejection or breakthrough
mechanism was found in ES/NQ five-minute OHLCV during 2018-2022.

No validation-partition (2023+) study follows. This matches the
preregistered fallback in `SPEC_SESSION_HORIZONS.md` §15 and is
consistent with, and further sharpens, the base generation's own null
finding for New York RTH under `FULL_SESSION_EMA`.
