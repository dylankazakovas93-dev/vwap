# SPEC_LEVELS.md — Cash-Open Level Library (Generation 7, Part 2A)

Revision 2 (final, incorporating two corrections to Revision 1). Branch
`research/cash-open-level-library`, base `research/cash-open-path-taxonomy`
@ `796ad3f`. **Level construction only. No touches, reactions, subsequent
returns, taxonomy-conditional outcomes, profitability, entries, or exits
anywhere in this generation.**

## Corrections applied in this revision

1. **Family 5 (prior-session ATR30 bands) removed.** It was an unapproved
   additional feature family beyond what was authorized; it is not
   implemented here and may be proposed as a separate generation later.
2. **Placebo scheme replaced.** Revision 1 proposed a cross-session
   shuffle (borrowing another real session's actual excursion/level
   value) — rejected as internally inconsistent, since it still smuggled
   in real structural information from a different session. Replaced with
   **generic synthetic controls**: a value drawn independently of any
   named structural price, matched only on instrument, session, side,
   horizon-exposure category, and normalized-distance bucket (Sec. 6).

## Families implemented

### Family 1 — rolling empirical 09:30-candle excursion levels

Reuses generation 6's `build_scale_tables` (`research/cash_open_taxonomy/
src/taxonomy.py`, imported by exact file path) verbatim — same causal
exact-60-valid-session trailing window, same `U_0930`/`D_0930` definitions,
no re-derivation. For session `s` with open `O(s)`:

- Multiplier levels: `O(s) + m * scale_U(s)` (upside) and
  `O(s) - m * scale_D(s)` (downside), `m ∈ {0.5, 1.0, 1.5, 2.0}` (the same
  ladder as generation 6, for continuity).
- Quantile levels: `scale_U`/`scale_D` are causal trailing MEDIANS, i.e.
  the `m=1.0` multiplier level is *structurally* the trailing p50 quantile
  level. To avoid re-deriving a second causal-quantile engine for this
  pass, the quantile family is represented by the **already-computed**
  p50-equivalent (`m=1.0`) plus the MAD-based level below; no additional
  independent-quantile computation is added on top of the median (see
  Decision on structural duplication, Sec. 5).
- MAD levels: `O(s) + k * scale_U_mad(s)` / `O(s) - k * scale_D_mad(s)`,
  `k ∈ {1.0, 1.5, 2.0}` (frozen MAD multipliers).
- U and D sides are always constructed separately (asymmetric scales),
  never symmetrized.
- Causal availability: identical to generation 6 — requires exactly 60
  valid prior sessions; sessions without a valid scale produce no family-1
  levels (missing, not imputed, not backfilled with an expanding window).

### Family 2 — frozen overnight-VWAP deviation levels

Overnight window for session `s`: all bars with `ts_event` strictly before
the timestamp of session `s`'s 09:30 bar, taken in chronological `ts_event`
order (not an `et_minute` range filter, since `et_minute` wraps at
midnight) and belonging to that same session's Globex overnight leg (i.e.
all bars already present in the base parquet with `session_date == s` and
`et_minute < 570`, which by construction of the processed data are exactly
the bars from the prior evening through 09:29 ET).

- `VWAP_on(s) = sum(Vol_i * p_i) / sum(Vol_i)`, `p_i = (H_i+L_i+C_i)/3`,
  over all overnight bars `i` of session `s`.
- `sigma_on(s) = sqrt(max(0, sum(Vol_i*p_i^2)/sum(Vol_i) - VWAP_on(s)^2))`.
- Valid only if the overnight bar count `>= 30`; otherwise missing.
- Levels: `VWAP_on(s) + j * sigma_on(s)`, `j ∈ {-2, -1, 0, +1, +2}`
  (`j=0` is the VWAP itself; negative/positive are downside/upside
  deviation bands).
- Causal availability: all overnight bars complete strictly before 09:30
  ET, so `VWAP_on(s)`/`sigma_on(s)` are known in full at 09:30 open — no
  same-session lookahead.

### Family 3 — prior-session structural levels

For session `s`, let `p = prior(s)` be the immediately preceding session
in the base data with a full regular-hours window (i.e. NOT an early
close — an early close is detected as `p`'s last RTH bar, `et_minute<=959`,
having `et_minute < 959`). If `p` is an early close, family 3 is missing
for `s` (no substitution, no skip-back to an earlier session).

- `prior_high(p)`, `prior_low(p)`, `prior_close(p)` — from `p`'s full RTH
  window (`et_minute` 570-959 inclusive).
- `prior_settlement_open(p)` — `p`'s own 09:30 open, retained for
  continuity/reference (not a new construction).
- Causal availability: `p`'s full session is complete well before `s`'s
  09:30 open by construction (`p < s`).

### Family 4 — overnight structural levels

Computed over the same overnight window as family 2 (chronological,
strictly pre-09:30 bars of session `s`), cross-referenced against family
2's `VWAP_on(s)`:

- `overnight_high(s)`, `overnight_low(s)` — max high / min low over the
  overnight window.
- Deviation of each from `VWAP_on(s)`: `overnight_high(s) - VWAP_on(s)`
  and `VWAP_on(s) - overnight_low(s)`, reported alongside the raw levels
  so overnight-range levels and VWAP-deviation levels can be compared on
  the same causal basis.
- Valid only when family 2 is valid (`>=30` overnight bars) for the VWAP
  cross-reference fields; `overnight_high`/`overnight_low` themselves only
  require >=1 overnight bar but are flagged separately if family 2 is
  invalid (so a level can be reported alone, without a false VWAP
  deviation).

### Family 5 — REMOVED

Prior-session ATR30 bands are explicitly out of scope for this generation
per Dylan's correction. Not implemented, not listed as a placeholder
formula — entirely absent from the library and its diagnostics.

### Family 6 — dynamic levels (listed only, not implemented)

Retained as a listed-only future family, unchanged from Revision 1:
running same-session VWAP-from-open, running same-session high/low. Not
computed, not tested, not counted in any diagnostic in this generation.
Earliest observable bar for a dynamic level is definitionally `tau=0`
(the 09:30 bar itself) but the level's own value only stabilizes as later
bars accrue — flagged as a design note only.

## Levels enumerated (families 1-4 only)

| family | level_id | side | requires |
|---|---|---|---|
| 1 | mult_U_0.5 / mult_U_1.0 / mult_U_1.5 / mult_U_2.0 | up | scale_U (60-session) |
| 1 | mult_D_0.5 / mult_D_1.0 / mult_D_1.5 / mult_D_2.0 | down | scale_D (60-session) |
| 1 | mad_U_1.0 / mad_U_1.5 / mad_U_2.0 | up | scale_U_mad |
| 1 | mad_D_1.0 / mad_D_1.5 / mad_D_2.0 | down | scale_D_mad |
| 2 | vwap_on_j-2 .. vwap_on_j+2 | both (j=0 neutral) | >=30 overnight bars |
| 3 | prior_high / prior_low / prior_close | up/down/neutral | non-early-close prior session |
| 4 | overnight_high / overnight_low | up/down | >=1 overnight bar |

`mult_U_1.0` and `mad`-family levels are NOT the same value (median vs.
MAD-scaled); the only structural duplicate in this library is
`mult_U_1.0`/`mult_D_1.0` being definitionally the trailing p50 quantile
level (Sec. 5) — there is no separately-computed `quantile_50` level
that would double-count it.

## Sec. 5 — deduplication / structural-duplicate policy

`scale_U`/`scale_D` are causal trailing MEDIANS by construction (Sec.
`taxonomy.py`), so the `m=1.0` multiplier level is structurally identical
to "the trailing p50 quantile level" — these are **one level with two
possible names**, never counted twice. The diagnostics (Sec. 8) flag this
explicitly as a structural duplicate (by formula, not by empirical
coincidence) and report it once, tagged with both aliases.

Beyond this single known structural case, **empirical clustering** (two
distinct, differently-defined levels landing numerically close together
in a given session) is a separate, non-structural phenomenon, handled by
Sec. 5b below — a numeric closeness is not evidence of formula identity
and is reported as "clustered", not "duplicated".

### Sec. 5b — empirical clustering

Two levels (from different families, or different named levels within
family 1 that are not the known structural duplicate) are flagged as
**empirically clustered** for a given session if `|level_a - level_b| <
0.1 * scale` where `scale` is `scale_U` for upside-side pairs, `scale_D`
for downside-side pairs, and `(scale_U+scale_D)/2` for cross-side or
neutral-level pairs (e.g. a family-3 `prior_close` compared against a
family-2 VWAP band). Clustering is a per-session, per-instrument, per-
level-pair diagnostic — it does not merge or drop levels, only flags
which pairs are numerically close in that session, so a later generation
that studies reactions is warned that separating their effects will be
hard on those sessions.

## Sec. 6 — generic synthetic control (corrected placebo)

For each real level observation (instrument, session, side, level_id,
value, distance-from-open normalized by that side's scale), a synthetic
control is drawn as follows:

1. Compute the level's **normalized distance** `nd = |value - O(s)| /
   scale_side(s)` (side-appropriate scale from family 1) and place it into
   one of the fixed buckets `{[0,0.5), [0.5,1.0), [1.0,1.5), [1.5,2.0),
   [2.0,inf)}`.
2. Compute a **horizon-exposure category** for the level, defined purely
   from the level's causal-availability time relative to the session (not
   from any later price behavior): `PRE_OPEN` (families 2, 4 — fully known
   before 09:30), `PRIOR_SESSION` (family 3 — known since the prior
   session's close), `INTRADAY_ROLLING` (family 1 — known at 09:30 open
   via the 60-session trailing window, same timing bucket as PRE_OPEN but
   kept as its own category since its formula basis differs).
3. Within the matched cell (instrument x session's side x
   horizon-exposure category x normalized-distance bucket), draw a
   synthetic normalized distance `nd_synth` uniformly at random from the
   bucket's own interval (e.g. uniform on `[0.5, 1.0)` if the real level's
   bucket is `[0.5,1.0)`), using a **fixed, recorded seed** for
   reproducibility, and set `value_synth(s) = O(s) +/- nd_synth *
   scale_side(s)` (sign matching the real level's side).
4. `value_synth` is not read from, or a function of, any other real
   session's actual level value, any other family's real level in the
   same session, or any subsequent price in session `s` — it is a
   structurally-blind draw that only preserves the matching attributes
   (instrument, side, horizon-exposure category, distance bucket) that a
   later reaction study would want to hold constant. This directly
   resolves the earlier internal inconsistency: nothing about a synthetic
   control's value is derived from any named structural price.
5. One synthetic control is generated per real level observation (not per
   session), so the synthetic-control table has the same row count and
   grouping keys as the real-level table, joinable 1:1 for a later
   generation's matched comparison.

## Sec. 7 — causal availability summary

| family | known as of |
|---|---|
| 1 | 09:30 open (60-session trailing window, computed from strictly prior sessions) |
| 2 | 09:30 open (overnight window fully elapsed) |
| 3 | prior session's RTH close (well before current 09:30) |
| 4 | 09:30 open (overnight window fully elapsed) |
| synthetic control | same instant as the real level it is matched to (drawn from already-known bucket boundaries, no new information) |

## Sec. 8 — diagnostics in scope (and only these)

1. **Level counts** — per instrument, per family, per level_id: how many
   sessions have a valid (non-missing) value.
2. **Missingness** — per instrument, per family: fraction of development
   sessions with a missing value, and the reason class (60-session
   warm-up for family 1; <30 overnight bars for families 2/4; early-close
   predecessor for family 3).
3. **Structural duplicates** — the family-1 `mult_*_1.0` <-> quantile-p50
   identity, confirmed programmatically (bit-for-bit equality check) and
   reported as one row, not two.
4. **Empirical clustering** — count and rate of clustered level pairs per
   session (Sec. 5b threshold), broken out by family-pair and by
   instrument.
5. **Coverage** — per instrument, per year (2018-2022): number of sessions
   with at least one valid level from each family, and with all four
   families simultaneously valid.
6. **Overlap** — for sessions with multiple valid families, the count of
   distinct level values within the family-1 scale-sized neighborhood of
   each other (this is the same statistic as clustering, aggregated to
   session level rather than pair level, to describe "how crowded is the
   level landscape in this session" as a single number).

Explicitly OUT OF SCOPE for this generation, regardless of how natural it
would be to compute alongside the above: any touch/reaction detection,
subsequent-return computation, taxonomy-class-conditional statistics, or
profitability/entry/exit logic. Those require a separate preregistration
and generation.

## Sec. 9 — leakage safeguards (unchanged from Revision 1)

- Every family's causal-availability time is verified by a
  mutate-after-boundary test: mutating any bar at or after 09:30 (or,
  for family 2/4, any bar within the overnight window at or after its
  true end) must leave that family's value for session `s` unchanged only
  if the mutation is strictly after the level's causal cutoff; mutating a
  bar strictly before the cutoff must be capable of changing the value.
- Family 1 reuses generation 6's already-audited `build_scale_tables`
  unmodified — no independent re-implementation that could silently drift
  from the accepted exact-60-session convention.
- The synthetic control generator never reads any `value` column from the
  real-level table when constructing `value_synth` — only the matching
  keys (instrument, side, horizon-exposure category, distance bucket) and
  `O(s)`/`scale_side(s)`, which are already causally known for session `s`
  itself.
