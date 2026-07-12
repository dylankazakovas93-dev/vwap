# KNOWN_LIMITATIONS.md — generation 7 (cash-open level library)

1. Level construction only; no level here is a signal, predictor, or
   tradable edge. Part 2A explicitly excludes touch/reaction detection,
   subsequent-return computation, taxonomy-conditional outcomes, and
   profitability/entry/exit logic.
2. Development partition only (2018-2022); validation/holdout untouched.
3. Family 1 requires 60+ valid prior sessions (generation 6's exact-window
   convention, unmodified); the first ~60 development sessions have no
   family-1 levels.
4. Families 2/4 require >=30 overnight bars; thin-overnight sessions
   (e.g. holiday-adjacent, data gaps) are excluded, not imputed.
5. Family 3 requires a non-early-close predecessor session; a session
   immediately following an early close has no family-3 levels for that
   occurrence (no fallback to an earlier session).
6. Family 5 (prior-session ATR30 bands) is entirely absent from this
   generation — an explicit scope decision, not an oversight, and may be
   proposed as a separate generation later.
7. Family 6 (dynamic levels) is listed only in `SPEC_LEVELS.md`, never
   computed or tested in this generation.
8. The empirical-clustering threshold (`0.1 * scale`) is a single fixed
   design choice with no sensitivity grid in this pass — a scope
   limitation, not a tuned/optimized value.
9. The synthetic-control draw uses a fixed, recorded random seed; it is
   one realization per real level observation, not a distribution of
   controls — a future generation wanting a full null distribution would
   need to redraw with multiple seeds.
10. Roll-week sessions are not excluded (consistent with prior
    generations' policy).
11. Overnight-window bar counts can vary substantially across sessions
    (holidays, DST transitions, data gaps); the `>=30`-bar validity floor
    is a coarse filter, not a data-quality audit of the overnight leg.
12. (Revision 3 correction) The family-1 quantile ladder (`p25/p75/p90/
    p95`) uses pandas' default (linear) interpolation for the rolling
    quantile; no alternative interpolation method is tested or offered.
13. `prior_settlement_open` is explicitly NOT implemented and must not be
    added without a fresh, explicit approval — its earlier appearance in
    SPEC_LEVELS.md Revision 2 was a drafting error, not an authorized
    candidate level (DECISIONS.md #13).
14. `overnight_high_dev_vwap`/`overnight_low_dev_vwap` remain diagnostic
    distances, not price levels; a future generation wanting to test
    reactions to "how far the overnight range sits from VWAP" as a level
    in its own right would need a fresh design decision, not an assumption
    that these fields are already usable as such.
