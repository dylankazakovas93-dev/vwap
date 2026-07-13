# RESEARCH_CHARTER.md — ES-NQ unsupported move discovery

Branch: `research/es-nq-unsupported-move-discovery`, base commit
`201896d` (Generation 3: cash-open target atlas — engine, descriptive
analysis). Independent generation: no levels, taxonomy, or methodology
imported from any prior generation. Inherits only the audited ES/NQ
one-minute OHLCV data infrastructure (`data/processed/{es,nq}_front_1m.parquet`,
re-verified this generation) and general no-lookahead discipline. This
is the first generation in this repository to jointly analyze ES and NQ
as a paired cross-instrument system rather than as separate primary
series.

## Research classification

Descriptive, causally-normalized cross-instrument dislocation study. When
one instrument (the "leader") makes a large five-minute move that the
other (the "laggard") does not confirm, and that dislocation is not
explained by the causally estimated ES-NQ relationship (a large
residual), does the dislocation resolve by leader reversal, laggard
catch-up, joint convergence, persistence, or further expansion — and is
this more true of *extreme* dislocations than of *moderate* ones? No
profitability, entries, exits, sizing, or prop-account simulation
anywhere. No hypothesis rescue: thresholds, matching strata, the
regression orientation, and the rearming rule are all frozen below,
before any development-partition result is viewed, and are never
re-tuned afterward.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet`: re-hashed raw archives and
  re-ran `research/vwap_shock/src/data_build.py` unmodified this
  generation; counters matched root `DATA_CONTRACT.md` exactly (ES:
  2,968,335 front-month bars / 2,179 sessions; NQ: 2,963,298 bars /
  2,178 sessions).
- Development partition: 2018-01-03 -> 2022-12-30 (root convention).
  Validation (2023 onward) is never read by any code in this generation.
- Session leg definitions (Asia 18:00-02:59 ET, London 03:00-08:29 ET,
  New York 09:30-15:59 ET, excluded 08:30-09:29 and 16:00-17:59 ET) are
  reused unchanged from the audited convention already used in
  `research/ema21_session_horizon/` — "use the repository's audited
  session definitions" is satisfied by reusing that existing convention
  rather than inventing a new one.

## Assumptions

- A1: **Synchronization** — ES and NQ 1-minute bars are joined on exact
  `ts_event` equality (inner join); any minute where either instrument's
  bar is absent is excluded from *both* instruments for that minute, no
  forward fill, no synthetic bars (per explicit instruction).
- A2: **Five-minute return** — for a synchronized-bar sequence with
  window endpoint at local position `t` (within one `(session_date,
  leg)` instance), the five-minute return is `Close_t / Close_{t-5} - 1`
  (close-to-close change over exactly the 5 one-minute bars `t-4..t`,
  using the bar immediately preceding the window, `t-5`, as the causal
  base price) — the plain, standard definition of a 5-minute return
  computed from completed 1-minute bars, requiring position `t >= 5`
  within the leg instance.
- A3: **"Previous 60 paired valid sessions"** at an exact clock slot
  (`(leg, et_minute)` pair, where `et_minute` is the *window endpoint*
  bar's ET minute) means: the 60 chronologically most recent leg
  instances, strictly before the current one, in which a synchronized
  return was computable at that same `et_minute` (i.e. both instruments'
  bars `t-5..t` were all present in the synchronization join for that
  leg instance). No pooling across different `et_minute` clock slots, no
  pooling across legs, no shorter-history fallback — a clock slot with
  fewer than 60 prior valid occurrences produces no normalized/regression
  output for the current occurrence (excluded, not imputed).
- A4: **Regression orientation** — frozen as `NQ_return = alpha + beta *
  ES_return + residual`, estimated by ordinary least squares over the
  trailing 60 valid prior sessions at the same `(leg, et_minute)` slot
  (`DECISIONS.md` #2). This orientation is fixed regardless of which
  instrument turns out to be the leader in any given event — it is not
  re-oriented per event, which is what makes the residual comparable
  across ES-led and NQ-led events under one consistent definition.
- A5: **Armed dislocation / rearming** — since no explicit bar-count
  arming rule is specified for this generation (unlike the single-
  instrument level-touch generations), the frozen rule is: scan each
  `(session_date, leg)` instance's window endpoints in chronological
  order; a window endpoint is a *candidate* if it satisfies either the
  `EXTREME_UNSUPPORTED_MOVE` or `MODERATE_UNSUPPORTED_MOVE` definition
  (`SPEC_UNSUPPORTED_MOVE.md` §5); the first candidate found becomes the
  recorded event for that armed dislocation; the leg instance is then
  "consumed" through `min(t+15, leg_end)` (the primary outcome horizon,
  or the leg's own end if shorter); scanning resumes at the first window
  endpoint strictly after the consumed range. This guarantees "one event
  per armed dislocation," "no overlapping event or outcome windows," and
  identical chronology/overlap handling for treatment and control events
  (`DECISIONS.md` #3).
- A6: Session-leadership diagnostic metric (frozen, per
  `SPEC_UNSUPPORTED_MOVE.md` §9): for each `(leg, et_minute)` slot, the
  fraction of the trailing 60 valid prior sessions in which ES had the
  larger absolute return z-score (vs. NQ) — a single, causal, frozen-at-
  event-time metric; no competing definition is introduced after seeing
  results.

## Falsifiers

Per `SPEC_UNSUPPORTED_MOVE.md` §"Interpretation," a coherent development
candidate requires *all* of: extreme moves closing more often than
matched moderate controls; a material percentage-point effect; BH-
corrected significance; adequate matched controls; coherent adjacent-
horizon behavior; reasonable year stability; replication across more
than one closely related primary cell; and interpretable resolution
attribution (leader-reversal vs. laggard-catch-up vs. joint, not an
undifferentiated "convergence" label). Unconditional mean reversion,
high raw convergence without the moderate-divergence control, one
isolated significant cell, sparse matched controls, a same/contemporaneous-
data regression confound, or raw significance without multiplicity
survival are explicitly disqualified from being called a mechanism. If
extreme and moderate moves converge at similar rates, the extremity
hypothesis is null even if unconditional convergence is common.
