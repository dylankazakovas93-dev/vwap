# SPEC_ATLAS.md — locked before any development-partition result viewed

## 1. Opening reference

`O` = `open` of the bar with `et_minute == 570` (09:30:00-09:31:00 ET),
per instrument per session. Bars are indexed by `tau = et_minute - 570`
(tau=0 is the 09:30 bar).

## 2. Horizon-to-bar mapping (exact, derived and verified against every
   stated example before any code was run)

The task specifies endpoints as "h=H: HH:MM candle close," where "the
HH:MM candle" denotes the one-minute bar whose OPEN is HH:MM (Databento
bar-open convention, inherited and re-verified here). Solving for `tau`:

| h (minutes) | stated endpoint | candle open time | tau = h-1 |
|---|---|---|---|
| 1  | 09:30 candle close | 09:30 | 0 |
| 3  | 09:32 candle close | 09:32 | 2 |
| 5  | 09:34 candle close | 09:34 | 4 |
| 10 | 09:39 candle close | 09:39 | 9 |
| 15 | 09:44 candle close | 09:44 | 14 |
| 30 | 09:59 candle close | 09:59 | 29 |
| 60 | 10:29 candle close | 10:29 | 59 |

In every case, `tau = h - 1` exactly (the h-th one-minute bar counting
09:30 as bar #1). This is the sole mapping used; no alternative
interpretation (e.g., "h minutes after the close of the 09:30 bar") is
used anywhere in the code.

`Close_h = close(tau = h-1)`. The window "09:30 through horizon h" used
for `U_h`/`D_h` is bars `tau = 0 .. h-1` inclusive (the first h bars).

## 3. Target definitions (exact)

For each session and horizon h:

```
R_h = Close_h - O
U_h = max(High[tau=0..h-1]) - O
D_h = O - min(Low[tau=0..h-1])
Q_h = (U_h - D_h) / (U_h + D_h)          [undefined if U_h+D_h == 0]
E_h = R_h / (U_h + D_h)                   [undefined if U_h+D_h == 0]
```

`U_h, D_h >= 0` always (O is within [min Low, max High] of its own bar by
construction, so both are non-negative; this is a coded invariant, not an
assumption, and is unit-tested). `Q_h in [-1, 1]` whenever defined
(mathematical identity of the ratio given `U_h, D_h >= 0`), also tested.

## 4. Sample gating (SPEC, not discretionary per-run)

- **Primary sample** (h in {1,3,5,10,15,30}): a session is included only if
  bars `tau = 0..29` (09:30-09:59 ET, 30 bars) are ALL present (no gaps).
  This single gate is applied uniformly across all six primary horizons —
  the primary sample size is identical for h=1 through h=30 within an
  instrument-year (does not shrink with h).
- **Secondary sample** (h=60): a session is included in the h=60 report
  only if bars `tau=0..59` (09:30-10:29 ET, 60 bars) are ALL present. This
  is evaluated independently; failing the h=60 gate never removes a
  session from the primary sample, and passing gate implies the primary
  gate is also satisfied (60-bar completeness is a superset of 30-bar
  completeness).
- One row per (instrument, session_date). Sessions failing the primary
  gate are excluded from the ledger's primary columns entirely (not
  imputed, not zero-filled) but are recorded in a separate
  missing-sessions log with the reason (partial day, data gap, etc.).

## 5. Derived labels

- `closing_direction_h = sign(R_h)` in {UP, DOWN, NEUTRAL}; NEUTRAL iff
  `R_h == 0` exactly.
- `dominant_side_h = sign(Q_h)` in {UPPER, LOWER, NEUTRAL}; NEUTRAL iff
  `Q_h` is exactly 0 or undefined (U_h+D_h==0).
- `initial_final_agree_h` (h != 1): TRUE if
  `sign(R_1) == sign(R_h)` and neither is 0; FALSE if signs differ and
  neither is 0; NEUTRAL if either `R_1` or `R_h` is exactly 0.

## 6. Outputs (per instrument x horizon, unless noted)

Valid session count (primary and secondary reported separately); mean,
median, {5,10,25,75,90,95}th percentiles of R,U,D,Q,E (Q,E computed only
over defined observations, with the undefined count reported alongside);
day-block bootstrap 95% CI (500 resamples over session_date, seed
20260711) for the mean of each of R,U,D,Q,E; frequency of
UP/DOWN/NEUTRAL closing direction and UPPER/LOWER/NEUTRAL dominant side;
initial/final agreement rate per horizon; year-by-year (2018-2022) mean
and count for R and Q; upper-vs-lower symmetry (mean U_h vs mean D_h,
paired day-block bootstrap CI on the difference); concentration (share of
total |R_h| and of total (U_h+D_h) contributed by the top decile of
sessions by that metric); Spearman correlation matrix across
{R,U,D,Q,E} x horizons within an instrument, and between ES and NQ at
matching horizons; full null/anomaly inventory (any coded-invariant
violation, any horizon/year cell below a 20-session reporting floor,
any missing-session reason breakdown).

## 7. Search / registry discipline

This is a fixed, fully-enumerated descriptive report (2 instruments x 7
horizons x a fixed statistic set) — there is no threshold search, no model
selection, and therefore no trial-budget concept in the Sec. 7-style sense
of prior generations. Every executed analysis pass is still logged in
`RUN_REGISTRY.csv` for reproducibility and to make the "nothing else was
tried" claim auditable.
