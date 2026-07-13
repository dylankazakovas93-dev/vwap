# Known limitations

- OHLCV cannot determine intrabar order; dual barrier touches are ambiguous.
- Sparse low-volume controls may leave cells underpowered; they are retained,
  not replaced.
- This observational development study cannot establish economic causation or
  execution feasibility.
- No validation partition is used.
- The ES input archive is a 2020–2023 bundle; the cutoff-safe reader stops at
  the development cutoff and no post-2022 rows enter the data frame or outputs.
