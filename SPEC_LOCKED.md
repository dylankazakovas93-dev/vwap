# SPEC_LOCKED.md

Locked before any development-partition strategy results were viewed.
Only engineering fixtures (synthetic data, schema checks) preceded this lock.
Amendments require a DECISIONS.md entry and increment the research generation.

## Research classification

Original hypothesis (paper-inspired context only; NOT a replication).
Primary objective: establish whether a raw conditional signal exists —
specifically whether 1-minute OHLCV features distinguish continuation from
reversal after an extreme directional displacement in ES and NQ front-month
futures. No TP/SL optimization is authorized in Stages 0-2.

## Event definition (causal)

Grid: every completed front-month bar t in the development partition with
valid features (no roll/session-boundary window overlap, valid minute-of-day
baseline).

Shock over k bars: `s_t = C_t - C_{t-k}`, k ∈ {1, 3} (within session and
contract). Direction d = sign(s_t).

Minute-of-day robust scale: `sigma_MOD(m, t)` = 1.4826 × median of |s| at ET
minute m over the trailing 60 sessions strictly before session(t), minimum
20 sessions, else invalid.

Event: `|s_t| / sigma_MOD >= z_thr`, z_thr ∈ {3 (primary), 4 (robustness)}.
Events are identified at the close of bar t only — no retrospective
move-start anchoring. Overlapping events are all recorded; analysis uses
session-block bootstrap to handle dependence.

## Feature families (all as of close of bar t; earliest entry = open of t+1)

Let `r_i = C_i - C_{i-1}`. Lookback L ∈ {5, 15, 60}. Windows end at t-1 so
the shock bar is excluded from its own context.

1. Prior displacement: `D_L = C_{t-1} - C_{t-1-L}`; normalized `D_L / ATR30(t-1)`.
2. Persistence: `P_L` = fraction of `r_i`, i ∈ [t-L, t-1], with
   sign(r_i) == sign(D_L); zero-change bars count as non-matching; null if D_L == 0.
   Signed version `P_L_d` uses sign match with shock direction d.
3. Path efficiency: `E_L = |D_L| / sum |r_i|` over the same window; null if
   denominator is 0. Signed context: `E_L_d = E_L * sign_match(D_L, d)`.
4. Terminal run length: R = count of consecutive same-sign `r_i` ending at
   r_{t-1}; signed by agreement with d.
5. Shock normalizations: `z_atr = s_t / ATR30(t-1)` (ATR = mean true range,
   30 completed bars ending t-1, within session); `z_mod = s_t / sigma_MOD`
   (event trigger uses |z_mod|).
6. Volume shock: `z_vol = (V_t - med_MOD) / (1.4826 * MAD_MOD)` where med/MAD
   are over the same trailing-60-session minute-of-day window; also
   `vol_ratio = V_t / med_MOD`; null if MAD == 0.
7. Candle geometry over the k shock bars: body_eff = |C_t - O_{t-k+1}| /
   (max H - min L); close_loc = (C_t - min L) / (max H - min L), folded so
   1.0 = closed at the directional extreme; adverse wick = distance from C_t
   to the adverse extreme divided by range. Null if range == 0.
8. VWAP (two anchors): Globex VWAP from 18:00 ET anchor; RTH VWAP from
   09:30 ET (defined only for bars >= 09:30 ET). VWAP_t = cumulative
   sum(p̄·V)/sum(V), p̄ = (H+L+C)/3, through bar t.
   Dispersion: sigma_vwap,t = sqrt(sum V_i (p̄_i - VWAP_t)^2 / sum V_i).
   Validity: >= 30 completed bars since anchor. Deviation
   `delta_t = (C_t - VWAP_t) / sigma_vwap,t`, signed by d.
