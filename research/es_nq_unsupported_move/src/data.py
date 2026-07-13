"""Load audited 1-minute bars, development partition guard, ES-NQ
synchronization, and session-leg assignment.
See DATA_CONTRACT.md "Synchronization", "Session legs".
"""
import os

import numpy as np
import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")

DEV_START = pd.Timestamp("2018-01-03").date()
DEV_END = pd.Timestamp("2022-12-30").date()

ASIA_EVENING = (18 * 60, 24 * 60 - 1)
ASIA_MORNING = (0, 2 * 60 + 59)
LONDON = (3 * 60, 8 * 60 + 29)
NEW_YORK = (9 * 60 + 30, 15 * 60 + 59)


def load_1m(root: str) -> pd.DataFrame:
    path = os.path.join(PROC, f"{root.lower()}_front_1m.parquet")
    return pd.read_parquet(path)


def filter_development(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(df["session_date"]).dt.date
    m = (d >= DEV_START) & (d <= DEV_END)
    return df.loc[m].copy()


def assign_leg(bucket_min: int) -> str:
    m = bucket_min
    if (ASIA_EVENING[0] <= m <= ASIA_EVENING[1]) or (ASIA_MORNING[0] <= m <= ASIA_MORNING[1]):
        return "ASIA"
    if LONDON[0] <= m <= LONDON[1]:
        return "LONDON"
    if NEW_YORK[0] <= m <= NEW_YORK[1]:
        return "NEW_YORK"
    return "EXCLUDED"


def synchronize(es1m: pd.DataFrame, nq1m: pd.DataFrame):
    """Exact ts_event inner join; no forward fill. Returns (sync_df, coverage_dict)."""
    es = es1m[["ts_event", "session_date", "et_minute", "open", "high", "low", "close", "volume"]].copy()
    nq = nq1m[["ts_event", "session_date", "et_minute", "open", "high", "low", "close", "volume"]].copy()
    merged = es.merge(nq, on="ts_event", suffixes=("_es", "_nq"), how="inner")
    mismatch = int((merged["session_date_es"] != merged["session_date_nq"]).sum())
    mismatch += int((merged["et_minute_es"] != merged["et_minute_nq"]).sum())
    merged["session_date"] = merged["session_date_es"]
    merged["et_minute"] = merged["et_minute_es"]
    merged = merged.drop(columns=["session_date_es", "session_date_nq", "et_minute_es", "et_minute_nq"])
    merged["leg"] = merged["et_minute"].map(assign_leg)
    coverage = {
        "es_raw_bars": int(len(es)), "nq_raw_bars": int(len(nq)),
        "synchronized_bars": int(len(merged)),
        "es_dropped": int(len(es) - len(merged)), "nq_dropped": int(len(nq) - len(merged)),
        "session_or_minute_mismatch_count": mismatch,
    }
    return merged, coverage


def add_leg_instances(sync_df: pd.DataFrame) -> pd.DataFrame:
    out = sync_df.loc[sync_df["leg"] != "EXCLUDED"].copy()
    out = out.sort_values("ts_event").reset_index(drop=True)
    out["session_leg_id"] = out["session_date"].astype(str) + "|" + out["leg"]
    out["local_rank"] = out.groupby("session_leg_id").cumcount() + 1
    return out
