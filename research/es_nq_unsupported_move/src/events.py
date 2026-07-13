"""EXTREME/MODERATE unsupported-move classification and the frozen
sequential rearming/non-overlap scan.
See SPEC_UNSUPPORTED_MOVE.md sections 5-6.
"""
import numpy as np
import pandas as pd

PRIMARY_HORIZON = 15


def _classify_candidate(row) -> str:
    if row["leader"] is None or pd.isna(row["leader_ret_z"]) or pd.isna(row["laggard_ret_z"]) or pd.isna(row["residual_z"]):
        return None
    lz, gz, rz = abs(row["leader_ret_z"]), abs(row["laggard_ret_z"]), abs(row["residual_z"])
    if lz >= 2.0 and gz <= 0.75 and rz >= 2.0:
        return "EXTREME_UNSUPPORTED_MOVE"
    if 1.0 <= lz < 2.0 and gz <= 0.75 and 1.0 <= rz < 2.0:
        return "MODERATE_UNSUPPORTED_MOVE"
    return None


def scan_events(reg_df: pd.DataFrame, leg_lengths: dict) -> pd.DataFrame:
    events = []
    reg_df = reg_df.sort_values(["session_leg_id", "local_rank"])
    for leg_id, g in reg_df.groupby("session_leg_id", sort=False):
        g = g.reset_index(drop=True)
        leg_end = leg_lengths.get(leg_id, int(g["local_rank"].max()))
        consumed_until = -1
        for _, row in g.iterrows():
            t = int(row["local_rank"])
            if t <= consumed_until:
                continue
            cls = _classify_candidate(row)
            if cls is None:
                continue
            event = row.to_dict()
            event["event_class"] = cls
            event["outcome_end_rank"] = min(t + PRIMARY_HORIZON, leg_end)
            event["horizon_15_available_bars"] = event["outcome_end_rank"] - t
            events.append(event)
            consumed_until = min(t + PRIMARY_HORIZON, leg_end)
    return pd.DataFrame(events)


def count_leader_ties(reg_df: pd.DataFrame) -> int:
    return int(reg_df["leader_tie"].sum())
