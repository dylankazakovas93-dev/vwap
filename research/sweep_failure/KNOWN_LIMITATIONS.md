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
12. The primary `FAILED_BREACH` vs. `SUCCESSFUL_BREACH_CONTROL`
    comparison is confounded by each class's own defining anchor: failed
    breaches anchor at a close-inside bar, successful-breach controls
    anchor at a close-outside bar, while both are scored against
    symmetric barriers fixed at the causal level. The uniformly large,
    highly significant effect found in nearly every primary cell
    (`DECISIONS.md` #9) is very likely dominated by this anchor-side
    confound rather than genuine new predictive information about
    post-failure price behavior — see `SWEEP_FAILURE_REPORT.md` for the
    full discussion and corroborating evidence (touch controls with an
    inside close show a similarly elevated rotation rate despite never
    breaching).
13. `DELAYED_FAILURE_CONTROL` and `NEITHER_RESOLVED_WITHIN_10MIN` are
    extremely rare (4 and 3 events respectively, pooled across both
    instruments) because they require all of `B, B+1, B+2` to close
    exactly tick-equal to the causal level — a narrow edge case that
    real tick-quantized OHLCV rarely produces. Findings involving these
    two classes should be read as anecdotal, not statistically
    supported.
