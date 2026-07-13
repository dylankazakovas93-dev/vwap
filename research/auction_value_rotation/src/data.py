"""Load audited 1-minute bars, hard partition guard, session-leg
assignment, causal ATR. See DATA_CONTRACT.md.
"""
import json
import os

import numpy as np
import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(os.path.dirname(__file__), "..", "outputs")

DEV_YEARS = (2018, 2020, 2022, 2024)
OOS_YEARS = (2019, 2021, 2023, 2025)
HOLDOUT_YEARS = (2026,)
TICK = 0.25

ASIA_EVENING = (18 * 60, 24 * 60 - 1)
ASIA_MORNING = (0, 2 * 60 + 59)
LONDON = (3 * 60, 8 * 60 + 29)
NEW_YORK = (9 * 60 + 30, 15 * 60 + 59)


def load_1m(root: str) -> pd.DataFrame:
    path = os.path.join(PROC, f"{root.lower()}_front_1m.parquet")
    return pd.read_parquet(path)


def filter_partition(df: pd.DataFrame, years) -> pd.DataFrame:
    """The single choke point for the 2026-holdout guard. `years` must be
    an explicit literal tuple (DEV_YEARS or OOS_YEARS), never a range."""
    if any(y in HOLDOUT_YEARS for y in years):
        raise ValueError("HOLDOUT_YEARS (2026) may never be requested by this generation's pipeline.")
    y = pd.to_datetime(df["session_date"]).dt.year
    return df.loc[y.isin(years)].copy()


def log_timestamp_boundary(stage: str, df: pd.DataFrame, ts_col: str = "ts_event"):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "timestamp_boundaries.json")
    record = {}
    if os.path.exists(path):
        with open(path) as fh:
            record = json.load(fh)
    if len(df):
        record[stage] = {
            "min_ts": str(pd.Timestamp(df[ts_col].min())),
            "max_ts": str(pd.Timestamp(df[ts_col].max())),
            "n_rows": int(len(df)),
        }
    with open(path, "w") as fh:
        json.dump(record, fh, indent=2, default=str)


def assign_leg(bucket_min: int) -> str:
    m = bucket_min
    if (ASIA_EVENING[0] <= m <= ASIA_EVENING[1]) or (ASIA_MORNING[0] <= m <= ASIA_MORNING[1]):
        return "ASIA"
    if LONDON[0] <= m <= LONDON[1]:
        return "LONDON"
    if NEW_YORK[0] <= m <= NEW_YORK[1]:
        return "NEW_YORK_RTH"
    return "EXCLUDED"


LEG_EXPECTED_BARS = {"ASIA": 540, "LONDON": 330, "NEW_YORK_RTH": 390}


def add_causal_atr(df1m: pd.DataFrame) -> pd.DataFrame:
    out = df1m.sort_values("ts_event").reset_index(drop=True)
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [out["high"] - out["low"], (out["high"] - prev_close).abs(), (out["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    tr = tr.where(prev_close.notna(), np.nan)
    out["tr"] = tr
    out["atr20_event"] = tr.rolling(20).mean().shift(1)
    return out


def add_leg_instances(df1m: pd.DataFrame) -> pd.DataFrame:
    out = df1m.copy()
    out["leg"] = out["et_minute"].map(assign_leg)
    out = out.sort_values("ts_event").reset_index(drop=True)
    non_excl = out["leg"] != "EXCLUDED"
    out["session_leg_id"] = None
    out.loc[non_excl, "session_leg_id"] = (
        out.loc[non_excl, "session_date"].astype(str) + "|" + out.loc[non_excl, "leg"]
    )
    out["local_rank"] = np.nan
    out.loc[non_excl, "local_rank"] = out.loc[non_excl].groupby("session_leg_id").cumcount() + 1
    counts = out.loc[non_excl].groupby("session_leg_id")["local_rank"].transform("max")
    out.loc[non_excl, "leg_bar_count"] = counts
    out["leg_complete"] = False
    for leg_name, expected in LEG_EXPECTED_BARS.items():
        m = (out["leg"] == leg_name) & (out["leg_bar_count"] == expected)
        out.loc[m, "leg_complete"] = True
    return out
