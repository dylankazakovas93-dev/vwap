# RESEARCH_CHARTER.md — sweep-and-failure discovery

Branch: `research/sweep-and-failure-discovery`, base commit `201896d`
(Generation 3: cash-open target atlas — engine, descriptive analysis).
Independent generation: no levels, taxonomy, or methodology imported
from any prior generation. Inherits only the audited ES/NQ one-minute
OHLCV data infrastructure (`data/processed/{es,nq}_front_1m.parquet`,
re-verified this generation) and general no-lookahead discipline.

## Research classification

Descriptive OHLCV-geometry study of a precise, narrow hypothesis:

> A brief breach of a causal prior high or low, followed within one to
> three completed one-minute bars by a close back inside the level,
> predicts rotation away more strongly than an ordinary touch, a
> successful breakout, or a delayed failure.

This is explicitly a **mechanical sweep-and-failure study**, not a claim
about stop hunting, liquidity engineering, dealer positioning, or any
other market-microstructure narrative. "ICT" terminology is not used as
evidence anywhere; the four event/control classes (`FAILED_BREACH_*`,
`SUCCESSFUL_BREACH_CONTROL`, `DELAYED_FAILURE_CONTROL`,
`TOUCH_WITHOUT_BREACH`) are defined purely by OHLCV geometry relative to
a causal level. No trading strategy, entry, exit, sizing, or prop
simulation is defined anywhere. Thresholds (breach magnitude bands,
volume strata, permutation matching strata) are fixed before any
development-partition result is viewed and are never re-tuned afterward.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet`: re-hashed raw archives and
  re-ran `research/vwap_shock/src/data_build.py` unmodified this
  generation; counters matched root `DATA_CONTRACT.md` exactly.
- Development partition unchanged: 2018-01-03 -> 2022-12-30.

## Assumptions

- A1: "Immediately previous valid session" for the previous-RTH-high/low
  levels means the most recent prior `session_date` (root front-month
  series) with a complete 09:30-15:59 ET bar set (390 one-minute bars);
  a session with a gap in that window is skipped when looking backward
  for the previous valid session (never imputed, never partially used).
- A2: "Current futures session's 18:00-09:29 ET" overnight window for a
  given RTH session date `D` means the continuous Globex bars from
  18:00 ET on the prior calendar day through 09:29 ET on `D`, which —
  per the root `session_date = date(ET+6h)` convention — all carry
  `session_date == D`; the overnight level is valid only if that full
  interval's 1-minute bars are present with no gap (930 bars @ 1-minute
  resolution from 18:00 to 09:29 inclusive... actually 15.5 hours = 930
  minutes; exact bar count is derived and asserted by a test, not
  assumed).
- A3: Tick size 0.25 for both ES and NQ (as in the prior EMA21/10:00-open
  generations) is used for tick-normalized equality tests
  (`TOUCH_WITHOUT_BREACH`'s `High_T == level`) and the one-tick breach
  requirement.
- A4: The causal clock-minute volume percentile (60 prior valid
  sessions, same exact ET minute) is a **secondary diagnostic** used
  only for the `HIGH_VOLUME`/`NORMAL_VOLUME`/`LOW_VOLUME` context strata
  and the volume secondary comparison — never for primary event
  eligibility, per explicit instruction.
- A5: ES and NQ are processed as fully separate primary series (separate
  level ledgers, separate episode/event streams); the ES-NQ pairing
  described in "ES-NQ confirmation" is computed as an additional,
  secondary diagnostic column attached to each event, never used to
  filter or merge the two instruments' primary event streams.

## Falsifiers

Per `SPEC_SWEEP_FAILURE.md` §"Classification", a primary cell is only
`FAILED_BREACH_ROTATION_SUPPORTED` or `..._BREAKOUT_SUPPORTED` under
eight joint conditions (sample floors in both compared states, >=5pp
effect, BH q<0.05 from a stratified permutation test, matching
median-signed-close contrast, >=4/5-year sign agreement, and support at
one adjacent horizon beyond the primary 15-minute horizon). Any
volume/confirmation/previous-test claim additionally requires its own
sample floor, incremental effect, corrected significance, and
>=3-year sign agreement. One isolated significant subgroup is never
promoted. If nothing coherent survives, the final report states the
preregistered fallback sentence verbatim.
