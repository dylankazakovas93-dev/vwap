# SPEC_AUCTION_VALUE.md — formal specification

Single source of truth. Where this spec and code disagree, this spec
wins and the code has a bug. Tick size 0.25 NQ points throughout.

## 1. Profile construction (three deterministic approximations)

Fixed price bins of width `w` in `{0.25 (1 tick), 0.50 (2 ticks), 1.00
(4 ticks)}`, anchored at a fixed grid origin (`floor(session_low / w) *
w`) so bin edges are reproducible.

- **PRIMARY `UNIFORM_RANGE`**: each 1-minute bar's volume is split
  evenly across every bin its `[Low, High]` range intersects (equal
  share per bin, including partial-overlap bins — no partial-bin
  weighting by overlap fraction, per "distribute... uniformly across
  every bin intersected," a bin is either intersected or not).
- **SENSITIVITY 1 `TYPICAL_PRICE_ROW`**: full bar volume to the bin
  containing `(High+Low+Close)/3`.
- **SENSITIVITY 2 `CLOSE_PRICE_ROW`**: full bar volume to the bin
  containing `Close`.

All three conserve total session volume exactly (tested).

**POC**: the bin with maximum volume. Tie-break (frozen): the
lowest-priced bin among ties.

**Value area expansion** (target `p` in `{68%, 70% (primary), 72%}` of
total profile volume): start at the POC bin; repeatedly add whichever
adjacent bin (immediately above the current upper boundary, or
immediately below the current lower boundary) has the greater volume;
tie-break (frozen): add the **upper** (higher-priced) bin. Continue
until cumulative included volume `>= p * total_volume`. If one side runs
out of bins (session low/high reached), continue expanding only on the
remaining side. `VAH`/`VAL` = the upper/lower boundary of the final
included range.

## 2. Session profiles (three legs, reused audited definitions)

`ASIA` 18:00-02:59 ET, `LONDON` 03:00-08:29 ET, `NEW_YORK_RTH`
09:30-15:59 ET (`DATA_CONTRACT.md`). A profile is built from one
completed leg instance's 1-minute bars; incomplete leg instances (bar
count short of the leg's expected full count) are excluded outright, not
repaired. A profile freezes at the leg's final bar's close timestamp
(`completion_ts`); `VAH`/`VAL`/`POC` never change afterward. No profile
ever uses volume from bars in the period during which it is *being
traded against* (i.e. only the leg's own, already-completed, bars build
it — trivially true since it freezes before the next leg starts, but
tested explicitly against a synthetic future-leaking construction).

**Profile mappings (evaluated and reported separately, never merged
into one result):**

1. completed Asia profile -> used during London.
2. completed London profile -> used during New York RTH.
3. prior completed New York RTH profile -> used during the *following*
   overnight session (i.e. the Asia leg that starts that evening).
4. prior completed New York RTH profile -> used during the *next* RTH
   session (i.e. skip one full day/night cycle; this profile's
   `expiry_ts` is the start of that next RTH session).

Expiry (frozen per mapping, `DECISIONS.md` #3): mapping 1 expires at
London's end; mapping 2 expires at NY RTH's end; mapping 3 expires at
the next Asia leg's end; mapping 4 expires at the next RTH leg's end —
i.e. every mapping's profile is valid for exactly the one target leg
instance it is defined for for, never beyond, regardless of the
freshness parameter in §4E (freshness is an *additional*, tighter,
gate within that same window, never an extension past it).

## 3. Event state machine (VAH and VAL independently, long/short symmetric)

States: `INACTIVE -> ARMED -> OUTSIDE_EXCURSION -> REACCEPTANCE_PENDING
-> EVENT_RECORDED -> LOCKED`, or `-> EXPIRED` from any non-terminal
state when the mapped profile's `expiry_ts` passes.

- `INACTIVE -> ARMED`: the mapped profile is completed, active
  (`completion_ts <= current_ts < expiry_ts`), and price has not yet
  interacted with the edge in this leg instance.
- `ARMED -> OUTSIDE_EXCURSION`: a bar's range **trades below `VAL`**
  (long side) or **above `VAH`** (short side) — an actual trade, not a
  mere touch (touch-without-breach is a separate control, §6 Control 1).
  The first such bar is the excursion's `breach_first_idx`.
- `OUTSIDE_EXCURSION -> REACCEPTANCE_PENDING -> EVENT_RECORDED`: a
  frozen reacceptance rule (§4C) is satisfied; the confirming bar is
  `confirmation_idx`. The event is **knowable**, and therefore recorded,
  only once `confirmation_idx`'s bar has closed — never earlier.
  Canonical strict additional requirements: the confirmation close is
  inside value (`VAL < close <= VAH` long-appropriate side; mirrored),
  and (long) `confirmation_close < POC` / (short) `confirmation_close >
  POC` — an event whose confirming close already sits at/above POC
  (long) does not qualify as this mechanism (there is no "toward POC"
  distance left for the primary outcome to measure).
- `EVENT_RECORDED -> LOCKED`: canonical analysis allows **at most one
  event per edge per completed profile**; once recorded, that
  `(profile_id, side)` combination locks for the remainder of that
  profile's active window — no second canonical event from the same
  profile/side. (The descriptive repeated-test ledger, §5, is a
  *separate* pass that does not feed the canonical single-event
  analysis.)
- Any bar within the same `OUTSIDE_EXCURSION` never spawns more than one
  candidate event (mechanically true: the state machine only evaluates
  reacceptance rules once armed into `OUTSIDE_EXCURSION`, and locks
  immediately upon the first satisfied rule's confirmation).
- The four combinations explicitly excluded (never constructed, never
  reported as part of this mechanism): failed-VAL-discovery paired with
  ordinary-movement-down-from-VAH bookkeeping, failed-VAH-discovery
  paired with ordinary-movement-up-from-VAL bookkeeping, and any
  "moved from the opposite edge" derived rule.

## 4. Bounded development matrix (evaluated only on development years)

Implementation note (`RESEARCH_CHARTER.md` A2): rather than 432
independent event-detection passes, one master **excursion/acceptance
ledger** is built per `(profile mapping, side)`, recording — for every
armed excursion, independently for **each** of the four acceptance
rules below — whether and when that rule's confirmation bar occurs, the
maximum breach depth reached by `breach_first_idx..confirmation_idx`,
the bars-outside count (`confirmation_idx - breach_first_idx`), the
entry(confirmation)-to-POC distance as a fraction of value-area width,
and hours-since-`completion_ts` at confirmation. The 432-cell grid
(**A x B x C x D x E** below) is then five boolean filters applied to
this one ledger — statistically identical to 432 independent scans,
verified by a test that spot-re-derives one grid cell via an independent
direct scan and confirms an identical event set.

- **A. Breach depth** (max depth reached before confirmation, in
  points, converted to ticks / %VA-width): `>= 1 tick`; `>= 5% of VA
  width`; `>= 10% of VA width`.
- **B. Max time outside before reacceptance** (`confirmation_idx -
  breach_first_idx <=`): `1 bar`; `3 bars`; `5 bars`.
- **C. Reacceptance definition** (confirmation bar per rule):
  - `R1_ONE_CLOSE`: the first 1-minute close `>= VAL + 1 tick` (long) /
    `<= VAH - 1 tick` (short) after `breach_first_idx`.
  - `R2_TWO_CONSECUTIVE_CLOSES`: the second of the first two
    *consecutive* inside-value closes (both `> VAL` long / `< VAH`
    short, tick-normalized) after `breach_first_idx`.
  - `R3_TWO_OF_THREE_CLOSES`: the bar completing the first 3-bar rolling
    window (starting no earlier than `breach_first_idx+1`) with `>= 2`
    inside-value closes; confirmation = that window's last bar.
  - `R4_DEPTH_ACCEPTANCE`: the first close `>= VAL + 0.10*VA_width`
    (long) / `<= VAH - 0.10*VA_width` (short).
- **D. Distance remaining to POC at confirmation** (entry-to-POC
  distance `>=`, as a fraction of VA width): `0%`; `10%`; `20%`.
- **E. Profile freshness** (hours from `completion_ts` to
  `confirmation_idx`'s timestamp, `<=`): `2h`; `4h`; `6h`; "valid until
  mapped trading period ends" (i.e. no additional cap beyond the
  mapping's own `expiry_ts`, §2).

3 x 3 x 4 x 3 x 4 = 432 combinations, evaluated per `(profile mapping,
side)` = 4 x 2 = 8 -> 3,456 grid cells total, all computed as filters
over 8 master ledgers (one per profile-mapping x side). No unrestricted
optimizer: only these 432 combinations per mapping/side are ever
evaluated; no additional threshold is tried.

## 5. Repeated-test ledger (descriptive, separate from canonical)

Later interactions at the same edge within the same profile's active
window are numbered `1st/2nd/3rd+`. A later interaction is eligible to
be recorded only after (a) the prior interaction's outcome horizon
(§6, 120 minutes, the longest) is complete, **and** (b) price has since
reached a neutral state: `POC touched`, `opposite half of value
touched`, or `profile expired`. No arbitrary cooldown is used as the
primary rearming rule for this ledger; the neutrality condition is.

## 6. Primary outcome: `POC_REACHED_BEFORE_REDISCOVERY`

Legal outcome bars: `confirmation_idx+1` onward; the event/acceptance
bars never re-enter outcome measurement. Horizons: 15/30/60/120 minutes,
each requiring the complete window inside data (no partial-window
fallback; horizon may cross into the next leg/session using the
continuous 1-minute series, since the *outcome* is about price behavior,
not the profile's own validity window).

Long: success = POC touched (`Low <= POC <= High` on some bar);
failure = close back below `VAL`, or a trade below the excursion's own
low reached before confirmation (`min(Low[breach_first_idx..confirmation_idx])`)
— whichever is reached first is recorded as the failure definition.
Short: exactly mirrored around `VAH` / excursion high.

Retained categories per horizon: `POC_FIRST`, `REDISCOVERY_FIRST`,
`SAME_BAR_AMBIGUOUS` (both in one bar — intrabar order never inferred),
`NEITHER`, `INCOMPLETE_HORIZON`.

Secondary path outcomes (recorded, not separately hypothesis-tested):
time-to-POC, MFE toward POC, MAE, excursion-beyond-edge magnitude, bars
spent inside value, count of inside-value closes, whether POC was
reached before profile expiry.

**Conditional second-stage `POC_TO_OPPOSITE_EDGE_COMPLETION`** (for
`POC_FIRST` events only): from the POC-touch bar, does price reach the
*opposite* value-area edge before returning to the originating edge,
within the same set of horizons, measured from the POC-touch bar the
same way (`+1` onward, mirrored success/failure)? Reported as an
entirely separate table, never merged into the edge-to-POC result.

## 7. Controls (matched to the same chronology and strata)

Matching variables (all four controls): profile mapping, side,
clock-time stratum (ET hour of confirmation/control-anchor bar),
value-area-width band (terciles within development years, frozen after
computation on development data only), profile-age band (freshness
tercile), event distance-from-POC band (tercile), realized-volatility
band (ATR20 tercile, causal, computed the same way as prior generations'
`ATR20`), and breach-magnitude band (§4A) where applicable.

- **CONTROL 1 `TOUCH_WITHOUT_BREACH`**: price touches the edge
  (tick-equal high/low, VAL/VAH) without trading outside, closes inside,
  anchor = touch bar, matched distance-to-POC band.
- **CONTROL 2 `MATCHED_INSIDE_STATE`** (primary/most important control):
  a bar fully inside the same value-area half (between POC and the
  relevant edge), matched distance-to-POC/age/session/clock-time bands,
  with **no edge breach in the recent event lookback** (the longest
  freshness window, 6h, scanned backward from the control anchor).
- **CONTROL 3 `SUCCESSFUL_DISCOVERY`**: a breach that remains outside
  under the frozen breach-depth definition and does **not** satisfy any
  reacceptance rule within the maximum window (5 bars) — the mirror
  image of a canonical event.
- **CONTROL 4 `REPEATED_TEST`**: the §5 ledger's 1st interaction vs.
  2nd/3rd+ interactions, compared directly (not matched further, since
  the comparison is internal to the repeated-test structure itself).

Controls are drawn from the same matched strata as their corresponding
treatment cells; unmatched global averages are never used as a control.

## 8. Development statistics

Primary comparison: canonical event (failed discovery + reacceptance)
vs. `MATCHED_INSIDE_STATE`. Primary metric: difference in `POC_FIRST`
rate among resolved, non-ambiguous outcomes (excludes
`SAME_BAR_AMBIGUOUS`, `NEITHER`, `INCOMPLETE_HORIZON`), at horizon 60
minutes as the primary reporting horizon (30/60 both checked for
directional consistency per candidate criterion 7; 15/120 reported as
additional robustness). Matched stratified permutation (>=10,000
permutations, seed `20260713`, reused frozen constant from prior
generations), BH correction applied within each `profile_mapping`
family across all tested `(side x acceptance_family)` grid cells that
have >= 1 matched stratum. Year-by-year, pooled, profile-model
sensitivity, and neighboring-parameter-stability tables are all
produced; all null/underpowered cells retained, none dropped.

## 9. Candidate family selection (verbatim gate, restated for the engine)

A candidate family (one `profile_mapping x side x acceptance_family`
combination, "acceptance family" meaning one C-value optionally paired
with a fixed A/B/D/E neighborhood) qualifies for OOS only if **all 12**
hold: >=300 development failed-discovery events; >=150 usable matched
control events; positive treatment-minus-control difference in >=3 of 4
development years; pooled development effect >=+5pp; worst development-
year effect no worse than -3pp; BH q<=0.10; same directional sign at
30 and 60 minutes; support under >=2 profile bin widths; support under
`UNIFORM_RANGE` and >=1 sensitivity profile; >=2 adjacent parameter
definitions show the same directional sign; not explained solely by
starting closer to POC (tested by comparing the candidate's
distance-to-POC distribution against its matched control's — a
candidate is disqualified if its treatment group starts materially
closer to POC than its own matched control, since `MATCHED_INSIDE_STATE`
is matched on distance-to-POC band, this is a positive-control check on
the matching itself, not an extra filter); no single development year
contributes >50% of the pooled effect (measured as that year's share of
total treatment-minus-control "effect mass," i.e. `n_year *
|effect_year|` relative to the sum across years). No isolated clock-
time/volume/volatility subgroup is ever promoted on its own.

## 10. Pre-OOS freeze procedure

Before any OOS computation: write `CANDIDATE_MANIFEST.md` (or a
`NO_CANDIDATE` manifest if nothing qualifies) listing every qualifying
family, every exact allowed parameter definition, the primary outcome
and horizon, all control matching rules, and the OOS pass/fail criteria
verbatim; commit and push it; verify no `outputs/oos_*` file exists on
disk; only then run `src/oos_pipeline.py` (which itself refuses to run
if `CANDIDATE_MANIFEST.md` is absent from the committed tree — a
runtime guard, not just a process rule).

## 11. OOS evaluation (2019, 2021, 2023, 2025 only, once)

Only the frozen candidate families are evaluated, using the exact same
code path and thresholds as development (no redefinition). Pass
requires all 9 listed OOS criteria (positive pooled effect; pooled OOS
effect >= half the development effect; positive in >=3 of 4 OOS years;
OOS q<=0.10; adequate samples; same-direction 30/60-minute persistence;
no single OOS year entirely driving the result — operationalized the
same way as development criterion 12; directional consistency under
>=1 alternate profile construction; second-stage completion reported
but not required). 2026 is never read. After OOS is opened, no
threshold, definition, or subgroup change is made regardless of outcome.

## 12. Prohibited (unchanged pattern, restated)

No Pine Script. No profit/reward:risk/stop/size/Sharpe/prop-account
optimization anywhere in this generation. No threshold search after
seeing development results beyond the fixed 432-cell grid. No OOS
subgroup search. No re-opening OOS after results are known. No 2026
access.
