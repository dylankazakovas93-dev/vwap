# KNOWN_LIMITATIONS.md — generation 2

1. No aggressor side, depth, queue, or options data — same OHLCV-only
   constraint as generation 1; "overnight positioning" is a price-path
   proxy, never actual inventory.
2. No verified macro/news calendar available; ordinary-day vs. news-day
   split is not performed this generation (Decision #8).
3. Detection granularity is one completed bar; "reaches or closes beyond" a
   level is only knowable as of a bar's close, so outer-excursion and
   reclaim timing are accurate to +-1 minute and intrabar order is never
   inferred (consistent with generation 1's discipline).
4. Opening episodes are rare relative to generation 1's shock events
   (at most one per instrument/session/A); several A=2.0 or B=0 (full
   reclaim) cells may fall below the 100-event minimum and will be reported
   as inadequate rather than interpreted.
5. The held-vs-reclaimed matched comparison assigns a hypothetical
   direction to held episodes (Decision #7); this is a discovery-stage
   convention for a fair comparison, not a claim about held-episode
   behavior in isolation.
6. Opening-scale S(tau) requires 20 prior RTH sessions with a valid
   same-tau observation; the first ~20-60 development sessions contribute
   no episodes (logged, not imputed).
7. The 13:00 ET placebo anchor is one control; it does not rule out that
   some other non-cash-open anchor could show a similar artifact, only
   that this specific anchor does or doesn't.
8. Roll-week sessions are not excluded from the opening-episode search
   (consistent with generation 1's non-exclusion policy); flagged via the
   inherited `roll` column, not removed.
