# Frozen research charter: efficient intraday displacement

This branch implements a preregistered, descriptive discovery study on audited Databento ES and NQ one-minute OHLCV. The development partition is 2018-01-01 through 2022-12-31 only. The study tests whether unusually large, path-efficient three-minute directional impulses continue more often than equally large, path-inefficient impulses. It is not a trading strategy and contains no entries, exits, sizing, costs, or profitability simulation.

The primary comparison is efficient displacement versus inefficient displacement within instrument, session, direction, event-end-hour, and causal move-size band. The primary outcome is first passage of the 0.50 x impulse-size continuation or reversal barrier during the complete 15-minute post-impulse window. ES-NQ confirmation is secondary.

All thresholds, horizons, session windows, matching strata, permutation seed, and multiple-testing families are frozen in `SPEC_EFFICIENT_DISPLACEMENT.md`.
