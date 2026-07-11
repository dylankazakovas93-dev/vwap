# Stage 2 gate report

Branch: claude/reversal-continuation-research-p6hsdi. Development partition
only (2018-2022); validation and 2025→ holdout untouched. Full numeric
evidence: STAGE2_FINDINGS.md and reports/tables/.

## Gate criteria (from SPEC_LOCKED.md)

| Criterion | Result | Verdict |
|---|---|---|
| Deterministic engine + hand-calc fixtures pass | 8/8 pytest | PASS |
| Causal features, no lookahead, next-open outcomes | enforced + tested | PASS |
| Preregistered quantile/monotonicity/increment/placebo/acceptance run on both instruments | done, registered | PASS |
| "Signal exists": monotone response, same sign both instruments, ≥2-tick top-bottom forward-return spread, robust across z and neighbouring L | NOT MET for continuation | FAIL |
| Weak-effect stop: all conditional mean spreads < 1 tick | met outside cash-open segment | triggers stop |

## Findings vs the two hypotheses

- Continuation hypothesis: **REJECTED** as a tradable directional signal.
  Displacement alone is directionally uninformative (cont 0.483/0.488);
  no conditioning feature produces an economically material continuation
  effect; causal VWAP acceptance is null after removing anchor leakage.
- Reversal hypothesis: **weak, coherent, sub-floor.** Abnormal volume and
  low path efficiency lean toward reversal (consistent sign, CI excludes
  zero) but < 1 tick in mean forward return except at the 09:30 cash open.

## Recommendation

**REVISE HYPOTHESIS.** Do NOT proceed to entry freeze / TP-SL research on
the continuation thesis — it fails the preregistered economic floor and the
one impressive-looking result (VWAP acceptance) is anchor leakage. The only
live thread is a **reversal** effect (extreme displacement + abnormal
volume + inefficient path, concentrated at the cash open). It is sign-stable
across ES and NQ but currently below the 2-tick significance floor outside
the cash-open window and must not be promoted without: (a) a fresh
preregistration targeting reversal specifically, (b) an honest reckoning of
whether the cash-open pocket survives the 1-tick ES spread and the small
sample, and (c) an independent audit (Stage 3, not yet run).

No TP/SL sweep, no validation-partition access, no holdout access performed.
Stage stops here per instructions.

## Addendum — family G (extremity-threshold & retracement study)

Thresholds were made explicit and swept (top 10/5/2/1% of |z_mod1|; VWAP
deviation 1.5-4.0σ x 2 anchors; acceptance 2of3/3of4/4of5 x veto on/off).
Result reinforces the verdict: under a **symmetric** ±0.5M first-passage test
the extend-before-retrace probability is 0.463 (ES) / 0.473 (NQ) and **flat
across the entire extremity domain** (Spearman ≈ +0.0006). The monotone
"continuation strengthens with extremity" seen under an asymmetric 1-tick-vs-
M/2 barrier is a barrier-scaling artifact. Acceptance strength and the inner-
band veto add no causal information (veto reclassifies <0.1% of events).
See STAGE2G_EXTREMITY.md. Recommendation unchanged: REVISE HYPOTHESIS.

## Reproduction

```
cd research/vwap_shock
python -m pytest tests/ -q
python -m src.data_build
python -m src.run_stage2 ES && python -m src.run_stage2 NQ
python -m src.run_analysis
```
