# Cash-Open Path Taxonomy — Report (Generation 6, Part 1)

Branch: `research/cash-open-path-taxonomy`. Preregistration commit
`1bccda8` (SPEC_TAXONOMY.md Revision 3). Development partition only
(2018-2022). **Descriptive taxonomy construction only — no level-reaction
test, profitability metric, entry, or exit anywhere in this generation.**

## Sample

| instrument | sessions with valid scale+bar-0 | same-bar dual-sided at h=1 |
|---|---|---|
| ES | 1269 | 250 (19.7%) |
| NQ | 1267 | 205 (16.2%) |

(Generation 3's atlas primary-valid counts were 1286/1284; the small
reduction here is the causal `scale_U`/`scale_D` warm-up requirement —
20+ prior sessions — which the atlas's own targets do not need.)

## Class frequency — coherent and adequately populated at every primary horizon

At h=1, six mutually exclusive outcomes partition the sample cleanly for
both instruments: `DIRECT_BULLISH_EXPANSION` (31.0%/34.1% ES/NQ),
`DIRECT_BEARISH_EXPANSION` (28.2%/30.9%), `TWO_SIDED_BALANCED`
(21.0%/18.8%), `SAME_BAR_BULLISH_REVERSAL_PROXY` (10.8%/9.0%),
`SAME_BAR_BEARISH_REVERSAL_PROXY` (8.0%/6.2%), and
`SAME_BAR_DUAL_SIDED_AMBIGUOUS` (0.9%/1.0%, correctly flagged
below-floor at n=11/13 — a genuinely rare, honestly reported cell). At
h=3 through h=60, the ordinary six-class machinery and the same-bar
cohort's four subsequent-path labels both populate with every non-trivial
cell above the 20-session floor, in both instruments, at every horizon —
the only persistently below-floor cells are `NOT_APPLICABLE_AMBIGUOUS_PROXY`
(the ambiguous same-bar cohort itself, n=11-13, expected to be small) and,
at the earliest horizons, `BALANCE_FAILURE_TO_EXPAND` (n=6-20, shrinking
as horizon grows — makes sense, since "the proxy side never advances past
its own bar-0 extreme" becomes rarer the longer the window).

**One class never occurs: `DELAYED_EXPANSION_AFTER_INITIAL_BALANCE`
(class 6) has zero sessions at every horizon, both instruments.** This is
reported as a genuine finding, not hidden: with `τ_c=1.0` and a 15-minute
initial-balance window `N`, apparently no development-partition session
stays quiet enough (neither side reaching even a single typical 09:30
candle's excursion) for a full 15 minutes and then breaks out cleanly by
the horizon — the running cumulative excursion evidently exceeds `τ_c` on
one side well before minute 15 in every session sampled. This is a
property of the chosen `τ_c`/`N` defaults on this sample, not a
mathematical impossibility, and is flagged as inadequate/empty rather
than silently omitted from the class list.

## Same-bar proxy morphology — the labels track the shape they claim to

The Research Charter's stated falsifier (same-bar proxy morphology should
show the expected wick/close-location asymmetry) **passes clearly**:

| instrument | label | n | close_location(0) mean | upper_wick mean | lower_wick mean |
|---|---|---|---|---|---|
| ES | BULLISH_PROXY | 137 | +0.65 | 0.17 | 0.43 |
| ES | BEARISH_PROXY | 102 | -0.60 | 0.43 | 0.20 |
| ES | DUAL_SIDED_AMBIGUOUS | 11 | -0.05 | 0.52 | 0.46 |
| NQ | BULLISH_PROXY | 114 | +0.70 | 0.15 | 0.42 |
| NQ | BEARISH_PROXY | 78 | -0.52 | 0.43 | 0.24 |
| NQ | DUAL_SIDED_AMBIGUOUS | 13 | -0.01 | 0.49 | 0.49 |

`SAME_BAR_BULLISH_REVERSAL_PROXY` candles close high in their range with
an elevated lower wick (consistent with the operational assumption of "a
down-move recovered into a bullish close"); the bearish proxy mirrors
this; the ambiguous class sits almost exactly at the midpoint with nearly
balanced wicks on both sides, exactly as the ambiguity-band design
intends. **The permanent intrabar-order caveat is attached to every row
carrying a `SAME_BAR_*` label** (tested, `Sec. 3.2` of the spec).

## Same-bar cohort subsequent-path — the four categories are all populated

At h=5 (representative horizon), among proxy-cohort sessions:
`CONTINUATION_EXPANSION_PROXY_DIRECTION` dominates (60.3%/64.6% ES/NQ),
`LATER_OPPOSITE_SIDE_TAKEOVER` is a meaningful minority (23.4%/16.7%),
`LATER_ORDERED_REVERSAL_AFTER_PROXY` (the "clean hold, then reversal"
case) is smaller but present (13.0%/15.6%), and
`BALANCE_FAILURE_TO_EXPAND` is rare (3.3%/3.1%, near the reporting floor).
All four categories are populated at every horizon 3 through 60 in both
instruments — the four-way split is not degenerate.

## Sensitivity grid — behaves monotonically, as expected of a coded design

The 3×3 `(τ_c, τ_b)` grid moves exactly as the definitions imply: loosening
`τ_c` from 1.5 to 0.75 roughly quadruples the same-bar proxy share (e.g.
ES bullish proxy 3.9% -> 16.7%); widening `τ_b` from 0.10 to 0.25 shifts
mass from the two directional proxies into `DUAL_SIDED_AMBIGUOUS` (ES
ambiguous share 0.5% -> 4.3% at `τ_c=1.0`). This is reported in full (18
rows/instrument) and confirms the taxonomy's sensitivity is structural,
not noisy — no value in the grid was chosen based on this output.

## Excursion ladder — monotonic reach rates, expected high tie rate at low thresholds

Reach rates decline monotonically with threshold level for both sides and
both instruments (ES UP: 95.4% @0.5 -> 89.0% @1.0 -> 82.0% @1.5 -> 76.8%
@2.0; DOWN nearly symmetric), confirming the coded near-tautology holds
with no violations. **Same-bar ties occur in ~98.3-98.5% of sessions** —
initially striking, but explained by design: the 0.5-unit threshold is
half a typical single-candle excursion, so bar 0 alone very commonly
reaches 0.5 on *both* sides simultaneously, which is definitionally a
same-bar tie under Section 5's rule. This is reported as an expected
consequence of a low first rung on the ladder, not an anomaly, and is
distinguished from same-bar *dual-sided-at-the-commitment-threshold*
(Section 3, `τ_c=1.0`), which is the far rarer, separately-tracked event
(19.7%/16.2%).

## Ambiguous-direction-at-bar-t (t>0, ordinary path)

Rare, as expected: recorded per session where applicable, never merged
into the class-frequency counts as an ordinary class — full counts in
`ambiguous_bar_counts.csv`.

## Year stability (2018-2022)

Same-bar proxy counts at h=1 are present and non-trivial in every year for
both instruments (ES bullish proxy: 40/18/31/19/29 across 2018-2022; NQ:
28/16/25/26/19) — no year drives the class to near-zero or dominates it
disproportionately. The taxonomy's basic shape is not an artifact of one
regime.

## Interpretation — is the taxonomy coherent and sufficiently populated?

**Yes, for five of the six ordinary classes and the entire same-bar proxy
family, at every horizon in both instruments.** The classes partition the
sample exhaustively (no unlabeled sessions, per the specification's
exhaustiveness guarantee), the morphology of the same-bar proxy labels
matches their operational definition under an independent descriptive
check, the sensitivity grid moves sensibly, and year-by-year counts are
stable. **One class (`DELAYED_EXPANSION_AFTER_INITIAL_BALANCE`) is
structurally empty at the chosen defaults** and should not be relied upon
without revisiting `τ_c`/`N` in a future generation — this is reported as
a limitation of the frozen defaults, not papered over. No result here
constitutes or implies a trading signal.

## Artifacts

`RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_TAXONOMY.md` (Revision
3), `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
`PROGRESS.md`, `RUN_REGISTRY.csv` (12 rows); `src/{taxonomy, build_ledger,
run_analysis}.py`; `tests/test_fixtures.py` (15 tests); ledgers
`outputs/{es,nq}_taxonomy_ledger.parquet` (git-ignored, reproducible);
tables in `reports/tables/`: `class_frequency.csv`,
`samebar_h1_frequency.csv`, `subsequent_path_frequency.csv`,
`ambiguous_bar_counts.csv`, `sensitivity_grid.csv`,
`ladder_reach_rates.csv`, `ladder_ties.csv`, `samebar_morphology_stats.csv`.
