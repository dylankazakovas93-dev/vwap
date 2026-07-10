# KNOWN_LIMITATIONS.md

1. OHLCV only: no aggressor side, delta, depth, queue or options data. No
   feature here measures absorption, order-flow imbalance or book state;
   such language is interpretation only.
2. Volume during roll weeks is split across two liquid contracts; the
   front-month series understates total root volume for ~2-3 sessions per
   quarter, which perturbs minute-of-day volume baselines around rolls.
   Roll sessions carry a flag; not excluded.
3. Macro windows are tagged by fixed clock times, not an actual release
   calendar; misses irregular events (FOMC minutes days vs. statement days,
   surprise announcements) and tags minutes with no release.
4. Minute-of-day baselines treat all session types alike; half-days and the
   sessions following them have distorted baselines (flagged short sessions
   retained).
5. Candidate ledger persists only |z_mod|>=2 bars plus per-session counts
   (Decision #8); the full bar grid is reproducible deterministically from
   raw data + code.
6. Databento 1-minute bars aggregate trades only; bars with no trades are
   absent. Missing minutes are treated as non-tradeable (no fill possible),
   and forward horizons index by bar sequence within session with actual
   timestamps recorded.
7. First-passage barrier touches use bar high/low; intrabar ordering is
   unknown — AMBIG handling is conservative but still an approximation.
8. The 31%-reversal benchmark (Rif & Utz 2021) is for Nasdaq-100 single
   stocks, not index futures; used as context, not as an expected value.
9. Zero-slippage exact-price fills are a simulator property, not a market
   property; all economics here are gross and simulator-conditional.
10. 2020-03 COVID sessions include a halt day and extreme baselines; they
    remain in development data by design (no post-hoc exclusion).
11. VWAP acceptance as defined overlaps the forward label window; the raw
    acceptance-vs-continuation sort (0.57 vs 0.10) is contemporaneous
    leakage, not prediction. Only the post-decision-bar version
    (post_cont_rate) is causal, and it is null. Any future acceptance
    feature must be evaluated strictly post-decision.
12. Extreme 1-minute events are concentrated overnight/European (thin
    liquidity); the cash-open reversal pocket rests on ~1.4-1.8k events over
    five years per instrument — small, regime-sensitive, and untested for
    the 1-tick spread. Not a deployable result as it stands.
13. Stage 3 independent audit has not been run; Stage 2 findings are
    implementation-agent self-reported and must be audited before any
    promotion.
