"""Level construction -- SPEC_EXCURSION_TIMING.md secs 4-5. Self-
contained, arithmetic-mean-only, 10-session causal lookback, no median
or EMA, no synthetic controls, no other level family.
"""
import os

import numpy as np
import pandas as pd

OPEN_MINUTE = 570  # 09:30 ET
LOOKBACK_N = 10
K_RUNGS = (0, 1, 2, 3)

DEV_START = pd.Timestamp("2018-01-01")
DEV_END = pd.Timestamp("2022-12-31")


def load_dev(instrument: str, proc_dir: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(proc_dir, f"{instrument.lower()}_front_1m.parquet"))
    df = df[(df["session_date"] >= DEV_START) & (df["session_date"] <= DEV_END)].copy()
    assert df["session_date"].min() >= DEV_START and df["session_date"].max() <= DEV_END, "partition breach"
    return df


def build_levels(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a DataFrame indexed by session_date with O_0930, U_0930,
    D_0930, mean_U_10, mean_D_10, sd_U_10, sd_D_10, and the 8 level_ids
    (UPPER_k0..k3, LOWER_k0..k3), using EXACTLY the previous 10 valid
    sessions (no expanding/partial-window fallback)."""
    sub = df[df["et_minute"] == OPEN_MINUTE][["session_date", "open", "high", "low"]].copy()
    sub = sub.drop_duplicates("session_date").sort_values("session_date").reset_index(drop=True)
    sub["U"] = sub["high"] - sub["open"]
    sub["D"] = sub["open"] - sub["low"]
    sub = sub.set_index("session_date")

    out = pd.DataFrame(index=sub.index)
    out["O_0930"] = sub["open"]
    out["U_0930"] = sub["U"]
    out["D_0930"] = sub["D"]

    roll_u = sub["U"].rolling(LOOKBACK_N, min_periods=LOOKBACK_N)
    roll_d = sub["D"].rolling(LOOKBACK_N, min_periods=LOOKBACK_N)
    out["mean_U_10"] = roll_u.mean().shift(1)
    out["mean_D_10"] = roll_d.mean().shift(1)
    out["sd_U_10"] = roll_u.std(ddof=1).shift(1)
    out["sd_D_10"] = roll_d.std(ddof=1).shift(1)

    O = out["O_0930"]
    for k in K_RUNGS:
        out[f"UPPER_k{k}"] = O + out["mean_U_10"] + k * out["sd_U_10"]
        out[f"LOWER_k{k}"] = O - out["mean_D_10"] - k * out["sd_D_10"]
    return out


def level_ids():
    return [f"UPPER_k{k}" for k in K_RUNGS] + [f"LOWER_k{k}" for k in K_RUNGS]


LEVEL_META = {}
for k in K_RUNGS:
    LEVEL_META[f"UPPER_k{k}"] = ("upper", k)
    LEVEL_META[f"LOWER_k{k}"] = ("lower", k)

assert len(level_ids()) == 8
