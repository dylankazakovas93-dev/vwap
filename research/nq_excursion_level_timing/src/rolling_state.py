"""Causal rolling continuation/reversal-state diagnostic --
SPEC_EXCURSION_TIMING.md sec 20. One frozen secondary experiment. A
causal diagnostic only, not a trading rule.
"""
import numpy as np
import pandas as pd
from scipy import stats as sstats

from . import stats as st

PRIOR_WINDOW = 10
STATE_MAJORITY = 6
MIN_TOTAL_DIRECTIONAL = 50
MIN_PER_STATE = 20
MIN_DIFF = 0.10
MIN_YEARS_SIGN = 4


def _state_for_prior(prior_outcomes):
    n_cont = sum(1 for o in prior_outcomes if o == "CONTINUATION_FIRST")
    n_rev = sum(1 for o in prior_outcomes if o == "REVERSAL_FIRST")
    if n_cont >= STATE_MAJORITY:
        return "CONTINUATION_STATE"
    if n_rev >= STATE_MAJORITY:
        return "REVERSAL_STATE"
    return "MIXED_STATE"


def build_rolling_state_events(barriers_tbl: pd.DataFrame, events_tbl: pd.DataFrame) -> pd.DataFrame:
    """One row per eligible (instrument, level_id, session_date) event:
    touched within 30 min, complete 30-min horizon, b=1.0 not tied/neither."""
    b1_30 = barriers_tbl[(barriers_tbl["b"] == 1.0) & (barriers_tbl["horizon"] == 30)
                         & (barriers_tbl["first_touch_elapsed_bar"] <= 30)
                         & (barriers_tbl["barrier_first_outcome"].isin(["CONTINUATION_FIRST", "REVERSAL_FIRST"]))]
    rows = []
    for (instrument, level_id), g in b1_30.groupby(["instrument", "level_id"]):
        g = g.sort_values("session_date").reset_index(drop=True)
        outcomes = g["barrier_first_outcome"].tolist()
        for i in range(len(g)):
            prior = outcomes[max(0, i - PRIOR_WINDOW):i]
            state = "STATE_UNAVAILABLE" if len(prior) < PRIOR_WINDOW else _state_for_prior(prior)
            rows.append({"instrument": instrument, "level_id": level_id,
                        "session_date": g.loc[i, "session_date"], "calendar_year": g.loc[i, "calendar_year"],
                        "prior_state": state, "current_outcome": outcomes[i],
                        "current_is_continuation": int(outcomes[i] == "CONTINUATION_FIRST")})
    return pd.DataFrame(rows)


def rolling_state_summary(state_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (instrument, level_id), g in state_events.groupby(["instrument", "level_id"]):
        cont_state = g[g["prior_state"] == "CONTINUATION_STATE"]
        rev_state = g[g["prior_state"] == "REVERSAL_STATE"]
        mixed_state = g[g["prior_state"] == "MIXED_STATE"]
        unavailable = g[g["prior_state"] == "STATE_UNAVAILABLE"]

        n_cont_state, n_rev_state = len(cont_state), len(rev_state)
        cont_rate_given_cont = cont_state["current_is_continuation"].mean() if n_cont_state else np.nan
        cont_rate_given_rev = rev_state["current_is_continuation"].mean() if n_rev_state else np.nan
        diff = (cont_rate_given_cont - cont_rate_given_rev) if (n_cont_state and n_rev_state) else np.nan

        row = {
            "instrument": instrument, "level_id": level_id,
            "n_continuation_state": n_cont_state, "n_reversal_state": n_rev_state,
            "n_mixed_state": len(mixed_state), "n_state_unavailable": len(unavailable),
            "continuation_rate_given_continuation_state": cont_rate_given_cont,
            "continuation_rate_given_reversal_state": cont_rate_given_rev,
            "continuation_rate_diff": diff,
        }
        if n_cont_state >= 1 and n_rev_state >= 1:
            a = int(cont_state["current_is_continuation"].sum()); b_ = n_cont_state - a
            c = int(rev_state["current_is_continuation"].sum()); d = n_rev_state - c
            _, p = sstats.fisher_exact([[a, b_], [c, d]])
            row["p_raw"] = p
        else:
            row["p_raw"] = np.nan
        n_directional = n_cont_state + n_rev_state
        row["n_directional_total"] = n_directional
        row["confirmatory_eligible"] = bool(n_directional >= MIN_TOTAL_DIRECTIONAL and n_cont_state >= MIN_PER_STATE and n_rev_state >= MIN_PER_STATE)
        rows.append(row)
    out = pd.DataFrame(rows)
    out = st.bh_within(out, "p_raw", group_cols=("instrument",))
    return out


def rolling_state_year_stability(state_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (instrument, level_id, year), g in state_events.groupby(["instrument", "level_id", "calendar_year"]):
        cont_state = g[g["prior_state"] == "CONTINUATION_STATE"]
        rev_state = g[g["prior_state"] == "REVERSAL_STATE"]
        cr_c = cont_state["current_is_continuation"].mean() if len(cont_state) else np.nan
        cr_r = rev_state["current_is_continuation"].mean() if len(rev_state) else np.nan
        rows.append({"instrument": instrument, "level_id": level_id, "year": year,
                    "n_continuation_state": len(cont_state), "n_reversal_state": len(rev_state),
                    "continuation_rate_given_continuation_state": cr_c,
                    "continuation_rate_given_reversal_state": cr_r,
                    "diff": (cr_c - cr_r) if (len(cont_state) and len(rev_state)) else np.nan})
    return pd.DataFrame(rows)


def classify_rolling_state(summary: pd.DataFrame, year_stability: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        instrument, level_id = row["instrument"], row["level_id"]
        if not row["confirmatory_eligible"]:
            cls = "STATE_UNDERPOWERED"
        else:
            q = row["q_value"]
            diff = row["continuation_rate_diff"]
            sig = np.isfinite(q) and q < st.BH_ALPHA
            yrs = year_stability[(year_stability.instrument == instrument) & (year_stability.level_id == level_id)]
            yr_diffs = yrs["diff"].dropna()
            pooled_sign = np.sign(diff) if np.isfinite(diff) else 0
            n_same_sign = int((np.sign(yr_diffs) == pooled_sign).sum())
            year_ok = n_same_sign >= MIN_YEARS_SIGN
            if sig and diff >= MIN_DIFF and year_ok:
                cls = "STATE_PERSISTENCE_SUPPORTED"
            elif sig and diff <= -MIN_DIFF and year_ok:
                cls = "STATE_REVERSAL_SUPPORTED"
            else:
                cls = "STATE_NULL"
        rows.append({**row.to_dict(), "classification": cls})
    return pd.DataFrame(rows)
