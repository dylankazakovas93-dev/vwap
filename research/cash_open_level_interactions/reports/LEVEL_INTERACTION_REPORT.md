# Cash-Open Level Interaction Study — Report (Generation 8, Part 2B-1)

Branch `research/cash-open-level-interactions`. Base commit `3c734ca`
(38 level_ids/instrument). Preregistration commit `1f2609f`.
Implementation commit `e71c0bc`. Development partition only (2018-2022).
**Unconditional phenomenon-discovery study only — no strategy, no
profitability, no entries/exits/sizing, no taxonomy conditioning
anywhere in this generation.**

## CRITICAL CAVEAT — read before any other result in this report

**A large share of Family A's Bonferroni-significant touch-rate
differences are very likely dominated by a matching-quality artifact
inherited from generation 7's synthetic-control construction, not by a
genuine reaction to the named level.** This was discovered during this
generation's analysis (not previously known), verified quantitatively,
and is disclosed here in full rather than worked around, since this
generation's instructions were to reuse generation 7's synthetic control
exactly as built, not redesign it.

**The mechanism**: generation 7 buckets a level's normalized distance
from the open into `{[0,0.5),[0.5,1.0),[1.0,1.5),[1.5,2.0),[2.0,∞)}` and
draws the matched synthetic control uniformly **within that bucket's own
interval** — for the open-ended top bucket, the draw is capped at
`[2.0, 3.0)` (`hi_draw = lo + 1.0` when the bucket has no upper bound).
But the **real** level's actual normalized distance, when it falls in
that same bucket, is unbounded and often far larger. Verified for ES
`prior_low`: of 1119 sessions in the `[2.0,∞)` bucket, the real value's
normalized distance has **mean 23.1, median 18.5, max 126.5**, while its
matched synthetic control's is capped at **mean 2.5, max 3.0**. The
synthetic arm is therefore mechanically far closer to the open — and far
more likely to be touched in a 30-minute window — for every level that
predominantly lands in this bucket, independent of any market phenomenon.

**Levels affected** (>50% of sessions in the `[2.0,∞)` bucket, verified):
`mult_U_2.0`, `mult_D_2.0`, `q_U_p90`, `q_U_p95`, `q_D_p90`, `q_D_p95`,
`vwap_on_j±2`, `vwap_on_j±3`, `prior_high`, `prior_low`, `prior_close`,
`prior_rth_mid`, `prior_rth_vwap`, `overnight_high`, `overnight_low`,
`overnight_mid`, `overnight_open` — **17 of 38 level_ids**, and the
majority of Family A's Bonferroni survivors (see table below). Levels
whose normalized distance is bounded by construction (`mult_U/D_{0.5,
1.0,1.5}`, `mad_U/D_*`, `q_*_p25/p75`, `vwap_on_j{0,±1}`) are not subject
to this artifact and their (smaller, but still often significant)
touch-rate differences are the more interpretively reliable Family A
results in this report.

**This is a limitation of the frozen, reused synthetic-control mechanism,
not a bug introduced in this generation** — generation 7's own tests
confirmed the control is deterministic, matched, and unrelated to any
named price, all of which remain true here; this generation additionally
found that "matched on distance bucket" is a materially weaker guarantee
for the open-ended top bucket than for the bounded buckets. No fix is
applied here, per instruction not to redesign the frozen methodology;
this is reported as the single most important interpretive caveat on
Family A's results.

## Sample

| instrument | unit rows | event rows | outcome rows | barrier rows |
|---|---|---|---|---|
| ES | 49058 | 98116 | 314245 | 1235400 |
| NQ | 48982 | 97964 | 318510 | 1245660 |

## Primary Family A — touch rate (McNemar, 76 tests, Bonferroni α=0.05/76)

**55 of 76 (instrument, level_id) cells survive Bonferroni** — see the
critical caveat above before interpreting this as 55 genuine phenomena.
All cells reached the ≥100-mutual/≥20-discordant confirmatory floor
except one (`NULL`/`UNDERPOWERED` split: 0 null, 1 underpowered — nearly
every level had ample mutual-eligible sessions and discordant pairs).

The largest, most caveat-affected effects (`[2.0,∞)`-bucket-dominated
levels): `vwap_on_j-3` (ES: real−synth touch-rate diff **−0.516**,
`p_bonferroni≈7e-187`), `prior_low` (ES: **−0.540**), `overnight_low`
(ES: **−0.387**) — all showing the real arm touched *far less often*
than its synthetic control, consistent with the artifact (a real value
sitting, on average, ~20 scale-units from the open is touched far less
often within 30 minutes than a synthetic control capped at ~2.5).

