# Family A Distance-Match Audit (Part 2B-1, read-only audit)

Branch `research/cash-open-level-interactions`. Audited commit `bf0426b`
(original Family A results, unmodified). This audit is read-only: it does
not redesign the study, generate new controls, recompute Family A's
touch-rate statistics, run any post-touch hypothesis, access 2023+, or
begin taxonomy-conditioned analysis. It reads the already-committed
`O_0930`/`scale_U`/`scale_D`/`V_real`/`V_synth`/eligibility fields from
`outputs/{es,nq}_levels.parquet` and the committed
`reports/tables/primary_family_a_results.csv`, and adds one new table:
`reports/tables/family_a_distance_match_audit.csv` (76 rows, one per
instrument × level_id). No original result file was changed. No audit
mismatch was found between this audit's recount of
`n_mutually_touch_eligible` and the committed Family A table's own count
(`audit_mismatch` column is empty on every row).

## 1. Classification counts (76 rows)

| classification | n |
|---|---|
| `VALID_DISTANCE_MATCH` | 12 |
| `QUESTIONABLE_DISTANCE_MATCH` | 4 |
| `INVALID_DISTANCE_MATCH` | 60 |

## 2. Original 55 Bonferroni survivors remaining valid after the audit

**0 of 55.** None of the original Family A Bonferroni survivors carry a
`VALID_DISTANCE_MATCH` control. Of the 55: 53 are `INVALID_DISTANCE_MATCH`,
2 are `QUESTIONABLE_DISTANCE_MATCH` (ES `q_D_p75`, ES `q_U_p75` — both
fail only the tightened `|SMD|≤0.20` valid threshold, not any invalid
threshold). The 12 rows that ARE `VALID_DISTANCE_MATCH` (`mad_U/D_*` at
several multipliers, NQ `q_D_p75`/`q_U_p75`) are **not** among the 55
Bonferroni survivors — they were already `NULL` in the original Family A
result.

## 3. Valid surviving level_ids by instrument

**None.** No `(instrument, level_id)` pair is both a Bonferroni survivor
and `VALID_DISTANCE_MATCH`.

## 4. Invalid survivors attributable to the open-ended-bucket artifact

Of the 55 survivors, **36** show an explicit real/synthetic support
mismatch (`real_p95 exceeds synthetic max` and/or the literal "synthetic
capped near 2-3 while real extends beyond 5" rule) — this is the
open-ended-bucket artifact identified in the prior generation report:

`ES: overnight_high, overnight_low, overnight_mid, overnight_open,
prior_close, prior_high, prior_low, prior_rth_mid, prior_rth_vwap,
q_D_p95, q_U_p95, vwap_on_j+0, vwap_on_j+1, vwap_on_j+2, vwap_on_j+3,
vwap_on_j-1, vwap_on_j-2, vwap_on_j-3`
`NQ: overnight_high, overnight_low, overnight_mid, overnight_open,
prior_close, prior_high, prior_low, prior_rth_mid, prior_rth_vwap,
q_D_p95, q_U_p95, vwap_on_j+0, vwap_on_j+1, vwap_on_j+2, vwap_on_j+3,
vwap_on_j-1, vwap_on_j-2, vwap_on_j-3`

## 5. Do the bounded Family 1 and central VWAP results remain credible?

**No, not under the literal frozen classification — but for a different
reason than the open-ended-bucket artifact, and this distinction matters.**
The remaining **17** invalid survivors (all `mult_U_*`/`mult_D_*` at every
multiplier, both instruments, plus ES `q_U_p25`) fail *only* the
`|standardized mean difference| ≤ 0.50` rule, with `|SMD|` values of
**2.4-2.5** — enormous by the usual interpretation of Cohen's d. The
mechanism: `mult_U_1.0`/`mult_D_1.0`-style levels have a normalized
distance that is **exactly constant** across every session by
construction (e.g. `mult_U_1.0` is always precisely `1.0` scale-units from
the open) — real-side standard deviation is ≈0. The standardized-mean-
difference formula divides by a pooled SD dominated by this near-zero
real-side variance, so even the modest raw gap (median distance
difference ≈ 0.25, right at the `VALID` boundary, driven entirely by the
synthetic control's within-bucket spread) is inflated into a huge SMD.
**This is an artifact of applying a variance-normalized metric to a
zero-variance arm, not evidence that the bounded family-1 levels'
controls are badly matched in raw, substantive terms** — their raw
median/p90 distance differences are near or within the `VALID`
thresholds. Applying the frozen classification rules exactly as
specified, however, these 17 are still `INVALID_DISTANCE_MATCH` — this
audit reports that literal result while flagging the mechanism, per
instruction not to silently reinterpret the frozen rule.

## 6. Concise verdict

**Family A contains no result that is simultaneously a Bonferroni
survivor and a valid-distance-matched comparison.** Applying the frozen
control-match classification exactly as specified to all 76 cells: zero
survive as `VALID_SUPPORTED_TOUCH_RATE_DIFFERENCE`. Of the original 55
"significant" cells, 36 are contaminated by a genuine, large real/
synthetic support mismatch (the open-ended-bucket artifact — real values
routinely 5-100+ scale-units from the open against a synthetic control
capped near 2-3), and the remaining 19 (17 `INVALID` + 2 `QUESTIONABLE`)
are driven by a variance-normalization artifact specific to zero-variance
family-1 multiplier levels rather than by a comparably large raw distance
gap. **No defensible, distance-matched touch-rate finding survives this
audit.** This does not itself prove the underlying market phenomenon is
absent — it means this specific frozen synthetic-control design cannot
currently support a confirmatory claim for any of the 76 cells, and any
future revision would need either a support-aware control (not an
open-ended-bucket uniform draw) or a distance-matching metric that
doesn't penalize legitimately low-variance real distributions.
