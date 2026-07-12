# NQ Excursion-Level Timing Study — Report (Generation 10)

Branch `research/nq-excursion-level-timing`. Base commit `4d5ee1b`.
Preregistration commit `38b0617`. Implementation commit `5a357de`.
Development partition only (2018-2022). **Pure phenomenon discovery —
no profitability, entries, sizing, TP/SL, or prop-account outcomes. NQ is
primary; ES is a preregistered negative-control replication, interpreted
separately and never used to alter NQ definitions.**

## Sample

| instrument | level rows | touch events | outcome rows | barrier rows |
|---|---|---|---|---|
| NQ | 10296 | 7800 | 84172 | 336688 |
| ES | 10312 | 7929 | 85448 | 341792 |

Exactly 8 level_ids/instrument confirmed and locked by test
(`UPPER/LOWER_k{0,1,2,3}`). Timing surface: 2×8×11×11 = 1936 primary
cells, all retained.

## 1. Does NQ `UPPER_k0` show continuation, and when?

**Yes — and it is genuinely a cash-open mechanism, not a late-morning
artifact.** `UPPER_k0` classifies `COHERENT_OPEN_CONTINUATION`, anchored
at **activation window A=2 minutes, horizon H=2 minutes**: touched within
the first 2 minutes of 09:30 (i.e., essentially the 09:30 candle itself
or the very next bar), continuation dominates reversal by **+10.2
percentage points** (`n=732` touches, `n_nontied=594`, `q=0.0375`,
median `SIGNED_CLOSE_SD=+0.30`). This is not an isolated cell — it meets
all seven coherence conditions, including adjacent-activation-window and
adjacent-horizon support and 4-of-5-year sign stability (§4).

## 2. How does the result change across post-touch horizons 1-120 min?

The 104 qualifying (A,H) cells supporting `UPPER_k0`'s classification
span both short and longer horizons with the same sign, but the
strongest, earliest-anchored evidence is concentrated at short
horizons (`H=1,2,3`) paired with short activation windows (`A≤10`).
Full cell-by-cell detail: `reports/tables/timing_surface_table.csv`
(filter `level_id==UPPER_k0`).

## 3. Does the lower mirror show bearish continuation?

**No.** `LOWER_k0` classifies `MIXED_OR_NULL` — no cell reaches
Benjamini-Hochberg significance strongly enough, or with enough
coherence, to support a continuation (or reversal) classification. The
canonical candidate's bullish/upper-side asymmetry is confirmed: this is
a **bullish-only** effect in this data, not a symmetric excursion-level
phenomenon.

## 4. Do `k=1/2/3` extensions become reversal-dominant?

**No — `k=1` and `k=2` remain continuation-dominant (not reversal), and
`k=3` is null, not reversal.** `UPPER_k1` (`COHERENT_OPEN_CONTINUATION`,
anchor `A=2,H=1`, `n=429`, diff `+12.5pp`, `q=0.045`) and `UPPER_k2`
(`COHERENT_OPEN_CONTINUATION`, anchor `A=5,H=2`, `n=430`, diff `+12.7pp`,
`q=0.045`) both extend the same bullish-continuation signature farther
from the open. `UPPER_k3` never reaches Benjamini-Hochberg significance
at any cell (best `q=0.23`) — null, not reversal/exhaustion. On the
downside, `LOWER_k1` produces exactly one significant cell
(`A=1,H=1`, diff `-20.7pp` toward reversal, `q=0.034`) but fails the
adjacency and year-stability conditions — classified
`ISOLATED_SIGNIFICANT_CELL`, not promoted. `LOWER_k2`/`LOWER_k3` are
`MIXED_OR_NULL`. No level in this study shows a coherent
reversal/exhaustion signature.

## 5. Is the effect present in ES?

**No.** All 8 ES level_ids classify `MIXED_OR_NULL` — zero coherent or
even isolated-significant cells anywhere in the ES timing surface. This
is a clean negative-control result: the NQ effect does not appear to be
a generic artifact of the touch/outcome/barrier pipeline itself (which is
identical code, identical constants, run on ES), and the finding is
NQ-specific, not instrument-agnostic.

## 6. Year stability and cross-year SD audit

