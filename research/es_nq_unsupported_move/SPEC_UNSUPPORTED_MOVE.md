# SPEC_UNSUPPORTED_MOVE.md — formal specification

Single source of truth for formulas/thresholds used by `src/`. Where this
spec and code disagree, this spec wins and the code has a bug.

## 1. Synchronization

Exact `ts_event` inner join of ES/NQ 1-minute bars; no forward fill, no
synthetic bars. Session legs reused unchanged from
`research/ema21_session_horizon/`: `ASIA` (18:00-02:59 ET), `LONDON`
(03:00-08:29 ET), `NEW_YORK` (09:30-15:59 ET), `EXCLUDED` (08:30-09:29,
16:00-17:59 ET). A "leg instance" = one `(session_date, leg)` pair,
`leg != EXCLUDED`, with a 1-indexed local rank over its synchronized
bars in `ts_event` order.

## 2. Five-minute synchronized return

Per instrument, per leg instance, local rank `t >= 5`:
`return_t = Close_t / Close_{t-5} - 1`. The "event window" is bars
`t-4..t`; the "window endpoint" is bar `t`; `et_minute` of the window
endpoint is the clock slot used for normalization.

## 3. Causal normalization (per instrument, independently)

For clock slot `(leg, et_minute)`, using the 60 chronologically prior
*valid* leg instances at that slot (current excluded, no shorter-history
fallback): `RET_MEAN`, `RET_STD` (sample std, ddof=1), `RET_Z =
(return_t - RET_MEAN) / RET_STD`. Requires `RET_STD > 0`.

## 4. Causal ES-NQ regression

Frozen orientation: `NQ_return = alpha + beta * ES_return + residual`
(`RESEARCH_CHARTER.md` A4). For clock slot `(leg, et_minute)`, using the
same trailing-60-valid-prior-occurrences window (current excluded):
`beta = Cov(ES_return, NQ_return) / Var(ES_return)` (both computed over
the 60 prior occurrences), `alpha = mean(NQ_return) - beta *
mean(ES_return)`. Predicted `NQ_return_hat_t = alpha + beta *
ES_return_t` (current `ES_return_t` used only as the regressor input,
never as part of alpha/beta estimation). `residual_t = NQ_return_t -
NQ_return_hat_t`. `RESIDUAL_STD` = sample std (ddof=1) of the
*historical* residual series at that same clock slot over its own
trailing 60 prior occurrences (each historical residual itself computed
from that occurrence's own causal alpha/beta — never from `residual_t`
itself). `RESIDUAL_Z = residual_t / RESIDUAL_STD`. Requires `Var(ES_return)
> 0` and `RESIDUAL_STD > 0`.

## 5. Leader, laggard, primary event/control definitions

Leader = instrument with larger `|RET_Z|`; laggard = the other. Exact
tie (`|ES RET_Z| == |NQ RET_Z|`) -> `LEADER_TIE_UNRESOLVED`, excluded
from treatment/control assignment, retained in counts.

`EXTREME_UNSUPPORTED_MOVE`: `|leader RET_Z| >= 2.0` AND `|laggard RET_Z|
<= 0.75` AND `|RESIDUAL_Z| >= 2.0`.

`MODERATE_UNSUPPORTED_MOVE`: `1.0 <= |leader RET_Z| < 2.0` AND
`|laggard RET_Z| <= 0.75` AND `1.0 <= |RESIDUAL_Z| < 2.0`.

Thresholds are frozen before any development-partition event count is
viewed and never changed afterward. A window endpoint satisfying neither
definition is retained in the leg instance's scan (see §6) but is not a
candidate event.

## 6. Rearming and non-overlap (frozen, `RESEARCH_CHARTER.md` A5)

