# KNOWN_LIMITATIONS.md — 10:00 open / pre-10:00 rejection-block discovery

1. Purely descriptive OHLCV-geometry study; no profitability, entry,
   exit, sizing, or TP/SL logic anywhere. Not a validation of any ICT
   pattern, trading system, or order-flow/absorption/dealer-positioning/
   liquidity-sweep narrative — those claims are explicitly out of scope
   regardless of what any result looks like.
2. Development partition only (2018-2022, ES/NQ); 2023+ never read.
3. One-minute OHLCV confirms a bar's range overlapped the 10:00 candle or
   a block zone but does not establish true intrabar sequence — same-bar
   morphology, same-bar ties, and the 10:00-candle caveat are proxies,
   restated in the final report per the mandated permanent caveats.
4. Exactly two block types (upper/lower wick zones from the 09:30-09:59
   window) are tested; no other ICT concept (order block, breaker, fair
   value gap, liquidity sweep, etc.) is defined or tested anywhere.
5. Fixed context strata (`PRE10_UP/DOWN/FLAT`, `CLOSE_LOW/MIDDLE/HIGH`,
   `UP/BALANCED/DOWN_DOMINANT`, `PRISTINE/PRETOUCHED`,
   `MOMENTUM_INTO_BLOCK`) are the only conditioning variables tested; no
   threshold search or additional combination was performed after
   viewing results.
6. `RANGE_30` and `MEDIAN_RANGE_20` are two different, sometimes
   materially different, normalization scales (current-session vs.
   trailing-20-session); both are reported for every excursion/signed-
   close output rather than one being chosen — readers should check both
   before treating a normalized effect size as robust.
7. Sessions before the 20th valid prior session in the development
   partition (a small number at the start of 2018) have no
   `MEDIAN_RANGE_20`-normalized outputs; they are retained for
   `RANGE_30`-normalized and raw-point outputs.
8. Ties for "the last bar whose high/low equals the 30-minute extreme"
   are broken by recency (`DECISIONS.md` #4); a different tie-break
   (e.g. first occurrence, or largest wick) would select a different
   block-forming bar and produce different zone boundaries.
9. Module B's post-interaction outcome horizons can read 1-minute bars
   past 11:00 ET for late interactions (`DECISIONS.md` #7); this is
   intentional (outcome horizons are defined in elapsed minutes from the
   interaction bar, not capped at the interaction-search window) but
   means "60-minute outcome" does not always mean "by 11:59," it means
   "60 minutes after this specific interaction," which may land later.
10. Multiple-testing correction (BH) controls false discovery within each
    declared family (`instrument x module`); it does not correct across
    modules or across the separately labeled exploratory families
    (other horizons, barriers, activation windows, context strata).
11. Contract-roll weeks are not specially excluded, consistent with the
    root front-month series' policy of no back-adjustment.
