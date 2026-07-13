# Frozen specification

For each instrument, session, and exact three-minute clock slot, calculate causal empirical percentiles from the previous 60 valid sessions only, requiring all 60 observations. The distributions are absolute net displacement, three-minute high-low range, and volume. Warm-up observations are retained in the normalization ledger but cannot create eligible events.

For consecutive bars t-2,t-1,t, use Open[t-2], Close[t], signed net move, absolute move, path length as the sum of the first candle body and two close-to-close moves, efficiency = absolute move/path length, directional close location relative to the three-bar range, and mean adjacent candle overlap. Zero net moves, zero path length, and zero range/union are invalid.

An eligible event has absolute-move percentile >= .90. Efficient requires efficiency >= .80, close location >= .80, and mean overlap <= .35. Inefficient requires efficiency <= .50 and mean overlap >= .50. Other eligible events are INTERMEDIATE and remain in ledgers. Scan chronologically per instrument/session; after recording an eligible event, suppress candidate windows beginning before the event's 30-minute outcome window ends.

Outcomes begin at T+1 and require complete same-session horizons 5, 10, 15, and 30 minutes. Excursions and signed closes are mirrored by direction and normalized by absolute move. Symmetric barriers are .25, .50, and 1.00 times absolute move. If both barriers first occur in one one-minute bar, record a tie; do not infer intrabar ordering.

The primary comparison is the .50 barrier at 15 minutes, stratified by instrument x session x direction x event-end-hour x move-size band (P90-P95, P95-P99, P99+). Report a control-count-weighted aggregate and a within-stratum 10,000-permutation two-sided test with seed 20260713. Apply BH at 5% across the 12 instrument/session/direction primary cells. Secondary families are labelled separately.

ES-NQ confirmation is exact-timestamp, same-window, same-direction with paired percentile >= .70; unconfirmed is paired percentile < .50 or opposite direction; the remainder is partial. It is never a primary eligibility filter.
