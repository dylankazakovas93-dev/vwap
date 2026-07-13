"""Causal clock-minute volume percentile (trailing 60 valid sessions).
See SPEC_SWEEP_FAILURE.md section 11.
"""
import numpy as np
import pandas as pd

REQUIRED_PRIOR = 60


def build_volume_percentile_table(level_records: list) -> dict:
    """Returns {(session_date, et_minute): percentile_or_nan}."""
    valid_recs = [r for r in level_records if r["rth_valid"]]
    by_minute = {}
    for rec in valid_recs:
        rth = rec["_rth_bars"]
        for _, row in rth.iterrows():
            by_minute.setdefault(int(row["et_minute"]), []).append(
                (rec["session_date"], float(row["volume"]))
            )

    out = {}
    for et_minute, series in by_minute.items():
        vols = np.array([v for _, v in series])
        for i, (session_date, vol) in enumerate(series):
            if i < REQUIRED_PRIOR:
                out[(session_date, et_minute)] = np.nan
                continue
            window = vols[i - REQUIRED_PRIOR : i]
            pct = float((window <= vol).sum()) / REQUIRED_PRIOR
            out[(session_date, et_minute)] = pct
    return out


def volume_stratum(pct: float) -> str:
    if np.isnan(pct):
        return None
    if pct >= 0.80:
        return "HIGH_VOLUME"
    if pct < 0.20:
        return "LOW_VOLUME"
    return "NORMAL_VOLUME"
