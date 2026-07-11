# DECISIONS.md — generation 3 (cash-open target atlas)

| # | Date | Decision | Rationale / consequence |
|---|---|---|---|
| 1 | 2026-07-11 | New branch `research/cash-open-target-atlas` from `1d39d8e`; new directory `research/cash_open_atlas/`; generations 1-2 untouched, no cross-imports | Per instruction: preserve all previous research generations unchanged |
| 2 | 2026-07-11 | Horizon "h: HH:MM candle close" resolved as `tau = h-1` (the h-th one-minute bar from 09:30, bar-OPEN-labeled) | Verified against all 7 stated (h, endpoint) pairs before writing any code; documented derivation in SPEC_ATLAS.md Sec. 2 |
| 3 | 2026-07-11 | Primary sample gate = full 30-bar (09:30-09:59) presence, applied identically to all 6 primary horizons; secondary h=60 gate = full 60-bar (09:30-10:29) presence, evaluated independently | Matches task instruction exactly; keeps the primary sample size constant across h so cross-horizon comparisons are apples-to-apples |
| 4 | 2026-07-11 | Reuse generation 1's audited `data/processed/{es,nq}_front_1m.parquet`; no data rebuild | Raw data and causal front-month mapping already audited in Stage 0 |
| 5 | 2026-07-11 | Q_h, E_h marked undefined (NaN), not 0/0 or any forced value, when `U_h+D_h==0` | Per explicit instruction; undefined-count reported per horizon rather than silently imputed |
| 6 | 2026-07-11 | No predictive, entry, exit, VWAP-band, pivot, reclaim, or sizing logic introduced anywhere in this generation | Per explicit purpose statement; this is a pure descriptive atlas |
