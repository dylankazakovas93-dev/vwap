# Simple Cash-Open Level Study — Report (Generation 9)

Branch `research/simple-cash-open-level-study`. Base commit `201896d`.
Preregistration commit `7039473`. Implementation commit `5b43853`.
Development partition only (2018-2022). **Pure phenomenon discovery —
no strategy, no profitability, no entries/exits/sizing, no taxonomy
conditioning. Does not claim evidence of order flow, absorption,
participant inventory, dealer positioning, stop hunting, or queue
behavior.**

## Sample

| instrument | level rows | touch events | outcome rows | barrier rows |
|---|---|---|---|---|
| ES | 111026 | 79272 | 387095 | 1548380 |
| NQ | 110854 | 78895 | 386525 | 1546100 |

86 level_ids/instrument confirmed (14 Family A + 72 Family B), locked by
test. Median touch rate across all 172 (instrument×level_id) cells:
**73.9%** (range 19.8%-91.4%) — these are all near-the-open levels, so
high touch rates within a 2-hour window are expected and not evidence of
anything beyond the levels' own proximity to price.

## 1. Overnight-VWAP levels (Family A1)

No overnight-VWAP level_id (`ON_VWAP_{m3..p3}`, either instrument) appears
in the `CONTINUATION_DOMINANT`/`REVERSAL_DOMINANT` list at any primary
horizon. **Behavior: null** — adequately powered (all cells cleared the
sample floors) but `MIXED_OR_NULL` throughout.

## 2. Prior-RTH-VWAP levels (Family A2)

Same result: no `PR_VWAP_{m3..p3}` level_id shows a directional
classification at any primary horizon. **Behavior: null.**

## 3. Historical 09:30-excursion levels (Family B) — by parameterization

**The only non-null post-touch result in the entire study is confined to
NQ, upper-side, k=0 (center-only, no SD buffer added).** 21 of 516
(instrument × level_id × primary-horizon) cells are `CONTINUATION_DOMINANT`
— specifically `upper_N{5,10,20}_{mean,median,ema}_k0` on NQ (not all 9
parameterizations qualify at every horizon; `N5_mean_k0`/`N5_median_k0`
do not reach significance, only `N5_ema_k0` does). **Zero cells are
`REVERSAL_DOMINANT`.** No `lower_*` (downside excursion) level shows a
directional post-touch classification on either instrument. No `k≥1`
level (i.e., adding any SD buffer beyond the bare center) shows a
directional post-touch classification. Lookback (5 vs 10 vs 20) and
center (mean vs median vs EMA) do not materially change the qualifying
set beyond the collapse described in §5 below.

Same-bar morphology tells a different, non-overlapping story: 5 level_ids
are `SAME_BAR_REVERSAL_BIASED` — ES `lower_N5_median_k0`,
`lower_N20_median_k0`; NQ `lower_N5_mean_k0`, `lower_N5_median_k0`,
`lower_N10_median_k0` — all **lower-side, k=0** levels, reversal-biased
on the touch candle itself (price tends to close back above these
levels within the same bar more than it blasts through). Zero
`SAME_BAR_BLAST_THROUGH_BIASED` results. Same-bar reversal rate vs
blast-through rate across all 172 level_ids is close to 50/50 on average
(reversal 50.5% ± 2.2pp, blast-through 49.2% ± 2.5pp) — these 5 are the
tail, not the norm.

## 4. Stability across 2018-2022

The flagship result (NQ `upper_N10_mean_k0`, h=60) shows a positive
continuation-minus-reversal barrier difference in **all five years**
(2018: +0.083, 2019: +0.151, 2020: +0.117, 2021: +0.053, 2022: +0.067,
each on 210-230 touches/year) — this is exactly the 4-of-5-year
condition the frozen classification requires, verified directly, not
just inferred from the pass/fail flag. Full year-by-year detail for
every cell: `reports/tables/year_stability_barrier_table.csv` /
`year_stability_touch_table.csv`. No 2020-dominance or single-year
concentration was found among the 21 qualifying cells.

## 5. Are the 21 results duplicated parameterizations of one physical level?

