# Known limitations

- OHLCV cannot determine intrabar order; dual barrier touches are ambiguous.
- Sparse low-volume controls may leave cells underpowered; they are retained,
  not replaced.
- This observational development study cannot establish economic causation or
  execution feasibility.
- No validation partition is used.
