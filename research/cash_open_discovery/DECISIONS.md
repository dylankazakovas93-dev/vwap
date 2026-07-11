# DECISIONS.md — generation 2 (cash-open discovery)

| # | Date | Decision | Rationale / consequence |
|---|---|---|---|
| 1 | 2026-07-11 | New branch `research/cash-open-failed-auction-discovery` from `1d39d8e`; new research directory `research/cash_open_discovery/`; generation-1 files untouched | Per instruction: do not reinterpret the exploratory cash-open finding as though it had been preregistered in generation 1 |
| 2 | 2026-07-11 | Reuse generation 1's `data/processed/{es,nq}_front_1m.parquet` and its Stage-0 audit/partitions unchanged; no data rebuild | Raw data + causal front-month mapping already audited; re-deriving would duplicate work with no new information |
| 3 | 2026-07-11 | Outer-excursion search window: tau in [0,60] (09:30-10:30 ET); reclaim search window: 60 minutes past the outer bar or session end | Declared before any table viewed; bounds an otherwise unbounded "opening episode"; documented as Assumption A2 |
| 4 | 2026-07-11 | Opening-scale S(tau): 1.4826*median of |close(tau)-O| over trailing 60 prior RTH sessions, min 20 | Mirrors generation 1's already-validated minute-of-day robust-scale convention (same multiplier/window), applied to open-referenced rather than bar-to-bar displacement |
| 5 | 2026-07-11 | Minimum reported cell = 100 episodes (vs. 300 in generation 1) | Opening episodes are at most 1/session/A, far rarer than generation 1's whole-session shock events (~1291 dev sessions/instrument ceiling vs. ~100k shock events); declared before results |
| 6 | 2026-07-11 | Same-bar upper+lower threshold breach -> AMBIGUOUS_DIRECTION, excluded from primary analysis | Intrabar ordering unknowable from OHLCV; consistent with generation 1's AMBIG handling |
| 7 | 2026-07-11 | Held-episode forward outcomes direction-aligned to the hypothetical reclaim convention (lower=long, upper=short) for the matched comparison only | Needed for an apples-to-apples Question-1 comparison; does not imply held episodes "have" a direction; documented as Assumption A3 |
| 8 | 2026-07-11 | No news/macro calendar acquired; ordinary-vs-news-day stratification out of scope this generation | Per instruction: do not improvise a calendar; logged as limitation, not approximated |
| 9 | 2026-07-11 | Placebo anchor = 13:00 ET (midday), reusing identical state-machine logic re-based at that time | Away from cash open/close and overnight/European segments; tests specificity of any effect to 09:30 |
| 10 | 2026-07-11 | Discovery-stage verdict: REVISE HYPOTHESIS. HALF-only-reclaim reversal pattern recorded as a candidate for generation 3, not acted on this generation | Master hypothesis (reclaim=continuation) null; opposite-sign pattern found in a different subgroup than hypothesized, per protocol recorded not exploited |
