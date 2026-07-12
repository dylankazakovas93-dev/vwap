# Cash-Open Level Library — Report (Generation 7, Part 2A)

Branch: `research/cash-open-level-library`. Preregistration commit
`e2ef210` (`SPEC_LEVELS.md` Revision 2 — family 5 removed, placebo
replaced with generic synthetic controls). Development partition only
(2018-2022). **Level construction, causal availability, missingness,
deduplication, clustering, coverage, and overlap diagnostics only — no
touch, reaction, subsequent return, taxonomy-conditional outcome, or
profitability computation anywhere in this generation.**

## Amendment (2026-07-12): implementation-fidelity correction (Revision 3)

A post-implementation audit (Dylan) found the shipped library did not
match the approved candidate set. Corrected in `SPEC_LEVELS.md` Revision 3
and this report:

- **Added** (14 new level_ids): family 1 raw trailing-60-session causal
  quantiles `q_{U,D}_{p25,p75,p90,p95}` (8; `p50` intentionally excluded —
  alias of `mult_U_1.0`/`mult_D_1.0` only); family 2 `vwap_on_j±3` (2);
  family 3 `prior_rth_mid`, `prior_rth_vwap` (2); family 4 `overnight_mid`,
  `overnight_open` (2).
- **Retracted, not added**: `prior_settlement_open` — it appeared in
  Revision 2's text but was never part of the approved candidate set; that
  was a drafting error, not an instruction from Dylan, and it remains
  unimplemented.
- **Confirmed unchanged**: `overnight_high_dev_vwap`/`overnight_low_dev_
  vwap` remain diagnostic distances only, not level_ids; family 4 still
  cross-references family 2's `vwap_on` rather than recomputing an
  independent overnight VWAP.

All figures below are from the corrected (Revision 3) implementation.

## Amendment (2026-07-12): documentation arithmetic correction (Revision 4)

Dylan caught a count contradiction between this report's own family-1
formula description (8 multiplier + 6 MAD + 8 quantile level_ids = 22)
and the table below, which previously stated family 1 had 14 level_ids
and a total library of 30. **This was a documentation transcription
error only** — the implementation, `LEVEL_COLUMNS`, and every generated
table (`level_counts.csv`, `clustering_summary.csv`, etc.) were already
correct at 22/family 1 and 38/instrument total, independently confirmed
via the pairwise-clustering row count (`C(22,2)=231 × 1229` ES sessions
`= 283,899`, exactly matching `clustering_summary.csv`'s `family1×family1`
row). The table and totals below are now corrected to match the
already-correct implementation; two new regression tests
(`test_level_columns_exact_inventory_count_by_family`,
`test_level_counts_table_matches_level_columns_inventory`) lock the exact
count going forward.

## Sample

| instrument | sessions in library (union of any family) |
|---|---|
| ES | 1291 |
| NQ | 1289 |

## Level counts (families 1-4; family 5 removed, family 6 listed-only) — corrected, 38 level_ids

| instrument | family | levels | valid sessions (each level_id) |
|---|---|---|---|
| ES | family1 (mult ×4/side + mad ×3/side + quantile ×4/side = 22 level_ids) | 22 | 1229 |
| ES | family2 (vwap_on j∈{-3..3} = 7 level_ids) | 7 | 1291 |
| ES | family3 (prior_high/low/close/rth_mid/rth_vwap = 5 level_ids) | 5 | 1245 |
| ES | family4 (overnight_high/low/mid/open = 4 level_ids) | 4 | 1291 |
| NQ | family1 | 22 | 1227 |
| NQ | family2 | 7 | 1289 |
| NQ | family3 | 5 | 1243 |
| NQ | family4 | 4 | 1289 |

Total: **38** level_ids/instrument (22+7+5+4), up from 24 before the
Revision 3 correction (this table previously, and wrongly, said 30 — see
the Revision 4 amendment above). Every level_id within a family has an
identical valid-session count (the family's own validity gate applies
uniformly to all of its levels), confirmed in `reports/tables/
level_counts.csv` (76 rows: 2 instruments × (22+7+5+4) level_ids).

## Missingness

