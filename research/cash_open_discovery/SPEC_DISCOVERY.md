# SPEC_DISCOVERY.md — locked before any development-partition result viewed

Discovery-stage preregistration (no strategy, no TP/SL, no MAE/MFE, no
validation/holdout access). Amendments require a DECISIONS.md entry and a
new research generation for anything material discovered after viewing
results.

## 1. Opening reference and elapsed-minute grid

`O` = `open` of the bar with `et_minute == 570` (09:30:00-09:31:00 ET),
per instrument per session. Elapsed minute `tau = et_minute - 570`,
`tau = 0, 1, 2, ...`. Bar `tau` covers ET time `[9:30+tau, 9:31+tau)`.

## 2. Opening-displacement scale S(tau) — primary

For each session and each `tau` in `[0, 90]`, define the historical
displacement `d(tau, session) = |close(tau, session) - O(session)|`
(close of the bar at elapsed minute `tau` relative to that session's own
open). For a given session `s` and elapsed minute `tau`:

`S(tau, s) = 1.4826 * median( d(tau, s') for s' in the trailing 60 RTH
sessions strictly before s )`, minimum 20 prior sessions with a valid
`d(tau, ·)` observation, else `S` is undefined (episode search skipped for
that tau on that session). This mirrors generation 1's minute-of-day robust
baseline (same multiplier, same trailing-60/min-20 convention), applied to
open-referenced displacement instead of bar-to-bar shock. Current/future
sessions are never used in their own scale.

## 3. Secondary robustness scales (reported, not selected on)

- Pre-open ATR: mean true range over the 30 completed RTH-eligible bars
  immediately before 09:30 in prior sessions is not applicable pre-open;
  instead use ATR30 computed on the prior session's last 30 RTH bars
  (14:31-16:00 ET), frozen and carried into the current session as the
  "pre-open ATR" context variable.
- Trailing realised volatility available by 09:29: stdev of 1-minute
  close-to-close returns over the final 60 minutes of Globex trading before
  09:30 (i.e., et_minute in [510, 569]), current session, fully causal.
- Fixed point/tick displacement: descriptive only (ES 1.0pt=4 ticks, NQ
  1.0pt=4 ticks reported in raw points), never used to trigger an episode.

These are recorded per episode and used only for descriptive robustness
comparison (Sec. 8), never to redefine S if the primary scale is "too
common" or "underpowered" — that outcome is reported as a finding, not
patched by swapping scales.

## 4. Outer excursion (STATE 1)

For threshold multiple `A`, per (instrument, session, A): scan bars
`tau = 0 .. 60` in order. A bar qualifies as an outer excursion if its
`high >= O + A*S(tau)` (upper) or `low <= O - A*S(tau)` (lower), using
`S(tau, s)` valid at that tau (episode skipped if undefined for all tau in
window). The FIRST qualifying bar (earliest tau) freezes the episode:
`outer_direction` (upper/lower), `outer_time`, `outer_price` (the exact O+-
A*S level, since "reaches or closes beyond" is checked via bar H/L, which is
knowable only as of that bar's close — detection granularity is one bar),
`minutes_to_outer = tau`. If the SAME bar's high and low both qualify
(upper AND lower breached in one bar), the episode is marked
`AMBIGUOUS_DIRECTION` and excluded from the primary directional analysis
(logged; intrabar order is not knowable from OHLCV). No second episode is
created after this one resolves (one primary episode per instrument/session
per A, per spec).

Search window: `tau in [0, 60]` (09:30-10:30 ET). If no bar qualifies by
tau=60, the session has NO EPISODE for that A (recorded, not imputed).

## 5. Reclaim (STATE 2) and legal decision point (STATE 3)

Reclaim search begins at the bar AFTER the outer-excursion bar (never the
same bar — ordering inside one bar is unknowable) and runs for a maximum of
60 minutes past the outer-excursion bar or session end, whichever is first.
For lower excursions, reclaim level `B` is checked via bar CLOSE
`>= O - B*S(tau_outer)` (the scale is fixed at the outer bar's tau, not
recomputed per subsequent bar — the episode has one displacement scale).
For upper excursions: CLOSE `<= O + B*S(tau_outer)`. Two `B` values are
tested per episode: `B = 0.5*A` (50% reclaim) and `B = 0` (full reclaim to
O). The FIRST bar whose close satisfies the loosest (0.5A) condition sets
`reclaim_50_time`; the first bar whose close additionally satisfies the
`B=0` condition sets `reclaim_full_time` (full reclaim implies 50% reclaim
already occurred, since `O` is more extreme than `O -/+ 0.5*A*S`). If
neither is reached within the 60-minute window, the episode is `HELD` for
that B. `decision_time` = the reclaim bar's close (= next bar's open,
contiguous bars). `legal_outcome_start_time` = that same timestamp (the
open of the bar immediately following the reclaim bar). No same-minute
signal/outcome overlap.

## 6. Matched held/reclaimed comparison (checkpoints)

