# ES-NQ Unsupported Move Discovery Report

Generation: ES-NQ unsupported move discovery (base `201896d`). Branch:
`research/es-nq-unsupported-move-discovery`. Partition: development
only, 2018-01-03 -> 2022-12-30. 2023 onward was never read. No
profitability, entries, exits, sizing, or prop-account simulation
anywhere.

## Synchronization coverage

| | ES | NQ |
|---|---|---|
| Raw 1-minute bars | 1,754,270 | 1,751,547 |
| Dropped (no counterpart) | 4,339 | 1,616 |
| Synchronized bars | 1,749,931 | 1,749,931 |

99.75%/99.91% coverage; 0 session-date/et-minute mismatches between the
two instruments' joined rows (tested invariant). 3,867 leg instances
(Asia/London/New York), 1,591,766 legal window endpoints scanned, 19
exact leader z-score ties (excluded from treatment/control, retained in
counts).

## Sample accounting

25,603 total events: 1,133 `EXTREME_UNSUPPORTED_MOVE`, 24,470
`MODERATE_UNSUPPORTED_MOVE` (moderate is a much wider z-band, so this
ratio is expected). By session: Asia 2,982 (563 raw counted per leader/
direction split, see `reports/tables/classification_table.csv`), London
1,684, New York 1,020 primary-cell-eligible extreme events (full
per-cell breakdown in the classification table, which also reports
ambiguous/neither/incomplete counts per cell — `SAME_BAR_AMBIGUOUS`
count is 0 in every cell; `NEITHER_WITHIN_HORIZON` and
`INCOMPLETE_HORIZON` counts are material and reported, never hidden).

## Primary matched comparison (12 cells: leg x leader_instrument x leader_direction)

**0/12 cells `EXTREME_CONVERGES_MORE_SUPPORTED`; 11 `MIXED_OR_NULL`, 1
`UNDERPOWERED`** (NEW_YORK, ES-led, UP — smallest resolved sample).
Effect sizes range from **-17.2pp to +7.9pp** (extreme closure rate
minus moderate closure rate), with **3 of 12 cells positive and 9
negative** — no consistent direction. No cell reaches BH-adjusted q<0.05
in the direction implied by the hypothesis (the one cell with the
smallest raw p-value, London/ES-led/UP, is *negative*: extreme
converges *less* than moderate there, q=0.14, still not significant
after correction). 6-9 matched permutation strata per cell (well above
the "at least one" floor), 10,000 permutations each, seed `20260713`.

This is a clean, non-degenerate null: closure rates for both extreme and
moderate events cluster in the same 40-65% range across every cell
(`reports/tables/classification_table.csv`), consistent with the
task's own interpretation rule: *"If both extreme and moderate
unsupported moves converge at similar rates, the extremity hypothesis
is null even if unconditional convergence is common."* That is exactly
what is observed here.

## Effect sizes, p-values, q-values

See `reports/tables/primary_matched_comparison.csv` and
`reports/tables/classification_table.csv` for the full 12-row table
(raw counts, resolved/ambiguous/neither/incomplete counts, matched
strata count, both closure rates, pp difference, raw p-value, BH q-value,
sample/effect/significance/year gates, and final classification per
cell).

## Year-by-year stability

Sign agreement across 2018-2022 is inconsistent per cell (3-4 of 5 years
agreeing in the dominant sign in most cells, per
`reports/tables/year_stability.csv`) — but since no cell has a
consistent, material, significant effect to begin with, year "stability"
here just describes noise oscillating around zero, not a stable
phenomenon. 2020 is not a systematic outlier in either direction across
cells (spot-checked: ASIA/ES-led/DOWN shows 2020 as the one year with a
*negative* diff while the other four years are positive — not a pattern
that would rescue the hypothesis, and not treated as one).

## Adjacent-horizon results (5/10/15/30 minutes)

Closure rates for both classes move together and stay close across all
four horizons (extreme: 58.5% / 55.9% / 56.5% / 56.9%; moderate: 60.1% /
58.7% / 58.3% / 58.2% — `reports/tables/adjacent_horizon_table.csv`).
No horizon shows extreme pulling ahead of moderate. This is coherent
*non*-evidence: the null holds uniformly across horizons rather than
appearing only at one convenient horizon.

## Full resolution-attribution table

`reports/tables/attribution_table.csv` (by leg x leader, pooled across
extreme+moderate since the primary hypothesis itself is null — reported
descriptively per instructions). Roughly consistent proportions across
legs/leaders: `DIVERGENCE_EXPANDS` 34-45%, `JOINT_CONVERGENCE` 30-39%,
`LEADER_REVERSAL` 7-14%, `LAGGARD_CATCHUP` 6-10%, `DIVERGENCE_PERSISTS`
5-7%, `PARTIAL_OR_MIXED` <0.2%. Where convergence does occur (across
both extreme and moderate pooled), it is roughly 3-4x more often
`JOINT_CONVERGENCE` than either `LEADER_REVERSAL` or `LAGGARD_CATCHUP`
alone — i.e. when ES and NQ come back together, both instruments
typically contribute materially, rather than one purely following the
other. This descriptive pattern does not change the primary null result
(the question of *whether* extreme moves converge more is separate from
*how* the convergence that does happen is composed).

