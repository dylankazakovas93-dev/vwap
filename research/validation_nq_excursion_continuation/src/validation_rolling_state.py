"""Rolling direction-state replication -- SPEC_VALIDATION.md sec 11.
Reuses generation 10's frozen build_rolling_state_events unmodified
(same prior-10-event, >=6/10-majority state logic); prior state may draw
on pre-2023 touches (DECISIONS.md #9), current event restricted to the
validation partition. No new lookback or threshold introduced.
"""
import numpy as np
import pandas as pd
from scipy import stats as sstats

from research.nq_excursion_level_timing.src import rolling_state as rs10

VALIDATION_START = pd.Timestamp("2023-01-01")
MIN_PER_STATE = 20
MIN_DIFF = 0.10
MIN_YEARS_SIGN = 3
VALIDATION_YEARS = (2023, 2024, 2025, 2026)


def build_validation_state_events(full_barriers_tbl: pd.DataFrame) -> pd.DataFrame:
    """full_barriers_tbl: b=1.0/H=30 barrier stream over the FULL history
    (2018+), one row per (instrument, level_id, session_date). Prior
    state uses generation 10's unmodified frozen logic over full history;
    returned rows are filtered to current-event session_date >= 2023."""
    state_events = rs10.build_rolling_state_events(full_barriers_tbl, pd.DataFrame())
    return state_events[state_events["session_date"] >= VALIDATION_START].copy()


def summarize(state_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (instrument, level_id), g in state_events.groupby(["instrument", "level_id"]):
        cont_state = g[g["prior_state"] == "CONTINUATION_STATE"]
        rev_state = g[g["prior_state"] == "REVERSAL_STATE"]
        n_cont_state, n_rev_state = len(cont_state), len(rev_state)
        cr_c = cont_state["current_is_continuation"].mean() if n_cont_state else np.nan
        cr_r = rev_state["current_is_continuation"].mean() if n_rev_state else np.nan
        diff = (cr_c - cr_r) if (n_cont_state and n_rev_state) else np.nan

        if n_cont_state >= 1 and n_rev_state >= 1:
            a = int(cont_state["current_is_continuation"].sum()); bb = n_cont_state - a
            c = int(rev_state["current_is_continuation"].sum()); d = n_rev_state - c
            _, p = sstats.fisher_exact([[a, bb], [c, d]])
        else:
            p = np.nan

        year_rows = []
        for year in VALIDATION_YEARS:
            gy = g[g["calendar_year"] == year]
            cs = gy[gy["prior_state"] == "CONTINUATION_STATE"]
            rs_ = gy[gy["prior_state"] == "REVERSAL_STATE"]
            crc = cs["current_is_continuation"].mean() if len(cs) else np.nan
            crr = rs_["current_is_continuation"].mean() if len(rs_) else np.nan
            year_rows.append({"year": year, "partial": year == 2026, "n_continuation_state": len(cs),
                             "n_reversal_state": len(rs_),
                             "continuation_rate_given_continuation_state": crc,
                             "continuation_rate_given_reversal_state": crr,
                             "diff": (crc - crr) if (len(cs) and len(rs_)) else np.nan})
        year_df = pd.DataFrame(year_rows)
        yr_diffs = year_df["diff"].dropna()
        pooled_sign = np.sign(diff) if np.isfinite(diff) else 0
        n_same_sign = int((np.sign(yr_diffs) == pooled_sign).sum())

        eligible = n_cont_state >= MIN_PER_STATE and n_rev_state >= MIN_PER_STATE
        if not eligible:
            cls = "STATE_UNDERPOWERED"
        else:
            sig = np.isfinite(p) and p < 0.05
            year_ok = n_same_sign >= MIN_YEARS_SIGN
            if sig and np.isfinite(diff) and diff >= MIN_DIFF and year_ok:
                cls = "STATE_PERSISTENCE_SUPPORTED"
            elif sig and np.isfinite(diff) and diff <= -MIN_DIFF and year_ok:
                cls = "STATE_REVERSAL_SUPPORTED"
            else:
                cls = "STATE_NULL"

        rows.append({"instrument": instrument, "level_id": level_id,
                    "n_continuation_state": n_cont_state, "n_reversal_state": n_rev_state,
                    "n_mixed_state": int((g["prior_state"] == "MIXED_STATE").sum()),
                    "n_state_unavailable": int((g["prior_state"] == "STATE_UNAVAILABLE").sum()),
                    "continuation_rate_given_continuation_state": cr_c,
                    "continuation_rate_given_reversal_state": cr_r,
                    "continuation_rate_diff": diff, "p_raw": p, "n_years_with_pooled_sign": n_same_sign,
                    "classification": cls, "year_table": year_df})
    return pd.DataFrame(rows)
