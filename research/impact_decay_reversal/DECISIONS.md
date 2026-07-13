# Decisions

1. Front-month construction follows the audited repository implementation and
   is causal: prior-session volume leader.
2. Exact three-minute slots are non-overlapping windows ending on ET minute
   values divisible by three minus one; diagnostic clock slots are the ending
   minute of the second diagnostic bar.
3. A 30-minute overlap lock is used for all events, including controls, because
   the longest registered outcome horizon is 30 minutes.
4. Same-bar barrier ambiguity is never ordered from OHLC data.
