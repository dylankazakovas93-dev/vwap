# Data contract

Input is supplied outside Git as the named zip archives under the user's quant-data-upload directory. The engine reads only the 2018, 2020, and 2021 NQ archives and the 2018 and 2020-2022 ES archive (`es2023.zip` contains 2020-2023 data and is allowed only after filtering through 2022). The 2023, 2025, and 2026 files are never opened.

Each archive contains a Databento `ohlcv-1m` CSV compressed with zstandard. The loader identifies the CSV member, parses its timestamp and OHLCV columns, and converts timestamps to America/New_York. Source timestamps are bar-open timestamps. Duplicate timestamps, nonpositive ranges, malformed rows, and rows outside 2018-01-01 through 2022-12-31 are rejected or logged. No raw market data is committed.

Session labels are assigned in Eastern Time: Asia 18:00-02:59 mapped to the following session date for times before midnight and the preceding overnight date for times after midnight; London 03:00-08:29; New York 09:30-15:59. The excluded intervals are 08:30-09:29 and 16:00-17:59. Impulses, outcomes, and barriers cannot cross a session boundary.
