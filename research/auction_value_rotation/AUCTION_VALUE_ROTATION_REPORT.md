# Auction Value Reacceptance and Rotation Engine — Final Report

Branch: `research/auction-value-rotation-engine` (base `201896d`)
Instrument: NQ front-month, 1-minute bars. ES not evaluated (see item 20).
Final verdict: **NULL — does not survive out-of-sample evaluation.**

## 1. Hypothesis under test

Price that (a) attempts discovery beyond a completed session's
value-area edge (VAH/VAL), (b) fails to remain outside, and (c) is
reaccepted inside the prior value area, is more likely to subsequently
rotate to that session's POC than a matched bar that was simply sitting
inside value with no such episode (`MATCHED_INSIDE_STATE`).

## 2. Data and partition

- `data/processed/nq_front_1m.parquet`, re-verified against
  `DATA_CONTRACT.md` (hashes, `data_build.py` re-run, counters matched)
  during preregistration.
- Non-consecutive regime-generalization split, **not** a chronological
  walk-forward test: development years `2018, 2020, 2022, 2024`; locked
  OOS years `2019, 2021, 2023, 2025`, evaluated exactly once; holdout
  year `2026` never read (enforced by a tested, hard-coded guard in
  `src/data.py::filter_partition`).
- Session legs (reused audited convention): ASIA 18:00-02:59 ET, LONDON
  03:00-08:29 ET, NEW_YORK_RTH 09:30-15:59 ET.

## 3. Profile construction

Three deterministic volume-profile approximations from 1-minute OHLCV
(`UNIFORM_RANGE` primary, `TYPICAL_PRICE_ROW` and `CLOSE_PRICE_ROW`
sensitivity), bin widths `{0.25, 0.50, 1.00}`, value-area percentages
`{68%, 70%, 72%}`, deterministic POC/VA construction with frozen
tie-breaks. All conserve total session volume exactly; unit-tested
against 9 hand-calculated synthetic sessions (`tests/test_profiles.py`).

## 4. Profile mappings (4, kept separate)

`M1_ASIA_TO_LONDON`, `M2_LONDON_TO_NY`, `M3_RTH_TO_OVERNIGHT`,
`M4_RTH_TO_NEXT_RTH` — each with its own `expiry_ts` tied to its target
leg's own end (`DECISIONS.md` #3). All 4 mappings populated on real
data (821-988 mapping rows each, dev partition) after fixing a bug
where `LEG_EXPECTED_BARS["ASIA"]` was wrong (item 15 below), which had
silently zeroed out mappings 1 and 3.

## 5. Event state machine

`src/events.py::scan_profile_side` classifies the first interaction
with a level as `TOUCH` or `BREACH`; for breaches, evaluates all 4
acceptance rules (`R1_ONE_CLOSE`, `R2_TWO_CONSECUTIVE_CLOSES`,
`R3_TWO_OF_THREE_CLOSES`, `R4_DEPTH_ACCEPTANCE`) independently per
excursion, recording confirmation index/timestamp, bars outside, breach
depth (ticks and %VA-width), POC distance, and freshness. Long/short
symmetry and expiry-boundary correctness verified by unit tests
(10 tests, `tests/test_events.py`), including one that caught an
off-by-one in the expiry check before any real data was touched.

## 6. The 432-cell development grid

Implemented as one master excursion/acceptance ledger per
(profile-mapping, side), with the grid's 5 dimensions (breach depth x
max time outside x acceptance rule x POC-distance floor x freshness
cap) applied as post-hoc boolean filters (`src/grid.py`), rather than
432 independent scans — verified statistically identical to an
independent direct re-scan on a spot-check cell
(`tests/test_grid.py::test_grid_cell_matches_independent_direct_scan`).
432 x 4 mappings x 2 sides = 3,456 cells, all computed and retained
(including null/underpowered cells), no cells discarded, no additional
thresholds tried.

## 7. Controls

