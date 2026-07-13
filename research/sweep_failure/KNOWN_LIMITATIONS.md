# KNOWN_LIMITATIONS.md — sweep-and-failure discovery

1. Purely descriptive OHLCV-geometry study; no profitability, entry,
   exit, sizing, or prop-simulation logic anywhere. Not a trading
   strategy and not evidence of stop-hunting, liquidity engineering, or
   dealer positioning — those narratives are explicitly out of scope
   regardless of what any result looks like.
2. Development partition only (2018-2022, ES/NQ); 2023+ never read.
3. One-minute OHLCV confirms both prices traded during a minute but does
   not establish true intrabar sequence — same-bar morphology and
   same-bar ties are proxies, restated in the final report per the
   mandated permanent caveat.
4. Exactly four causal levels are tested (previous-RTH high/low,
   overnight high/low); no opening range, swing point, VWAP, order
   block, or previous-week level is defined or tested anywhere.
5. Breach-magnitude bands, volume strata, and permutation matching
   strata are fixed before any development-partition result was viewed
   and are never re-tuned after seeing results.
6. ES-NQ confirmation is a secondary diagnostic column attached to each
   event; it never filters or merges the two instruments' primary event
   streams, and any confirmation-related claim requires its own
   incremental-effect and significance bar (`SPEC_SWEEP_FAILURE.md`
   §20) — it is not treated as evidence on its own.
7. The stratified permutation test matches on six dimensions at once
   (instrument x level type x time stratum x breach-magnitude band x
   prior-test-count category x side); some matching strata may contain
   very few observations, producing wide permutation-test uncertainty
   even when the pooled comparison looks large — the permutation
   procedure itself (not a t-test or normal approximation) is used
   specifically because it does not assume large-sample normality within
   thin strata, but thin strata still limit resolving power.
8. A breach with no completed inside close within `B..B+9` is retained
   as `NEITHER_RESOLVED_WITHIN_10MIN` (`DECISIONS.md` #5); this
   population exists and is reported but is not one of the task's four
   named comparison classes and is not used in the primary or secondary
   comparisons.
9. Multiple-testing correction (BH) controls false discovery within each
   declared family; it does not correct across the primary and every
   secondary family jointly.
10. Contract-roll weeks are not specially excluded, consistent with the
    root front-month series' policy of no back-adjustment.
11. Causal clock-minute volume percentiles require 60 prior valid
    sessions at the exact same ET minute; early-partition events (before
    60 valid prior sessions exist) have no volume stratum and are
    excluded from volume-stratified tables only (retained everywhere
    else).
