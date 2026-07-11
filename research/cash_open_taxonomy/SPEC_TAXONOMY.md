# SPEC_TAXONOMY.md — Revision 3 (final, authorized for implementation)

Locked before any development-partition result is viewed. Descriptive
taxonomy only: no level-reaction testing, no profitability metric, no
entries/exits, no 2023+ access anywhere in this generation.

## 1. Causal excursion normalization

For prior valid session `s'` (bar `tau=0` = the 09:30 ET bar):
```
U_0930(s') = High(tau=0, s') - Open(tau=0, s')
D_0930(s') = Open(tau=0, s') - Low(tau=0, s')
```
Causal scale for session `s`, using only sessions `s' < s`, **exactly the
previous 60 valid sessions** — no expanding window, no reduced-minimum
fallback. A session with fewer than 60 valid predecessors has an
**undefined** scale (excluded, not approximated from a partial window):
```
scale_U(s) = median( { U_0930(s') : s' in the 60 sessions immediately before s } )
scale_D(s) = median( { D_0930(s') : s' in the 60 sessions immediately before s } )
```
(Corrected 2026-07-11: an earlier implementation pass used a
`min_periods=20` rolling fallback, which silently computed a scale from
as few as 20 prior sessions once past the 20th session, contrary to this
requirement. Fixed in `src/taxonomy.py`; see `DECISIONS.md`.)
Kept permanently separate — never pooled, never averaged. A secondary MAD
companion scale (`1.4826 * median(|X - median(X)|)`) is computed alongside
both, reported but never substituted.

## 2. Path primitives

For session `s`, completed bar `tau=t` (0-indexed from the 09:30 bar):
```
running_high(t) = max(High[tau=0..t]);  running_low(t) = min(Low[tau=0..t])
u(t) = (running_high(t) - O) / scale_U(s)     [non-negative, non-decreasing in t]
d(t) = (O - running_low(t))  / scale_D(s)     [non-negative, non-decreasing in t]
close_disp(t) = Close(t) - O                   [signed, points]
Q(t) = (u(t) - d(t)) / (u(t) + d(t))           [in [-1,1]; undefined if u(t)=d(t)=0]
```

**Commitment threshold** `τ_c = 1.0` (primary). A side "commits" at the
first bar `t` where `u(t) >= τ_c` (upside) or `d(t) >= τ_c` (downside).
**Dominance threshold** `τ_d = 0`: a side is "dominant" at bar `t` when
`sign(Q(t))` matches that side and `|Q(t)| > τ_d` (with `τ_d=0` this is
simply a strict sign condition on `Q(t)`).

### Bar-0 morphology fields (descriptive, always computed, bar-0 data only)
```
close_disp(0), close_location(0) = 2*(Close(0)-Low(0))/(High(0)-Low(0)) - 1  [undef if H0=L0]
body_ratio(0)       = |Close(0)-Open(0)| / (High(0)-Low(0))                   [undef if H0=L0]
upper_wick_ratio(0) = (High(0) - max(Open(0),Close(0))) / (High(0)-Low(0))    [undef if H0=L0]
lower_wick_ratio(0) = (min(Open(0),Close(0)) - Low(0)) / (High(0)-Low(0))     [undef if H0=L0]
norm_close_disp(0)  = close_disp(0)/scale_U(s) if close_disp(0)>0,
                      close_disp(0)/scale_D(s) if close_disp(0)<0, else 0
```
Invariant (coded, tested): `body_ratio(0) + upper_wick_ratio(0) +
lower_wick_ratio(0) == 1` whenever defined.

## 3. Same-bar (bar-0) morphology proxy family — permanent, first-class

### 3.1 Detection and ambiguity band
```
dual_sided(s) := u(0) >= τ_c AND d(0) >= τ_c

if dual_sided(s):
    if   norm_close_disp(0) >  τ_b:  label_h1 = SAME_BAR_BULLISH_REVERSAL_PROXY
    elif norm_close_disp(0) < -τ_b:  label_h1 = SAME_BAR_BEARISH_REVERSAL_PROXY
    else:                             label_h1 = SAME_BAR_DUAL_SIDED_AMBIGUOUS
```
`τ_b = 0.15` (primary, accepted). Frozen sensitivity grid `τ_b ∈ {0.10,
0.15, 0.25}`, reported for every cell alongside the primary value, never
used to pick a "better" value after viewing class frequencies.