9. VWAP slope: (VWAP_t - VWAP_{t-10}) / 10, in ATR30 units, signed by d.
10. Acceptance (decided after the event, entry only after decision):
    given |delta_t| >= 2 on side d, examine closes of bars t+1..t+n:
    - A1 (fast): >= 2 of 3 closes beyond the 2.0-sigma band on side d AND no
      close inside the 1.0-sigma band; decision bar t+3.
    - A2 (slow): >= 3 of 5 closes beyond, same inner-band veto; decision bar t+5.
    Rejection: any close inside the 1.0-sigma band within the window.
    A band touch is never acceptance. Bands use sigma_vwap as of each
    completed bar (never end-of-day variance).

## Forward outcomes (measured from open of bar t+1; acceptance-conditional
outcomes additionally from open of decision bar + 1)

- Signed forward returns at horizons {1, 5, 15, 30, 60} minutes:
  `(C_{t+h} - O_{t+1}) * d`, in points, ticks, and ATR30 units.
- MAE/MFE over 60 minutes from O_{t+1} using bar highs/lows; time to each.
- Symmetric first passage: barriers O_{t+1} ± 1.0 × ATR30(t-1), window 120
  minutes capped at session end. If both barriers are touched within one
  bar, the outcome is AMBIGUOUS and counted against continuation
  (conservative). Outcomes: CONT / REV / AMBIG / NONE.
- VWAP reclaim: first bar after t with close inside the 1.0-sigma band;
  reclaim time in minutes (censored at 120/session end).

## Session segments (ET, predeclared)

overnight 18:00-02:59 | european 03:00-08:29 | precash 08:30-09:29 |
cashopen 09:30-09:59 | morning 10:00-11:29 | midday 11:30-13:59 |
afternoon 14:00-15:29 | close 15:30-16:59.
Macro tag (approximation, fixed clock times, causal): bars whose ET time is
in {08:30-08:32, 09:45-09:47, 10:00-10:02, 14:00-14:02} are flagged
`macro_window=1`. Tagging only; no exclusion.

## Preregistered analysis set (Stage 2)

Continuous-variable-first: quantile (quintile) response maps of each feature
vs continuation probability and mean signed forward returns; monotonicity by
Spearman rank correlation with session-block bootstrap CIs (500 resamples of
session dates, fixed seed 20260710).

Nested increments (per instrument, per k, per z_thr): displacement alone;
+persistence; +path efficiency; +candle efficiency; +volume; +VWAP distance;
+VWAP acceptance; full stack; matched placebo (non-event bars matched on
session segment, minute-of-day ±15, ATR30 decile; sampled 1:1, seed fixed).
Each increment is judged by top-vs-bottom-quintile continuation-rate
difference within events, overall and stratified by |z_mod| quintile
(controls displacement magnitude), with bootstrap CIs.

## Trial accounting

Registered Stage 2 trial axes: 2 instruments × 2 k × 2 z_thr × 3 L for the
lookback families, 2 VWAP anchors × 2 acceptance rules for family 10.
Cartesian full sweep would be 2×2×2×3×2×2 = 96 threshold-style cells; the
continuous/quantile design replaces threshold search, and the registered
budget is a hard cap of **150 rows in RUN_REGISTRY.csv across Stages 2-4**,
counting every analysis configuration executed (including failures).

## Economic significance floors (preregistered)

- Stage 2 "signal exists": monotone quantile response with bootstrap-CI
  support in BOTH instruments (same sign), and top-bottom quintile spread of
  forward mean signed return >= 2 ticks (ES 0.50 pt, NQ 0.50 pt) at some
  horizon, robust across z_thr ∈ {3,4} and neighbouring L.
- Weak-effect stop: all conditional mean spreads < 1 tick at every horizon.

## Fill and position rules (for any later strategy stage; not exercised here)

Next-bar-open market fill at recorded open; one global position across both
instruments' tested strategy; no overlap; no same-bar re-entry; conservative
same-bar stop/target ordering (stop first). Zero costs = "gross, simulator
assumption"; a 1-tick-spread + $4 round-turn sensitivity must accompany any
later P&L claim.
