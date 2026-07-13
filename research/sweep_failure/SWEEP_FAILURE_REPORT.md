# Sweep-and-Failure Discovery Report

Generation: sweep-and-failure discovery (base `201896d`). Branch:
`research/sweep-and-failure-discovery`. Partition: development only,
ES + NQ, 2018-01-03 -> 2022-12-30. 2023 onward was never read. Pure
mechanical OHLCV geometry; no ICT terminology used as evidence, no
stop-hunting/liquidity-engineering claim, no trading strategy, no
threshold optimization after viewing results.

## Session/event counts

| Instrument | RTH-valid sessions | Prev-RTH-level valid | Overnight-level valid | Armed episodes | Events |
|---|---|---|---|---|---|
| ES | 1242/1291 | 1290/1291 | 914/1291 | 8,642 | 5,794 |
| NQ | 1240/1291 | 1290/1291 | 1009/1291 | 9,330 | 6,344 |

Event class counts (pooled ES+NQ): `FAILED_BREACH_1MIN` 4,188,
`SUCCESSFUL_BREACH_CONTROL` 3,455, `TOUCH_WITHOUT_BREACH` 1,995,
`FAILED_BREACH_2MIN` 1,708, `FAILED_BREACH_3MIN` 729,
`INCOMPLETE_EPISODE` 56, `DELAYED_FAILURE_CONTROL` 4,
`NEITHER_RESOLVED_WITHIN_10MIN` 3. The last two are vanishingly rare, as
expected (`DELAYED_FAILURE_CONTROL`/`NEITHER` require all of `B, B+1,
B+2` to close *exactly* tick-equal to the level — a narrow edge case).

## Primary classification (40 cells: instrument x level_type x side x time_stratum)

**29/40 cells `FAILED_BREACH_ROTATION_SUPPORTED`, 11 `UNDERPOWERED`, 0
`MIXED_OR_NULL`, 0 `FAILED_BREACH_BREAKOUT_SUPPORTED`.** Every single
tested cell shows the same pattern: failed-breach rotation-first rate
~73-88%, successful-breach-control rotation-first rate ~3-15%, effect
size 65-84 percentage points, permutation p-value pinned at the
procedure's floor (1/10,001, i.e. **zero of 10,000 permutations** in any
matching stratum ever produced a difference as large as observed), 5/5
years agreeing in sign everywhere. This is not a subtle or marginal
result — it is uniform, enormous, and statistically overwhelming across
every instrument, level type, side, and time-of-day stratum tested.

**This uniformity and magnitude is itself diagnostic, and — exactly as
with the prior generation's Module A finding — must be read with a
structural caveat before being treated as evidence of a predictive
"failed sweep" mechanism**, per this generation's charter commitment to
distinguish genuine signal from mechanical construction:

