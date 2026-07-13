# KNOWN_LIMITATIONS.md — EMA21 session-and-horizon decomposition

1. Descriptive level-interaction study; no profitability, entry, exit,
   sizing, or TP/SL logic anywhere. Not a validation of any trading
   system.
2. Development partition only (2018-2022, ES/NQ); 2023+ never read.
3. Five-minute OHLCV confirms the EMA traded during a bar but does not
   establish true intrabar sequence (same-bar morphology and same-bar
   ties are proxies, not intrabar ground truth) — restated in the final
   report per the mandated permanent caveat.
4. Only `FULL_SESSION_EMA21` is tested; this generation cannot speak to
   `RTH_EMA`, other spans, or other indicator families. A session/timing
   effect (or its absence) found here for EMA21 under the full-session
   construction should not be assumed to hold for the RTH-only
   construction studied in the base generation, or vice versa.
5. Session windows (Asia/London/New York) and touch-time buckets are
   fixed, somewhat arbitrary partitions of the trading day; a different
   choice of boundaries could produce different event sets. Fixed before
   any event data was viewed and not tuned against results.
6. Asia and London legs typically have thinner volume/participation than
   New York for ES/NQ; smaller or noisier event counts in those legs are
   expected and are reported via `sample_status`/`UNDERPOWERED`, not
   hidden.
7. The `EXCLUDED` transition intervals (08:30-09:29, 16:00-17:59 ET)
   contribute to the continuous EMA21/ATR20 recursion (never reset) but
   never host an event or outcome bar; this is intentional, not a data
   gap.
8. Session-level mechanism classification (`SPEC_SESSION_HORIZONS.md`
   §14) is a coherence heuristic over a modest number of cells per
   session (4 touch-time buckets x 9 horizons x 2 sides); "at least 2
   adjacent horizons/buckets, 4-of-5 years" is a low bar in absolute
   terms and should be read as "not obviously an isolated fluke," not as
   strong statistical evidence on its own.
9. Multiple-testing correction (BH) controls false discovery within each
   declared family (`instrument x session`, 72 members); it does not
   correct across the six primary families jointly, nor across the
   separately labeled exploratory families (same-bar, 0.5-ATR barriers,
   `ALL_SESSION`).
10. Contract-roll weeks are not specially excluded, consistent with the
    root front-month series' policy of no back-adjustment.