### 3.2 Permanent caveat (verbatim, attached as a literal string column
to every row carrying a `SAME_BAR_*` label; required, tested field)

> "One-minute OHLCV does not establish the true intrabar order. Same-bar
> bullish and bearish reversal labels are morphology-based proxies
> determined by dual-sided excursion and closing side."

### 3.3 Relationship to the parent taxonomy (corrected, final)

**The proxy's closing side is the *resulting* direction of a possible
prior opposite excursion — not a freshly observed initial direction.**
Using it as an assumed `t_init`/initial-direction for h>1 classification
(as tentatively proposed in Revision 2) is internally inconsistent with
the proxy's own operational meaning and is **rejected**. Same-bar
dual-sided sessions are therefore kept as a **permanently separate
cohort at every horizon** — they never enter the ordinary six-class
machinery (Section 4) at any h, because that machinery requires an
initial side that is observed on a *separate, orderable* bar, which bar 0
alone cannot provide.

### 3.4 Same-bar cohort: subsequent-path classification (h > 1 only)

Applies only to sessions labeled `SAME_BAR_BULLISH_REVERSAL_PROXY` or
`SAME_BAR_BEARISH_REVERSAL_PROXY` at h=1 (proxy_sign = +1 or -1
respectively). `SAME_BAR_DUAL_SIDED_AMBIGUOUS` sessions have no directional
proxy to evaluate continuation against and are labeled
`NOT_APPLICABLE_AMBIGUOUS_PROXY` at every h>1 (reported separately, not
silently dropped).

For each horizon `h>1` (`t_h = tau(h) = h-1`), using only bars `t=1..t_h`
(bars *after* the completed 09:30 candle — genuinely orderable):

1. Find `t_takeover` = the first bar `t in [1, t_h]` where
   `sign(Q(t)) == -proxy_sign AND |Q(t)| > τ_d` (opposite side dominant).
   If none exists within `[1, t_h]`, `t_takeover = None`.
2. **If `t_takeover` is None:**
   - If the proxy-side extreme was pushed strictly beyond bar 0's own
     extreme (`u(t_h) > u(0)` for bullish proxy, `d(t_h) > d(0)` for
     bearish) -> **`CONTINUATION_EXPANSION_PROXY_DIRECTION`**.
   - Else (`u(t_h) == u(0)` / `d(t_h) == d(0)`, i.e. the running extreme
     on the proxy side never advanced past the 09:30 candle's own high/
     low) -> **`BALANCE_FAILURE_TO_EXPAND`**.
3. **If `t_takeover` exists:**
   - Let `hold_bars` = the bars `t in [1, t_takeover-1]`. If `hold_bars`
     is empty (`t_takeover == 1`) OR any bar in `hold_bars` does not have
     `sign(Q(t)) == proxy_sign` (the proxy side was not cleanly held
     immediately after bar 0 before the flip) -> **`LATER_OPPOSITE_SIDE_TAKEOVER`**.
   - Else (`hold_bars` is non-empty and every bar in it has
     `sign(Q(t)) == proxy_sign`, i.e. the proxy direction was cleanly
     re-affirmed on at least one separate, orderable bar before the
     opposite side took over) -> **`LATER_ORDERED_REVERSAL_AFTER_PROXY`**,
     with `t_takeover` (expressed as candle count `h' = t_takeover+1`)
     recorded as its timing value, reported using the same minute bins as
     Section 4's reversal-timing table (minutes 2-3, 4-5, 6-10, 11-15,
     later-than-15 — the same-candle bin is structurally unreachable here
     since `t_takeover >= 2` is required for this branch).

These four labels are exhaustive and mutually exclusive by construction
(steps 2-3 partition all cases). They are reported **only** for the
same-bar proxy cohort and are never merged into Section 4's classes 1-6.

## 4. Ordinary (multi-bar, order-observable) parent taxonomy

Applies only to sessions where bar 0 is **not** dual-sided
(`NOT dual_sided(s)`), so any initial side is genuinely first observed on
an identifiable, separately-orderable bar.

