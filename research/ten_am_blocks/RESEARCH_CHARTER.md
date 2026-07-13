# RESEARCH_CHARTER.md — 10:00 open mechanism and pre-10:00 rejection-block discovery

Branch: `research/ten-am-rejection-block-discovery`, base commit `201896d`
(Generation 3: cash-open target atlas — engine, descriptive analysis).
Independent generation: no levels, taxonomy, or methodology imported
from any prior generation (cash-open, EMA21, or otherwise). Inherits only
the audited ES/NQ one-minute OHLCV data infrastructure
(`data/processed/{es,nq}_front_1m.parquet`, re-verified this generation)
and general no-lookahead discipline (causal features, frozen event
zones, partition guards).

## Research classification

Descriptive OHLCV-geometry study of two related but separable questions:

- **Module A**: does the 10:00 ET one-minute candle's own bullish/
  bearish/neutral close state carry repeatable continuation or reversal
  information over the following hour?
- **Module B**: do two mechanically defined pre-10:00 "wick zones" (an
  upper zone built from the 09:30-09:59 high-making bar's wick, a lower
  zone from the low-making bar's wick) show repeatable reversal or
  breakthrough behavior when price returns to them after 10:00?

This is explicitly **not** a test of ICT ("rejection block," "breaker,"
"order block," liquidity-sweep, absorption, or dealer-positioning)
terminology or narrative. The zones are defined purely as OHLCV geometry
(§ "Module B" in `SPEC_TEN_AM_BLOCKS.md`); any resemblance to a named
retail pattern is coincidental to the geometric construction, not an
endorsement of the narrative behind it. No order-flow, absorption,
dealer-positioning, or liquidity-sweep claim is made anywhere in this
generation. No profitability, entries, exits, sizing, or TP/SL logic
either.

## Facts (inherited, verified)

- `data/processed/{es,nq}_front_1m.parquet`: re-hashed raw archives and
  re-ran `research/vwap_shock/src/data_build.py` unmodified this
  generation; counters matched root `DATA_CONTRACT.md` exactly.
- Development partition unchanged: 2018-01-03 -> 2022-12-30 (root
  `DATA_CONTRACT.md` uses the first trading session on/after 2018-01-01,
  which is 2018-01-03).
- Every session has a 09:30 ET bar at `et_minute==570` (verified in the
  base-generation atlas work; re-verified here independently via the
  session-ledger completeness gate in `SPEC_TEN_AM_BLOCKS.md` §1).

## Assumptions

- A1: The pre-10:00 construction window is exactly the 30 one-minute
  bars with `et_minute` in `[570, 599]` (09:30-09:59 inclusive); a
  session missing any of these 30 bars is excluded from the session
  ledger outright (no imputation), consistent with "no partial-window
  fallback."
- A2: The post-10:00 interaction search window is exactly the 60
  one-minute bars with `et_minute` in `[600, 659]` (10:00-10:59
  inclusive); a session missing any of these 60 bars is excluded from
  Module B's interaction search (Module A's own 10:00 candle and its
  horizon-H outcome windows are checked independently per horizon, per
  §"Post-event outcome horizons").
- A3: "Last bar within 09:30-09:59 whose high equals the final 30-minute
  high" (and the mirrored low rule) is resolved by scanning the 30 bars
  in chronological order and keeping the most recent bar whose own high
  (low) equals `RANGE_30`'s high (low) endpoint — i.e. ties among
  multiple bars sharing the extreme are broken by recency, exactly as
  stated ("last bar ... whose high equals").
- A4: Tick size 0.25 for both ES and NQ (stated directly in the task) is
  used only for the 10:00 candle's `BULLISH_1000`/`BEARISH_1000`/
  `NEUTRAL_1000` threshold and the one-tick minimum block-width gate;
  it is not used anywhere else.
- A5: `MEDIAN_RANGE_20` requires 20 prior **valid** sessions (RANGE_30 >
  0, all 30 pre-10:00 bars present) drawn from the session ledger in
  chronological order — the "previous 20" count skips invalid/excluded
  sessions rather than counting calendar sessions, so the first eligible
  session for `MEDIAN_RANGE_20` is the 21st *valid* session of the
  partition, not the 21st calendar session.

## Falsifiers

Per `SPEC_TEN_AM_BLOCKS.md` §"Classification", a cell is only
`TEN_AM_CONTINUATION`/`TEN_AM_REVERSAL` (Module A) or
`REJECTION_BLOCK_REVERSAL_DOMINANT`/`..._BREAKTHROUGH_DOMINANT` (Module
B) under five joint conditions (sample floor, >=5pp effect, BH q<0.05,
matching median-signed-close sign, >=4/5-year sign agreement), and a
"coherent conditional mechanism" additionally requires support across
>=2 adjacent horizons and >=2 adjacent activation windows (Module B
only; waived only when confined to the 10:00 candle itself). One
isolated significant cell is never promoted. If nothing coherent
survives in either module, the final report states the preregistered
fallback sentence verbatim.
