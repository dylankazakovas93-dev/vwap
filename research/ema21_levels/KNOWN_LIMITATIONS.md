# KNOWN_LIMITATIONS.md — intraday EMA21 level discovery

1. This is a level-interaction discovery study, not a strategy backtest
   and not the "21 EMA strategy" from the motivating screenshot. No
   profitability, entry, exit, sizing, or TP/SL logic is defined or
   implied anywhere in this generation; any resemblance of a rejection or
   breakthrough statistic to a trading edge must not be read as one
   without a separate, dedicated validation-partition study.
2. Development partition only (2018-2022, ES/NQ); results may not
   generalize to 2023 onward, which this generation never reads.
3. Five-minute bars built from one-minute OHLCV confirm that the EMA
   level traded during a bar but do not establish true intrabar sequence
   (stated per-section in `SPEC_EMA21_LEVELS.md` §6 and repeated in the
   final report). Same-bar morphology and same-bar-tie barrier outcomes
   are proxies, not intrabar ground truth.
4. `RTH_EMA` and `FULL_SESSION_EMA` are two genuinely different state
   series (different bar counts feeding the recursion, different warm-up
   calendar time); they are reported side by side and neither is treated
   as ground truth for the other.
5. EMA20/EMA21/EMA22 are the only periods tested, by design — this
   generation cannot speak to EMA9, EMA50, EMA200, or any SMA/VWAP/MACD/
   RSI construction. A "generic EMA zone" finding at spans 20-22 does not
   imply the effect (or its absence) holds at other spans.
6. The 3-bar arming rule is a specific, somewhat arbitrary choice for
   "clearly separated" — a different bar count would produce a different
   event set. It is fixed before any event data was viewed (`DECISIONS.md`
   #5) and not tuned against results.
7. Barrier same-bar ties are reported as `SAME_BAR_TIE`, never resolved by
   assumed intrabar order; this understates whichever barrier a trader
   might argue "obviously" hit first on a given bar, by design.
8. Year-stability results use 5 development years only; "4 of 5 years
   agree" is a low bar with only 5 data points and should not be read as
   strong evidence of temporal stability on its own — it is one of five
   joint conditions required for a directional classification.
9. Multiple testing correction (BH) is applied within family as specified;
   it controls false discovery rate within each declared family, not
   across every number ever computed in this generation. Exploratory
   families are labeled as such and are not used to justify
   `EMA21_SPECIFIC` claims.
10. Per-time-stratum `touch_rate` in `reports/tables/full_exploratory_results.csv` can
    exceed 1.0 for individual strata (observed up to ~1.13) because eligible
    armed excursions are attributed to a stratum by their *start* bar while
    touches are attributed by the *touch* bar (`DECISIONS.md` #10); an
    excursion that starts in one stratum and touches in the next is counted
    once in each. `ALL_RTH` touch rates are unaffected (observed max 0.98)
    and this does not affect the primary classification, which uses touch
    and barrier-outcome counts directly rather than touch_rate.
11. Contract-roll weeks are not specially excluded from 5-minute bar
    construction (consistent with the root front-month series, which is
    not back-adjusted); a roll-induced price step could occasionally
    contaminate an ATR or excursion calculation spanning a roll bar. Not
    separately quantified in this generation.
