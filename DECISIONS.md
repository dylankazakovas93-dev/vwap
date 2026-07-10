# DECISIONS.md

| # | Date (UTC) | Decision | Rationale / consequence |
|---|---|---|---|
| 1 | 2026-07-10 | Raw .zst files kept out of git; SHA256 hashes committed instead | ~130MB binary data; reproduction requires files matching recorded hashes |
| 2 | 2026-07-10 | Partitions: dev 2018-2022, val 2023-2024, holdout 2025->end | Reserved before any strategy results viewed; holdout spans a distinct regime |
| 3 | 2026-07-10 | Front month = prior-session volume leader; no back-adjustment; features never span roll/session boundaries | Causal; avoids splice artifacts; loses ~L bars of events at each session start |
| 4 | 2026-07-10 | Minute-of-day baselines: trailing 60 sessions, min 20, robust (median/MAD) | Robust to COVID-type outliers; first ~20 sessions of data carry no events |
| 5 | 2026-07-10 | Lookback domain L={5,15,60}; ATR horizon fixed at 30; k={1,3}; z_thr={3,4}; anchors={Globex,RTH}; acceptance={2of3,3of5}; band 2.0σ/1.0σ inner | Minimal defensible domains per QUANT_RESEARCH_OS §7; full Cartesian (96 cells) replaced by continuous quantile analysis; hard budget 150 registry rows |
| 6 | 2026-07-10 | Macro tagging by fixed clock times (08:30/09:45/10:00/14:00 ET) without an event calendar | No calendar dataset supplied; documented approximation, tag-only, no exclusion |
| 7 | 2026-07-10 | First-passage AMBIG (both barriers in one bar) counted against continuation | Conservative ordering per OS §5.3 |
| 8 | 2026-07-10 | Candidate ledger persisted for all event-grid bars with |z_mod|>=2 plus per-session candidate counts; full every-bar ledger not persisted | Full grid ~2.9M rows/instrument x 2; size. Eligibility is still evaluated on every bar; only persistence is restricted. Logged as limitation |
| 9 | 2026-07-10 | Zero-cost results labeled gross (simulator assumption); economic floors expressed in ticks | Per Dylan's deployment assumption and OS §5.5 |
| 10 | 2026-07-10 | Placebo ATR-decile matching uses full-development-sample decile edges (not expanding causal quantiles) | Placebo is an analysis-time null construct, not a tradable feature; no forward information enters any tradable decision. Deviation from SPEC_LOCKED wording recorded here |
| 11 | 2026-07-10 | Event ledgers built once at z>=3; z>=4 analysed as a row subset | Identical features/outcomes; avoids duplicate computation; registered configs unchanged |
| 12 | 2026-07-10 | Bug fix before any analysis results viewed: signed persistence/efficiency folding used a numpy-bool identity comparison and produced NaN/sign-flipped values; fixed, regression test added, ledgers rebuilt | Found during ledger schema inspection (feature summary stats only, no outcome analysis had been run); not a results-driven change |
| 13 | 2026-07-10 | Engineering bug fix (placebo step referenced et_minute absent from event ledger); et_minute added to ledger builder + backfilled; run_analysis reordered to write main tables before placebo; RUN_REGISTRY truncated to header and analysis rerun cleanly | Crash occurred before any table was written; the truncated rows were duplicate configs from the same crashed run, not distinct research trials. No results were viewed between crash and fix |
| 14 | 2026-07-10 | Stage 2 verdict: REVISE HYPOTHESIS (continuation rejected; weak reversal thread). No entry freeze / TP-SL / validation / holdout performed | Continuation fails 2-tick floor; VWAP acceptance is anchor leakage; reversal is sign-stable but sub-floor outside cash open |
