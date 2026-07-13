"""Five-minute synchronized returns per instrument, per leg instance.
See SPEC_UNSUPPORTED_MOVE.md section 2.
"""
import numpy as np
import pandas as pd


def add_five_min_returns(leg_df: pd.DataFrame) -> pd.DataFrame:
    out = leg_df.sort_values(["session_leg_id", "local_rank"]).copy()
    g = out.groupby("session_leg_id", sort=False)
    close_es_lag5 = g["close_es"].shift(5)
    close_nq_lag5 = g["close_nq"].shift(5)
    out["es_ret"] = out["close_es"] / close_es_lag5 - 1
    out["nq_ret"] = out["close_nq"] / close_nq_lag5 - 1
    return out


def window_endpoints(leg_df_with_ret: pd.DataFrame) -> pd.DataFrame:
    """Rows with a valid (non-null) 5-min return in both instruments -- the
    set of legal event/control window endpoints."""
    return leg_df_with_ret.loc[
        leg_df_with_ret["es_ret"].notna() & leg_df_with_ret["nq_ret"].notna()
    ].reset_index(drop=True)
