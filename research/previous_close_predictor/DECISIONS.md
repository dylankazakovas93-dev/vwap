# DECISIONS.md — generation 4 (previous-close predictor discovery)

| # | Date | Decision | Rationale / consequence |
|---|---|---|---|
| 1 | 2026-07-11 | New branch `research/previous-close-predictor-discovery` from `research/cash-open-target-atlas` @ `201896d`; new directory `research/previous_close_predictor/`; generations 1-3 untouched | Per instruction; preserves prior generations |
| 2 | 2026-07-11 | Generation 3's `atlas.py` imported by file path (`importlib`), not copied or reimplemented, for target R_h/Q_h computation | Per instruction "use the existing cash-open atlas targets without redefining them" |
| 3 | 2026-07-11 | Early close = session's last RTH-window bar (`et_minute<=959`) has `et_minute<959`; early-close predecessors excluded from primary analysis, count reported separately; also excluded from trailing-baseline pools | Matches instruction exactly; a partial RTH day has no standard 16:00 close to anchor windows on |
| 4 | 2026-07-11 | `signed_efficiency_W` numerator/denominator both telescope from `first_bar_open_W` to `official_close`, using close-to-close diffs for all but the first bar (which uses open-to-close) | Ensures `sum(d_i) == ret_W` exactly, so the ratio is bounded in [-1,1] by the triangle inequality, matching the stated interpretation |
| 5 | 2026-07-11 | `range_ratio_W` = simple ratio to trailing median (not MAD z-score); `norm_ret_W` = MAD-based robust z-score (1.4826x) | Matches the instruction's differing wording for the two normalizations ("robust scale" for return vs. "relative to trailing median" for range) |
| 6 | 2026-07-11 | Coverage levels fixed at {100,50,30,15}%; multiple-testing budget fixed at 480 elementary tests (2 instr x 5 features x 6 windows x 4 horizons x 2 targets), Bonferroni alpha=0.05/480 declared before results | Per instruction: do not choose coverage/thresholds post hoc; report the complete test count |
| 7 | 2026-07-11 | No interactions, combinations, ML models, entries, TP/SL, MAE/MFE, PF/Sharpe, sizing, or validation/holdout access anywhere in this generation | Per explicit research restrictions in the task |
