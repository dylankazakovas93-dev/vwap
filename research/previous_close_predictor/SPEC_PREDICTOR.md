# SPEC_PREDICTOR.md — locked before any development-partition result viewed

## 1. Session mapping

For target session `s` (a generation-3 atlas primary-valid session, dev
partition), the predictor session `p` = the nearest earlier `session_date`
in the same instrument's full loaded series with `p < s`. If no such
session exists (data start) or `p` is an early close (Sec. 3), `s` is
excluded from the primary analysis and logged with a reason. Weekend/
holiday mapping is automatic: `session_date` already skips non-trading
days (generation 1), so "nearest earlier session_date" is exactly "the
previous valid trading day" with no separate calendar table.

## 2. RTH close and windows

Official close = `close` of the bar with `et_minute==959` (session `p`).
For `W in {1,5,10,15,30,60}`, the window is bars with
`et_minute in [960-W, 959]` (the last W one-minute bars of session `p`'s
RTH day). `first_bar_open_W` = `open` of the bar at `et_minute==960-W`.
A window is **complete** only if all W bars in the range are present with
no gaps; incomplete windows are marked undefined for that (session,
feature, W) cell, not imputed.

## 3. Early close (session-level flag, per RESEARCH_CHARTER A2)

Session `p` is an early close if its maximum `et_minute` among bars with
`et_minute<=959` is `< 959`. Early-close predecessor sessions are excluded
from the primary target-session sample entirely (all W, since the anchor
"final close" itself is non-standard) and their count is reported
separately, per instruction. Early-close sessions are also excluded from
every trailing-baseline pool (Sec. 5).

## 4. Feature definitions (exact, per window W)

```
ret_W              = official_close - first_bar_open_W
range_W            = max(High[window]) - min(Low[window])
close_location_W   = 2*(official_close - min(Low[window])) /
                      (max(High[window]) - min(Low[window])) - 1
                      [undefined if range_W == 0]
signed_efficiency_W = ret_W / sum(|d_i|)
                      where d_1 = close(et=960-W) - first_bar_open_W,
                            d_i = close(et=960-W+i-1) - close(et=960-W+i-2)
                            for i=2..W (successive close-to-close diffs),
                            so that sum(d_i, i=1..W) == ret_W exactly
                      [undefined if sum(|d_i|) == 0]
volume_ratio_W     = sum(volume[window]) / trailing_median_volume_W(p)
```

`range_W >= 0` always (coded invariant, tested). `close_location_W in
[-1,1]` whenever defined (coded invariant, tested).

## 5. Normalization (causal, prior sessions only)

- `norm_ret_W(p) = ret_W(p) / sigma_ret_W(p)`, where
  `sigma_ret_W(p) = 1.4826 * median(|ret_W(p')|)` over the trailing 60
  prior valid (non-early-close) sessions `p' < p`, minimum 20 valid
  observations, else undefined. This is the "robust scale" per SPEC.
- `range_ratio_W(p) = range_W(p) / median(range_W(p'))` over the same
  trailing-60/min-20 prior-valid-session window (simple ratio to median,
  not MAD-scaled, per instruction wording "relative to the trailing
  prior-session median").
- `trailing_median_volume_W(p)` = median of `sum(volume[window])` over the
  same trailing-60/min-20 prior-valid-session window.
- All three baselines use only sessions strictly before `p`, restricted to
  the loaded development-partition frame; no current/future/validation/
  holdout data can enter a baseline (coded and tested).

## 6. Standalone features tested (5 per window, 6 windows = 30 features)

`norm_ret_W`, `range_ratio_W`, `close_location_W`, `signed_efficiency_W`,
`volume_ratio_W`. Raw `ret_W` and `range_W` are also stored (descriptive,
not separately tested) alongside their normalized counterparts.

## 7. Targets (reused unmodified from generation 3)

`R_h`, `Q_h` for `h in {5,10,15,30}` (subset of generation 3's full
`{1,3,5,10,15,30,60}` output; not redefined). Derived labels
`sign(R_h)`, `sign(Q_h)` with exact-zero as NEUTRAL, reused from
generation 3's `closing_direction_h`/`dominant_side_h` columns.

## 8. Analysis plan (every feature tested standalone; no interactions)

For every (instrument, feature, window W, horizon h, target in {R_h,Q_h}):
Pearson r, Spearman rho, day-block (session-row) bootstrap 95% CI (500
resamples, seed 20260711) on both; sign-agreement rate between the
feature's sign and the target's derived label (excluding NEUTRAL on
either side); conditional mean target across feature quintiles (5 bins)
and a monotonicity check (Spearman of quintile index vs. quintile mean);
accuracy/coverage at fixed strongest-|feature| levels {100%, 50%, 30%,
15%} of the valid sample (coverage levels fixed in advance, never chosen
post hoc); year-by-year (2018-2022) mean/count; bullish-vs-bearish
symmetry (mean target conditional on feature>0 vs feature<0, paired diff
CI); concentration (top-decile |feature| session share of total |target|
movement, and vice versa) and outlier-influence (statistic recomputed with
the single largest-|feature| session dropped).

## 9. Multiple-testing accounting

Elementary tests = 2 instruments x 5 features x 6 windows x 4 horizons x
2 targets (R,Q) = **480** standalone correlation tests, each logged as one
`RUN_REGISTRY.csv` row (stage=`predictor_screen`). No threshold, window,
or feature is chosen post hoc; every one of the 480 is reported (nulls
preserved). Declared adjustment: Bonferroni-corrected alpha =
0.05/480 = 1.0417e-4 applied to the raw two-sided p-value implied by each
Spearman rho (via the standard normal approximation, n-3 valid pairs);
an effective-test-count sensitivity is also reported using the
average pairwise |Spearman| among the 30 features (per instrument) to
estimate the correlation-adjusted effective N, since the 6 windows and
5 within-window features are not independent of each other. Both the raw
result and the Bonferroni-adjusted verdict are reported per cell; effect
size (rho, quintile spread) is always reported separately from the
significance verdict.

## 10. Coverage levels (fixed, not chosen post hoc)

100% (all valid sessions), 50%, 30%, 15% by descending `|feature|`. These
four levels are computed for every one of the 480 cells; no other level is
computed or reported.
