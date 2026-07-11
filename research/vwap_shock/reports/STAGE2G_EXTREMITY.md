# Stage 2 extension — family G: extremity-threshold & retracement study

Development partition only (2018-2022), ES & NQ front-month, k=1 impulse.
Gross, simulator-conditional. Tables: reports/tables/ext_*.csv. Engine:
src/extremity.py (+ fixture test_impulse_retracement_engine). Event set =
top-10% of |z_mod1| per instrument (ES threshold 2.248, NQ 2.361), 171,005 /
169,813 impulses; stratified into whole-sample top 10/5/2/1% bands.

## Exact thresholds already in force (restated, unobscured)

- Shock trigger (Stage 2 baseline): `|z_mod_k| >= 3.0` primary, `>= 4.0`
  robustness, k in {1,3}. `z_mod_k = (C_t - C_{t-k}) / (1.4826 * median(
  |C_t - C_{t-k}|))`, median over the trailing 60 prior sessions at the same
  ET minute (min 20). `|z_mod1| >= 3` == the 94th percentile of bars.
- ATR-normalized shock (also stored): `z_atr_k = s_k / ATR30`,
  ATR30 = mean true range over 30 completed bars ending t-1.
- VWAP outer band 2.0 sigma, inner 1.0 sigma; deviation
  `(C_t - VWAP_t)/sigma_vwap,t`; `sigma_vwap` = causal volume-weighted
  dispersion, valid only after >= 30 completed bars since anchor.
- First-passage barrier (Stage 2): `+-1.0 * ATR30`, 120-min window.

## Extremity domain and cell counts (top 10/5/2/1%)

| band | ES |z_mod1| | ES n | NQ |z_mod1| | NQ n |
|---|---|---|---|---|
| top 10% (p90) | >= 2.25 | 171,005 | >= 2.36 | 169,813 |
| top 5% (p95) | >= 3.37 | 94,139 | >= 3.37 | 87,066 |
| top 2% (p98) | >= 5.40 | 35,889 | >= 5.02 | 34,478 |
| top 1% (p99) | >= 7.82 | 17,219 | >= 6.74 | 17,462 |

Minimum reported cell = 300 events. The VWAP `4.0σ+` cell (n=24-56) is
**inadequate and flagged, not interpreted**, exactly as anticipated.

## 1. Does reversal/continuation change monotonically with shock magnitude?

**The answer depends entirely on whether the test barrier is symmetric, and
the honest (symmetric) answer is NO.**

- Asymmetric race — P(new extreme, +1 tick, before retracing 50% of M):
  rises monotonically ES 0.729 -> 0.788 -> 0.828 -> 0.804, NQ 0.826 ->
  0.841 -> 0.866 -> 0.883 (Spearman +0.071 / +0.060). This **looks** like
  continuation strengthening with extremity.
- **But the barriers are asymmetric**: the "break" barrier is a fixed 1 tick
  while the "retrace" barrier is M/2, which grows from ~2.5 to ~24 ticks
  across the bands. Larger impulses push the retrace barrier farther away,
  mechanically raising the extend-first rate. This is a barrier-scaling
  artifact, the same class of error the FX paper warns about.
- Symmetric race — P(reach extreme +0.5M before extreme -0.5M): **0.463 (ES)
  / 0.473 (NQ), below 0.5, and FLAT across the extremity domain**
  (ES 0.462/0.468/0.471/0.455; NQ 0.473/0.475/0.473/0.469; Spearman
  +0.0008 / +0.0005, band CIs overlap). At f=1.0M: 0.482 / 0.491, also flat.

Conclusion: under a fair symmetric test, extreme 1-minute impulses are, if
anything, marginally reversal-prone, and this does **not** change as shock
magnitude increases from the top 10% to the top 1%. The monotone appearance
under the asymmetric barrier is spurious.

Supporting: full-failure rate (retrace 100% of M within 120 min) declines
with magnitude (Spearman -0.040 ES / -0.054 NQ, CIs exclude zero), but
post-50%-retrace MFE approx equals MAE at every band (ES 85 vs 82 ticks at
p99; NQ 248 vs 242), i.e. subsequent excursions are directionally symmetric.
The full-failure decline is a magnitude/mechanical effect (bigger M is harder
to fully retrace in fixed time), not a directional edge.