4 matched controls per `SPEC_AUCTION_VALUE.md` section 7:
`TOUCH_WITHOUT_BREACH`, `MATCHED_INSIDE_STATE` (primary/most important),
`SUCCESSFUL_DISCOVERY`, `REPEATED_TEST` (ledger only, not further
analyzed in this generation since the base mechanism did not survive
OOS). Matching variables: clock-time (ET hour), value-area-width
tercile, freshness tercile, POC-distance tercile, causal-ATR20 tercile
— all tercile cutoffs frozen on development data only and reused
unchanged for OOS (`DECISIONS.md` #5).

## 8. Outcomes

Primary: `POC_REACHED_BEFORE_REDISCOVERY` at horizons 15/30/60/120
minutes, `POC_FIRST` / `REDISCOVERY_FIRST` / `SAME_BAR_AMBIGUOUS` /
`NEITHER` / `INCOMPLETE_HORIZON`, no lookahead into the confirmation bar
itself (unit-tested). Secondary: `POC_TO_OPPOSITE_EDGE_COMPLETION`,
computed for `POC_FIRST` events only, reported as an entirely separate
table, never merged into the primary result.

## 9. Statistics

Matched-stratified permutation test (10,000 draws, seed `20260713`,
vectorized per stratum for tractability across the full grid), BH
correction within each profile-mapping family. Year-by-year, pooled,
profile-model-sensitivity, and neighboring-parameter-stability tables
produced for every cell; null/underpowered cells retained, not dropped.

## 10. Candidate selection (12 criteria, all required)

Of 3,456 grid cells: 72 cleared the raw count floor (>=300 treatment,
>=150 matched control); 7 passed criteria 1-7/11/12; 6 passed all 12,
including second-pass bin-width, profile-model, and
adjacent-parameter-neighborhood sensitivity checks (run only for
near-qualifying cells, `DECISIONS.md` #11d). All 6 rows belong to a
single, coherent family: `M2_LONDON_TO_NY`, short side, `R1_ONE_CLOSE`,
POC-distance floor 10-20% of VA width. See `CANDIDATE_MANIFEST.md` for
the exact 6 parameter rows and full detail.

Development pooled effect (primary row): **+17.4 percentage points**
in `POC_FIRST` rate vs. `MATCHED_INSIDE_STATE`, positive in all 4
development years, BH q = 0.0066, worst single-year effect +11.1pp, no
year contributing more than 39% of pooled effect mass.

## 11. Pre-OOS freeze

`CANDIDATE_MANIFEST.md` committed and pushed (`cfba108`) before
`src/oos_pipeline.py` was written. Verified no `outputs/oos_*` file
existed on disk beforehand. `oos_pipeline.py` refuses to execute unless
the manifest is present in the committed git HEAD tree (tested,
`tests/test_oos_guard.py`), and refuses to re-run if `oos_results.json`
already exists.

## 12. OOS evaluation — the result

Evaluated exactly once, 2019/2021/2023/2025, same code path and
thresholds as development, frozen matching bands, 2026 never read.

**All 6 candidate rows FAIL.** Primary row: pooled OOS effect **+2.6
percentage points** (vs. +17.4pp development), permutation p = 0.83,
positive in only 3 of 4 OOS years (2021 was slightly negative), BH
q = 0.957. The effect required >=8.7pp (half of development) to pass
criterion 2; it did not clear even a third of that bar. No row passed
the BH-significance criterion. This is not a borderline result — the
effect that looked strong and consistent in development was
statistically indistinguishable from zero out of sample.

## 13. Bugs found and fixed during this generation (transparency)

1. `LEG_EXPECTED_BARS["ASIA"]` was `930` instead of the correct `540`
   (9-hour window), which silently zeroed mappings 1 and 3 entirely —
   caught immediately by running the pipeline on real data and
   inspecting mapping row counts before any grid computation.
2. `GlobalSeries` compared tz-aware and tz-naive timestamps, which
   would have crashed (not silently miscomputed) on real data — caught
   by unit tests before real data was touched.
3. `MATCHED_INSIDE_STATE`'s `excursion_extreme` fallback was set to the
   control's own anchor close, making the "trade below excursion
   extreme" failure test trigger on almost any 1-tick downtick on the
   very next bar. This inflated the treatment-vs-control gap to an
   implausible 35-48pp before the fix (a mechanical confound, in the
   same family as prior generations' anchor-confound findings); after
   the fix, effects fell to the 8-20pp range reported above. Caught by
   noticing the effect size was implausibly large before trusting it,
   not by a test — a live example of the "diagnose before reporting a
   large effect" discipline this research series has followed
   throughout.
4. `stratum_id` originally returned a tuple, and numpy's `==` against a
   tuple-valued object array silently mis-broadcasts (compares
   positionally instead of whole-tuple), which would have corrupted
   every stratified treatment/control comparison. Caught by a unit test
   before real data was touched; fixed by using a string key instead.

## 14. What this generation does NOT establish

No profit, reward:risk, position sizing, stop placement, Sharpe ratio,
or prop-account simulation was computed anywhere in this generation.
Only path/outcome information (`POC_FIRST` rate and secondary path
stats) was recorded, for a possible later, separate execution study —
which this null result does not license, since the underlying
directional mechanism itself did not survive OOS.

---

## Plain-English summary

**Did the mechanism work?** No. In development it looked like a real,
sizeable effect — about a 17-percentage-point higher chance of
rotating to London's POC after a failed breakout above London's VAH,
holding across all 4 development years. Out of sample, that effect
collapsed to about 3 percentage points and was statistically
indistinguishable from noise.

**Why did it look real in development and then disappear?** Two
reasons, both documented above. First, an actual bug in how the control
group's "failure" condition was defined inflated the effect before it
was caught and fixed — a reminder that a large, clean-looking effect is
itself a reason to look harder, not a reason to trust it. Second, even
after that fix, a 6-row, single-family "survivor" of a 3,456-cell
search is still exactly the kind of result multiple-comparisons theory
predicts will sometimes clear even a strict 12-criteria gate by chance,
and that is what the out-of-sample test is for. It did its job here.

**Is any part of this usable?** Not as a trading signal. The engine
itself — profile construction, the event state machine, the matched
controls, the grid-as-ledger-filter architecture, the permutation/BH
statistics, the OOS-gating discipline — is reusable machinery for
testing other auction-value hypotheses, and it is tested and correct as
far as this generation's test suite can verify. But the specific
mechanism this generation set out to test (failed discovery ->
reacceptance -> rotation to POC) is not supported by the evidence.

**What would change this conclusion?** A genuinely different dataset
(a different instrument tested on its own frozen development/OOS split,
not NQ's OOS years reused) surviving the same gate, or a materially
different — and separately preregistered — definition of the mechanism.
Neither of those has been attempted here, per the prohibition on
redefining after seeing OOS results.

**Why wasn't ES tested too?** The task specified ES only as secondary
confirmation for a mechanism that first survives on NQ. Since nothing
survived NQ's OOS test, there is no finding for ES to confirm; testing
ES now would just be a second, undisclosed attempt to salvage a result,
which is exactly what the "no OOS subgroup search" rule prohibits.

**What's the honest one-line takeaway?** A plausible, mechanistically
sensible auction-value rotation effect was found in development,
survived an unusually strict 12-criteria gate, and still failed cleanly
out of sample — the null result is the finding.
