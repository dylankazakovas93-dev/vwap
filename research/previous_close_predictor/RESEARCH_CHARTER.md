# RESEARCH_CHARTER.md — Previous-Close Predictor Discovery (Generation 4)

Branch: `research/previous-close-predictor-discovery`, base
`research/cash-open-target-atlas` @ `201896d`. Preserves generations 1
(`research/vwap_shock`), 2 (`research/cash_open_discovery`), and 3
(`research/cash_open_atlas`) unchanged.

## Research classification

Discovery / standalone-feature screening (QUANT_RESEARCH_OS.md Sec. 4.2:
"establish whether a raw signal exists"). **Not** model-building, not
combination testing, not a trading rule. Every feature is tested alone
against the atlas targets; interactions, combinations, ML models, entries,
fills, TP/SL, MAE/MFE, PF/Sharpe, sizing, and validation/holdout access are
explicitly out of scope for this generation (per instruction) and are
recorded as candidates for a possible future generation only if a feature
here shows credible standalone evidence.

## Purpose

Test whether six previous-RTH-session closing-window features (1/5/10/
15/30/60 minutes before the verified prior close) carry any standalone
statistical relationship with the NEXT session's cash-open targets (R_h,
Q_h at h in {5,10,15,30}), as already defined by generation 3's atlas
(`research/cash_open_atlas/src/atlas.py`) — reused unmodified, not
redefined.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged):
  `ts_event` = bar OPEN, `et_minute` DST-resolved per bar, `session_date` =
  calendar date of ET+6h.
- RTH window = 09:30-16:00 ET (`et_minute` 570-959 inclusive marks
  completed RTH bars; the bar opening at 15:59 ET, `et_minute==959`,
  closes at 16:00 ET and is the official RTH close print).
- Generation 3's atlas (`atlas.py`) computes, per session,
  `R_h = Close_h - O`, `Q_h = (U_h-D_h)/(U_h+D_h)` at `tau=h-1` for
  `h in {1,3,5,10,15,30,60}` (primary gate: full 09:30-09:59 window;
  secondary gate for h=60: full 09:30-10:29 window) — reused here via
  direct import, not reimplemented.
- Development partition: 2018-01-03 -> 2022-12-30, unchanged.

## Assumptions

- A1: "Immediately preceding valid RTH session" = the nearest earlier
  `session_date` (in the same instrument's continuous front-month series)
  that is NOT an early close (see Sec. "Early close" below). Weekends and
  holidays are handled automatically because `session_date` already skips
  non-trading days (generation 1's construction); no separate calendar
  logic is introduced.
- A2: A session is an **early close** if its last available RTH-window bar
  (`et_minute <= 959`) has `et_minute < 959`, i.e. the session's own data
  ends before the 16:00 ET print. This is a session-level flag, independent
  of any single window W's data completeness.
- A3: A target session is included in the **primary analysis** only if its
  immediately preceding valid session (A1) is not an early close and has
  complete data for the specific window W being tested; early-close
  predecessors are excluded and counted separately (per instruction), not
  imputed or approximated.
- A4: Trailing normalization baselines (Sec. "Windows") draw only from
  prior sessions that are themselves non-early-close, and only from the
  loaded development-partition frame (session_date <= 2022-12-30), so no
  validation/holdout information can enter a baseline.

## Falsifiers / stop conditions (discovery framing)

- A feature/window/horizon/target cell showing a raw correlation is not
  "credible standalone evidence" unless: the sign is consistent between
  Pearson and Spearman, the year-by-year sign is not driven by a single
  year, the effect survives the declared multiple-testing adjustment, and
  bullish/bearish symmetry does not reveal a one-sided artifact.
- If no feature clears this bar, the honest verdict is that previous-close
  behavior carries no standalone predictive value for these targets in
  this sample — a valid and expected discovery-stage outcome.
