# Decisions

1. Base is the full commit `201896db5eafd0aec56e8b1eaeb47eabbe42b9f8`; the implementation branch is `research/efficient-displacement-continuation`.
2. The source files are external user uploads; no data is copied into Git.
3. `es2023.zip` is used only because its manifest spans 2020-2023; the loader applies the hard 2022-12-31 cutoff before event construction.
4. Databento timestamps are treated as bar-open times. A 3-minute event ending at bar T uses exactly T-2,T-1,T; post-event outcomes start at T+1.
5. Midnight Asia session dates are mapped to a single futures session date by ET date: 18:00-23:59 belongs to the next calendar date, 00:00-02:59 to the current calendar date.
