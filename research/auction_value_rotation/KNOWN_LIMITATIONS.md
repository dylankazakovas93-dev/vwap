# KNOWN_LIMITATIONS.md — auction value reacceptance and rotation engine

1. All volume profiles are deterministic **approximations** from
   1-minute OHLCV; one-minute bars do not reveal true exchange
   volume-at-price. `UNIFORM_RANGE` (primary), `TYPICAL_PRICE_ROW`, and
   `CLOSE_PRICE_ROW` (sensitivity) are three different, reasonable
   approximations, not ground truth. A candidate surviving under only
   one of them is explicitly disqualified by candidate-selection
   criterion 9.
2. No profitability, entries, exits, sizing, reward:risk, or
   prop-account simulation logic anywhere in this generation. A survived
   OOS mechanism licenses, but is not itself, an execution study.
3. Development partition (2018, 2020, 2022, 2024) and OOS partition
   (2019, 2021, 2023, 2025) are non-consecutive by design — this
   evaluates regime generalization, not a chronological walk-forward
   test, and must not be described as one.
4. The 432-cell development grid is bounded and preregistered; it is
   still 432 cells x 8 (mapping x side) = 3,456 tested combinations
   before BH correction — a large family. BH correction is applied
   within each profile-mapping family as specified, but readers should
   still expect some cells to appear locally significant by chance; the
   12-condition candidate gate (requiring multi-year, multi-horizon,
   multi-profile-model, non-isolated-parameter-neighborhood support) is
   the primary defense against this, not the BH correction alone.
5. Tie-breaking rules (POC: lowest price; value-area expansion: prefer
   upper bin) are frozen, deterministic, and documented, but are
   themselves one reasonable choice among several defensible
   alternatives (`DECISIONS.md` #2); a different tie-break would shift
   VAH/VAL/POC by at most one bin width in tied cases.
6. Matching-variable bands (value-area width, profile age, distance-to-
   POC, realized volatility) are tercile cuts computed on development
   data only and frozen for OOS (`DECISIONS.md` #5) — OOS-period
   distribution shifts in these variables are not accounted for by
   re-cutting; an OOS event could fall into a development-defined band
   that is no longer representative of OOS-period conditions. This is a
   feature of the frozen-definition requirement, not an oversight.
7. Session-leg definitions are reused from a prior generation's audited
   convention rather than the task's own literal fallback (London
   03:00-09:29 ET); this generation's London leg is therefore 30 minutes
   shorter than the task's stated fallback would have produced
   (`DECISIONS.md` #1). Documented, not hidden.
8. Profile mappings 3 and 4 (prior RTH profile used overnight / used the
   next RTH session) reuse the *same* completed RTH profile for two
   different, non-overlapping target windows; a session with an
   incomplete RTH leg (excluded per session-completeness rules)
   produces no profile for *either* downstream mapping that session,
   which can create gaps in the mapping-3/4 event stream around holidays
   or data irregularities.
9. Realized-volatility band uses a causal ATR20 computed the same way as
   prior generations' `ATR20` (continuous 1-minute recursion, never
   reset); it is a volatility-scale proxy, not a claim about the true
   forward-looking volatility regime.
10. Contract-roll weeks are not specially excluded, consistent with the
    root front-month series' policy of no back-adjustment.
11. If the study is null (no candidate family qualifies), context
    variables (§ "Volume and context variables") are never computed
    (`DECISIONS.md` #7) — this generation cannot speak to whether any
    context variable would have mattered for a mechanism that itself was
    not found to be robust.
