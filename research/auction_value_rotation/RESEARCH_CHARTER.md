# RESEARCH_CHARTER.md — auction value reacceptance and rotation engine

Branch: `research/auction-value-rotation-engine`, base commit `201896d`
(Generation 3: cash-open target atlas — engine, descriptive analysis).
Independent generation: no levels, taxonomy, or methodology imported
from any prior generation. Inherits only the audited NQ (primary) and ES
(secondary confirmation, added only after the base NQ mechanism is
evaluated) one-minute OHLCV data infrastructure
(`data/processed/{nq,es}_front_1m.parquet`, re-verified this
generation) and general no-lookahead discipline.

## Research hypothesis

> When price attempts discovery beyond a completed session value-area
> edge, fails to remain outside, and becomes reaccepted inside the prior
> value area, price is more likely to rotate toward POC than comparable
> price states that did not experience the same failed discovery
> process.

Not a generic POC mean-reversion study. The essential question: does the
*history* of attempted discovery and reacceptance add information beyond
merely being inside value and positioned on one side of POC? This is
tested by comparing failed-discovery-plus-reacceptance events against
`MATCHED_INSIDE_STATE` — an ordinary inside-value control matched on
distance-to-POC, profile age, session/clock-time, and value-area width,
with no recent edge breach. If the matched control performs as well as
the treatment, the "failed discovery adds information" hypothesis is
null even if both groups show some POC-ward drift.

No Pine Script, no profit optimization (reward:risk, stop distance,
contract size, net profit, profit factor, Sharpe, prop-account outcomes)
anywhere in this generation. Only a mechanism study that, if it survives
out-of-sample, may license a *separate*, later execution/profitability
generation — never this one.

## Facts (inherited, verified)

- `data/processed/{nq,es}_front_1m.parquet`: re-hashed raw archives and
  re-ran `research/vwap_shock/src/data_build.py` unmodified this
  generation; counters matched root `DATA_CONTRACT.md` exactly.
- The processed parquet files span 2018-01-03 through 2026-06-08/09
  (confirmed by direct inspection before any feature code was written).
  2026 is present in the underlying file and must never be read by any
  stage of this generation's pipeline — enforced by an explicit filter
  applied immediately after load, in every entry point, and tested.
- Session leg definitions are reused, where compatible, from
  `research/ema21_session_horizon/`'s audited convention (Asia
  18:00-02:59 ET, London 03:00-08:29 ET, New York RTH 09:30-15:59 ET).
  The task's own fallback freeze (London 03:00-09:29 ET) differs from
  that prior convention by 30 minutes at the London/NY boundary; per
  "use existing audited repository session definitions where available,"
  the prior generation's audited London window (03:00-08:29 ET) is used
  instead of the task's fallback, since an audited definition already
  exists in this repository (`DECISIONS.md` #1).

## Data partitions (frozen, verified before any result-producing code)

- Development / model-selection years: **2018, 2020, 2022, 2024**.
- Locked non-consecutive OOS years: **2019, 2021, 2023, 2025**.
- Final untouched holdout: **2026** — never read, never reported, in this
  or any future generation started from this one.
- This is a regime-generalization split, not a chronological walk-
  forward test — development years and OOS years are interleaved by
  design and must never be described as sequential train/test halves.

## Assumptions (see `SPEC_AUCTION_VALUE.md` for full formal detail)

- A1: Profile construction is a deterministic approximation of true
  exchange volume-at-price from 1-minute OHLCV; stated as a permanent
  caveat in every output that reports VAH/VAL/POC.
- A2: The primary development grid (breach depth x max-time-outside x
  acceptance definition x POC-distance x freshness) is evaluated once,
  under the primary profile construction (`UNIFORM_RANGE`, 1-tick bins,
  70% value area), by building one master per-excursion "acceptance
  ledger" per `(profile mapping, side)` that records, for every armed
  excursion, the outcome of *all four* acceptance rules independently
  (confirmation bar, bars-outside, breach depth reached, POC distance,
  freshness at confirmation) — the 432-cell grid is then computed as
  post-hoc boolean filters over this one ledger, not as 432 independent
  event-detection passes. This is mathematically equivalent to running
  the full grid natively and is documented here because it changes the
  *implementation* shape, not the *statistical* content, of "test the
  bounded development matrix" (`DECISIONS.md` #4).
- A3: Profile-model/bin-width/value-area-percentage sensitivity
  (`SENSITIVITY 1/2`, 2-tick/4-tick bins, 68%/72% value area) is
  evaluated only for candidate families that already pass the base
  criteria under the primary profile construction (criteria 8-9 in
  `SPEC_AUCTION_VALUE.md` §"Candidate family selection" are themselves
  robustness *confirmations* of a candidate, not part of the grid
  search that produces candidates in the first place).
- A4: Context variables (volume percentiles, ATR ratios, ES confirmation,
  etc.) are computed and reported **only if at least one candidate
  family passes the base mechanism criteria** — per the task's own
  instruction that they are secondary and may only be studied after the
  base ledger is complete and a family has already passed. If no
  candidate qualifies, this generation states the null/inconclusive
  verdict without computing context variables, consistent with "if no
  family qualifies, classify the study as null or inconclusive and do
  not open OOS outcomes" (and, by direct extension, do not run
  secondary-only analyses that exist to further characterize a
  qualifying candidate that does not exist).

## Falsifiers

A candidate family is only promoted to OOS if it satisfies all 12
listed criteria in `SPEC_AUCTION_VALUE.md` §"Candidate family
selection" — no single highest-performing cell, no isolated clock-time/
volume/volatility subgroup, no result explained solely by starting
closer to POC, no single year carrying more than 50% of the pooled
effect. OOS passes only under the 9 listed OOS criteria, evaluated
exactly once, with no redefinition afterward. If nothing qualifies at
either stage, the generation states that plainly and stops — it does
not become a validation study or a new generation.
