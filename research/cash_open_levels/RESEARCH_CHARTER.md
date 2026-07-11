# RESEARCH_CHARTER.md — Cash-Open Level Library (Generation 7, Part 2A)

Branch: `research/cash-open-level-library`, base `research/cash-open-path-
taxonomy` @ `796ad3f`. Preserves generations 1 (`research/vwap_shock`), 2
(`research/cash_open_discovery`), 3 (`research/cash_open_atlas`), 4
(`research/previous_close_predictor`), 5
(`research/overnight_preopen_predictor`), and 6
(`research/cash_open_taxonomy`) unchanged.

## Research classification

**Level construction only, Part 2A.** This generation defines every
candidate cash-open level causally and mechanically: its formula, its
causal availability time, its deduplication/clustering treatment, and a
matched synthetic control. It does **not** test level reactions, does not
compute touches, subsequent returns, taxonomy-class-conditional outcomes,
or profitability, and does not define entries/exits. It does not access
2023-01-01 onward. No result in this generation implies a trading signal
— it is a structural census of candidate levels, exactly as generation 3
was a census of continuous targets and generation 6 a census of path
shapes.

## Purpose

1. Build a frozen library of causally-available cash-open levels across
   four families (rolling empirical 09:30-candle excursion levels,
   frozen overnight-VWAP deviation levels, prior-session structural
   levels, overnight structural levels), each with an exact formula and
   causal-availability time.
2. Detect and report structural duplicates (levels that are the same
   value by formula, not coincidence) and empirical clustering (distinct
   levels landing numerically close together in a given session).
3. Generate a matched **generic synthetic control** for every real level
   observation, structurally unrelated to any named price, for later use
   as a placebo baseline in a future reaction-testing generation.
4. Report level counts, missingness (with reason class), structural
   duplicates, and clustering/coverage/overlap diagnostics for ES and NQ
   separately, on the 2018-2022 development partition.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged).
- `research/cash_open_taxonomy/src/taxonomy.py` (generation 6, unchanged):
  `build_scale_tables` — the causal exact-60-valid-session trailing
  median/MAD scale, `U_0930`/`D_0930` definitions — reused verbatim by
  exact file-path import for family 1. No independent re-derivation.
- Development partition 2018-01-03 -> 2022-12-30, unchanged.
- Accepted taxonomy: `research/cash-open-path-taxonomy` @ `796ad3f`
  (context only; the taxonomy itself is not used to condition any level
  or diagnostic in this generation — that is explicitly out of scope).

## Design history (for audit trail)

- Revision 1 (proposed, not implemented): six level families including a
  prior-session ATR30-band family (family 5) and a cross-session-shuffle
  placebo.
- **Revision 2 (this document, final, authorized for implementation)**:
  family 5 removed as an unapproved additional feature family (may be
  proposed separately later); placebo replaced with a generic synthetic
  control matched on instrument, session, side, horizon-exposure category,
  and normalized-distance bucket, structurally unrelated to any named
  price (`SPEC_LEVELS.md` Sec. 6). Family 6 (dynamic levels) remains
  listed-only, never implemented, as in Revision 1.

## Assumptions

Carried from generation 6 for family 1 (exact-60-valid-session causal
window, `U_0930`/`D_0930` scale basis). New for this generation: overnight
window defined as all bars of session `s` with `et_minute < 570` (the
processed data's own overnight-leg convention, confirmed chronological by
`ts_event`, not wrap-sensitive `et_minute` arithmetic); `>=30` overnight
bars required for a valid VWAP/sigma; non-early-close predecessor required
for family 3; a fixed, recorded random seed for the synthetic-control
draw. All detailed in `SPEC_LEVELS.md`.

## Falsifiers / what would make this level library incoherent

- Any family's value for session `s` changing when a bar strictly *after*
  that family's declared causal-availability cutoff is mutated — would
  indicate a leakage bug, not a market fact, and must be fixed before any
  diagnostic is trusted.
- The family-1 `mult_*_1.0` level failing to equal the trailing-median
  scale level bit-for-bit — would indicate the structural-duplicate claim
  is wrong and the dedup policy is unsound.
- A synthetic control whose value can be shown to depend on any other
  session's actual level value, or on any other real level in the same
  session — would indicate the corrected placebo design was not actually
  implemented as specified and the internal-inconsistency problem persists.
- Coverage collapsing to near-zero for any family across the whole
  development partition (as opposed to a bounded, explained warm-up/early-
  close/thin-overnight exclusion) — would indicate a bug in bar selection
  or timestamp handling, not a genuine data limitation.