To compare "otherwise similar" held vs. reclaimed excursions fairly
(Question 1), status is additionally evaluated at 3 fixed checkpoints
`H in {5, 10, 15}` minutes after the outer-excursion bar: at each H, an
episode is classified `HELD` / `RECLAIMED_50` / `RECLAIMED_FULL` using
whichever reclaim (if any) occurred at or before `outer_time + H`. The
comparison origin for that checkpoint is: the actual reclaim bar's close if
reclaim occurred at or before H, otherwise the close of the bar at
`outer_time + H` (the "still held as of H" checkpoint). Forward outcomes
(Sec. 7) are then measured from the bar immediately after that origin,
direction-aligned to the reclaim-direction convention (lower excursion =
long convention, upper excursion = short convention) for ALL three groups —
held episodes are assigned the hypothetical direction they would need to
reclaim, purely so the comparison is apples-to-apples (Assumption A3,
HYPOTHESES.md). This is a discovery comparison, not a claim that held
episodes "have a direction."

## 7. Outcome measures (from legal_outcome_start_time, direction-aligned)

**Fixed-horizon returns**: `(close[origin + h] - open[origin]) * dir` at
h in {1,3,5,10,15,30} minutes, in points and in opening-scale units
(`/S(tau_outer)`); mean, median, decile, P(>0), day-block bootstrap CI
(500 resamples over session_date, seed 20260711). 60-minute horizon is
computed and reported only if it does not saturate the session (i.e., only
for episodes whose origin is at or before et_minute 960 / 16:00 ET).

**Symmetric first passage** from `origin+1` bar open: barriers
`+-f * M` where `M` = initial outer-excursion magnitude in points
(`|outer_price - O|`) and `f in {0.25, 0.50}`, plus `f=1.0` using
`S(tau_outer)` directly as a scale-based symmetric barrier family
(3 barrier families total, all symmetric — the asymmetric-barrier error
from generation 1 is not repeated). Positive barrier = reclaim direction.
Window 120 minutes or session end. Same-bar-both-barriers -> AMBIGUOUS,
counted against the positive outcome (conservative, matches generation 1).

**Structural outcomes** (causal, descriptive, not exits): time to opposite
opening threshold (`O -+ A*S`, other side); time to re-break of the
original excursion extreme; time to return inside the overnight range;
overnight high/low break-and-reclaim; time to reach/cross the frozen
09:29 VWAP (Sec. 9). All measured from `legal_outcome_start_time` forward,
capped at 120 minutes or session end.

## 8. Bounded discovery domains (exact, preregistered)

- Outer magnitude `A`: {0.5, 1.0, 1.5, 2.0} (opening-scale units).
- Reclaim level `B`: {0.5*A, 0} only (no additional fractions this stage).
- Deadlines: outer-excursion timing reported continuously + bins
  {0-5, 5-10, 10-15, >15 min}; reclaim-speed timing reported continuously +
  same 4 bins; matched-comparison checkpoints fixed at {5, 10, 15} min
  (Sec. 6) — this is NOT a Cartesian product of outer-deadline x
  reclaim-deadline; each dimension is examined one at a time or as the
  single nested checkpoint design in Sec. 6.
- Minimum reported cell: 100 episodes (opening episodes are far rarer than
  generation 1's whole-session shock events: ~1 candidate per session per A
  at most, vs. ~1291 dev sessions/instrument, so a 300-minimum as used in
  generation 1 would eliminate most cells; 100 is declared here, before
  results, and applied uniformly).
- If A=0.5 is too common (fires nearly every session) or A=2.0 is
  underpowered (too few sessions), that fact is reported, not patched by
  silently changing the domain.

## 9. Frozen overnight/session VWAP (secondary context, not a trigger)

`VWAP_0929` = cumulative volume-weighted `(H+L+C)/3` from the session's
Globex open (18:00 ET) through the last bar with `et_minute <= 569`
(09:29 ET), inclusive — frozen before 09:30, never updated intra-episode.
Used only as a descriptive distance/crossing variable (Sec. "VWAP role"),
never as an opening-episode trigger and never swept across multiple VWAP
variants in this generation.

## 10. Placebo

A later-session placebo applies the identical state machine (Sec. 4-6) to
a control anchor time of 13:00 ET (midday, away from cash open, cash
close, and the overnight/European session), using the same S(tau)
construction re-based at the control anchor, same A/B domain. This tests
whether the reclaim effect (if any) is specific to 09:30 or is a generic
excursion/reclaim artifact.

## 11. Search accounting

Every (instrument x A x B x checkpoint/outcome-family) combination executed
is one RUN_REGISTRY.csv row. Estimated ceiling: 2 instruments x 4 A x
(2 B x [fixed-horizon + symmetric-passage + structural] + 3 checkpoints x 3
status-groups) + overnight/prior-session explanatory tests + placebo ≈ 90-
120 rows; hard cap 150 for this generation, consistent with generation 1's
budget discipline. No cell is optimized or selected by profitability —
there is no profitability metric in this stage.
