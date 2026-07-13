# RESEARCH_CHARTER.md — EMA21 session-and-horizon decomposition

Branch: `research/ema21-session-horizon-surface`, base commit `7853a9c`
(intraday EMA21 level discovery: engine, ES/NQ analysis, final report).
This is a decomposition of the same underlying question along session and
touch-timing axes, not a hypothesis redesign: the prior generation found
no coarse New-York-RTH-level EMA21 rejection/breakthrough mechanism; it
did not test Asia, London, session-elapsed-time, or fine post-touch
horizon structure. This generation tests exactly that gap and nothing
else — no new indicators, no new EMA periods, no profitability.

## Research classification

Descriptive level-interaction study, one indicator (`FULL_SESSION_EMA21`
only — no EMA20/22 controls this generation, per instruction), decomposed
by three fixed trading sessions (Asia, London, New York), four touch-time
buckets within each session, two approach sides, and nine post-touch
horizons. Still no entries, exits, sizing, or TP/SL anywhere.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet`: same audited artifact used
  by the base generation, re-verified again this generation (hashes and
  `data_build.py` audit counters match root `DATA_CONTRACT.md`).
- Root `session_date = date(ET + 6h)` already groups one continuous
  Globex futures session (18:00 ET open -> 17:00 ET close next day) under
  one `session_date` value, including the midnight-crossing Asia leg —
  see `DATA_CONTRACT.md` and `DECISIONS.md` #3 for the derivation used to
  assign Asia/London/New York/excluded without a naive calendar-date
  filter.
- Development partition unchanged: 2018-01-03 -> 2022-12-30.

## What is new this generation (not inherited from the base generation)

- Three fixed session windows (Asia 18:00-02:59 ET, London 03:00-08:29
  ET, New York 09:30-15:59 ET) replace the base generation's RTH-only
  time-of-day strata (OPEN/MID_MORNING/MIDDAY/AFTERNOON).
  08:30-09:29 ET and 16:00-17:59 ET are excluded outright.
- Event-arming state resets at the start of each session leg (Asia,
  London, New York) even though the underlying EMA21 recursion itself
  never resets — see `SPEC_SESSION_HORIZONS.md` §3.
- Touch-time buckets measure elapsed bars since that session leg's own
  first bar (not clock time-of-day), in four buckets:
  `SESSION_0_TO_30/30_TO_60/60_TO_120/120_PLUS`, plus `ALL_SESSION`.
- Nine post-touch horizons (1,2,3,4,6,9,12,18,24 bars) replace the base
  generation's six (1,2,3,5,10,20); every horizon must complete inside
  the same session leg — no crossing into the next session or the
  excluded interval, no partial-window fallback.
- Only EMA21 is computed (no EMA20/22 specificity controls this
  generation, per explicit instruction).
- BH multiple-testing family is `instrument x session` (across
  touch-time-bucket x approach-side x horizon), not `instrument x
  session_definition x time_stratum` (across span x side) as in the base
  generation.
- Session-level mechanism classification
  (`{ASIA,LONDON,NEW_YORK}_{REJECTION,BREAKTHROUGH}_MECHANISM` /
  `NO_COHERENT_SESSION_MECHANISM`) requiring adjacent-horizon and
  adjacent-touch-time-bucket coherence plus 4-of-5-year support is new;
  the base generation had no analogous session-level rollup.

## Assumptions

- A1: "Chronological futures-session mapping" for Asia's midnight wrap is
  satisfied by the existing `session_date` column (root DATA_CONTRACT):
  bars with `et_minute` in `[1080,1439]` (18:00-23:59, previous calendar
  date) and bars with `et_minute` in `[0,179]` (00:00-02:59, same
  calendar date as `session_date`) both carry the same `session_date`
  value and are therefore already grouped into one continuous session —
  verified by direct construction and by test #9.
- A2: Touch-time-bucket elapsed time is measured in five-minute bars
  counted from a session leg's own first bar in `ts_event` order (true
  chronological order, so the Asia wrap is handled automatically without
  a separate elapsed-clock calculation) — bars 1-6 = 0-30 min, 7-12 =
  30-60 min, 13-24 = 60-120 min, 25+ = 120+ min, exactly as specified.
- A3: EMA21 warm-up (60 completed 5-minute bars, unchanged from the base
  generation's `DECISIONS.md` #4) is evaluated on the full continuous
  bar sequence, not reset per session leg — only the *arming* state
  resets per leg, never the EMA recursion or its warm-up gate.
- A4: A session leg with fewer than 3 usable bars (data gaps, holidays)
  simply never arms in that leg; this is not treated as an error, only as
  zero contributed excursions for that leg-instance.

## Falsifiers

Per `SPEC_SESSION_HORIZONS.md` §11, a cell is `REJECTION_DOMINANT` or
`BREAKTHROUGH_DOMINANT` only under five joint conditions (sample floor,
>=5pp effect, q<0.05, matching median-signed-close sign, >=4/5-year sign
agreement). A session-level mechanism additionally requires coherence
across >=2 adjacent horizons and >=2 adjacent touch-time buckets (unless
confined to the first 30 minutes) and >=4/5-year support — one isolated
significant cell is never promoted to a session-level claim. If no
session/side combination reaches a session-level mechanism label, the
final report states the preregistered fallback sentence verbatim (§15).
