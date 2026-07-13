"""Session-leg assignment and per-leg-instance local bar ranking.

See DATA_CONTRACT.md "Session leg assignment" and
SPEC_SESSION_HORIZONS.md sections 3 and 5.
"""
import numpy as np
import pandas as pd

ASIA_EVENING = (18 * 60, 24 * 60 - 1)   # 1080-1439
ASIA_MORNING = (0, 2 * 60 + 59)          # 0-179
LONDON = (3 * 60, 8 * 60 + 29)           # 180-509
NEW_YORK = (9 * 60 + 30, 15 * 60 + 59)   # 570-959


def assign_leg(bucket_start_min: int) -> str:
    m = bucket_start_min
    if (ASIA_EVENING[0] <= m <= ASIA_EVENING[1]) or (ASIA_MORNING[0] <= m <= ASIA_MORNING[1]):
        return "ASIA"
    if LONDON[0] <= m <= LONDON[1]:
        return "LONDON"
    if NEW_YORK[0] <= m <= NEW_YORK[1]:
        return "NEW_YORK"
    return "EXCLUDED"


def touch_time_bucket(local_rank: int) -> str:
    if 1 <= local_rank <= 6:
        return "SESSION_0_TO_30"
    if 7 <= local_rank <= 12:
        return "SESSION_30_TO_60"
    if 13 <= local_rank <= 24:
        return "SESSION_60_TO_120"
    return "SESSION_120_PLUS"


def add_session_columns(bars: pd.DataFrame) -> pd.DataFrame:
    out = bars.copy()
    out["leg"] = out["bucket_start_min"].map(assign_leg)
    out["session_leg_id"] = np.where(
        out["leg"] == "EXCLUDED",
        None,
        out["session_date"].astype(str) + "|" + out["leg"],
    )
    out = out.sort_values("ts_event").reset_index(drop=True)
    out["local_rank"] = np.nan
    non_excl = out["leg"] != "EXCLUDED"
    out.loc[non_excl, "local_rank"] = (
        out.loc[non_excl].groupby("session_leg_id").cumcount() + 1
    )
    out["touch_time_bucket"] = None
    out.loc[non_excl, "touch_time_bucket"] = out.loc[non_excl, "local_rank"].map(
        lambda r: touch_time_bucket(int(r))
    )
    return out
