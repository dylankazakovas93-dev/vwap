"""Deterministic 1-minute -> 5-minute bar construction, RTH and full-session.

Reads the audited, unchanged data/processed/{es,nq}_front_1m.parquet built
by research/vwap_shock/src/data_build.py. See DATA_CONTRACT.md.
"""
import os

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")

DEV_START = pd.Timestamp("2018-01-03").date()
DEV_END = pd.Timestamp("2022-12-30").date()

RTH_START_MIN = 9 * 60 + 30   # 570
RTH_END_MIN = 15 * 60 + 59    # 959 (last eligible bar-open minute, bar covers 15:55-16:00)


def load_1m(root: str) -> pd.DataFrame:
    path = os.path.join(PROC, f"{root.lower()}_front_1m.parquet")
    return pd.read_parquet(path)


def filter_development(df: pd.DataFrame) -> pd.DataFrame:
    """Hard 2023+ guard: only session_date in [2018-01-03, 2022-12-30]."""
    d = pd.to_datetime(df["session_date"]).dt.date
    m = (d >= DEV_START) & (d <= DEV_END)
    return df.loc[m].copy()


def _aggregate_5m(df: pd.DataFrame, bucket_col: str) -> pd.DataFrame:
    g = df.groupby(["session_date", bucket_col], sort=True)
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
    out = out.rename(columns={bucket_col: "bucket_start_min"})
    out = out.sort_values(["ts_event"]).reset_index(drop=True)
    return out, int(len(counts) - len(complete))


def build_rth_5m(df1m: pd.DataFrame):
    """RTH-only 5-minute bars, 09:30-15:59 bar-open window (12 bars/hour)."""
    m = (df1m["et_minute"] >= RTH_START_MIN) & (df1m["et_minute"] <= RTH_END_MIN)
    rth = df1m.loc[m].copy()
    rth["bucket_start_min"] = (rth["et_minute"] // 5) * 5
    bars, n_incomplete = _aggregate_5m(rth, "bucket_start_min")
    bars["is_rth"] = True
    return bars, n_incomplete


def build_full_5m(df1m: pd.DataFrame):
    """Continuous chronological 5-minute bars, all sessions, all minutes."""
    df = df1m.copy()
    df["bucket_start_min"] = (df["et_minute"] // 5) * 5
    bars, n_incomplete = _aggregate_5m(df, "bucket_start_min")
    bars["is_rth"] = (bars["bucket_start_min"] >= RTH_START_MIN) & (
        bars["bucket_start_min"] <= RTH_END_MIN
    )
    return bars, n_incomplete
