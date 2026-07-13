"""Load audited 1-minute bars and enforce the development partition guard."""
import os

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")

DEV_START = pd.Timestamp("2018-01-03").date()
DEV_END = pd.Timestamp("2022-12-30").date()

PRE10_START, PRE10_END = 570, 599     # 09:30-09:59
POST10_START, POST10_END = 600, 659   # 10:00-10:59
RTH_START, RTH_END = 570, 959         # 09:30-15:59


def load_1m(root: str) -> pd.DataFrame:
    path = os.path.join(PROC, f"{root.lower()}_front_1m.parquet")
    return pd.read_parquet(path)


def filter_development(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(df["session_date"]).dt.date
    m = (d >= DEV_START) & (d <= DEV_END)
    return df.loc[m].copy()