Per leg instance, scan window endpoints (local rank `t=5,6,7,...`) in
order. A window endpoint is a *candidate* if `EXTREME_UNSUPPORTED_MOVE`
or `MODERATE_UNSUPPORTED_MOVE` holds (leader-tie window endpoints are
never candidates). The first candidate found becomes the recorded event;
the leg instance is consumed through `min(t+15, leg_instance_end)`;
scanning resumes at the first window endpoint strictly after the
consumed range (i.e. next candidate search starts at local rank
`min(t+15, leg_end)+1`). At most one event per armed dislocation; no
recorded event's `[t-4, t+15]` span overlaps another's. Treatment and
control events use this identical rule (no separate logic per class).

## 7. Primary outcome: causal residual path

Legal outcome bars: `T+1 .. T+H`, `T`'s own bars never re-enter the
regression or normalization. Horizons: 5, 10, 15, 30 minutes (15 =
primary). Frozen event-time `alpha`, `beta` (from §4, at the event
window endpoint `T`) are reused for the entire outcome window — never
refit. Cumulative price returns from the bar immediately preceding the
event window (`T-5`, the same causal base as `return_T`):
`ES_cum(h) = Close_ES(T+h)/Close_ES(T-5) - 1`,
`NQ_cum(h) = Close_NQ(T+h)/Close_NQ(T-5) - 1` for `h = 0..H` (`h=0` is
`T` itself, recovering the event return exactly). Causal residual path:
`RESIDUAL_PATH(h) = NQ_cum(h) - alpha - beta * ES_cum(h)`. By
construction `RESIDUAL_PATH(0) = residual_T = r0` exactly.

`r0 = RESIDUAL_PATH(0)`. Barriers (identical formula for positive and
negative `r0`, sign-preserving by construction, `SPEC_UNSUPPORTED_MOVE.md`
verbatim from the task): `closure_barrier = 0.50 * r0`,
`expansion_barrier = 1.50 * r0`. For `r0 > 0`: closure crossed when
`RESIDUAL_PATH(h) <= closure_barrier` (moving down toward/through it from
`r0`); expansion crossed when `RESIDUAL_PATH(h) >= expansion_barrier`.
For `r0 < 0`: closure crossed when `RESIDUAL_PATH(h) >= closure_barrier`;
expansion crossed when `RESIDUAL_PATH(h) <= expansion_barrier`. Scan
`h=1..H` bar by bar; first bar crossing only closure ->
`RESIDUAL_CLOSURE_FIRST`; only expansion -> `RESIDUAL_EXPANSION_FIRST`;
both in the same bar -> `SAME_BAR_AMBIGUOUS` (intrabar order never
inferred); neither by `h=H` -> `NEITHER_WITHIN_HORIZON`; horizon itself
incomplete (leg instance ends before `T+H`) -> `INCOMPLETE_HORIZON`
(checked before scanning; no partial-window fallback).

## 8. Resolution attribution (convergent events only, i.e. `RESIDUAL_CLOSURE_FIRST`)

