"""Load audited 1-minute bars, development partition guard, causal
TR/ATR20 on the continuous front-month recursion.
"""
import os

import numpy as np
import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")

DEV_START = pd.Timestamp("2018-01-03").date()
DEV_END = pd.Timestamp("2022-12-30").date()

RTH_START, RTH_END = 570, 959   # 09:30-15:59 (390 bars)
TICK = 0.25


def load_1m(root: str) -> pd.DataFrame:
    path = os.path.join(PROC, f"{root.lower()}_front_1m.parquet")
    return pd.read_parquet(path)


def filter_development(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.to_datetime(df["session_date"]).dt.date
    m = (d >= DEV_START) & (d <= DEV_END)
    return df.loc[m].copy()


def is_overnight_minute(et_minute: int) -> bool:
    """18:00-09:29 ET: et_minute in [1080,1439] (prev cal day) union [0,569] (session_date's own day)."""
    return et_minute >= 1080 or et_minute <= 569


def add_causal_atr(df1m: pd.DataFrame) -> pd.DataFrame:
    """TR/ATR20 on the continuous chronological 1-minute front-month series."""
    out = df1m.sort_values("ts_event").reset_index(drop=True)
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr = tr.where(prev_close.notna(), np.nan)
    atr20_asof = tr.rolling(20).mean()
    out["tr"] = tr
    out["atr20_event"] = atr20_asof.shift(1)  # ATR20_T = mean TR over T-20..T-1
    return out


def tick_round(x):
    return np.round(np.asarray(x) / TICK) * TICK


def tick_eq(a, b):
    return np.isclose(tick_round(a), tick_round(b), atol=1e-9)