The smaller, more reliable effects (bounded-bucket family-1 levels):
`mult_U_1.0`/`mult_D_1.0` (ES: **+0.049**/**+0.043**, real touched
*more* often than synthetic), `mult_U_0.5`/`mult_D_0.5` (ES: **+0.048**
each), similar magnitudes on NQ. These are small in absolute terms
(4-8 percentage points) but statistically overwhelming given ~1200
mutual-eligible sessions each — still not proof of a trading edge, per
the frozen interpretation rules (§22).

Full results: `reports/tables/primary_family_a_results.csv` (76 rows, no
omissions). Sample coverage: `reports/tables/primary_family_sample_coverage.csv`.

## Primary Family B — paired D_5 (Wilcoxon signed-rank, 76 tests)

**0 of 76 cells reached the confirmatory floor (≥50 valid pairs, ≥20
non-zero differences); all 76 are `no_valid_pairs`.** This is a genuine,
verified finding, not a bug: the intersection of `real_isolated=1` AND
`synthetic_isolated=1` (both required for Family B) occurred in only 1
of 49058 ES unit-rows. With 38 densely-packed level_ids sharing a
`0.10·side_scale` cluster/isolation threshold, essentially every touched
level has *some* other named level (of the other 37) within that
distance or co-touching the same bar — the isolation criterion, applied
literally to this specific 38-level library, is almost never jointly
satisfiable for both arms simultaneously. Family B is reported in full as
**uniformly underpowered**, per the frozen spec's explicit instruction to
report such cases as "underpowered descriptive evidence," not omit them.

Full results: `reports/tables/primary_family_b_results.csv` (76 rows,
all `status=no_valid_pairs`, `bonferroni_survivor=False`).

## Secondary/exploratory grid

Unpaired `D_5`/`D_1`/`D_3`/`D_10`/`D_15`/`MFE`/`MAE`/`Q` (Mann-Whitney),
`post_touch_retouch` and `directional_close_recross` (Fisher exact),
continuation/rejection label distributions, and barrier reach rates —
all computed on the full (non-isolated-restricted) touched sample, each
cell reported with Benjamini-Hochberg correction within its own
`(instrument, outcome_name, horizon)` family across the 38 level_ids.
Never promoted to a confirmatory claim. Full tables:
`reports/tables/secondary_*.csv`, `barrier_order_table.csv`.

## Cluster / co-touch limitations

`reports/tables/cluster_co_touch_table.csv`: named-level cluster rates
and isolation rates per (instrument, level_id). Consistent with the
Family B finding above, `real_isolated` and `synthetic_isolated` are rare
events given 38 densely-spaced levels sharing one 09:30 candle's scale —
disclosed as a structural property of this specific level library, not a
computation error (verified by the required tests' isolation-logic
fixtures, all passing).

## Year stability

`reports/tables/year_stability_table.csv`: per (instrument, level_id,
year) eligible-session counts, touch rates, and median `D_5` values,
2018-2022. No confirmatory year-by-year tests were run, per instruction.
Given the dominant matching-artifact caveat above, year-by-year
inspection is most informative for the bounded-bucket family-1 levels
(where the artifact does not apply) — those levels' touch-rate
differences are visibly stable in sign across all five years in the
underlying table (not concentrated in any single year, including 2020).

## Null and underpowered inventories

`reports/tables/family_a_null_inventory.csv` (cells not surviving
Bonferroni, including the 1 underpowered cell),
`family_a_underpowered_inventory.csv`,
`family_b_null_inventory.csv`/`family_b_underpowered_inventory.csv` (all
76 Family B cells, since none reached the confirmatory floor) — complete,
no omissions.

## Final classification (`reports/tables/final_classification.csv`)

| classification | count (of 76 instrument×level_id cells) |
|---|---|
| `SUPPORTED_TOUCH_RATE_DIFFERENCE` | 55 |
| `UNDERPOWERED` | 1 |
| `NULL` | 20 |
| `SUPPORTED_PAIRED_POST_TOUCH_DIFFERENCE` | 0 |
| `SUPPORTED_BOTH` | 0 |

No level receives `SUPPORTED_BOTH` (Family B never reaches its floor).
**Every `SUPPORTED_TOUCH_RATE_DIFFERENCE` classification must be read
alongside the critical caveat above** — for the 17 open-ended-bucket
level_ids this is very likely measuring the synthetic-control matching
artifact, not a market phenomenon; for the bounded-bucket family-1 levels
it is a small but statistically robust touch-rate difference, still not
a strategy, edge, or proof of any trading mechanism.

## Explicitly not claimed anywhere in this report

Not a strategy. Not profitable. Not an entry. Not a rejection trade. Not
a continuation trade. Not proof of order flow, absorption, stop-hunting,
or dealer positioning. No taxonomy-conditional analysis was begun.

## Artifacts

`RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_LEVEL_INTERACTIONS.md`,
`DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
`PROGRESS.md`, `RUN_REGISTRY.csv`; `src/{interactions, build_ledger,
families, secondary, run_analysis}.py`; `tests/test_fixtures.py` (34
tests covering all 36 required test items); ledgers
`outputs/{es,nq}_{levels,events,outcomes,barriers}.parquet` and
`outputs/family_b_pairs.parquet` (git-ignored, reproducible); 18 tables
in `reports/tables/`.