**Initial directional excursion**: the side (`UP`/`DOWN`) whose `u(t)` /
`d(t)` first reaches `τ_c`, at bar `t_init`. If neither reaches `τ_c`
through the horizon, no initial excursion exists (routes to class 5/6,
below). (Note: since bar 0 is not dual-sided by construction in this
branch, `t_init=0` with a single unambiguous side is possible and normal
— e.g. bar 0 alone reaches `τ_c` on the upside only.)

**Open recross**: first bar `t_r > t_init` whose close is on the opposite
side of `O` from the initial direction.

**Reversal confirmation**: first bar `t_conf >= t_r` where the opposite
side's `u`/`d` also reaches `τ_c`, via a **completed close only** (never
an intrabar touch).

### Classes

1. **`DIRECT_BULLISH_EXPANSION`**: `t_init` exists, direction UP; no
   reversal confirmed by the horizon; `Q(t_h) > τ_d` and `close_disp(t_h) > 0`.
2. **`DIRECT_BEARISH_EXPANSION`**: mirror of 1.
3. **`INITIAL_DOWNSIDE_BULLISH_REVERSAL`**: `t_init` exists, direction
   DOWN; `t_conf` exists (upside later reaches `τ_c`); `Q(t_h) > τ_d`
   (dominance has flipped to upside) by the horizon.
4. **`INITIAL_UPSIDE_BEARISH_REVERSAL`**: mirror of 3.
5. **`TWO_SIDED_BALANCED`**: no `t_init` through the horizon, OR both
   sides reach `τ_c` (on different bars, since same-bar dual-sided is
   excluded from this branch) but `Q(t_h)` never moves decisively past
   `τ_d` in either direction.
6. **`DELAYED_EXPANSION_AFTER_INITIAL_BALANCE`**: neither side reaches
   `τ_c` for an initial quiet period of `N=15` minutes; after minute `N`,
   one side reaches `τ_c` and remains dominant through the horizon.

Reversal-timing sub-dimension for classes 3/4 (bins: minutes 2-3, 4-5,
6-10, 11-15, later-than-15 — **no same-candle bin**, since same-candle
dual-threshold events are structurally excluded from this branch and
handled exclusively by Section 3).

### Precedence (unchanged logic from Revision 1, restated)
Reversal classes (3/4) take precedence over direct classes (1/2)
whenever `t_conf` exists; class 6 takes precedence over class 5 when the
delayed-breakout condition is met; class 5 is the exhaustive residual.
`AMBIGUOUS_DIRECTION_AT_BAR_t` (both sides first reaching `τ_c` on the
*same later bar*, `t>0`) remains a rare, flagged, excluded-from-strict-
ordering-statistics edge case, unchanged from Revision 1 — this is
distinct from bar-0 dual-sidedness (Section 3), which is now handled
productively rather than flagged as ambiguous.

## 5. Full excursion ladder (restored, always computed, independent of
   the sensitivity grid)

For every session (regardless of cohort — same-bar proxy or ordinary),
using `scale_U(s)` / `scale_D(s)` separately, over bars `tau=0..59` (the
full available window, capped exactly where generation 3's atlas caps its
secondary horizon — no bar beyond 10:30 ET is used):

For each side in `{UP, DOWN}` and each threshold `τ in {0.5, 1.0, 1.5,
2.0}`:
```
reached(side, τ)   = whether u(t) [or d(t)] ever reaches τ within tau=0..59
first_bar(side, τ) = the first tau at which it does (else undefined/NaN)
```
**Order of reaching**: the full sequence of `(side, τ, tau)` events across
both sides and all four thresholds, sorted ascending by `tau`, is recorded
per session as an ordered list (e.g. `[(UP,0.5,0), (DOWN,0.5,2), (UP,1.0,4),
...]`). **Same-bar ties**: whenever two or more `(side, τ)` events share
the same `tau` (including, but not limited to, the bar-0 dual-sided case
of Section 3), the tie is recorded explicitly (`tie_group_id`) and no
order is asserted among tied events — consistent with the project's
standing rule that intrabar order is never inferred.