## ES-led versus NQ-led results

`reports/tables/leader_instrument_table.csv`: ES-led extreme closure
45.9% vs. ES-led moderate 55.3% (extreme *lower*); NQ-led extreme 39.1%
vs. NQ-led moderate 51.6% (extreme *lower* again). Both leader
instruments show the same qualitative pattern — extreme moves close
*less* often than moderate ones in the raw pooled comparison (though
this pooled view collapses the leg/direction stratification the
permutation test respects; the per-cell table is the primary evidence).
No asymmetry that would suggest ES-led and NQ-led dislocations behave
differently.

## Historically typical versus atypical leader results

`reports/tables/typicality_table.csv`: closure rates are similar across
`TYPICAL` (36.1% extreme / 52.5% moderate), `ATYPICAL` (39.7% / 52.5%),
and `NO_STABLE_HISTORICAL_LEADER` (45.0% / 53.8%) — whether the observed
leader matches the session's historically dominant leader does not
distinguish the (null) primary result.

## Strongest result

London, ES-led, `UP` direction: extreme closure 43.6% vs. moderate
closure 60.9%, effect **-17.2pp** (extreme converges *less*), raw
p=0.012, BH q=0.14 (does not survive correction). This is the single
largest-magnitude cell in the entire study, and it points *against* the
hypothesis, not for it.

## Strongest null

Asia, NQ-led, `DOWN`: extreme closure 60.0% vs. moderate closure 62.3%,
effect -2.3pp, p=0.63, n=120/2,604 resolved — a textbook null with ample
sample on both sides.

## Implementation limitations / possible mechanical confounds

- The causal residual path (§7 of the spec) applies the frozen event-time
  `alpha`/`beta` to increasingly long cumulative windows as the horizon
  grows; this is explicitly instructed ("do not refit... during the
  outcome window") but means the 30-minute residual-path value is not on
  the same effective scale as the 5-minute regression it was estimated
  from — a limitation, not a bug, and disclosed in
  `KNOWN_LIMITATIONS.md` #7.
- `residual_z` and the causal leadership-history fraction both require
  120 valid prior occurrences at the exact clock slot (60 for the return/
  regression stats, plus another 60 for the residual-history std), which
  is a materially stricter bar than the "60 valid prior sessions" stated
  requirement taken at face value — this is a faithful, if demanding,
  reading of "using only the previous 60 paired valid sessions" applied
  recursively to the residual series itself, not a shortcut.
- A genuine implementation bug was found and fixed during this run: the
  causal residual path was initially capped at the primary horizon (15)
  instead of the largest secondary horizon (30), silently producing zero
  resolved events at `h=30`. Caught before finalizing results; fixed in
  a separate commit; the corrected run is what this report describes.
- Matched-stratum permutation shuffles on `leg x leader_instrument x
  leader_direction x clock_hour` only (not also leader-z/residual-z
  bands, `DECISIONS.md` #6) — a stricter six-key stratification was not
  run and could in principle show a different (though, given how close
  the raw closure rates already are, unlikely to be materially
  different) result.

## Plain-English answers

**Do extreme unsupported moves converge more than comparable moderate
divergences?** No. Across all 12 primary cells, extreme and moderate
unsupported moves close (converge) at similar rates — some cells lean
slightly toward extreme converging *less*, none show extreme converging
significantly *more* after correction for multiple comparisons.

**When convergence occurs, does it come from leader reversal, laggard
catch-up, or both?** Predominantly both together (`JOINT_CONVERGENCE`,
~30-39% of resolved events) rather than one instrument doing all the
work — `LEADER_REVERSAL` and `LAGGARD_CATCHUP` alone are each roughly
half to a third as common as joint convergence. This is a real
descriptive pattern, but it describes the *composition* of convergence
when it happens, not evidence that extreme dislocations are special.

**Does the result depend on which instrument normally leads in that
session?** No — closure rates are similar whether the observed leader
matches, mismatches, or has no stable historical relationship with the
session's typical leader.

## Verdict

No supported extreme-unsupported-move convergence mechanism was found:
extreme and moderate unsupported ES-NQ dislocations resolve at
statistically indistinguishable rates in every tested cell, coherently
across horizons and years, so per the preregistered interpretation gate
the extremity hypothesis is null. No validation-partition (2023+) study
follows this generation.
