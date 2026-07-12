# KNOWN_LIMITATIONS.md — generation 9 (simple cash-open level study)

1. Pure phenomenon discovery; no level here is a signal, strategy, or
   tradable edge. No entries, exits, sizing, TP/SL optimization, or
   profitability computation anywhere. Does not claim evidence of order
   flow, absorption, participant inventory, dealer positioning, stop
   hunting, or queue behavior.
2. Development partition only (2018-2022); validation/holdout untouched.
3. Independent of generations 6-8: no synthetic control, no taxonomy
   conditioning, no reuse of the 38-level library. This means Family A/B
   here cannot be directly compared to generation 7/8's level families
   without a fresh alignment exercise (out of scope for this generation).
4. Touch search is restricted to 09:30-11:29 ET only; a level touched
   only after 11:29 is recorded as untouched in this generation, by
   design.
5. Family B requires exactly N (5/10/20) valid prior 09:30 candles with no
   fallback; the first N sessions of the development partition (per
   lookback) have no Family-B levels for that lookback.
6. Family A2 (prior-RTH VWAP) is unavailable whenever the immediately
   preceding session is an early close or incomplete — no substitution to
   an earlier session.
7. Same-bar `Close==level_value` neutral classification uses exact
   floating-point equality (DECISIONS.md #5) — a narrow definition that
   may undercount near-neutral bars that closed a fraction of a tick away.
8. Alias/coincident-level detection (§19) does not deduplicate or merge
   rows; every formula-specific result is retained even when multiple
   parameterizations reproduce the same physical price — by design, to
   allow reporting on redundancy rather than hiding it.
9. `EMA` center uses `ewm(span=N, adjust=False).mean()`'s final value
   computed over exactly the trailing N valid excursions each session;
   the smoothing coefficient is never retuned or selected by result.
10. As in prior generations, roll-week sessions are not excluded.
11. Behavior classification's "exact binomial test" for the 1.0-SD
    barrier and for same-bar morphology is a standard two-sided exact
    binomial test on non-tied/non-neutral outcomes; no alternative test is
    offered or compared.
