# Stage 2 findings — development partition (2018-2022), ES & NQ front-month

Gross, simulator-conditional; no costs. All numbers from
`reports/tables/*.csv`, produced by `src/run_analysis.py` (seed 20260710).
Continuation label = symmetric first passage of +1×ATR30 in the shock
direction before −1×ATR30 (AMBIG and REV counted as non-continuation;
NONE/INVALID excluded from the rate). "Ticks" = 0.25 index points.

## Event inventory (k=1, |z_mod|>=3)

| | ES | NQ |
|---|---|---|
| events | 101,297 | 103,439 |
| decided (CONT/REV/AMBIG) | 100,868 | 102,905 |
| NONE (no barrier in 120m) | 0.4% | 0.5% |
| AMBIG (both barriers, 1 bar) | 1.4% | 1.3% |

By year (k1z3): ES 20.5k/11.0k/32.6k/19.5k/17.7k, NQ
23.6k/12.8k/34.0k/19.0k/14.1k (2020 COVID-heavy). By segment the mass is
overnight (37.9k ES) and european (24.3k ES) — extreme 1-minute moves are
mostly a thin-liquidity phenomenon, not a cash-session one. k=3 and z>=4
sets are similar in shape (see tables).

## Result 1 — displacement alone carries no direction

Unconditional continuation rate is **0.483 (ES) / 0.488 (NQ)** — slightly
*below* 0.5. Bootstrap 95% CI ES [0.480, 0.486], NQ [0.485, 0.491]: both
exclude 0.50 on the reversal side. Mean forward signed return at every
horizon is a fraction of a tick; 30-min CI ES [−0.39, +0.13] ticks, NQ
[−0.53, +1.13] ticks — both span zero. MAE ≈ MFE (symmetric ~40 ticks ES,
~135 ticks NQ). **An extreme 1-minute displacement, by itself, is if
anything marginally reversal-prone and directionally uninformative.** This
reproduces the FX paper's occurrence-vs-direction result on ES/NQ.

## Result 2 — no conditioning feature recovers continuation

Spearman rank correlation of each feature with the continuation label
(primary configs, n≈100k):

- Every |ρ| < 0.03 in both instruments.
- The dominant sign is **negative**: higher prior displacement (D_L_d),
  path efficiency (E_L_d), terminal run (run_d), abnormal volume (z_vol,
  vol_ratio) and VWAP distance (dev_g_d) all associate with *slightly less*
  continuation — the opposite of the master continuation hypothesis.
- Displacement-controlled top-vs-bottom-quintile continuation differences
  (increments.csv) are all ≤ 0 within noise except candle efficiency (≈0).
  The largest and most consistent is **volume: −0.032 (ES) / −0.029 (NQ),
  CI excludes zero in both** — high abnormal volume on an extreme bar makes
  continuation *less* likely.
- The only feature leaning the hypothesised (continuation) way in both
  instruments is RTH VWAP deviation dev_r_d (ρ ≈ +0.011/+0.014), magnitude
  economically negligible and defined on only ~30k of the events.

Quintile response maps show continuation rates confined to 0.46–0.51 with no
monotone structure; forward-return quintiles flip sign with no pattern and
magnitudes almost always < 1 tick. No feature meets the preregistered
2-tick "signal exists" floor at any horizon.

## Result 3 — VWAP acceptance is an anchor-leakage trap

Raw ("event") continuation rate sorts dramatically by acceptance:
ACCEPT ≈ 0.57–0.58, REJECT ≈ 0.08–0.16 (Globex anchor, A1/A2, both
instruments). This looks like the master hypothesis confirmed — **but it is
contemporaneous leakage.** Acceptance is defined on closes of bars
t+1..t+n; the continuation label is measured on the same forward path.
Price that stays beyond the band on side d for 3–5 bars has by construction
already travelled toward the +1 ATR barrier.

The causal test measures continuation from the open *after* the acceptance
decision bar (post_cont_rate): **ACCEPT → 0.490 (ES) / 0.496 (NQ)**,
i.e. back to baseline; REJECT samples are tiny (n=108–302) and noisy.
Post-decision forward returns are sub-tick to a few ticks with inconsistent
signs across instruments. **Once the overlap is removed, sustained VWAP
acceptance adds no forward continuation information.** This is exactly the
first-passage/anchor-leakage artifact the FX paper warns about, reproduced
here as a negative control.

## Result 4 — events vs matched placebo

Event continuation (0.483 ES / 0.488 NQ) is ~1 point *below* the
time-of-day/volatility-matched non-event placebo (0.494 / 0.497). The
"extreme displacement" adds a small reversal tilt relative to ordinary
bars, not a continuation tilt.

## Result 5 — the only economically visible pocket: cash open reversal

Segment stratification (cont rate / 30-min fret ticks):

| segment | ES | NQ |
|---|---|---|
| cashopen 09:30–09:59 | 0.453 / −2.69 | 0.476 / −15.15 |
| all others | 0.477–0.495 / ~0 | 0.481–0.504 / ~0 |

The 09:30 cash open is the one window where extreme displacements reverse
with an economically meaningful signed return, strongest in NQ. But it is a
single segment with the smallest event count (1,803 ES / 1,366 NQ over five
years), consistent with opening-auction overreaction, and would require its
own preregistered study rather than an unconditional claim.

## Reading against the two hypotheses

- **Master continuation hypothesis:** NOT SUPPORTED. No feature — prior
  persistence, efficiency, run length, abnormal volume, close location, or
  causal VWAP acceptance — produces a monotone, economically material
  (≥2-tick) continuation effect in both instruments. Where features carry
  any signal it points to reversal.
- **Master reversal hypothesis:** WEAKLY AND COHERENTLY SUPPORTED IN SIGN.
  High abnormal volume + low path efficiency + extreme displacement lean
  toward reversal (volume increment −0.03 in both instruments, CI excludes
  zero), matching a liquidity-shock/overreaction mechanism; the effect is
  concentrated at the cash open. But the unconditional and conditional mean
  forward returns are < 1 tick outside the cash-open pocket — below the
  preregistered economic floor in gross terms.

## Did volume / VWAP acceptance add information beyond price?

- **Volume:** Yes, a little — but toward *reversal*, not continuation, and
  sub-tick in mean return outside the cash open.
- **VWAP acceptance:** No, once anchor leakage is removed.
