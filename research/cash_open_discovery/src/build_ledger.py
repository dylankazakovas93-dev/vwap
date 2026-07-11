"""Build the full episode ledger (outer/reclaim state machine + outcomes +
overnight/prior-session context) for one instrument and one anchor minute.
Development partition only (assertion enforced).
"""
import os

import numpy as np
import pandas as pd

from .context import build_context
from .episodes import CHECKPOINTS, build_episode_ledger
from .opening_scale import BAR_TAU_MAX, build_bar_frames, build_opening_tables
from .outcomes import fixed_horizon_returns, structural_outcomes, symmetric_first_passage

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
DEV_END = pd.Timestamp("2022-12-31")


def load_dev(instrument: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    df = df[df["session_date"] <= DEV_END].copy()
    assert df["session_date"].max() <= DEV_END, "partition breach"
    return df


def build_full_ledger(instrument: str, anchor_minute: int = 570) -> pd.DataFrame:
    df = load_dev(instrument)
    O, S = build_opening_tables(df, anchor_minute=anchor_minute)
    bar_frames = build_bar_frames(df, tau_max=BAR_TAU_MAX, anchor_minute=anchor_minute)
    led = build_episode_ledger(bar_frames, S, instrument)
    if led.empty:
        return led
    ctx = build_context(df)

    extra_rows = []
    for row in led.itertuples():
        sd = row.session_date
        bars = bar_frames[sd]
        rec = {}
        if row.outer_direction == "AMBIGUOUS_DIRECTION":
            extra_rows.append(rec)
            continue
        d = 1 if row.outer_direction == "lower" else -1
        M = abs(row.outer_price - row.O)
        Sv = row.S_tau_outer
        tau_outer = row.minutes_to_outer

        for name in ("reclaim_50", "reclaim_full"):
            tau = getattr(row, f"{name}_tau")
            if pd.notna(tau):
                origin_tau = int(tau) + 1
                fh = fixed_horizon_returns(bars, origin_tau, d, anchor_minute)
                fp = symmetric_first_passage(bars, origin_tau, d, M, Sv)
                st = structural_outcomes(bars, origin_tau, d, row.O, row.A, Sv,
                                         row.outer_price, ctx["overnight_high"].get(sd, np.nan),
                                         ctx["overnight_low"].get(sd, np.nan))
                for k, v in fh.items():
                    rec[f"{name}_{k}"] = v
                for k, (outc, tb) in fp.items():
                    rec[f"{name}_{k}_outcome"] = outc
                    rec[f"{name}_{k}_tbars"] = tb
                for k, v in st.items():
                    rec[f"{name}_{k}"] = v

        if row.reclaim_type == "NONE":
            origin_tau = min(len(bars["close"]) - 1, tau_outer + 60) + 1
            fh = fixed_horizon_returns(bars, origin_tau, d, anchor_minute)
            for k, v in fh.items():
                rec[f"held_{k}"] = v

        for H in CHECKPOINTS:
            origin_tau = int(getattr(row, f"cp{H}_origin_tau"))
            fh = fixed_horizon_returns(bars, origin_tau, d, anchor_minute)
            for k, v in fh.items():
                rec[f"cp{H}_{k}"] = v
        extra_rows.append(rec)

    extra = pd.DataFrame(extra_rows, index=led.index)
    led = pd.concat([led, extra], axis=1)

    ctx_cols = [c for c in ctx.columns]
    led = led.join(ctx[ctx_cols], on="session_date")
    led["overnight_continues_outer_dir"] = np.where(
        led["outer_direction"] == "lower", led["globex_open_to_0929_return"] < 0,
        np.where(led["outer_direction"] == "upper", led["globex_open_to_0929_return"] > 0, np.nan))
    led["dist_from_vwap_0929_at_outer"] = np.where(
        led["outer_direction"].isin(["upper", "lower"]),
        led["outer_price"] - led["vwap_0929"], np.nan)
    led["data_partition"] = "development"
    led["anchor_minute"] = anchor_minute
    return led
