# RESEARCH_CHARTER.md — Intraday EMA21 Level Discovery (new generation)

Branch: `research/intraday-ema21-level-discovery`, base commit `201896d`
(Generation 3: cash-open target atlas — engine, descriptive analysis).
All previous research generations (`research/vwap_shock`,
`research/cash_open_atlas`, and anything committed after `201896d` on other
branches) are left unchanged. This generation does not import conclusions,
levels, controls, taxonomy classes, or methodology from any prior cash-open
research. It inherits only:

- the audited ES/NQ one-minute OHLCV data infrastructure
  (`data/processed/{es,nq}_front_1m.parquet`, built by
  `research/vwap_shock/src/data_build.py`, unchanged, re-verified against
  the SHA256 hashes in `DATA_CONTRACT.md` before use — see
  `research/ema21_levels/DATA_CONTRACT.md`), and
- general no-lookahead engineering discipline (causal features only,
  frozen event levels, partition guards).

No level definition, arming rule, outcome definition, classification
taxonomy, or threshold is carried over from the cash-open work. Everything
in `SPEC_EMA21_LEVELS.md` is new and specific to this generation.

## Motivating context (explicitly not evidence)

A screenshot circulated showing a "21 EMA strategy" returning +0.72% vs.
+45.31% buy-and-hold, Sharpe 0.13, max drawdown -22.18%. That screenshot
describes a *trading system* (entries, exits, sizing) and is **not**
evidence about whether the 21-period EMA is a repeatable intraday price
*level*. This generation does not attempt to reproduce, validate, or
improve that strategy. No profitability, entries, exits, sizing, or TP/SL
logic is defined anywhere below.

## Research classification

**Descriptive level-interaction study, not a strategy backtest.** The
question under test:

> When five-minute price approaches and touches a causally frozen 21-period
> EMA after being clearly separated from it (three consecutive bars fully
> on one side), does the subsequent path show repeatable rejection back
> toward the approach side, or breakthrough continuation through the EMA?

A second, structurally mandatory question: is any observed effect specific
to period 21, or is it generic moving-average-zone behavior shared by
EMA20 and EMA22? Only EMA20/21/22 are computed; no other period, and no
other indicator family (SMA, VWAP, MACD, RSI), is tested anywhere in this
generation (`KNOWN_LIMITATIONS.md` and the Prohibited Analyses list in
`SPEC_EMA21_LEVELS.md` make this explicit).

## Facts (inherited, verified this generation)

- `data/raw/{es,nq}*.ohlcv-1m.csv.zst` re-hashed against
  `DATA_CONTRACT.md` (root): all 8 archives match exactly.
- `research/vwap_shock/src/data_build.py` re-run unmodified; produced
  audit counters identical to those recorded in the root `DATA_CONTRACT.md`
  (ES: 2,968,335 front-month bars / 2,179 sessions; NQ: 2,963,298 bars /
  2,178 sessions; 0 impossible OHLC rows; 0 duplicate rows after dedup).
- Development partition (from root `DATA_CONTRACT.md`, unchanged):
  2018-01-03 -> 2022-12-30. Validation (2023-2024) and holdout (2025->end)
  exist in the processed parquet files but are excluded by an explicit
  date filter before any event, outcome, or statistic is computed — see
  `DECISIONS.md` #2 and test #1/#2 in `tests/`.

## Assumptions

- A1: "Five-minute bar" means a deterministic, non-overlapping aggregation
  of the audited one-minute bars into `[HH:00, HH:05), [HH:05,HH:10), ...`
  boundaries (aligned to the top of each ET hour), each requiring all 5
  constituent one-minute bars present; a bar missing any constituent
  minute is dropped, not partially aggregated (per spec: "no partial
  five-minute bars").
- A2: RTH aggregation window is 09:30-15:59 ET inclusive of the bars whose
  *open* falls in that range, i.e. bars `[09:30,09:35) .. [15:55,16:00)`,
  which is the standard partition of 09:30-16:00 into twelve 5-minute
  bars per hour block; this yields 78 RTH five-minute bars per full
  session.
- A3: `FULL_SESSION_EMA` uses continuous chronological 5-minute closes
  across the full Globex session (18:00 ET -> 17:00 ET next day, per root
  DATA_CONTRACT maintenance-halt exclusion), carried across session
  boundaries with no reset; touches are only ever evaluated on RTH bars.
- A4: EMA warm-up requires at least 60 completed 5-minute bars of history
  (chosen conservatively, >> the largest span of 22) before any bar is
  eligible to arm or be touched; the exact count and its derivation are
  logged in `DECISIONS.md`.
- A5: Contract-roll boundaries are not treated specially for 5-minute bar
  construction beyond what the root front-month series already encodes
  (front-month is already a single causal series per the root
  DATA_CONTRACT; a roll is simply a price-continuity point like any other
  bar transition, consistent with root generation's own policy of not
  back-adjusting or excluding roll weeks).

## Falsifiers

Per the classification rules in `SPEC_EMA21_LEVELS.md`, a cell is only
called `REJECTION_DOMINANT` or `BREAKTHROUGH_DOMINANT` if it passes *all
five* joint conditions (sample floor, >=5pp effect, BH q<0.05, matching
median-signed-close sign, >=4/5 year-sign agreement). Anything short of
that is `MIXED_OR_NULL` or `UNDERPOWERED`, retained and reported, not
discarded. `EMA21_SPECIFIC` requires EMA21 to be directionally classified
while EMA20 and EMA22 are not classified the same way in the same cell,
*and* EMA21's effect to exceed both neighbors by >=5pp; otherwise, if
EMA20/21/22 show materially similar direction and magnitude, the cell is
called `GENERIC_EMA_ZONE`. If no cell in either instrument achieves
`EMA21_SPECIFIC`, `RESEARCH_CHARTER.md` and the final report state plainly
that no EMA21-specific mechanism was found — see the mandated fallback
sentence in `SPEC_EMA21_LEVELS.md`.
