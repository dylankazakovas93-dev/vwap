# Overnight/Pre-open Predictor Discovery — Report (Generation 5)

Branch: `research/overnight-preopen-predictor-discovery`, base
`research/cash-open-target-atlas` @ `201896d`. Development partition only
(2018-2022). **Standalone-feature discovery screen only — no strategy,
model, combination (with each other or with generation 4), or tradable
edge is claimed anywhere below.**

## Sample

| instrument | primary rows (Sec. 3-5) | Sec. 6 valid (has non-early-close predecessor) | Sec. 6 excluded |
|---|---|---|---|
| ES | 1286 | 1242 | 44 |
| NQ | 1284 | 1240 | 44 |

Sec. 3-5 (overnight path, frozen VWAP, pre-open windows) require only the
current session's own data through 09:29 and match generation 3's atlas
primary-valid counts exactly (1286/1284). Sec. 6 (prior-RTH/overnight
relationship) additionally requires a non-early-close predecessor,
excluding ~3.4% of sessions — consistent with generation 4's early-close
exclusion rate.

## Test count and multiple-testing accounting

**720 elementary tests** registered exactly as preregistered (2
instruments x 45 features x 4 horizons x 2 targets), all in
`reports/tables/feature_screen_full.csv`, logged in `RUN_REGISTRY.csv`
(92 rows: one per instrument/feature pass, plus 2 effective-N rows).

**Zero of the 720 cells clear the declared Bonferroni threshold**
(alpha = 0.05/720 = 6.94e-5). 32/720 (4.4%) clear the raw/nominal
alpha=0.05 — close to the ~36 expected by chance alone at a 5% false
-positive rate across 720 independent tests, though the features are not
independent (see effective-N below), so this comparison is only
suggestive.

**Effective-N sensitivity**: the 45 features are less redundant than
generation 4's 30 previous-close features but still substantially
correlated — average pairwise |Spearman| = 0.223 (ES) / 0.220 (NQ),
giving an effective feature count of **~4.2** out of 45 for both
instruments.

## Strongest evidence (still modest, none Bonferroni-significant)

**A short-horizon, cross-instrument, mean-reversion-flavored pattern
around the prior-close/overnight gap.** The three strongest cells are all
at h=10, target R (closing displacement), all negative:

| instrument | feature | rho | CI | raw p |
|---|---|---|---|---|
| NQ | above_below_prior_close | -0.105 | [-0.162,-0.044] | 0.0003 |
| ES | overnight_return | -0.104 | [-0.165,-0.041] | 0.0003 |
| ES | above_below_prior_close | -0.100 | [-0.155,-0.043] | 0.0006 |

Interpretation (descriptive only): when the 09:29 close sits above the
prior session's RTH close (or the overnight session gained), the next
10 minutes of RTH tend to display a slightly negative closing
displacement, and vice versa — a small fade-the-gap pattern, not a
momentum pattern. Outlier-drop barely moves any of the three (rho changes
by <0.003), so this is not a single-session artifact.

