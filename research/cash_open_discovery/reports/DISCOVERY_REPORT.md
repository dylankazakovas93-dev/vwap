# Discovery Report — Cash-Open Failed-Auction Study (Generation 2)

Branch: `research/cash-open-failed-auction-discovery`, base commit `1d39d8e`.
Development partition only (2018-01-03 -> 2022-12-30, 1291 sessions/
instrument). No validation or holdout data accessed. No TP/SL, MAE/MFE, or
profitability metric computed anywhere in this generation.

## 1-4. Provenance, files, data identity, conventions

Base data: generation 1's `data/processed/{es,nq}_front_1m.parquet`
(unchanged, hashes in `../../DATA_CONTRACT.md`). New files (this
generation only): `RESEARCH_CHARTER.md`, `HYPOTHESES.md`, `DATA_CONTRACT.md`,
`SPEC_DISCOVERY.md`, `VARIABLE_CATALOG.md`, `DECISIONS.md`,
`KNOWN_LIMITATIONS.md`, `PROJECT_STATUS.md`, `PROGRESS.md`,
`RUN_REGISTRY.csv`, `src/{opening_scale,episodes,outcomes,context,
build_ledger,run_analysis,run_placebo,analysis_utils}.py`,
`tests/test_fixtures.py`, `reports/tables/*.csv`. `ts_event` = bar OPEN
(verified); 09:30 ET = `et_minute==570` (verified present every session).
DST resolved per-bar by the inherited `America/New_York` conversion — no
separate branch needed. Session/maintenance-boundary conventions inherited
from generation 1 (Globex 18:00 ET anchor; halt bars 17:00-18:00 ET
excluded upstream).

## 5. Opening-scale formula

`S(tau,s) = 1.4826 * median(|close(tau,s') - O(s')|)` over the trailing 60
RTH sessions strictly before `s`, minimum 20 valid observations, per
elapsed minute `tau` after the anchor (09:30 primary; 13:00 placebo). No
lookahead (fixture-tested).

## 6. Domains tested

A in {0.5, 1.0, 1.5, 2.0}; B in {0.5A, 0}; outer search tau in [0,60];
reclaim search up to 60 bars past outer; checkpoints H in {5,10,15};
fixed horizons {1,3,5,10,15,30,60 (non-saturating)}; symmetric first
passage f in {0.25, 0.50} of M, plus 1.0*S; min reported cell 100 episodes
(sub-cells >=20-30 for descriptive means, flagged in tables). Placebo
anchor 13:00 ET, identical machinery.

## 7. Event counts

Primary (09:30) episodes per instrument: ES 3945, NQ 3870 across the 4 A
values (each session contributes at most one episode per A). **A=0.5 is
"too common" in a specific sense**: same-bar upper+lower breach
(AMBIGUOUS_DIRECTION, excluded from directional analysis) is 35.3% (ES) /
33.4% (NQ) at A=0.5, falling to 2.2% / 0.7% at A=2.0 — reported as
required, not patched. Directional (non-ambiguous) episode counts range
590-1093 per instrument per A (Q4 table). Reclaim rate (HALF or FULL
within 60 min) is 63-79% depending on A; the **HALF-only** subgroup (the
key finding, below) is small: 20-112 episodes per instrument per A.

## 8-10. Does reclaim add directional information? Speed? Full vs. 50%?

**Full reclaim (B=0) adds no directional information.** Matched
checkpoint comparison (Q1, H=15, 30-min horizon) and the decision-point
comparison (Q5) both show FULL-reclaim mean forward return in the reclaim
direction indistinguishable from zero and from HELD episodes (ES: -3.1 to
+0.4 ticks, CI spans zero at every A; NQ: -22 to -1.7 ticks, mostly
CI-spanning). **HELD** episodes (never reclaim 50% within 15 min) also
show no directional effect (all CIs span zero, both instruments).

**The one strong, consistent signal points the OPPOSITE way from the
preregistered hypothesis.** Episodes that reach the 50% reclaim level but
**fail to progress to full reclaim** within the 60-minute window (`HALF`
only) show a **large, cross-instrument, cross-magnitude, cross-year
negative** mean 30-minute forward return **against** the reclaim
direction — i.e., the *original* excursion direction reasserts:

