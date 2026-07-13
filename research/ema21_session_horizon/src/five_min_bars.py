"""Deterministic 1-minute -> continuous 5-minute bar construction.

Reads the audited, unchanged data/processed/{es,nq}_front_1m.parquet.
See DATA_CONTRACT.md. Only the continuous (full, incl. overnight) frame
is built this generation -- every session leg is a slice of it.
"""
import os

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")

DEV_START = pd.Timestamp("2018-01-03").date()
DEV_END = pd.Timestamp("2022-12-30").date()


def load_1m(root: str) -> pd.DataFrame:
    path = os.path.join(PROC, f"{root.lower()}_front_1m.parquet")
    return pd.read_parquet(path)


def filter_development(df: pd.DataFrame) -> pd.DataFrame:
    """Hard 2023+ guard: only session_date in [2018-01-03, 2022-12-30]."""
    d = pd.to_datetime(df["session_date"]).dt.date
    m = (d >= DEV_START) & (d <= DEV_END)
    return df.loc[m].copy()


def build_full_5m(df1m: pd.DataFrame):
    """Continuous chronological 5-minute bars, all sessions, all minutes."""
    df = df1m.copy()
    df["bucket_start_min"] = (df["et_minute"] // 5) * 5
    g = df.groupby(["session_date", "bucket_start_min"], sort=True)
    counts = g.size()
    complete = counts[counts == 5].index
    out = g.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        ts_event=("ts_event", "first"),
    )
    out = out.loc[out.index.isin(complete)].reset_index()
    out = out.sort_values(["ts_event"]).reset_index(drop=True)
    n_incomplete = int(len(counts) - len(complete))
    return out, n_incomplete
