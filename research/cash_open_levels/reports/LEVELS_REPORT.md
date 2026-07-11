# Cash-Open Level Library — Report (Generation 7, Part 2A)

Branch: `research/cash-open-level-library`. Preregistration commit
`e2ef210` (`SPEC_LEVELS.md` Revision 2 — family 5 removed, placebo
replaced with generic synthetic controls). Development partition only
(2018-2022). **Level construction, causal availability, missingness,
deduplication, clustering, coverage, and overlap diagnostics only — no
touch, reaction, subsequent return, taxonomy-conditional outcome, or
profitability computation anywhere in this generation.**

## Sample

| instrument | sessions in library (union of any family) |
|---|---|
| ES | 1291 |
| NQ | 1289 |

## Level counts (families 1-4; family 5 removed, family 6 listed-only)

| instrument | family | levels | valid sessions (each level_id) |
|---|---|---|---|
| ES | family1 (mult ×4/side + mad ×3/side = 14 level_ids) | 14 | 1229 |
| ES | family2 (vwap_on j∈{-2..2} = 5 level_ids) | 5 | 1291 |
| ES | family3 (prior_high/low/close = 3 level_ids) | 3 | 1245 |
| ES | family4 (overnight_high/low = 2 level_ids) | 2 | 1291 |
| NQ | family1 | 14 | 1227 |
| NQ | family2 | 5 | 1289 |
| NQ | family3 | 3 | 1243 |
| NQ | family4 | 2 | 1289 |

Every level_id within a family has an identical valid-session count
(the family's own validity gate applies uniformly to all of its levels),
confirmed in `reports/tables/level_counts.csv` (48 rows: 2 instruments ×
4 families × their level_ids).

## Missingness

| instrument | family | n_total (level rows) | n_missing | missing_frac | reason |
|---|---|---|---|---|---|
| ES | family1 | 18074 | 868 | 4.80% | 60-session warm-up (exact-window causal scale invalid) |
| ES | family2 | 6455 | 0 | 0.00% | <30 valid overnight bars (never triggers for ES/NQ) |
| ES | family3 | 3873 | 138 | 3.56% | predecessor session was an early close |
| ES | family4 | 2582 | 0 | 0.00% | no/thin overnight bars (never triggers for ES/NQ raw levels) |
| NQ | family1 | 18046 | 868 | 4.81% | same as ES |
| NQ | family2 | 6445 | 0 | 0.00% | same as ES |
| NQ | family3 | 3867 | 138 | 3.57% | same as ES |
| NQ | family4 | 2578 | 0 | 0.00% | same as ES |

Family 1's missingness (~62 sessions/instrument) is the same 60-session
causal warm-up cost already documented in generation 6 (ES 1291→1229, NQ
1289→1227 — consistent in shape with generation 6's ES 1269→1229/NQ
1267→1227, computed on a slightly different total-session base). Family
3's ~46 missing sessions/instrument are early-close predecessors (holiday-
adjacent half sessions), never imputed or substituted. Families 2 and 4
never hit the <30-overnight-bar floor anywhere in the ES/NQ development
partition — both instruments' overnight legs are consistently liquid
enough. Full detail in `reports/tables/missingness.csv`.

## Structural duplicates

Confirmed programmatically (bit-for-bit): `mult_U_1.0` and `mult_D_1.0`
(family 1) are exactly the trailing-median (`scale_U`/`scale_D`) level,
i.e. structurally identical to "the trailing p50 quantile level" — `
max_abs_diff = 0.0` for both sides, both instruments (`is_structural_
duplicate = True` in all 4 rows of `reports/tables/structural_duplicates.
csv`). This single known case is reported once with both aliases, never
double-counted in the level catalogue above (no separate `quantile_50`
level_id exists in the library).

## Empirical clustering

Per-session pairwise clustering (`|value_a - value_b| < 0.1 * scale`,
side-appropriate `scale_U`/`scale_D`/average) across all valid level pairs
(`reports/tables/clustering_summary.csv`, 20 rows):