## 2. VWAP distance (both anchors, causal deviation bins)

Full-failure rate declines monotonically with signed deviation across BOTH
anchors and BOTH instruments (Globex ES 0.873->0.850->0.825->0.786; NQ
0.860->0.840->0.813->0.758; RTH similar). But med impulse size rises with the
deviation bin (Globex ES 7->10 ticks, NQ 25->39), so deviation and M are
confounded — the same mechanical effect as in part 1. The directional
30-min forward return is sign-inconsistent across anchors (e.g. deep RTH
3-4σ: ES -4.1, NQ -14.8 ticks = reversal; deep Globex 3-4σ NQ +6.5 =
continuation) and rests on small cells (564-1388). The 4.0σ+ cell is
inadequate (n=24-56). **No clean directional edge from VWAP distance.**

## 3. Acceptance strength (post-decision, causal)

Post-decision break-extreme rate (measured strictly after the decision bar):

| rule | ES ACCEPT | ES REJECT | NQ ACCEPT | NQ REJECT |
|---|---|---|---|---|
| 2-of-3 | 0.946 | 0.692 | 0.943 | 0.667 |
| 3-of-4 | 0.945 | 0.676 | 0.942 | 0.654 |
| 4-of-5 | 0.948 | 0.678 | 0.944 | 0.652 |

- Requiring **stronger** acceptance (4-of-5 vs 2-of-3) does **not** raise the
  post-decision break rate — flat at ~0.945. Acceptance strength adds no
  information.
- The inner-band-reclaim veto reclassifies **< 0.1%** of eligible events
  (ES 2-of-3 ACCEPT: 11,233 with veto vs 11,241 without). Removing the veto
  leaves the ACCEPT set essentially unchanged. **The inner-band reclaim adds
  no information.**
- ACCEPT (~0.945) sits **below** the unconditional break baseline (~0.98)
  because accepted events have a shorter post-decision window; the ACCEPT-vs-
  REJECT gap is the reject leg (price already turned) doing the work, i.e.
  contemporaneous, not predictive. Consistent with the Stage 2 anchor-leakage
  finding: causal VWAP acceptance carries no forward continuation edge.

## 4. Retracement conditional on extremity — summary

Reported per band in ext_extremity.csv: bucketed max-retracement
probabilities (10-20 ... 50-100 ... >=100%), full-failure rate, break-extreme
rate and time, post-50% MFE/MAE and time-to-renewed-continuation. The deep
(50-100%) retracement bucket rises slightly with extremity (ES 0.061->0.088,
NQ 0.061->0.094) while full-failure falls — bigger shocks retrace partially
but not fully within the window — but the post-retracement excursions are
directionally symmetric, so none of this yields a tradable direction.

## 5. Search control

- Thresholds examined: extremity bands top 10/5/2/1% (|z_mod1| quantiles);
  VWAP deviation bins {1.5-2.0, 2.0-2.5, 2.5-3.0, 3.0-4.0, 4.0+} x 2 anchors;
  acceptance {2of3, 3of4, 4of5} x {veto, no-veto}; symmetric race f in
  {0.5, 1.0}. Every cell count is in the tables; min cell 300.
- Effective trial count: this is a continuous/binned response-map study, not
  an optimization. No cutoff was selected; no cell was promoted. The only
  monotone effects (full-failure vs magnitude / vs deviation) are shown to be
  magnitude confounds by the flat symmetric race and symmetric post-retrace
  MFE/MAE. No isolated cell is relied upon.
- No TP/SL optimization; no threshold called validated; no validation or
  holdout data accessed.

## Verdict impact

Family G does **not** overturn the Stage 2 verdict; it strengthens it. Made
explicit and swept, the shock-magnitude and VWAP-deviation thresholds show no
symmetric directional edge at any extremity level, acceptance strength and
the inner-band veto add nothing causally, and the one monotone pattern
(fuller retracement is rarer for bigger shocks) is a mechanical size effect
with symmetric forward excursions. Recommendation remains **REVISE
HYPOTHESIS** (continuation not supported; only a weak, sub-floor reversal
tilt concentrated at the cash open remains a candidate for a fresh
preregistered study).
