# Data contract

The engine reads only the supplied NQ 2018/2020/2021 archives and ES 2018 and
2020–2023 archive, hard-filtered to 2022-12-31 before event construction. The
2023+ rows are not admitted to the development dataset and no validation file
is opened. Raw archives are external and never committed.

The Databento parent-symbol data is filtered to outright quarterly contracts,
duplicate `(timestamp, symbol)` rows are removed, 17:00–17:59 ET maintenance
bars are excluded, and the repository's audited causal front-month rule is
used: the prior session's volume leader. Timestamps are bar-open timestamps in
America/New_York.

Session boundaries are the audited windows: Asia 18:00–02:59 ET, London
03:00–08:29 ET, and New York 09:30–15:59 ET. Asia 18:00–23:59 rows map to the
following session date; 00:00–02:59 rows map to the current date. Excluded
intervals are not used.