| instrument | busiest pair | clustered_rate | quietest pair | clustered_rate |
|---|---|---|---|---|
| ES | family1×family1 | 2.71% | family4×family4 | 0.08% |
| NQ | family1×family1 | 2.54% | family4×family4 | 0.08% |

Family1×family1 pairs (different multiplier/MAD levels within the same
excursion family) cluster most often — expected, since they all derive
from the same underlying `scale_U`/`scale_D` and can land close together
in low-volatility sessions. Cross-family clustering is rarer (0.4%-1.7%),
and family4×family4 (overnight_high vs overnight_low, one pair per
session) is clustered in essentially no sessions (a session where the
overnight high and low sit within 10% of scale of each other would be an
extremely thin overnight range). Per-session overlap ("crowdedness":
count of clustered pairs in that session) averages 3.8 (ES) / 4.1 (NQ)
pairs per session, ranging 0-26 (`reports/tables/overlap_per_session.csv`).

## Coverage

| instrument | year | sessions | all 4 families simultaneously valid |
|---|---|---|---|
| ES | 2018 | 257 | 189 (73.5%) |
| ES | 2019 | 258 | 249 (96.5%) |
| ES | 2020 | 259 | 249 (96.1%) |
| ES | 2021 | 259 | 251 (96.9%) |
| ES | 2022 | 258 | 250 (96.9%) |
| NQ | 2018 | 257 | 189 (73.5%) |
| NQ | 2019 | 257 | 248 (96.5%) |
| NQ | 2020 | 258 | 248 (96.1%) |
| NQ | 2021 | 259 | 251 (96.9%) |
| NQ | 2022 | 258 | 250 (96.9%) |

2018 is the only year with materially reduced all-family coverage, driven
entirely by family 1's 60-session warm-up (the very start of the
development partition) — not a data-quality problem, and consistent with
generation 6's own 2018 warm-up cost. 2019-2022 all sit at 96%+ coverage
for both instruments. Full table in `reports/tables/coverage.csv`.

## Synthetic controls (corrected placebo)

One synthetic control generated per real-level observation (30984 ES /
30936 NQ rows, matching the real-level tables 1:1), matched on instrument,
side, horizon-exposure category (`INTRADAY_ROLLING`/`PRE_OPEN`/
`PRIOR_SESSION`), and normalized-distance bucket. Each synthetic value is
priced only from that session's own open and side-appropriate scale (both
already causally known at 09:30), using a normalized distance drawn
uniformly from the matched bucket's own interval with a fixed, recorded
seed (`SYNTHETIC_SEED = 20260711`) — never from any other session's actual
level value or any other real level in the same session. Verified by
test: every synthetic draw's normalized distance falls inside its real
counterpart's own bucket interval, the draw is reproducible under the
fixed seed, and (spot-checked) synthetic values are not a copy of the real
values they are matched to.

## Leakage safeguards — verified

- Family 1: mutating a session's own 09:30 bar does not change that
  session's own scale (reuses generation 6's already-audited
  `build_scale_tables`); mutating a mid-window predecessor session's bar
  does change a later session's scale (confirms genuine causal inclusion,
  not an inert no-op).
- Family 2/4: mutating a session's own RTH bar (>=09:30) does not change
  that session's overnight VWAP/sigma/structural levels (which only read
  strictly-pre-09:30 bars).
- Family 3: mutating a session's own RTH bar does not change that
  session's own `prior_*` levels (which read only the immediately
  preceding session); it correctly does change the *next* session's
  `prior_*` levels.
- All four checks are automated tests (`tests/test_fixtures.py`), not
  spot-checks alone.

## Artifacts

`RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_LEVELS.md` (Revision 2),
`DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
`PROGRESS.md`, `RUN_REGISTRY.csv`; `src/{levels, diagnostics,
build_levels}.py`; `tests/test_fixtures.py` (12 tests); ledgers
`outputs/{es,nq}_{fam1,fam2,fam3,fam4,levels_long,synthetic_controls}.
parquet` (git-ignored, reproducible); tables in `reports/tables/`:
`level_counts.csv`, `missingness.csv`, `structural_duplicates.csv`,
`clustering_summary.csv`, `overlap_per_session.csv`, `coverage.csv`.
