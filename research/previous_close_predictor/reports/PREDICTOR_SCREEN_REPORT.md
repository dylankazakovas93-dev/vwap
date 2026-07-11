# Previous-Close Predictor Discovery — Report (Generation 4)

Branch: `research/previous-close-predictor-discovery`, base
`research/cash-open-target-atlas` @ `201896d`. Development partition only
(2018-2022). **Standalone-feature discovery screen only — no strategy,
model, combination, or tradable edge is claimed anywhere below.**

## Sample

| instrument | primary rows | excluded: predecessor early close | excluded: no predecessor |
|---|---|---|---|
| ES | 1240 | 45 | 1 |
| NQ | 1236 | 47 | 1 |

Early-close predecessor dates match CME's published equity-index-futures
early-close calendar almost exactly (MLK Day, Presidents Day, Memorial
Day, day before/of July 4th, Labor Day, Thanksgiving + day after,
Christmas Eve — verified spot-check, ~8-9/year, 43 total for ES 2018-2022)
— a real market-structure fact, not a data artifact.

## Test count and multiple-testing accounting

**480 elementary tests** registered exactly as preregistered (2 instruments
x 5 features x 6 windows x 4 horizons x 2 targets), each a row in
`reports/tables/feature_screen_full.csv` and logged in `RUN_REGISTRY.csv`
(62 rows: one per instrument/feature/window pass, covering all
horizon/target cells, plus 2 effective-N rows).

**Zero of the 480 cells clear the declared Bonferroni threshold**
(alpha = 0.05/480 = 1.04e-4). The smallest raw p-value observed is
~0.0008 (NQ, norm_ret window=60 vs Q_5), well short of Bonferroni
significance.

**Effective-N sensitivity** (SPEC Sec. 9): the 30 within-instrument
features (5 feature-families x 6 windows) are highly mutually correlated
— average pairwise |Spearman| = 0.40 (ES) / 0.385 (NQ) — giving an
effective feature count of only **~2.4 (ES) / ~2.5 (NQ)** out of 30. The
six windows of the same feature family are largely redundant with each
other, so the true multiple-testing burden is far smaller than 480 raw
cells; even so, **no cell survives even a much looser effective-test
correction with any economically meaningful margin** given the raw effect
sizes below.

## Strongest evidence (still modest, reported honestly)

**NQ: previous session's final 30-60 minute normalized return / signed
path efficiency vs. next session's h=5 dominant-excursion score (Q_5).**
Spearman rho -0.099 (window=60, CI [-0.153,-0.042], raw p~0.0008); -0.093
(window=30); similar magnitude for signed_efficiency at the same windows.
Quintile means are monotone (quintile-rank correlation -0.7): highest
prior-return quintile has mean Q_5 = -0.073, lowest quintile +0.126 —
i.e., a strong upward (or cleanly efficient) move in NQ's last hour before
the prior close weakly associates with the NEXT session's earliest
cash-open excursion favoring the **lower** side, on average. This decays
sharply with horizon: rho -0.099 (h=5) -> -0.056 (h=10, no longer
CI-significant) -> -0.042 (h=15) -> -0.021 (h=30, indistinguishable from
noise) — the same fade-with-horizon shape seen in every prior generation
of this project.

**ES: range_ratio (previous-close range relative to trailing median) vs.
Q_5, stable across ALL SIX windows.** Spearman rho 0.059-0.075, CI
excludes zero at 5 of 6 windows (marginal at W=10), quintile monotonicity
strongly positive (0.7-0.9) at every window — i.e., a previous session
with an unusually WIDE final-close range (at any lookback from 1 to 60
minutes) weakly associates with the next session's early cash-open
excursion favoring the **upper** side. Unlike the NQ finding, this is
remarkably uniform across the entire window domain rather than
concentrated at one or two windows — consistent with it reflecting a
persistent "previous-session volatility level" property rather than a
specific-window artifact, but the magnitude (rho ~0.06-0.07) is smaller
than the NQ effect and the two instruments do not show the same feature
or the same sign, which weakens any unified interpretation.

**Both are far below Bonferroni significance and both are small in
absolute correlation (|rho| < 0.10).**

## Coverage-level diagnostic (fixed 100/50/30/15%, not chosen post hoc)

