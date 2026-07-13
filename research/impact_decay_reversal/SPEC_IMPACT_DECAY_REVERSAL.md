# Frozen specification

For each instrument/session/exact three-minute clock slot, the impulse
absolute displacement percentile uses only the previous 60 valid sessions and
requires all 60. The diagnostic two-bar volume percentile uses the same causal
previous-60-session rule at the exact diagnostic clock slot. Current event and
current session are excluded from both histories.

An impulse is three consecutive one-minute bars with nonzero signed open-to-
close displacement, positive path/range, and causal absolute displacement
percentile >= 0.90. Direction is the sign of the impulse displacement. The
diagnostic phase is exactly the next two complete one-minute bars. Progress is
`s * (diagnostic_close - impulse_close)`, with `progress_ratio = P/I`;
`max_progress_ratio` is the maximum directional high excursion over those two
bars divided by I; `diagnostic_reversal_ratio` is the maximum opposite low
excursion divided by I. Diagnostic volume is the sum of the two bar volumes.

`HIGH_VOLUME_DECAY` requires progress ratio [-0.10, 0.25], max progress ratio
<= 0.40, diagnostic reversal ratio <= 0.25, and volume percentile >= 0.80.
`LOW_VOLUME_DECAY_CONTROL` has identical price conditions and volume percentile
<= 0.50. `HIGH_VOLUME_PROGRESS_CONTROL` requires volume percentile >= 0.80 and
progress ratio > 0.25. Other events are retained as `OTHER` and excluded from
the primary comparison.

One event is recorded per armed excursion. After recording an impulse, later
candidate impulses whose impulse, two-bar diagnostic, or 30-minute outcome
window overlaps the recorded event are suppressed. The armed state resets at
session boundaries. Treatment and controls use identical chronology.

Outcomes begin at D+1 after the diagnostic close. The anchor is diagnostic
close and barriers are +/- 0.50I in impulse-direction coordinates. Horizons
are 5, 10, 15, and 30 complete one-minute bars. Same-bar dual touches are
`SAME_BAR_AMBIGUOUS`; incomplete horizons are retained but excluded from the
binary denominator. The primary is reversal-first rate among non-tied resolved
15-minute outcomes.

Primary matching strata are instrument, session, direction, event clock-time
stratum, impulse percentile band (P90–P95/P95–P99/P99+), progress-ratio band
([-0.10,0.00), [0.00,0.10), [0.10,0.20), [0.20,0.25]), and max-progress band
([0.00,0.10), [0.10,0.20), [0.20,0.30), [0.30,0.40]). Labels are shuffled
within strata using seed 20260713 and 10,000 permutations. BH at 5% is applied
across the 12 instrument×session×direction primary cells only.
