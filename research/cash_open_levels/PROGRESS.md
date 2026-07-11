# PROGRESS.md — generation 7 (cash-open level library)

- 2026-07-11: New branch created from research/cash-open-path-taxonomy @
  796ad3f. Revision 1 of the level-library design (proposed in-chat, not
  committed) was revised per two corrections: family 5 (prior-session
  ATR30 bands) removed as an unapproved additional feature family; the
  placebo scheme replaced with a generic synthetic control matched on
  instrument/session-side/horizon-exposure-category/normalized-distance-
  bucket, structurally unrelated to any named price. RESEARCH_CHARTER.md,
  DATA_CONTRACT.md, SPEC_LEVELS.md (Revision 2, final), DECISIONS.md,
  KNOWN_LIMITATIONS.md, PROJECT_STATUS.md committed before any
  development-partition result was viewed (commit e2ef210).
- 2026-07-11: Engine built (levels.py: family 1 via generation-6
  build_scale_tables file-path import + multiplier/MAD ladders; family 2
  frozen overnight VWAP/sigma bands; family 3 prior-session structural
  levels with early-close exclusion; family 4 overnight structural levels
  cross-referenced with family 2's VWAP; generic synthetic-control
  generator with fixed seed. diagnostics.py: level counts, missingness,
  structural-duplicate confirmation, empirical clustering, coverage,
  overlap. build_levels.py: orchestration). 12 passing tests (causal
  no-lookahead for families 1/2/3, exact VWAP formula, 30-bar threshold,
  early-close exclusion, structural-duplicate confirmation, clustering
  sanity, synthetic-control bucket-matching/reproducibility/independence,
  ES/NQ separation). Ledgers: ES 1291 sessions / 30984 level rows, NQ 1289
  / 30936 (union of any family; family 1 valid for 1229/1227 after the
  60-session warm-up, consistent with generation 6). Full diagnostics run:
  level_counts, missingness (family1 ~4.8% warm-up, family3 ~3.6%
  early-close, family2/family4 0% — never hit the 30-bar floor for
  ES/NQ), structural_duplicates (mult_U/D_1.0 confirmed bit-for-bit
  identical to the trailing median, both instruments), clustering_summary
  (family1×family1 clusters most at ~2.6-2.7%, family4×family4 least at
  ~0.08%), coverage (96%+ all-family coverage 2019-2022, reduced in 2018
  only by family 1's warm-up), overlap_per_session (mean 3.8-4.1 clustered
  pairs/session). LEVELS_REPORT.md committed. No touches, reactions,
  subsequent returns, taxonomy-conditional outcomes, or profitability
  computed anywhere in this generation.
