# SPEC_OVERNIGHT.md — locked before any development-partition result viewed

## 1. Session mapping and chronology

Within a `session_date` group, `et_minute` wraps at midnight (18:00 ET one
calendar day -> 16:59 ET the next), so all "overnight" computations use
**chronological order by `ts_event`** (already sorted ascending in the
base parquet), never an `et_minute` range filter that would silently skip
the wrap. "Overnight" for session `s` = every bar of `s` strictly before
the position of the `et_minute==570` (09:30 ET) bar. "Pre-open window W"
(Sec. 4) uses a direct `et_minute` range filter instead, because
`[570-W, 569]` for `W<=60` never crosses the midnight wrap (verified:
`570-60=510 >= 0`).

## 2. Two overnight reference returns — kept explicitly separate

1. `prior_rth_close_to_0929_return = close_0929 - prior_rth_close`
   (anchor = previous valid RTH session's official 16:00 close).
2. `globex_open_to_0929_return = close_0929 - globex_open`
   (anchor = this session's own first bar's open, i.e. the verified
   Globex/futures-session open). This IS the "overnight return" used
   throughout Sec. 3.

These are never substituted for one another; (1) is used only in Sec. 6
(prior-RTH/overnight relationship variables), (2) is the Section-3/4
"overnight return."

`close_0929` = `close` of the bar with `et_minute==569` (the last
completed bar before the 09:30 bar).

## 3. Full overnight path (anchor = Globex open, Sec. 2 definition 2)

```
overnight_return          = close_0929 - globex_open
overnight_high             = max(High) over all overnight bars
overnight_low              = min(Low) over all overnight bars
range_position_0929        = 2*(close_0929 - overnight_low) /
                              (overnight_high - overnight_low) - 1
                              [undefined if range == 0]
signed_path_efficiency_on   = overnight_return / sum(|d_i|)
                              where d_1 = close(bar_1) - open(bar_1),
                              d_i = close(bar_i) - close(bar_{i-1}) for
                              i=2..N (N = overnight bar count), so that
                              sum(d_i) == overnight_return exactly
                              [undefined if sum(|d_i|) == 0]
dist_from_overnight_high    = overnight_high - close_0929
dist_from_overnight_low     = close_0929 - overnight_low
normalized_overnight_volume = overnight_total_volume /
                              trailing_median_overnight_volume(s)
                              [trailing 60 prior valid sessions, min 20;
                              Sec. 7]
```

## 4. Frozen overnight VWAP (bars through 09:29 only)

```
p_bar_i    = (High_i + Low_i + Close_i) / 3            (per overnight bar i)
VWAP_on    = sum(p_bar_i * Volume_i) / sum(Volume_i)     (cumulative, all
                                                          overnight bars)
sigma_on   = sqrt( sum(Volume_i * p_bar_i^2) / sum(Volume_i) - VWAP_on^2 )
             clipped at 0 under floating-point error
```

This is the exact VWAP-dispersion equation, stated here before any code is
written (identical in form to the causal within-session dispersion used
in generations 1-2, applied here to the overnight window instead of the
RTH session). **Validity**: requires >= 30 overnight bars, else all
VWAP-derived features below are undefined for that session (not imputed).

```
dist_0929_from_vwap        = close_0929 - VWAP_on
normalized_dist_from_vwap  = dist_0929_from_vwap / sigma_on
                              [undefined if sigma_on == 0 or invalid]
vwap_location_in_range     = 2*(VWAP_on - overnight_low) /
                              (overnight_high - overnight_low) - 1
                              [undefined if range == 0]
```

No bar at or after `et_minute==570` (09:30 ET) is ever used in `VWAP_on`,
`sigma_on`, or any Sec. 3-4 quantity (coded and tested).

## 5. Final pre-open windows (`et_minute` in `[570-W, 569]`, exact)

For `W in {5, 10, 15, 30, 60}`:

```
signed_return_W        = close(et=569) - open(et=570-W)
range_W                = max(High[window]) - min(Low[window])
close_location_W       = 2*(close(et=569) - min(Low[window])) / range_W - 1
                          [undefined if range_W == 0]
signed_path_eff_W       = signed_return_W / sum(|d_i|)   (same telescoping
                          construction as Sec. 3, over the W window bars)
                          [undefined if sum(|d_i|) == 0]
relative_volume_W       = sum(Volume[window]) /
                          trailing_median_volume_W(s)     [Sec. 7]
prev_window_return_W    = close(et=570-W-1) - open(et=570-2W)
                          (the immediately preceding, non-overlapping,
                          equal-length window, ending exactly where the
                          current window begins)
return_acceleration_W   = signed_return_W - prev_window_return_W
                          [undefined if the preceding window's bars are
                          incomplete, e.g. before ~09:00 ET for W=60 on a
                          session with a short overnight; never imputed]
```

`return_acceleration_W` is tested as its own standalone feature (per
instruction), never as a chosen-after-the-fact interaction.

## 6. Prior-RTH/overnight relationship (predefined only, Sec. 2 def. 1)

Predecessor session `p` = nearest earlier valid (non-early-close)
`session_date`, identical mapping logic to generation 4. If no
predecessor exists or `p` is an early close, all five variables below are
undefined for that target row (excluded from Sec. 6 analysis only; Sec.
3-5 features are unaffected and still computed/tested for that session).

```
overnight_direction              = sign(overnight_return)
prior_rth_direction               = sign(prior_rth_close - prior_rth_open)
overnight_agrees_with_prior_rth   = +1 if signs equal and both nonzero,
                                    -1 if signs differ and both nonzero,
                                     0 (NEUTRAL) if either is exactly zero
overnight_minus_priorrth_norm     = (overnight_return - prior_rth_close_to_
                                     0929_return... ) -- see note below,
                                     normalized by a causal trailing robust
                                     scale (1.4826*median(|diff|), trailing
                                     60 prior valid sessions, min 20)
above_below_prior_close          = sign(close_0929 - prior_rth_close),
                                    0 = NEUTRAL if exactly equal
broke_prior_rth_high_or_low       = 1 if (overnight_high > prior_rth_high)
                                    or (overnight_low < prior_rth_low),
                                    else 0
finished_inside_prior_rth_range   = 1 if prior_rth_low <= close_0929 <=
                                    prior_rth_high, else 0
```

Note on `overnight_minus_priorrth_norm`: the "difference" compared is
`overnight_return` (Globex-open anchor) minus `prior_rth_close_to_0929_
return` (prior-close anchor) — i.e. the gap between the two reference
returns defined in Sec. 2, which isolates the portion of the move that
occurred before the Globex session opened (the prior day's late-RTH-to-
Globex-open gap) from the portion after. This is the only place the two
anchors are combined, and only as a predefined difference, never
substituted for each other elsewhere.

## 7. Causal normalization (trailing baselines)

All trailing baselines: 1.4826*median(|feature|) (robust scale features:
`overnight_minus_priorrth_norm`) or plain median (ratio features:
`normalized_overnight_volume`, `relative_volume_W`), over the trailing 60
prior valid sessions strictly before `s`, minimum 20 valid observations,
restricted to the loaded development-partition frame — current/future
sessions never enter a baseline (coded and tested).

## 8. Targets (reused unmodified from generation 3)

`R_h`, `Q_h` for `h in {5,10,15,30}` (subset of generation 3's full
`{1,3,5,10,15,30,60}` output; not redefined), plus derived
`closing_direction_h` / `dominant_side_h` labels, identical to
generation 4's usage.

## 9. Standalone features tested (45 total per instrument)

- Sec. 3 (full overnight path): 7 — `overnight_return`, `overnight_range`
  (i.e. `overnight_high - overnight_low`), `range_position_0929`,
  `signed_path_efficiency_on`, `dist_from_overnight_high`,
  `dist_from_overnight_low`, `normalized_overnight_volume`.
- Sec. 4 (frozen VWAP): 3 — `dist_0929_from_vwap`,
  `normalized_dist_from_vwap`, `vwap_location_in_range`.
- Sec. 5 (pre-open windows): 6 feature types x 5 windows = 30 —
  `signed_return_W`, `range_W`, `close_location_W`, `signed_path_eff_W`,
  `relative_volume_W`, `return_acceleration_W`, W in {5,10,15,30,60}.
- Sec. 6 (relationship variables): 5 — `overnight_agrees_with_prior_rth`,
  `overnight_minus_priorrth_norm`, `above_below_prior_close`,
  `broke_prior_rth_high_or_low`, `finished_inside_prior_rth_range`.

Total = 7+3+30+5 = **45 features x 2 instruments x 4 horizons x 2 targets
(R,Q) = 720 elementary tests.**

## 10. Analysis plan (identical diagnostic set to generation 4, applied here)

Per (instrument, feature, horizon, target): Pearson r, Spearman rho,
day-block bootstrap 95% CI (500 resamples, seed 20260711); sign agreement
(excluding NEUTRAL either side); 5-bin quintile conditional means and
rank-correlation monotonicity check (n=5, no minimum-n gate, per
generation 4's corrected convention); year-by-year (2018-2022) mean AND
per-year Spearman; bullish/bearish symmetry (mean target given feature>0
vs feature<0, paired bootstrap diff CI); outlier influence (statistic
recomputed with the single largest-|feature| session dropped); accuracy/
coverage at fixed levels {100%,50%,30%,15%} of the valid sample by
descending |feature| (fixed in advance, never chosen post hoc).

## 11. Multiple-testing accounting

720 elementary tests, each logged as one `RUN_REGISTRY.csv` row (stage=
`overnight_screen`). Bonferroni alpha = 0.05/720 = 6.944e-5. An
effective-N sensitivity (average pairwise |Spearman| among the 45
features per instrument -> effective feature count) is also reported,
mirroring generation 4's Sec. 9 approach, since the six windows within
Sec. 5 and the overnight/VWAP features in Sec. 3-4 are expected to be
mutually correlated. Effect size (rho, quintile spread) is always reported
separately from the significance verdict; every one of the 720 cells is
reported (nulls preserved), and no single window/feature is highlighted
in isolation.
