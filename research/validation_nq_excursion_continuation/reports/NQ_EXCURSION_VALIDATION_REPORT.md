# NQ Upper-Excursion Continuation — Out-of-Sample Validation Report

Branch `validation/nq-upper-excursion-continuation`. Base commit
`dba98fe`. Preregistration commit `43969a5`. Implementation commit
`<final>`. Validation partition: 2023-01-01 through the latest audited
session (NQ 2026-06-08, ES 2026-06-09) — 2023/2024/2025 complete, **2026
explicitly partial**. No 2018-2022 session enters any validation
outcome (asserted in code); pre-2023 data is used only for causal
10-session warm-up. **This is validation, not discovery — no alternative
timing cell was computed or inspected, and the primary candidate's
failure was not used to search for a replacement.**

## Primary result: NQ `UPPER_k0`, A=2, H=2, b=1.0

| metric | value |
|---|---|
| touches within A=2 | 485 |
| non-tied barrier outcomes | 374 |
| continuation-first rate | 39.5% |
| reversal-first rate | 39.8% |
| **continuation − reversal difference** | **−0.84 pp** |
| one-sided exact binomial p (`H_a: cont>rev`) | **0.602** |
| median `SIGNED_CLOSE_SD` at H=2 | +0.198 (positive) |
| years with pooled sign | 2 of 4 |
| max single-year touch share | 29.9% |

## Did every primary success criterion pass? **No — 4 of 7 failed.**

| # | criterion | required | result | pass? |
|---|---|---|---|---|
| 1 | ≥100 touches | 485 | ✓ |
| 2 | ≥50 non-tied | 374 | ✓ |
| 3 | diff ≥ +5.0pp | **−0.84pp** | **✗** |
| 4 | one-sided p<0.05 | **0.602** | **✗** |
| 5 | median signed-close SD > 0 | +0.198 | ✓ |
| 6 | sign consistent ≥3/4 years | **2/4** | **✗** |
| 7 | no year >50% of touches | 29.9% | ✓ |

**Classification: `FAILED_VALIDATION`.** The development-sample effect
(continuation dominance of roughly +10pp, generation 10) did not
replicate — the out-of-sample effect is essentially flat and slightly
negative, with no statistical significance and inconsistent yearly sign.

## Supporting candidates (Holm-corrected together; cannot rescue the primary)

| level_id | A | H | n_touch | n_nontied | diff | raw p | Holm p | classification |
|---|---|---|---|---|---|---|---|---|
| `UPPER_k1` | 2 | 1 | 282 | 211 | +3.2pp | 0.291 | 0.291 | `FAILED_VALIDATION` |
| `UPPER_k2` | 5 | 2 | 275 | 227 | +7.0pp | 0.116 | 0.232 | `DIRECTIONALLY_POSITIVE_BUT_INCONCLUSIVE` |

Neither supporting candidate validates. `UPPER_k2` points in the
originally-hypothesized direction (+7.0pp) but does not clear
significance after Holm correction — reported honestly as inconclusive,
not as confirmatory. Per the frozen rule, this cannot rescue the failed
primary in any case.

## Lower mirrors (negative control)

| level_id | A | H | n_touch | diff | one-sided p |
|---|---|---|---|---|---|
| `LOWER_k0` | 2 | 2 | 480 | +4.2pp | 0.171 |
| `LOWER_k1` | 2 | 1 | 273 | +8.9pp | 0.055 |
| `LOWER_k2` | 5 | 2 | 266 | −3.0pp | 0.727 |

None reach significance. No systematic bearish-continuation signature
appears on the causal downside mirror, consistent with generation 10's
original null finding for `LOWER_*`.

## ES replication (negative control)

| level_id | A | H | n_touch | diff | one-sided p |
|---|---|---|---|---|---|
| `UPPER_k0` | 2 | 2 | 487 | −5.0pp | 0.897 |
| `UPPER_k1` | 2 | 1 | 253 | −5.6pp | 0.859 |
| `UPPER_k2` | 5 | 2 | 244 | 0.0pp | 0.529 |

All three ES cells are null or slightly negative — consistent with
generation 10's finding that the phenomenon (when it existed in
development) was NQ-specific. This remains true in validation, but the
comparison is now moot given the NQ primary itself failed.

## `UPPER_k3` null-extension check

`A=5, H=2`: 175 touches, diff +7.5pp, one-sided p=0.151 — not
significant, consistent with generation 10's original null finding at
`k=3`.

## Same-bar morphology (primary diagnostic: NQ `UPPER_k0`, A=2)

485 touch bars, 0 neutral (all non-neutral): blast-through rate 48.9%,
reversal rate 51.1%, difference −2.3pp, `p=0.650` — **no same-bar
morphology bias in validation**, whereas generation 10 found a
`SAME_BAR_BLAST_THROUGH_BIASED` signature in development for this same
level. This did not replicate either. Full table (all 10 named cells,
including one nominally significant but uncorrected/non-primary cell —
NQ `LOWER_k0`, `p=0.022`, reported for completeness only, not a
confirmatory finding): `reports/tables/same_bar_morphology_table.csv`.

## Yearly stability

Primary cell's year-by-year `cont_minus_rev_diff`: full detail in
`reports/tables/primary_year_table.csv`. The sign is inconsistent (2 of
4 partitions share the pooled sign), directly driving the failure of
success criterion 6 — this is not a borderline pass, the effect
genuinely does not hold up year to year in validation.

## Rolling direction-state replication

9 of 10 (instrument, level_id) cells are `STATE_NULL`, matching
generation 10's original null finding. One exception, reported honestly
and not used to rescue anything: NQ `UPPER_k1` (a supporting candidate,
not primary) shows `STATE_REVERSAL_SUPPORTED` (continuation-rate
difference −11.9pp, Fisher `p=0.023`, sign consistent ≥3 partitions) —
i.e., a prior continuation-heavy state very mildly *anti-predicts*
continuation on this one supporting level. This is disclosed as a
secondary, non-primary, single-cell finding on a candidate that itself
failed validation — it does not alter the primary verdict and is not
promoted to any conclusion beyond this description. Full table:
`reports/tables/rolling_state_replication_table.csv`.

## Concise classification: **FAILED_VALIDATION**

The primary NQ `UPPER_k0` candidate does not validate on 2023+ data: the
continuation-vs-reversal effect is statistically indistinguishable from
zero (and nominally slightly negative), fails the minimum-effect-size and
year-consistency criteria, and its own same-bar morphology signature also
did not replicate. The two supporting candidates likewise fail (one
outright, one inconclusive-after-correction). Per instruction, no
alternative validation winner was searched for after this failure, and no
further research generation begins.