**Year-by-year (the same caution as every prior generation's findings):**
all three cells are negative in 2018, 2020, 2021, 2022 but **flip
slightly positive in 2019** (rho +0.028, +0.006, +0.026 respectively), and
**2020 is again the largest-magnitude year** (rho -0.20, -0.25, -0.17) —
2-3x every other year. This is the same instability pattern seen in
generation 4's leading candidate: directionally consistent in 4 of 5
years, but with one year (2020) disproportionately driving the pooled
correlation, and one year (2019) not agreeing in sign at all.

**A separate, smaller, cross-window-stable pattern in ES only:**
`overnight_range` and the pre-open `range_5/10/15/30` features show a
positive correlation with Q_5 (rho 0.065-0.081, CI excludes zero for
overnight_range and range_5/10) — i.e., a wider overnight or pre-open
range weakly associates with the next 5 minutes' dominant excursion
favoring the upper side. This mirrors the shape (not magnitude or
instrument) of generation 4's ES range_ratio finding, though the two are
different features from different sessions and are not being combined or
compared as evidence for one another.

**All correlations are small (|rho| < 0.11) and none survive Bonferroni.**

## Coverage-level diagnostic (fixed 100/50/30/15%, not chosen post hoc)

For the NQ `above_below_prior_close` vs R_10 cell, restricting to the
strongest 50/30/15% subsets does not raise same-sign "accuracy" materially
above baseline — consistent with the underlying correlation being small;
full table in `feature_screen_full.csv`, all four coverage levels
reported for every one of the 720 cells, none selected post hoc.

## Complete null inventory

- **688 of 720 cells** are not even nominally significant at raw
  alpha=0.05; of the 32 that are, none survive Bonferroni.
- Frozen-VWAP features (Sec. 4: `dist_0929_from_vwap`,
  `normalized_dist_from_vwap`, `vwap_location_in_range`) are null
  throughout — no cell for either instrument exceeds |rho|=0.02.
- `return_acceleration_W` (tested as its own standalone feature, per
  instruction) is null for ES at every window; NQ shows a marginal
  nominal effect only at W=15 (rho -0.065 to -0.073, not Bonferroni
  significant, not replicated at any other window — exactly the kind of
  isolated, non-monotone-across-windows cell the analysis plan asks to
  flag rather than highlight).
- `close_location_W`, `signed_path_eff_W`, `relative_volume_W` (pre-open
  windows): null throughout for both instruments (|rho|<0.03 in nearly
  every cell).
- `broke_prior_rth_high_or_low` and `finished_inside_prior_rth_range`
  (Sec. 6 structural relationship variables): null to marginal-nominal
  only (ES `broke_prior_rth_high_or_low` vs Q_5, rho -0.066, not
  Bonferroni-significant); otherwise no signal.
- Horizons h=15 and h=30 are null for essentially every feature once the
  h=5/h=10 patterns (where present) have faded — the same horizon-decay
  shape observed in every previous generation of this project.

## Limitations

See `KNOWN_LIMITATIONS.md`. Chiefly: discovery-stage only (no
combinations tested, per instruction); the leading gap/overnight-return
finding is partly 2020-driven and sign-flips in 2019; 45 features are only
~4.2 effectively independent; no validation/holdout access.

## Verdict (plain English)

Overnight and pre-open ES/NQ behavior shows, at most, a **small,
horizon-decaying, partly year-concentrated** standalone correlation with
the next session's early cash-open closing displacement — largest for
whether the 09:29 close sits above or below the prior session's RTH close
and for the raw overnight return, both at h=10 (rho ~-0.10, fading by
h=15-30). A separate, smaller pattern links overnight/pre-open range to
the dominant-excursion score in ES only. **Nothing clears the
preregistered Bonferroni bar across 720 tests**, and the strongest single
result leans on one unusual year (2020) and disagrees in sign in another
(2019). This is not evidence of a standalone tradable predictor. Per
instruction, this generation does not combine these variables with each
other, with generation 4's previous-close features, or across ES/NQ; any
such combination belongs in a future research generation.

## Artifacts

`RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_OVERNIGHT.md`,
`DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
`PROGRESS.md`, `RUN_REGISTRY.csv` (92 rows); `src/{overnight_features,
build_ledger, run_analysis, analysis_utils}.py`; `tests/test_fixtures.py`
(9 tests, including a real-data DST/weekend-mapping check); ledgers
`outputs/{es,nq}_overnight_ledger.parquet` (git-ignored, reproducible),
`outputs/{es,nq}_target_missing.csv`; tables in `reports/tables/`:
`feature_screen_full.csv` (720 rows, all diagnostics),
`feature_screen_core.csv` (compact view), `effective_n_sensitivity.csv`,
`sample_summary.csv`.