| instrument | family | n_total (level rows) | n_missing | missing_frac | reason |
|---|---|---|---|---|---|
| ES | family1 | 28402 | 1364 | 4.80% | 60-session warm-up (exact-window causal scale/quantile invalid) |
| ES | family2 | 9037 | 0 | 0.00% | <30 valid overnight bars (never triggers for ES/NQ) |
| ES | family3 | 6455 | 230 | 3.56% | predecessor session was an early close |
| ES | family4 | 5164 | 0 | 0.00% | no/thin overnight bars (never triggers for ES/NQ raw levels) |
| NQ | family1 | 28358 | 1364 | 4.81% | same as ES |
| NQ | family2 | 9023 | 0 | 0.00% | same as ES |
| NQ | family3 | 6445 | 230 | 3.57% | same as ES |
| NQ | family4 | 5156 | 0 | 0.00% | same as ES |

Family 1's missingness (~62 sessions/instrument) is the same 60-session
causal warm-up cost already documented in generation 6 (ES 1291→1229, NQ
1289→1227 — consistent in shape with generation 6's ES 1269→1229/NQ
1267→1227, computed on a slightly different total-session base); the new
quantile levels share the identical warm-up gate as the multiplier/MAD
levels, so family 1's missing fraction is unchanged by the correction.
Family 3's ~46 missing sessions/instrument are early-close predecessors
(holiday-adjacent half sessions), never imputed or substituted — this
now also covers `prior_rth_mid`/`prior_rth_vwap`, gated identically to
`prior_high`/`prior_low`/`prior_close`. Families 2 and 4 never hit the
<30-overnight-bar floor anywhere in the ES/NQ development partition —
both instruments' overnight legs are consistently liquid enough; the new
`overnight_mid`/`overnight_open` levels only require >=1 overnight bar
(like `overnight_high`/`overnight_low`) and so are also never missing.
Full detail in `reports/tables/missingness.csv`.

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
(`reports/tables/clustering_summary.csv`, 20 rows — the new levels add
more pairs per session but the same 10 family-pair groupings):

| instrument | busiest pair | clustered_rate | quietest pair | clustered_rate |
|---|---|---|---|---|
| ES | family1×family1 | 2.49% | family2×family2 | 0.08% |
| NQ | family1×family1 | 2.54% | family2×family2 | 0.08% |

Family1×family1 pairs (now including the quantile ladder alongside
multiplier/MAD) cluster most often — expected, since they all derive from
the same underlying `scale_U`/`scale_D`/quantile distribution and can land
close together in low-volatility sessions. Cross-family clustering is
rarer (0.5%-1.4%), and family2×family2 (the vwap_on sigma-band pairs) is
clustered in essentially no sessions (adjacent sigma bands only coincide
when `sigma_on` is near zero). Per-session overlap ("crowdedness": count
of clustered pairs in that session) averages 8.9 (ES) / 10.1 (NQ) pairs
per session, ranging 0-62 (`reports/tables/overlap_per_session.csv`) — up
from the pre-correction 3.8/4.1, entirely a mechanical consequence of
having 38 level_ids/session instead of 24 (more pairs to test), not a
change in how tightly any given pair of levels sits together.

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

One synthetic control generated per real-level observation (49058 ES /
48982 NQ rows post-correction, up from 30984/30936, matching the
real-level tables 1:1), matched on instrument,
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

`RESEARCH_CHARTER.md`, `DATA_CONTRACT.md`, `SPEC_LEVELS.md` (Revision 4,
corrected), `DECISIONS.md`, `KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`,
`PROGRESS.md`, `RUN_REGISTRY.csv`; `src/{levels, diagnostics,
build_levels}.py`; `tests/test_fixtures.py` (21 tests: 7 added for the
Revision 3 level correction, 2 added for the Revision 4 inventory-count
lock); ledgers
`outputs/{es,nq}_{fam1,fam2,fam3,fam4,levels_long,synthetic_controls}.
parquet` (git-ignored, reproducible); tables in `reports/tables/`:
`level_counts.csv`, `missingness.csv`, `structural_duplicates.csv`,
`clustering_summary.csv`, `overlap_per_session.csv`, `coverage.csv`.
