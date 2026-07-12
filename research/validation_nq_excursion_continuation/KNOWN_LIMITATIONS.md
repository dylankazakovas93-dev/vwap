# KNOWN_LIMITATIONS.md — NQ upper-excursion continuation validation

1. This is a single, frozen, out-of-sample validation of one
   development-sample finding — not a new discovery process. No result
   here is a signal, strategy, or tradable edge; no profitability,
   entries, sizing, or TP/SL outcomes are computed anywhere.
2. The validation partition (2023 onward) spans roughly 3.4 years,
   materially shorter than the 5-year development partition; 2026 is
   explicitly partial (confirmed end date ~2026-06-08/09).
3. Only 4 calendar partitions exist for year-by-year reporting (2023,
   2024, 2025, partial 2026) versus the development study's 5 full years
   — the "≥3 of 4" year-sign-consistency bar is inherently a looser
   requirement in absolute count than generation 10's "≥4 of 5", though
   proportionally similar (75% vs 80%).
4. The primary test is a single one-sided exact binomial with no
   multiplicity correction, per explicit instruction ("no multiplicity
   correction is needed for this one primary hypothesis") — this is a
   deliberate departure from the BH-corrected discovery-stage discipline,
   appropriate specifically because this is a single frozen confirmatory
   test, not a search.
5. The two supporting candidates are Holm-corrected together but cannot
   rescue a failed primary result, per instruction — a `VALIDATED`
   classification requires the primary cell alone to pass all seven
   criteria.
6. As instructed, no other activation window, horizon, barrier, lookback,
   center estimator, or filter was computed or inspected — this
   validation cannot speak to whether some untested alternative
   parameterization would have validated better or worse.
7. Same-bar morphology and rolling-state results are supporting/secondary
   diagnostics only, never a substitute for or filter on the primary
   post-touch validation result.
8. As in all prior generations, roll-week sessions are not excluded.