`UPPER_k0` at its anchor cell (`A=2,H=2`): continuation-minus-reversal
difference is positive in **all five years** (2018 +6.2pp, 2019 +11.2pp,
2020 +12.6pp, 2021 +6.4pp, 2022 +15.3pp) — `n_years_with_pooled_sign=5`,
comfortably clearing the required 4-of-5. Three of five years fall
within one cross-year standard deviation of the five-year mean (2020 is
**not** the largest-magnitude year — 2022 is). No year contributes more
than 35% of total touches. Full detail (all anchor cells, all
qualifying level_ids): `reports/tables/yearly_stability_table.csv`.

## 7. Does the rolling prior-state variable predict today's touch?

**No.** Every `(instrument, level_id)` cell classifies `STATE_NULL` —
including NQ `UPPER_k0` (`n_continuation_state=431`,
`n_reversal_state=232`, `continuation_rate_diff=-0.055`, `q=0.95`, not
even directionally consistent with persistence). The prior 10-touch
continuation/reversal history does not predict the current touch's
outcome for any level on either instrument. This is a clean null,
reported in full: `reports/tables/rolling_state_table.csv`.

## 8. Are any findings duplicated aliases?

**No, for the coherent findings.** NQ's alias rate is **0%** — zero
sessions had any two of the 8 NQ levels within one tick of each other
(`k=0,1,2,3` are always well-separated given typical `SD_U_10`/`SD_D_10`
magnitudes at this instrument). ES shows a small alias rate (0.55% of
sessions, 0.09% of touches, always `UPPER_k0-k3` clustering together) —
irrelevant here since ES is null throughout. **The NQ `UPPER_k0/k1/k2`
finding is not an artifact of duplicated physical prices** — confirmed
by direct audit, not inferred.

## 9. Cash-open phenomenon, late-morning phenomenon, or null?

Per the frozen decision rule (§24): `UPPER_k0`'s (and `UPPER_k1`'s,
`UPPER_k2`'s) coherent region is anchored at activation windows of 2, 2,
and 5 minutes respectively — all **≤30 minutes**. Therefore, per
instruction:

**The candidate survives a coherent region at activation windows of 30
minutes or less.** Specifically: NQ `UPPER_k0` (activation ≤2 min,
horizons including 1-3 min and beyond, 104 qualifying cells),
`UPPER_k1` (activation ≤2 min, anchor horizon 1 min, 14 qualifying
cells), and `UPPER_k2` (activation ≤5 min, anchor horizon 2 min, 20
qualifying cells) all support `COHERENT_OPEN_CONTINUATION`. This is not
called profitable or deployable — it is a descriptive, year-stable,
alias-free, negative-control-passing statement about one-minute OHLCV
path behavior only.

`LOWER_*` levels, `UPPER_k3`, and the rolling-state diagnostic are all
null. ES replication is null throughout.

## Full tables (all committed, no omissions)

`timing_surface_table.csv` (1936 rows), `same_bar_surface_table.csv`,
`post_touch_outcome_table.csv`, `barrier_first_table.csv`,
`yearly_stability_table.csv`, `rolling_state_table.csv`,
`rolling_state_year_table.csv`, `timing_region_classification_table.csv`
(16 rows: 8 levels × 2 instruments), `same_bar_classification_table.csv`,
`alias_duplicate_table.csv`, `alias_top_collisions.csv`,
`timing_region_null_inventory.csv`, `timing_region_underpowered_
inventory.csv` (empty — every cell had ≥50 touches given how frequently
these near-the-open levels are touched), `same_bar_null_inventory.csv`,
`same_bar_underpowered_inventory.csv`.

## Verdict

The prior narrow NQ upper-continuation candidate survives precise
timing decomposition as a genuine, coherent, year-stable, alias-free,
bullish-only, cash-open-proximate (≤5-minute activation) phenomenon for
`k=0,1,2` — and is explicitly null (not reversal) at `k=3`. The lower
mirror is null. ES shows no trace of the effect anywhere. The causal
rolling-state diagnostic finds no predictive persistence or mean-reversion
in the touch outcome sequence. No result here is a strategy, profitability
claim, or deployable trading rule.
