# CANDIDATE_MANIFEST.md — auction value reacceptance and rotation engine

Frozen at the pre-OOS gate per `SPEC_AUCTION_VALUE.md` section 10. This
file is committed and pushed **before** the OOS pipeline is enabled, per
`DECISIONS.md` #9 (the OOS pipeline refuses to run without this file
present in the committed tree). Development results underlying this
manifest were computed from `src/pipeline_dev.py::select_candidates`,
NQ, dev years `2018, 2020, 2022, 2024` only — no 2019/2021/2023/2025/2026
data was read to produce this file.

## Development grid summary

- 3,456 grid cells evaluated (432 parameter combinations x 4 profile
  mappings x 2 sides).
- 72 cells cleared the raw count floor (>=300 treatment, >=150 matched
  control).
- 7 cells passed candidate criteria 1-7, 11, 12 (first pass).
- 6 of those 7 also passed the second-pass sensitivity criteria 8-10
  (bin-width support, profile-model support, adjacent-parameter-sign
  stability) — see per-cell detail below.

**One qualifying candidate family**, and it is exactly the mechanism
this generation set out to test: `M2_LONDON_TO_NY`, short side. In
words — NY RTH price attempts to break above the *prior London
session's* value-area high (`VAH`), fails to sustain the breakout
(closes back inside London's value area within `R1_ONE_CLOSE`), and is
more likely to subsequently rotate down to touch London's POC before
re-crossing back below London's VAH, compared to a matched bar that was
simply sitting inside London's value area with no breach in the last 6
hours.

No qualifying family was found on the long side, nor on any of
`M1_ASIA_TO_LONDON`, `M3_RTH_TO_OVERNIGHT`, or `M4_RTH_TO_NEXT_RTH` — see
`KNOWN_LIMITATIONS.md` (to be updated at final report time) for the
asymmetry discussion.

## Primary outcome and horizon (frozen, unchanged from `SPEC_AUCTION_VALUE.md` sec. 6, 8)

- Outcome: `POC_REACHED_BEFORE_REDISCOVERY`.
- Primary horizon: 60 minutes (30/60 minute directional consistency
  required by criterion 7; 15/120 reported as secondary robustness,
  never substituted as primary).
- Primary metric: difference in `POC_FIRST` rate among resolved,
  non-ambiguous outcomes (`POC_FIRST` vs `REDISCOVERY_FIRST` only;
  `SAME_BAR_AMBIGUOUS`/`NEITHER`/`INCOMPLETE_HORIZON` excluded from the
  denominator), canonical event minus `MATCHED_INSIDE_STATE` control,
  matched-stratified permutation (10,000 draws, seed `20260713`), BH
  correction within the `M2_LONDON_TO_NY` mapping family.

## Control matching rules (frozen, unchanged from `SPEC_AUCTION_VALUE.md` sec. 7)

Matched on: clock-time stratum (ET hour of confirmation/anchor bar),
value-area-width tercile, profile-age (freshness) tercile,
distance-from-POC tercile, realized-volatility (causal ATR20) tercile —
all tercile cutoffs frozen on development-year data only
(`outputs/NQ_frozen_bands.json`), reused unchanged for OOS. Control is
`MATCHED_INSIDE_STATE`: the last bar in the active window inside the
same value-area half with no edge breach (either side) in the trailing
6 hours.

## Exact allowed parameter definitions (the qualifying neighborhood — all 6 evaluated in OOS)

All rows: `mapping_id=M2_LONDON_TO_NY`, `side=short`,
`C=R1_ONE_CLOSE` (breach-and-reacceptance confirmed by the first
1-minute close `<= VAH - 1 tick`), PRIMARY profile config
(`UNIFORM_RANGE`, bin width 0.25, VA% 70%).

| # | A (breach depth) | B (max bars outside) | D (POC-distance floor) | E (freshness cap, h) | Dev pooled diff (h60) | Dev BH q | n_treat (dev) | n_control_matched (dev) | Role |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `A_GE_1_TICK` | 5 | 0.20 | none | +0.174 | 0.0066 | 352 | 240 | **PRIMARY** (largest matched sample) |
| 2 | `A_GE_1_TICK` | 5 | 0.20 | 4.0 | +0.187 | 0.0044 | 326 | 164 | support |
| 3 | `A_GE_1_TICK` | 5 | 0.20 | 6.0 | +0.179 | 0.0044 | 345 | 187 | support |
| 4 | `A_GE_1_TICK` | 3 | 0.20 | 6.0 | +0.204 | 0.0044 | 307 | 160 | support |
| 5 | `A_GE_1_TICK` | 3 | 0.20 | none | +0.185 | 0.0092 | 313 | 218 | support |
| 6 | `A_GE_5PCT_VA` | 5 | 0.10 | none | +0.082 | 0.0660 | 305 | 284 | support (weaker, still passed all 12) |

All 6 rows: positive in all 4 development years (2018/2020/2022/2024),
same directional sign at 30- and 60-minute horizons, worst single
development-year effect never below +0.05, no single development year
contributing more than 46% of pooled effect mass, supported by >=2 bin
widths and by >=1 sensitivity profile model (`TYPICAL_PRICE_ROW` and/or
`CLOSE_PRICE_ROW`), supported by >=2 adjacent-parameter-definition
cells with the same positive sign, and the candidate's matched-treatment
POC-distance distribution is not materially closer to POC than its
matched control's (positive-control check on the matching itself).

Full per-cell detail (year-by-year effects, permutation p-values,
sample counts) is in `outputs/candidate_grid_detail.json`.

## OOS evaluation plan (2019, 2021, 2023, 2025 only, evaluated exactly once)

`src/oos_pipeline.py` will evaluate all 6 rows above, using the exact
same code path (`profiles.build_profile`, `mapping.build_mappings`,
`events.scan_profile_side`, `outcomes.add_primary_outcomes`,
`controls.build_matched_inside_state_controls`,
`permutation.stratified_permutation_test`) and the exact same frozen
tercile bands from `outputs/NQ_frozen_bands.json`, against
`data.OOS_YEARS = (2019, 2021, 2023, 2025)`. `2026` is never read by
this pipeline (`data.filter_partition` raises on any request that
includes it). The pipeline refuses to execute unless this file
(`CANDIDATE_MANIFEST.md`) is present in the git-committed tree.

### OOS pass criteria (verbatim from `SPEC_AUCTION_VALUE.md` section 11 — all 9 required)

1. Positive pooled OOS effect (treatment minus `MATCHED_INSIDE_STATE`
   control, `POC_FIRST` rate at h60).
2. Pooled OOS effect >= half the development effect for that row.
3. Positive in >= 3 of 4 OOS years (2019/2021/2023/2025).
4. OOS BH q <= 0.10 (corrected across the 6 rows evaluated in OOS,
   the same family-scoped correction rule as development).
5. Adequate samples (same floors as development: >=300 treatment,
   >=150 matched control, applied to the pooled OOS population).
6. Same-direction persistence at 30- and 60-minute horizons.
7. No single OOS year entirely driving the result (same `n_year *
   |effect_year|` share formula as development criterion 12, capped
   below 50%).
8. Directional consistency (positive effect) under >= 1 alternate
   profile construction (`TYPICAL_PRICE_ROW` or `CLOSE_PRICE_ROW`,
   PRIMARY bin width), computed on the OOS partition only for rows
   that already pass criteria 1-7 above.
9. Second-stage `POC_TO_OPPOSITE_EDGE_COMPLETION` reported for
   informational purposes but **not required** for a pass verdict.

A row is a **PASS** only if it clears all 9. The family verdict is
reported per-row; the PRIMARY row (#1) is the headline result.

After this manifest is committed and pushed, and `oos_pipeline.py`
confirms no `outputs/oos_*` file exists, OOS is run exactly once. No
threshold, definition, mapping, side, rule, or subgroup is changed
after that point regardless of outcome, per `SPEC_AUCTION_VALUE.md`
section 12.
