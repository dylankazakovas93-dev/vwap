# KNOWN_LIMITATIONS.md — generation 10 (NQ excursion-level timing study)

1. Pure phenomenon discovery; no level here is a signal, strategy, or
   tradable edge. No entries, exits, sizing, TP/SL, or prop-account
   outcomes anywhere. The rolling-state test (§20) is a causal diagnostic
   only, explicitly not a trading rule.
2. Development partition only (2018-2022); validation/holdout untouched.
   No 2023+ access anywhere.
3. Independent of all prior generations: no synthetic control, no
   taxonomy conditioning, no prior-highs/lows, VWAP, ATR, HMM/trend-regime
   labels, or dynamic swing levels. Not directly comparable to generation
   9's 86-level results without a fresh alignment exercise (out of scope
   here).
4. Nested activation windows are NOT independent samples of each other —
   window `A=60` is a strict superset of `A=30`'s touch events. Every
   report of "coherence across adjacent windows" is describing degrees of
   the same underlying touch population, not independent replications.
5. The master touch search is restricted to 09:30-11:29 ET only; a level
   touched only after 11:29 is recorded as untouched in this generation,
   by design.
6. The 10-session lookback requires exactly 10 valid prior 09:30 candles
   with no fallback; the first 10 sessions of the development partition
   have no valid levels.
7. Same-bar `Close==level_value` neutral classification uses exact
   floating-point equality — a narrow definition that may undercount
   near-neutral bars that closed a fraction of a tick away.
8. The rolling-state test's prior-10-event window mixes calendar time
   across potentially large gaps (a level touched infrequently could have
   its "prior 10" span more than a year) — no recency weighting or gap
   cap is applied, per the frozen specification.
9. ES is a negative-control replication using the identical pipeline and
   constants as NQ; a null ES result does not prove the NQ result is
   real, and a non-null ES result would not automatically invalidate NQ —
   both are reported and interpreted separately, as instructed.
10. As in prior generations, roll-week sessions are not excluded.
11. The exact two-sided binomial test (barrier-first, same-bar) and
    Fisher exact test (rolling-state) are standard; no alternative test is
    offered or compared.