**Yes, overwhelmingly.** The coincident-level audit
(`reports/tables/coincident_level_top_collisions.csv`) finds that in 168
of ~1290 NQ sessions, **all nine** of `upper_N{5,10,20}_{mean,median,
ema}_k0` land within one tick of each other simultaneously — i.e., at
`k=0`, the center estimate is nearly insensitive to both the lookback
(5 vs 10 vs 20 sessions) and the center statistic (mean vs median vs
EMA) a majority of the time. The 21 "significant" cells are best read as
**a small number of independent discoveries (perhaps one) tested under
9 correlated aliases and 3 horizons**, not 21 separate confirmations.
This is disclosed as the central interpretive caveat on the Family-B
result: Benjamini-Hochberg corrected within `(instrument, horizon)`
across level_ids, as specified, but that correction does not account for
this near-total aliasing at k=0, so the effective number of independent
tests supporting the NQ upper-k=0 finding is much smaller than 9.
Overall alias rate: 56.8% of ES touch events and 27.8% of NQ touch events
occur in a multi-alias cluster (`reports/tables/coincident_level_alias_
table.csv`) — collisions are common but not universal, and are far more
common at higher `k` (SD-buffered) rungs (`k=2,3`) than at `k=0`.

## 6. Coherent same-bar morphology AND coherent post-touch dominance?

**No level shows both.** The `SAME_BAR_REVERSAL_BIASED` set (5 level_ids,
all **lower**-side k=0) and the `CONTINUATION_DOMINANT` post-touch set
(21 cells, all **upper**-side k=0) are disjoint — different sides
entirely. No level_id appears in both lists. Same-bar morphology and
post-touch path are, in this data, independent phenomena on different
sides of the level population, not two views of the same effect.

## Full tables (all committed, no omissions)

`level_inventory_table.csv` (86 rows), `level_availability_table.csv`,
`touch_rate_table.csv`, `touch_timing_table.csv`,
`same_bar_morphology_table.csv` (172 rows, all classified),
`post_touch_outcome_table.csv` (516 rows), `barrier_1sd_test_table.csv`,
`barrier_order_table.csv` (all 4 `b` rungs), `year_stability_barrier_
table.csv`, `year_stability_touch_table.csv`,
`behavior_classification_table.csv` (516 rows: 495 `MIXED_OR_NULL`, 21
`CONTINUATION_DOMINANT`, 0 `REVERSAL_DOMINANT`, 0 `UNDERPOWERED` — every
cell cleared the sample floors given how frequently these near-the-open
levels are touched), `coincident_level_alias_table.csv`,
`coincident_level_top_collisions.csv`, `behavior_null_inventory.csv`,
`behavior_underpowered_inventory.csv` (empty — no cell was underpowered),
`same_bar_null_inventory.csv`, `same_bar_underpowered_inventory.csv`.

## Verdict

Anchored VWAP deviation levels (both overnight-session and prior-RTH
anchors, all seven ±SD rungs each) show **no** stable, adequately-powered
reversal or continuation behavior on either instrument. Historical
09:30-candle excursion levels show exactly one directionally coherent,
year-stable signature — NQ, upper-side, center-only (`k=0`) — and even
that collapses substantially under the coincident-level audit to a much
smaller number of effectively independent tests than the raw 21-cell
count suggests. No downside excursion level, and no SD-buffered (`k≥1`)
rung of either side, shows any directional post-touch behavior. Same-bar
morphology separately flags a small, disjoint set of downside k=0 levels
as reversal-biased on the touch candle itself, with no corresponding
post-touch persistence.

Per the frozen interpretation rule (§22): a level that is overwhelmingly
crossed and continues beyond it must be reported as a possible
continuation/blast-through level, not dismissed for failing to reverse —
the NQ upper-k=0 finding is reported on exactly that basis, with the
aliasing caveat attached. Beyond that one (largely-aliased) signature:

> "No supported simple predetermined cash-open level mechanism was found
> in ES/NQ one-minute OHLCV using overnight/prior-RTH VWAP deviation
> levels or historical single-candle 09:30 excursion levels."

This statement is about this specific data source and these two level
mechanisms only — it does not claim that no cash-open edge can exist
under any data source or mechanism.
