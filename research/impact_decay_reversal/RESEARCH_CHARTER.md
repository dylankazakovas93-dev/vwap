# Frozen research charter: impact-decay reversal

Branch: `research/impact-decay-reversal`; base: `201896db5eafd0aec56e8b1eaeb47eabbe42b9f8`.

This study tests whether high diagnostic-phase volume adds information beyond
the same observed price stall after an extreme three-minute impulse. The
primary comparison is `HIGH_VOLUME_DECAY` versus `LOW_VOLUME_DECAY_CONTROL`.
It is a causal, descriptive development study only: no entries, exits, costs,
position sizing, profitability, or validation analysis.

The development partition is 2018-01-01 through 2022-12-31. ES and NQ are
separate. Asia, London, New York, and upward/downward impulses are separate.
All thresholds, matching strata, barrier definitions, horizons, and the
permutation/BH procedure are frozen in `SPEC_IMPACT_DECAY_REVERSAL.md`.
