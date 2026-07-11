# RESEARCH_CHARTER.md — Cash-Open Failed-Auction Discovery

Research generation: 2 (new branch, does not extend/reinterpret generation 1)
Branch: `research/cash-open-failed-auction-discovery`
Base commit: `1d39d8e` (tip of `claude/reversal-continuation-research-p6hsdi`
at branch time)

## Provenance and honesty about prior evidence

Generation 1 (`research/vwap_shock`) found, among preregistered tests of a
different hypothesis (extreme-displacement continuation vs reversal), an
**exploratory, non-preregistered** observation: the 09:30-09:59 ET segment
showed a reversal-leaning continuation rate and negative 30-minute forward
return in both ES and NQ, on a small event count (~1.4-1.8k events over
5 years per instrument). That observation was NOT preregistered in
generation 1 and must not be treated as confirmed evidence. This generation
exists solely to test a precisely specified, independently preregistered
version of that idea as a **fresh hypothesis**, on the same development
partition, with its own trial budget and its own null results counted
honestly.

## Source classification

Original / paper-inspired market-structure hypothesis (informally related to
"failed auction" / opening-range-failure concepts referenced in
practitioner literature; no specific academic paper is being replicated).
Not a literal replication of anything. Not a continuation of generation 1's
preregistration.

## Primary objective (single, exact)

Determine whether the **first statistically abnormal excursion from the
09:30 ET cash open**, having failed to hold and having reclaimed a
predefined inner level, is followed by directional movement in the reclaim
direction beyond what an equally large **non-reclaimed** excursion shows.

This is a **phenomenon-discovery study only**. No tradable strategy, no
TP/SL, no MAE/MFE, no profitability metric, no validation/holdout access.

## What would make this worth pursuing further

A causal reclaim event that (a) is directionally informative beyond
matched held excursions of the same magnitude, (b) is reasonably stable
across ES and NQ, across years, and is not driven by a handful of sessions,
and (c) does not depend on cherry-picked timing windows.

## What would falsify it

- Reclaimed and held excursions of the same magnitude show statistically
  indistinguishable forward outcomes.
- The apparent effect is concentrated in one year or a handful of sessions.
- The effect requires an unprincipled combination of A/B/deadline choices
  not part of the preregistered domain.
- Faster/slower reclaim, full/partial reclaim, and excursion speed show no
  coherent (monotone or stable) pattern.
