# Stage 1 gate report — PASS

SPEC_LOCKED.md and VALIDATION_PROTOCOL.md were committed before any
development-partition strategy result was computed or viewed. Only Stage 0
audit counters (row counts, session shapes, volume totals) were observed
first; these contain no forward-return information.

Frozen: event definition (k ∈ {1,3}, |z_mod| ∈ {3,4}), feature families 1-10
with exact causal formulas, L ∈ {5,15,60}, ATR30 fixed, VWAP anchors
(Globex 18:00 ET / RTH 09:30 ET) with 30-bar validity and 2.0σ/1.0σ bands,
acceptance A1 (2-of-3) / A2 (3-of-5) with inner-band veto, forward horizons
{1,5,15,30,60}m, ±1 ATR30 symmetric first passage (120m window, conservative
AMBIG), session segments, placebo matching rule, session-block bootstrap
(500, seed 20260710), economic floors (2-tick spread to claim signal; 1-tick
stop rule), and a 150-row registry hard cap for Stages 2-4.

Material ambiguities NOT silently resolved, recorded instead: macro calendar
approximation (DECISIONS #6), roll-week volume baseline distortion
(LIMITATIONS #2), simulator fill semantics unverified (LIMITATIONS #9).
None blocks Stage 2, which contains no P&L.
