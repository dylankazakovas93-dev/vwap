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
- 2026-07-12: CORRECTION applied after Dylan's post-implementation audit
  found the shipped library did not match the approved candidate set.
  SPEC_LEVELS.md Revision 3: added family 1 raw trailing-60-session causal
  quantiles p25/p75/p90/p95 (up/down, 8 ids; p50 excluded, alias-only of
  mult_U_1.0/mult_D_1.0); family 2 j=±3 sigma bands (2 ids); family 3
  prior_rth_mid/prior_rth_vwap (2 ids); family 4 overnight_mid/
  overnight_open (2 ids, VWAP still cross-referenced from family 2, never
  recomputed). prior_settlement_open explicitly RETRACTED (was never
  approved; its appearance in Revision 2 was a drafting error).
  overnight_high_dev_vwap/overnight_low_dev_vwap confirmed unchanged as
  diagnostic distances, not level_ids. 7 new tests added (19 total, all
  passing): quantile causal-window + p50-exclusion, p50-alias
  confirmation, 3-sigma band formula, prior_rth_mid/vwap causal
  no-lookahead + early-close exclusion, prior_settlement_open
  non-implementation, overnight_mid/open + VWAP cross-reference (not
  recomputed), dev_vwap fields' exclusion from LEVEL_COLUMNS. Ledgers
  rebuilt: ES/NQ now 30 level_ids/instrument (up from 24); ES 49058 / NQ
  48982 level rows and matching synthetic-control rows (up from
  30984/30936). Level counts, missingness, structural duplicates, and
  coverage are numerically unchanged in shape (new levels share existing
  families' validity gates); clustering/overlap diagnostics rerun and
  scale up mechanically with the larger per-session level set (mean
  clustered pairs/session 8.9 ES / 10.1 NQ, up from 3.8/4.1 -- a
  consequence of more pairs to test, not tighter clustering per pair).
  LEVELS_REPORT.md amended in place with corrected figures.
- 2026-07-12: CORRECTION (documentation only, no code/data change).
  Dylan caught a count contradiction: SPEC_LEVELS.md Revision 3 and
  LEVELS_REPORT.md stated family 1 had 14 level_ids and the library
  totaled 30 level_ids/instrument, but family 1's own formula list (8
  mult + 6 mad + 8 quantile) sums to 22. Verified against ground truth:
  `LEVEL_COLUMNS` (code), `level_counts.csv` (76 rows = 2 instruments x 38
  level_ids), and the pairwise-clustering row count (`C(22,2)=231 x 1229`
  ES sessions `= 283,899`, exactly matching `clustering_summary.csv`'s
  family1xfamily1 row) all independently confirm 22/family1 and 38/
  instrument total -- the implementation was correct throughout; only the
  prose in SPEC_LEVELS.md (Revision 3->4) and LEVELS_REPORT.md was wrong
  and has been corrected. 2 new regression tests added (21 total, all
  passing): `test_level_columns_exact_inventory_count_by_family` and
  `test_level_counts_table_matches_level_columns_inventory`, locking the
  exact per-family and total level_id count against future drift.
