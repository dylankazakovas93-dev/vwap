# Stage 0 gate report — PASS

Repository: dylankazakovas93-dev/vwap, branch
claude/reversal-continuation-research-p6hsdi, base commit 87ce679 (empty repo
+ README).

## Evidence

- Raw data identity, schema, coverage, hashes: DATA_CONTRACT.md and
  reports/raw_data_hashes.txt. ES 2018-01-01->2026-06-08, NQ
  2018-01-01->2026-06-07, contiguous across archives, zero overlap
  duplicates after dedup step (0 rows actually removed — ranges abut).
- Timestamps: UTC ns, bar-OPEN convention (Databento ohlcv). Verified
  session shape: first bar 18:00 ET, last bar 16:59 ET.
- Timezone/DST: America/New_York conversion per bar; maintenance-halt strays
  removed (70 ES / 38 NQ).
- Contract handling: outrights only; causal prior-session volume-leader
  front month; 33 rolls per root at expected mid-expiry-month dates; no
  back-adjustment; windows never span rolls.
- Quality: 0 impossible OHLC, 0 zero-volume front-month bars, 0 residual
  duplicate timestamps; short sessions enumerated and explained
  (2020-03-16 COVID halt 759 bars; 2025-11-28 early close; data-end stub).
- Partitions reserved before results: dev 2018-2022 / val 2023-2024 /
  untouched holdout 2025->end.

## Gate criteria

| Criterion | Verdict |
|---|---|
| Data identity + hashes recorded | PASS |
| Schema/timezone/session semantics established | PASS |
| Quality anomalies enumerated, none blocking | PASS |
| Raw data immutable | PASS (git-ignored, hash-pinned) |
| Partitions reserved pre-results | PASS |

Reproduction: `cd research/vwap_shock && python -m src.data_build`
(requires data/raw files matching recorded SHA256).