At the closure bar `h*`, compute each instrument's own price return from
`T` (not `T-5`) to `T+h*`: `ES_move = Close_ES(T+h*)/Close_ES(T) - 1`,
`NQ_move = Close_NQ(T+h*)/Close_NQ(T) - 1`. Let `d_L = sign(leader's
event-window return_T)`, `leader_post`/`laggard_post` = the respective
instrument's `*_move` value. `LEADER_REVERSAL_AMOUNT = -d_L *
leader_post` (positive = leader gave back its move). `LAGGARD_CATCHUP_AMOUNT
= d_L * laggard_post` (positive = laggard moved toward the leader's
original direction). **Materiality threshold (frozen)**: an amount is
material iff `|amount| >= 0.25 * |r0|`. Mutually exclusive
classification: both material -> `JOINT_CONVERGENCE`; only
`LEADER_REVERSAL_AMOUNT` material -> `LEADER_REVERSAL`; only
`LAGGARD_CATCHUP_AMOUNT` material -> `LAGGARD_CATCHUP`; neither material
-> `PARTIAL_OR_MIXED`. Non-convergent events: `RESIDUAL_EXPANSION_FIRST`
-> `DIVERGENCE_EXPANDS`; `NEITHER_WITHIN_HORIZON` -> `DIVERGENCE_PERSISTS`.
`SAME_BAR_AMBIGUOUS`/`INCOMPLETE_HORIZON` events receive no attribution
category (retained separately, never forced into one of the six).
Formulas use only `leader`/`laggard` roles and the sign `d_L`, never
hardcoding ES or NQ, and are unchanged for positive/negative `r0` — both
required symmetries hold by construction.

## 9. Session-leadership diagnostic (secondary, causal, frozen)

For clock slot `(leg, et_minute)`, using the trailing 60 valid prior leg
instances (current excluded): `HISTORICAL_ES_LEAD_FRACTION` = fraction
of those 60 in which `|ES RET_Z| > |NQ RET_Z|` (ties excluded from the
denominator). `HISTORICALLY_TYPICAL_LEADER` = ES if fraction `> 0.55`,
NQ if fraction `< 0.45`, else `NO_STABLE_LEADER`. Per event: `TYPICAL`
(observed leader == historically typical leader), `ATYPICAL` (observed
leader is the other instrument and a stable historical leader exists),
or `NO_STABLE_HISTORICAL_LEADER`.

## 10. Primary comparison

`EXTREME_UNSUPPORTED_MOVE` vs. `MODERATE_UNSUPPORTED_MOVE`. Primary
metric: residual-closure-first rate among resolved non-ambiguous events
(`RESIDUAL_CLOSURE_FIRST` + `RESIDUAL_EXPANSION_FIRST`, i.e. excluding
`SAME_BAR_AMBIGUOUS`, `NEITHER_WITHIN_HORIZON`, `INCOMPLETE_HORIZON`,
and `LEADER_TIE_UNRESOLVED`). Matching/stratification variables: session
(leg), leader instrument, leader direction, clock-hour stratum (ET hour
of the window endpoint), leader-z band (`[2.0,2.5), [2.5,3.0), [3.0,inf)`
for extreme; `[1.0,1.33),[1.33,1.67),[1.67,2.0)` for moderate — bands are
compared only *within* the matched-stratum permutation, not pooled
across treatment/control by value), residual-z band (same two-tier band
scheme). A matched stratum = one combination of
`(leg, leader_instrument, leader_direction, clock_hour)` containing at
least one `EXTREME` and at least one `MODERATE` event; the
permutation shuffles extreme/moderate labels only within such strata
(leader-z/residual-z bands are recorded per event and reported, not used
as an additional permutation-splitting key, to keep strata large enough
to be non-degenerate — `DECISIONS.md` #6). Stratified permutation:
>=10,000 permutations, deterministic seed `20260713` (same seed value
used in the prior sweep-and-failure generation, reused here as this
repository's frozen permutation seed constant). BH at 5% applied across
the primary family = `session(leg) x leader_instrument x
leader_direction` combinations that have at least one matched stratum.

## 11. Interpretation gate (verbatim from task, restated for the report)

A coherent development candidate requires all of: extreme moves closing
more often than matched moderate controls; a material (>=5pp) effect;
BH-corrected significance; adequate matched controls; coherent adjacent-
horizon (5/10/30-minute) behavior; reasonable year stability (>=4/5
years agreeing in sign); replication across more than one closely
related primary cell; and interpretable resolution attribution
(specifically which of leader-reversal/laggard-catchup/joint drives any
closure difference). None of the following may be called a mechanism:
unconditional residual mean reversion; high raw convergence without the
moderate control; one isolated significant cell; sparse matched
controls; a same/contemporaneous-data regression confound; convergence
without attribution; raw significance without multiplicity survival;
path convergence framed as trading profitability. If extreme and
moderate moves converge at similar rates, the extremity hypothesis is
null regardless of how common unconditional convergence is.

## 12. Prohibited (unchanged pattern)

No profitability, entries, exits, sizing, prop-account simulation, no
2023+ access, no threshold changes after seeing event counts, no
competing leadership-diagnostic definitions after seeing results, no
forward-filled or synthetic bars.
