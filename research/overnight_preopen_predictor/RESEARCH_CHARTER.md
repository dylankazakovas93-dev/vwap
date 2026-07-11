# RESEARCH_CHARTER.md — Overnight/Pre-open Predictor Discovery (Generation 5)

Branch: `research/overnight-preopen-predictor-discovery`, base
`research/cash-open-target-atlas` @ `201896d`. Preserves generations 1
(`research/vwap_shock`), 2 (`research/cash_open_discovery`), 3
(`research/cash_open_atlas`), and 4 (`research/previous_close_predictor`)
unchanged.

## Research classification

Standalone-feature discovery screen (QUANT_RESEARCH_OS.md Sec. 4.2:
"establish whether a raw signal exists"). Every feature is tested alone
against the atlas targets. **No combination with generation 4's
previous-close features, no ES/NQ cross-market predictors, no ML models,
no entries/levels/TP-SL/MAE-MFE/sizing/prop-simulation, and no
validation/holdout access** — all per explicit instruction.

## Purpose

Test whether overnight (Globex-session-open through 09:29 ET) and
immediately pre-open ES/NQ behavior carries any standalone statistical
relationship with the next session's cash-open direction (R_h) or
dominant excursion (Q_h), h in {5,10,15,30}, as already defined by
generation 3's atlas (`research/cash_open_atlas/src/atlas.py`) — reused
unmodified, exactly as in generation 4.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet` (generation 1, unchanged):
  `ts_event` = bar OPEN, `et_minute` DST-resolved per bar, `session_date`
  = calendar date of ET+6h. Globex session anchor 18:00 ET; maintenance
  halt bars (17:00-18:00 ET) already excluded upstream.
- Within a `session_date` group, `et_minute` wraps at midnight (a session
  runs 18:00 ET one calendar day through 16:59 ET the next), so
  chronological order within a session must be taken from `ts_event`
  (already sorted), not from `et_minute` directly — the same principle
  established and tested in generation 2's overnight-context module.
- The 09:30 ET bar (`et_minute==570`) exists every development session;
  "overnight" = every bar of a session strictly before that bar
  (chronologically, i.e. by `ts_event` position, not by an `et_minute`
  range filter).
- Development partition: 2018-01-03 -> 2022-12-30, unchanged.

## Assumptions

- A1: The Globex/futures-session open for session `s` = the `open` of the
  first bar (by `ts_event`) belonging to `s`. This is the "verified
  Globex/futures-session open" reference distinct from the prior RTH
  close reference (Sec. "Overnight definitions" in SPEC_OVERNIGHT.md).
- A2: A minimum overnight bar count (>=30 bars, mirroring the convention
  used for VWAP validity in generations 1-2) is required before the frozen
  overnight VWAP/dispersion is considered valid; below that, VWAP-derived
  features are undefined for that session, not imputed.
- A3: "Prior RTH" reference values (prior RTH close, prior RTH open, prior
  RTH high/low) come from the same previous-valid-RTH-session mapping
  logic used in generation 4 (nearest earlier `session_date`); if that
  predecessor is an early close, prior-RTH/overnight relationship
  variables (Sec. D) are undefined for that target row and the count is
  reported separately, consistent with generation 4's treatment. Overnight
  and pre-open-window features (Sec. A-C) do NOT depend on the predecessor
  session at all and are unaffected by an early-close predecessor.

## Falsifiers / stop conditions (discovery framing)

Same standard as generation 4: a cell is not "credible standalone
evidence" unless sign is consistent between Pearson and Spearman, the
year-by-year sign is not carried by one year, the effect survives the
declared multiple-testing adjustment, and bullish/bearish symmetry is not
a one-sided artifact. A fully null result is a valid, expected, and
useful discovery-stage outcome.