For the NQ norm_ret_60-vs-Q_5 cell, restricting to the strongest 50/30/15%
of |feature| observations does **not** raise sign-agreement accuracy above
50% (47.2% / 45.2% / 39.3% / 37.4% across 100/50/30/15% coverage) — because
the relationship is negative (feature-positive predicts target-negative),
naive same-sign "accuracy" understates the directional signal; read in
reverse-sign terms this is ~53-63% directional agreement at tighter
coverage, in the same direction as the Spearman sign, but this is a
description of the same modest correlation already reported, not
additional independent evidence, and is not being proposed as an accuracy
metric for any rule.

## Bullish/bearish (previous-close) symmetry

For the lead NQ cell, mean Q_5 given a positive previous-close return
(0.077) vs. a negative one (0.017 combined estimate via the pos/neg
group means), difference -0.060, day-block-bootstrap CI [-0.119,-0.0003]
— barely excludes zero, i.e. the asymmetry itself is only marginally
distinguishable from a symmetric response.

## Year-by-year stability (the most important caution)

Per-year Spearman (NQ, norm_ret_60 vs Q_5): 2018 -0.060, 2019 **+0.024**
(sign flips), 2020 **-0.236** (COVID year, much larger than any other
year), 2021 -0.099, 2022 -0.125. The sign is negative in 4 of 5 years but
2020 alone is 2-4x larger than every other year — **this raises a real
concern that the pooled 2018-2022 correlation is partly driven by one
unusual (COVID-volatility) year**, not a stable cross-year phenomenon.
This is exactly the kind of concentration the discovery protocol asks to
surface rather than paper over. Dropping the single largest-|feature|
session moves the pooled rho from -0.0988 to -0.0978 (outlier-influence
check) — negligible change, so it is not one extreme session, but the
2020 *year* still carries a disproportionate share of the pooled effect.

## Complete null inventory

- **474 of 480 cells** show |Spearman rho| that does not survive
  Bonferroni, and the great majority (>400) are not even nominally
  significant at raw alpha=0.05.
- `close_location_W` and `volume_ratio_W`: no cell for either feature
  exceeds |rho|=0.02 for ES; NQ's close_location_60 vs Q_5 reaches -0.075
  (nominal but not Bonferroni-significant) — otherwise null throughout.
- `signed_efficiency_W` largely mirrors `norm_ret_W` in sign and magnitude
  for NQ (expected, since the two are highly correlated features per the
  effective-N table) and is null for ES.
- Horizons h=15 and h=30 are null for every feature/window/instrument
  combination once the h=5 pattern (where it exists) has faded.
- R_h (closing displacement) shows uniformly weaker and less consistent
  correlations than Q_h (dominant-excursion score) across the whole
  screen — the previous-close window features relate more to which side
  of the open the next session's early excursion favors than to the
  signed magnitude of the close-to-open drift itself.

## Limitations

See `KNOWN_LIMITATIONS.md`. Chiefly: discovery-stage only (no
interactions tested, per instruction); 2020's disproportionate
contribution to the one candidate NQ finding; the 30 features' high
mutual correlation means the six windows are not adding six independent
pieces of evidence; no validation/holdout access.

## Verdict (plain English)

Previous-session closing-window behavior shows, at most, a **small,
horizon-decaying, partly year-concentrated** standalone correlation with
the next session's early cash-open dominant-excursion score — largest for
NQ's last-30/60-minute return and path efficiency at h=5 (rho ~-0.09 to
-0.10) and, separately and more uniformly across windows but smaller, for
ES's relative-range feature (rho ~0.06-0.07). **Nothing clears the
preregistered Bonferroni bar across 480 tests**, and the strongest single
result leans heavily on one unusual year. This is not evidence of a
standalone tradable predictor; per instruction, any further work on these
two candidate feature families (window x horizon combination, the
2020-dependence question, interaction with other already-studied
variables) belongs in a future research generation, not in this one.

## Artifacts

`RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_PREDICTOR.md`,
`DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
`PROGRESS.md`, `RUN_REGISTRY.csv` (62 rows); `src/{prev_close_features,
build_ledger, run_analysis, analysis_utils}.py`; `tests/test_fixtures.py`
(9 tests); ledgers `outputs/{es,nq}_predictor_ledger.parquet` (git-ignored,
reproducible), `outputs/{es,nq}_exclusions.csv`,
`outputs/{es,nq}_target_missing.csv`; tables in `reports/tables/`:
`feature_screen_full.csv` (480 rows, all diagnostics), `feature_screen_core.csv`
(compact view), `effective_n_sensitivity.csv`, `sample_summary.csv`.