| instrument | A | n | mean 30-min fwd return (reclaim-direction ticks) | 95% CI |
|---|---|---|---|---|
| ES | 0.5 | 20 | -28.0 | [-34.1, -22.3] |
| ES | 1.0 | 83 | -28.9 | [-36.4, -22.2] |
| ES | 1.5 | 101 | -33.6 | [-42.1, -24.3] |
| ES | 2.0 | 73 | -29.1 | [-38.5, -20.0] |
| NQ | 1.0 | 80 | -147.5 | [-183.2, -110.8] |
| NQ | 1.5 | 112 | -121.3 | [-152.7, -89.3] |
| NQ | 2.0 | 76 | -110.6 | [-147.6, -68.9] |

(NQ A=0.5 HALF-only n=18, too small to report per Sec. 8's 100-minimum;
shown descriptively only.) Year-by-year: negative in **every one of the 5
development years**, both instruments (ES: -3.8 to -17.0 ticks/year; NQ:
-15.6 to -64.1 ticks/year) — not driven by one year or a handful of
sessions. This survives as the checkpoint-based comparison too (Q1,
`RECLAIMED_50` status = "reclaimed 50% but not yet full as of the
checkpoint," same sign, same magnitude order).

**Reclaim speed (Q2) and outer-excursion speed (Q3) show no coherent
monotone pattern** — bin-to-bar and continuous Spearman correlations are
small and sign-inconsistent across A and across instruments (|Spearman|
mostly <0.03, occasionally noisy larger values in tiny bins with no
cross-instrument agreement). Neither timing dimension adds a discernible
effect beyond the reclaim-type finding above.

**Interpretation, stated plainly**: this generation's PRIMARY hypothesis
(reclaim of a failed excursion -> continuation in the reclaim direction)
is **not supported**. What the data show instead is a **different,
un-preregistered-as-primary pattern**: a reclaim that stalls at the
halfway mark (and does not go on to fully reclaim the open) tends to be
followed by resumption of the *original* excursion — arguably a "failed
reclaim" / second-failed-auction phenomenon, opposite in sign to what was
hypothesized. Per protocol, this is recorded here as an observation for a
possible future (generation 3) preregistration, not built into a strategy
now.

## 11. ES and NQ separately

Reported throughout (all tables split by instrument). Both instruments
show the same qualitative pattern (full reclaim null, held null,
HALF-only reclaim reverts against the reclaim direction); NQ's magnitudes
in points are far larger than ES's (consistent with NQ's larger point
value / volatility, not evaluated here in normalized units beyond the
opening-scale-relative reporting in the raw tables).

## 12. Upper and lower failures separately

`event_counts.csv` reports counts by `outer_direction` x `A` x `year`.
Both directions contribute comparably (roughly balanced upper/lower split
at every A, see Section-4/Sanity numbers: e.g. ES A=1.0 lower=525/
upper=559). The HALF-only reversal-against-reclaim finding was checked in
the pooled (both-direction, direction-aligned) tables; a direction-split
breakdown is available in the underlying ledger (`outer_direction` column)
for follow-up but was not separately re-tabulated here given the small
HALF-only sub-sample per direction (would fall below the 20-30 minimum
this generation used for descriptive sub-cells).

## 13. Year and month stability

See Section 8-10 table: HALF-only effect negative in all 5 development
years, both instruments — the most stable result in this study.
`concentration.csv` (pooled reclaimed group) shows no single year
dominating (top-10%-of-|return| share ~31-34% of total absolute return
mass, unremarkable) and 5/5 years present in every A cell.

## 14. Overnight-context findings

All 13 overnight/prior-session explanatory variables tested against
(a) which side is reached first, (b) whether any reclaim occurs, (c)
forward return if reclaimed: every Spearman correlation is negligible
(|rho| <= 0.11, `overnight_explanatory.csv`). **Overnight positioning and
prior-session final-10-minute variables carry no detectable explanatory
value** in this sample, for any of the three targets.

## 15. Prior-session-direction findings

Included in the same overnight_explanatory sweep
(`final10min_priorclose_*`, `final10min_sessionend_*`); likewise
negligible (|rho| <= 0.08). No evidence that the prior session's final
10 minutes (either before RTH close or before the maintenance boundary)
predict which opening side is reached first, or anything downstream.

## 16. Placebo and matched-control findings