> `FAILED_BREACH_*` events are anchored at `C+1`, where `C` is the bar
> whose close is **already back inside** the level (that is the
> definition of a failed breach). `SUCCESSFUL_BREACH_CONTROL` events are
> anchored at `B+3`, where `B+2`'s close is **already outside** the level
> (that is the definition of the control). Both rotation and breakout
> barriers are symmetric, fixed distances from the *level itself* — not
> from the anchor bar's own price. A price path that starts already
> inside the level is mechanically closer to the rotation barrier and
> farther from the breakout barrier (which requires first traveling back
> through the level); a path that starts already outside is mechanically
> the reverse. This is not a lookahead bug (every bar used is strictly
> at/after the anchor, exactly as specified in `SPEC_SWEEP_FAILURE.md`,
> mirroring the task's own anchor definitions for each class) — but it
> means the ~70-80pp gap is, in significant part, a **direct,
> near-tautological consequence of comparing two classes whose defining
> feature (inside vs. outside close) is itself measured relative to the
> same level used to anchor the outcome barriers**, not necessarily new
> information about what happens *after* a level interaction resolves.
>
> Two additional facts in the data reinforce this reading rather than
> undermine it: (1) `TOUCH_WITHOUT_BREACH` events with a close-inside
> sub-classification show a similarly high rotation-first rate (75.5%,
> `reports/tables/touch_control_table.csv`) despite **never having
> breached at all** — the touch class shares only one thing with
> `FAILED_BREACH`: its anchor bar's close sits inside the level, exactly
> the shared feature the caveat above identifies as doing the mechanical
> work. Touches that closed *exactly at* the level (a genuinely
> ambiguous starting position) show a near-50/50 rotation rate (46.8%),
> as the mechanical explanation predicts. (2) Failure delay
> (`FAILED_BREACH_1MIN` vs. `2MIN` vs. `3MIN`) and breach-magnitude band
> show only mild, non-monotonic variation (69-74% and 65-73%
> respectively, `reports/tables/failure_delay_table.csv`,
> `reports/tables/breach_magnitude_table.csv`) — if failure *speed* or
> breach *severity* carried real distinguishing information beyond the
> inside/outside anchor split, a clearer gradient would be expected.

Given this, the primary finding is reported honestly as: **failed
breaches are followed by a close-inside anchor from which the symmetric,
level-anchored rotation barrier is reached far more often than the
breakout barrier — but this is largely, and plausibly mostly, a
consequence of the anchor's starting position relative to the level
rather than a standalone discovery about post-failure price behavior.**

## Failed vs. successful breach results

See above and `reports/tables/primary_matched_comparison.csv` /
`reports/tables/classification_table.csv` for the full per-cell detail
(all 40 cells, including the 11 `UNDERPOWERED` ones, which failed only
the sample-size floor, not the effect — their point estimates are
consistent with the pattern above).

## Touch-control results

`TOUCH_CLOSE_INSIDE`: 75.5% rotation-first (mean across cells, n≈214).
`TOUCH_CLOSE_AT_LEVEL`: 46.8% rotation-first (n≈35, small sample) — a
level-agnostic, symmetric result, exactly as expected when the anchor
bar's close carries no directional lean.

## Failure-delay results

`FAILED_BREACH_1MIN` 68.7%, `2MIN` 74.1%, `3MIN` 72.9% rotation-first
(pooled means) — no clear monotonic relationship with delay; differences
are small relative to the ~70-80pp failed-vs-successful gap.

## Level-type results

All four level types (`prev_rth_high`, `prev_rth_low`, `overnight_high`,
`overnight_low`) show materially the same pattern and magnitude — no
level type stands out as behaving differently.

## Upper/lower differences

No material asymmetry between upper and lower levels; both sides show
the same ~70-85pp failed-vs-successful gap.

## Volume findings

Rotation-first rate is flat across `HIGH_VOLUME`/`NORMAL_VOLUME`/
`LOW_VOLUME` strata (roughly 55-76%, `reports/tables/volume_table.csv`,
no consistent monotonic pattern, several `LOW_VOLUME` cells have small
samples). No incremental volume effect clears the 5pp/corrected-
significance/3-year bar.

## Previous-test findings

`FIRST_TEST` 70.4%, `SECOND_TEST` 73.7%, `THIRD_PLUS_TEST` 69.2%
rotation-first (pooled means) — no material, consistent trend with
repeated testing.

## ES-NQ confirmation findings

`CONFIRMED_BREACH` 65.5%, `PARTIAL_CONFIRMATION` 74.4% (very small n=10),
`UNCONFIRMED_BREACH` 71.1% — no material difference; cross-market
confirmation does not distinguish the effect.

## Time-of-day findings

`OPEN`, `MID_MORNING`, `MIDDAY`, and `AFTERNOON` all show the same
pattern and magnitude (see `reports/tables/classification_table.csv`);
several individual strata fall to `UNDERPOWERED` only because of smaller
per-stratum sample sizes, not a different point estimate.

## Year stability

5 of 5 years agree in sign in every one of the 40 primary cells — the
pattern is not a single-year artifact. Given the mechanical explanation
above, this is unsurprising: the anchor construction applies identically
in every year.

## Strongest rotation result

ES, `overnight_low`, `MIDDAY`: rotation-first 87.6% (failed) vs. 4.1%
(successful), effect 83.5pp, p<0.0001, n=120/101, 5/5-year agreement.

## Strongest breakout result

None — 0/40 cells reached `FAILED_BREACH_BREAKOUT_SUPPORTED` anywhere.

## Strongest nulls

None of the 40 primary cells is a clean null in the traditional sense
(all point estimates are large); the closest to "underpowered but weak"
is NQ `overnight_low` `MIDDAY` (effect 69.3pp but n=226/90, below the
100/100 floor).

## Final report questions

1. **Do failed breaches rotate away more often than successful
   breaches?** Yes, overwhelmingly (65-84pp gap, every cell) — but see
   the structural caveat: this is very likely dominated by the
   inside-vs-outside anchor construction rather than new predictive
   information.
2. **Do they outperform ordinary touches?** No — `TOUCH_CLOSE_INSIDE`
   shows a similarly high rotation-first rate (75.5%), consistent with
   the mechanical explanation applying to any inside-anchored class, not
   something specific to "failure."
3. **Does failure within one minute differ from failure after two or
   three minutes?** Only mildly (69-74%, no clear trend) — delay speed
   does not add a distinguishing signal beyond the shared inside-anchor
   effect.
4. **Does breach magnitude matter?** Only mildly and non-monotonically
   (65-73% across bands) — magnitude does not add a clear incremental
   effect.
5. **Does high volume strengthen or weaken the effect?** No consistent
   pattern; volume strata are flat within noise.
6. **Does the number of previous tests matter?** No material trend
   across `FIRST_TEST`/`SECOND_TEST`/`THIRD_PLUS_TEST`.
7. **Does ES-NQ confirmation matter?** No — confirmed, partial, and
   unconfirmed breaches show similar rotation-first rates.
8. **Do previous-RTH and overnight levels behave differently?** No — all
   four level types show the same pattern and magnitude.
9. **Does behavior differ between upper and lower levels?** No material
   asymmetry.
10. **Does it differ across RTH time strata?** No — `OPEN`,
    `MID_MORNING`, `MIDDAY`, `AFTERNOON` all show the same pattern.
11. **Is the effect stable across 2018-2022?** Yes, 5/5 years in every
    cell — expected given the mechanical construction applies uniformly
    across years.
12. **Is there a coherent candidate worth freezing for 2023+
    validation?** Not as currently specified. The comparison as defined
    (failed vs. successful breach, both measured from their own
    class-defining anchor) is confounded by the anchor's inside/outside
    position relative to the very barriers used to score the outcome.
    A freeze-worthy candidate would need to hold when compared against a
    baseline that does not share this confound (e.g., an anchor common
    to both classes) — which this generation's preregistered design does
    not test and is not permitted to redesign post hoc.

## Verdict

A large, uniform, highly significant statistical pattern was found in
every primary cell, but it does not clear the bar for a genuinely novel,
non-mechanical, freeze-worthy discovery: the touch-control and
failure-delay/magnitude results both point toward the inside-vs-outside
anchor position — not the failed/successful distinction itself — as the
dominant driver. No supported sweep-and-failure rotation mechanism, free
of this structural confound, was found at previous-RTH or overnight
extremes in ES/NQ one-minute OHLCV during 2018-2022 that would be
responsible to carry into a 2023+ validation study as currently
specified.

No validation-partition (2023+) study follows this generation.