`τ_c = 1.0` remains the primary parent-class commitment threshold
(Section 2); the ladder is an independent, always-on diagnostic output,
not replaced or subsumed by the `{0.75,1.0,1.5}` sensitivity grid
mentioned in Section 6 — both are computed and reported.

## 6. Sensitivity grids (fixed, declared before results, never tuned)

- `τ_c ∈ {0.75, 1.0, 1.5}` (parent-class commitment threshold) x
  `τ_b ∈ {0.10, 0.15, 0.25}` (same-bar ambiguity band) — a fixed 3x3=9-cell
  grid, evaluated identically, reported in full (Section 9 diagnostics).
- The excursion ladder (Section 5) is fixed at `{0.5,1.0,1.5,2.0}` and is
  not part of the sensitivity grid — it is reported once, at its own
  stated values, for every session.

## 7. Horizon policy

`h ∈ {1,3,5,10,15,30}` primary (30-bar completeness gate), `h=60`
secondary (60-bar gate, independent). One classification per (instrument,
session, horizon) for the ordinary taxonomy (Section 4) and for the
same-bar cohort's subsequent-path label (Section 3.4); the same-bar h=1
label (Section 3.1) and the excursion ladder (Section 5) are computed once
per session, not per horizon (the ladder already reports its own bar-level
timing).

## 8. Ambiguity and precedence rules (final)

1. `dual_sided(s)` (bar 0) -> Section 3 family exclusively, at every
   horizon (h=1 label per 3.1; h>1 subsequent-path label per 3.4). Never
   enters Section 4.
2. Not dual-sided -> Section 4 classes 1-6, with `AMBIGUOUS_DIRECTION_AT_BAR_t`
   for `t>0` same-bar dual-threshold events (rare), excluded from strict-
   ordering statistics but retained and counted.
3. No-label sessions are a specification bug (classes 1-6 plus the
   Section-3 family are jointly exhaustive) — to be fixed before results
   are reported, not patched with a silent seventh bucket.

## 9. Expected class-frequency diagnostics

- Six-class (Section 4) frequency, ES/NQ separate, per horizon, per year.
- Same-bar family (`SAME_BAR_BULLISH_REVERSAL_PROXY`,
  `SAME_BAR_BEARISH_REVERSAL_PROXY`, `SAME_BAR_DUAL_SIDED_AMBIGUOUS`)
  frequency at h=1, ES/NQ separate, per year; subsequent-path frequency
  (Section 3.4's four labels) at h∈{3,5,10,15,30,60}, ES/NQ separate.
- `AMBIGUOUS_DIRECTION_AT_BAR_t` (t>0) counts, ES/NQ separate.
- 3x3 `(τ_c, τ_b)` sensitivity table of same-bar-family frequencies.
- Excursion-ladder reach rates by side/threshold/instrument (monotonicity
  in threshold level is a coded near-tautology, checked as an invariant,
  not a finding); same-bar-tie frequency.
- Morphology descriptive stats (`close_location(0)`, `body_ratio(0)`,
  `upper_wick_ratio(0)`, `lower_wick_ratio(0)`) for each of the three
  same-bar classes.
- Minimum reporting floor: 20 sessions/instrument/horizon/class; cells
  below this are flagged inadequate, not suppressed.

## 10. Leakage and implementation safeguards

- `scale_U(s)`/`scale_D(s)` use only `s' < s` within the loaded
  development-partition frame; no validation/holdout data read anywhere.
- Every primitive at bar `t` uses only bars `tau<=t`; enforced and tested
  via the standard mutate-after-bar-t / assert-unchanged fixture pattern
  used in every prior generation.
- Reversal confirmation (Section 4) and same-bar cohort's `t_takeover`
  (Section 3.4) both require a **completed bar close**, never a touch.
- The permanent caveat string (Section 3.2) is a required, tested column
  on every row carrying a `SAME_BAR_*` label.
- One row per (instrument, session, horizon) for Section 4 and 3.4 labels;
  one row per (instrument, session) for the excursion ladder and bar-0
  morphology fields.
- ES and NQ use independently fit `scale_U`/`scale_D` and are reported in
  fully separate tables throughout — never pooled.
- No TP/SL, MAE/MFE, PF/Sharpe, sizing, entry, level-reaction, or
  profitability computation appears anywhere in this generation.