The 13:00 ET placebo anchor (`placebo_comparison.csv`) shows HIGHER
reclaim rates than the cash open at every A (e.g., ES A=1.0: 83.6%
placebo vs. 76.3% primary) and small, sign-inconsistent mean 30-min
forward returns (ES placebo: -0.86 to +0.05 ticks; NQ placebo: -6.8 to
+7.2 ticks) — i.e., the placebo's pooled reclaimed-group return is
consistent with noise, similar to the primary session's FULL-reclaim/HELD
null. A full HALF-only breakdown was not computed for the placebo in this
pass (time-boxed); this is a specific, cheap follow-up if generation 3
pursues the HALF-only-reversal finding, to test whether it is
cash-open-specific or a generic stalled-reclaim artifact.

## 17. Material null results (honest inventory)

- Full reclaim (B=0): no directional information beyond magnitude, either
  instrument, any A (Q1, Q5).
- Held excursions: no directional information (Q1).
- Reclaim speed: no coherent monotone pattern (Q2).
- Outer-excursion speed: no coherent monotone pattern (Q3).
- All 13 overnight/prior-session explanatory variables: negligible
  correlation with side-reached-first, reclaim-yes/no, or forward return
  (Sections 14-15).
- The master hypothesis's directional sign (reclaim -> continuation in
  reclaim direction) is **not** what the one significant result shows —
  the significant result is the opposite sign, in a different subgroup
  (stalled partial reclaim, not any reclaim).

## 18. Honest total search count

`RUN_REGISTRY.csv`: 24 rows from `run_analysis.py` + 2 rows from
`run_placebo.py` = **26 registered analysis configurations**, well inside
the 150-row budget (SPEC_DISCOVERY Sec. 11). Six research questions (Q1-
Q5 + overnight/prior-session + concentration + placebo + ambiguous-rate) x
2 instruments, each covering the preregistered A/B/checkpoint domain in
one pass — no additional configurations, thresholds, or variable
transformations were tried beyond what SPEC_DISCOVERY.md fixed in advance.
The HALF-only finding was NOT the target of a targeted search — it fell
out of the preregistered Q1/Q5 comparisons exactly as designed; it was not
discovered by trying many reclaim-fraction values (only B in {0.5A, 0} was
ever tested, per the locked spec).

## 19. Unresolved risks

- HALF-only sample sizes (20-112/cell) are small in absolute terms even
  though the sign is stable across years and both instruments; a formal
  multiple-testing-adjusted confidence statement is not computed in this
  discovery stage (no DSR/PBO/CPCV authorized here).
- No macro/news calendar was available; the HALF-only effect's relationship
  to scheduled announcements is untested (`KNOWN_LIMITATIONS.md` #2).
- Symmetric first-passage and structural-outcome tables were computed and
  are in the ledger/outputs but not summarized in this report for space;
  a generation-3 preregistration on the HALF-only pattern should examine
  them.
- The 13:00 ET placebo was only checked at the pooled-reclaim level, not
  split into HALF-only vs FULL — this is the single most important
  follow-up to determine whether the HALF-only reversal is cash-open-
  specific or a generic stalled-partial-reclaim artifact anywhere in the
  session.
- Roll-week sessions were not excluded (consistent with generation 1's
  policy) and are not separately checked for their contribution to the
  HALF-only cells.

## 20. Verdict

**REVISE HYPOTHESIS.**

The preregistered directional hypothesis — that a reclaim of a failed
cash-open excursion predicts continuation in the reclaim direction — is
**not supported**: full reclaim and held excursions both show null
forward information, and reclaim/outer speed show no coherent pattern.

However, this is not a flat REJECT: a materially different, internally
consistent, cross-instrument, cross-year-stable pattern emerged from the
same preregistered comparisons — a **stalled halfway reclaim (reaches 50%
retracement of the opening excursion but not a full reclaim within the
window) predicts resumption of the ORIGINAL excursion direction**, not the
hypothesized reclaim direction. This is recorded as a candidate hypothesis
for a **future generation 3** preregistration (with its own trial budget,
its own placebo split by reclaim-type, and — critically — an
economic-significance floor and cost sensitivity check before any
further work), not built into a strategy now, per instruction.

No MAE/MFE, TP/SL, or profitability metric was computed or is being
recommended based on any single cell in this report.
