# VARIABLE_CATALOG.md

## Episode-level (one row per instrument x session x A, if an episode exists)

| Variable | Definition |
|---|---|
| instrument, contract, session_date | identity |
| open_0930 | O, the 09:30 ET bar's open |
| outer_direction | upper / lower / AMBIGUOUS_DIRECTION |
| A | outer magnitude multiple tested |
| outer_threshold_price | O +- A*S(tau_outer) |
| outer_price | the qualifying bar's high (upper) or low (lower) |
| outer_time, minutes_to_outer (tau_outer) | first qualifying bar |
| S_tau_outer | opening-scale value used (points) |
| atr_scale, realized_vol_scale | secondary robustness scales (Sec. 3) |
| reclaim_50_time, minutes_to_reclaim_50 | first bar closing beyond B=0.5A |
| reclaim_full_time, minutes_to_reclaim_full | first bar closing beyond B=0 |
| reclaim_type | NONE / HALF / FULL (best achieved within 60-min window) |
| max_excursion_before_reclaim | most extreme H/L reached before the first reclaim (or within window if none) |
| decision_time, legal_outcome_start_time | per Sec. 5 |
| direction (reclaim convention) | +1 (long, lower excursion) / -1 (short, upper excursion) |
| data_partition, config_hash, code_sha | provenance |

## Overnight positioning / path proxies (all available by 09:29 ET)

globex_open_to_0929_return, prior_close_to_0929_gap, overnight_high,
overnight_low, overnight_range, position_in_overnight_range,
dist_from_overnight_high, dist_from_overnight_low, overnight_path_efficiency,
overnight_pct_bars_up, final10min_return, final30min_return,
final60min_return, final10min_path_efficiency, outer_continues_overnight_dir
(bool), overnight_break_and_return (bool), vwap_0929, dist_from_vwap_0929_at_open,
dist_from_vwap_0929_at_outer.

## Prior-session direction module (separate descriptive variables)

final10min_priorclose_return, final10min_priorclose_netdisp,
final10min_priorclose_path_eff, final10min_priorclose_dirbars,
final10min_priorclose_runlen, final10min_priorclose_closeloc,
final10min_priorclose_volpctile; and the mirrored set for the final 10
completed minutes before the Globex maintenance boundary
(final10min_sessionend_*). Targets: which side reached first; whether
held/reclaimed; incremental value beyond overnight variables.

## Outcome variables

See SPEC_DISCOVERY.md Sec. 7: fixed-horizon returns (1/3/5/10/15/30[/60]
min, points + scale units, direction-aligned), symmetric first-passage
(f in {0.25,0.50,1.0}, outcome in {CONT,REV,AMBIG,NONE}), structural
outcomes (opposite-threshold time, re-break time, overnight-range-return
time, overnight H/L break-reclaim, VWAP_0929 cross time).
