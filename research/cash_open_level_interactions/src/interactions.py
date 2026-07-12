"""Cash-open level interaction engine -- SPEC_LEVEL_INTERACTIONS.md.

Implements Dylan's final frozen methodology exactly. No touches beyond
09:30-09:59 ET; no outcome bar beyond 10:14 ET; touch bar H/L/C never
enter any post-touch outcome. Level construction itself is NOT
reimplemented here -- generation 7's `levels.py`/`build_levels.py` are
imported by exact file path and reused unmodified.
"""
import itertools
import os

import numpy as np
import pandas as pd

TOUCH_START = 570          # 09:30 ET
TOUCH_END = 599             # 09:59 ET (inclusive)
TAU_MAX = 44                 # 10:14 ET (599 - 570 + 15 = 44)
HORIZONS = (1, 3, 5, 10, 15)
MAX_HORIZON = 15

BUCKETS = [
    ("B1", 570, 574), ("B2", 575, 579), ("B3", 580, 584),
    ("B4", 585, 589), ("B5", 590, 594), ("B6", 595, 599),
]

TAU_B = 0.15                 # orientation ambiguity band
CLUSTER_FRAC = 0.10
LABEL_THRESHOLDS = (0.5, 1.0, 1.5)
PRIMARY_LABEL_THRESHOLD = 1.0
BARRIER_K = (0.5, 1.0, 1.5, 2.0)

DEV_START = pd.Timestamp("2018-01-01")
DEV_END = pd.Timestamp("2022-12-31")

ARMS = ("REAL", "SYNTHETIC")


def bucket_for_et_minute(et_minute: int):
    for name, lo, hi in BUCKETS:
        if lo <= et_minute <= hi:
            return name
    return None


# ------------------------------------------------------------- data load --
def load_dev(instrument: str, proc_dir: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(proc_dir, f"{instrument.lower()}_front_1m.parquet"))
    df = df[(df["session_date"] >= DEV_START) & (df["session_date"] <= DEV_END)].copy()
    assert df["session_date"].min() >= DEV_START and df["session_date"].max() <= DEV_END, "partition breach"
    return df


def build_dense_bars_with_volume(df: pd.DataFrame, tau_max: int = TAU_MAX) -> dict:
    """session_date -> dict of open/high/low/close/volume arrays, tau=0..tau_max
    (et_minute = 570+tau), NaN where a minute is missing."""
    sub = df[(df["et_minute"] >= TOUCH_START) & (df["et_minute"] <= TOUCH_START + tau_max)].copy()
    sub["tau"] = sub["et_minute"] - TOUCH_START
    n = tau_max + 1
    out = {}
    for sd, g in sub.groupby("session_date", sort=True):
        arrs = {k: np.full(n, np.nan) for k in ("open", "high", "low", "close", "volume")}
        idx = g["tau"].to_numpy(int)
        for k in arrs:
            arrs[k][idx] = g[k].to_numpy(float)
        out[sd] = arrs
    return out


def _window_complete(arrs: dict, lo_tau: int, hi_tau: int, fields=("open", "high", "low", "close")) -> bool:
    for f in fields:
        seg = arrs[f][lo_tau:hi_tau + 1]
        if np.any(np.isnan(seg)):
            return False
    return True


# ------------------------------------------------------------ orientation --
def orientation_for(V, O, scale_U, scale_D):
    """Returns (orientation, dir, side_scale). orientation is one of
    'ABOVE_OPEN','BELOW_OPEN','AT_OPEN_AMBIGUOUS', or None (not computable
    -- scale unavailable)."""
    if not (np.isfinite(scale_U) and np.isfinite(scale_D) and scale_U > 0 and scale_D > 0):
        return None, None, None
    if not (np.isfinite(V) and np.isfinite(O)):
        return None, None, None
    delta = V - O
    if delta > 0 and (delta / scale_U) > TAU_B:
        return "ABOVE_OPEN", 1, scale_U
    if delta < 0 and (abs(delta) / scale_D) > TAU_B:
        return "BELOW_OPEN", -1, scale_D
    return "AT_OPEN_AMBIGUOUS", None, None


# ------------------------------------------------------- touch-bar diags --
def touch_bar_diagnostics(O_t, H_t, L_t, C_t, V):
    rng = H_t - L_t
    close_loc = (C_t - L_t) / rng if rng > 0 else np.nan
    body = abs(C_t - O_t)
    body_ratio = body / rng if rng > 0 else np.nan
    upper_wick = H_t - max(O_t, C_t)
    lower_wick = min(O_t, C_t) - L_t
    upper_wick_ratio = upper_wick / rng if rng > 0 else np.nan
    lower_wick_ratio = lower_wick / rng if rng > 0 else np.nan
    return {
        "touch_bar_open_minus_level": O_t - V,
        "touch_bar_close_minus_level": C_t - V,
        "touch_bar_close_location": close_loc,
        "touch_bar_body_ratio": body_ratio,
        "touch_bar_upper_wick_ratio": upper_wick_ratio,
        "touch_bar_lower_wick_ratio": lower_wick_ratio,
    }


def touch_bar_dual_sided(O_t, H_t, L_t, scale_U, scale_D):
    if not (np.isfinite(scale_U) and np.isfinite(scale_D)):
        return np.nan
    return int((H_t - O_t) >= scale_U and (O_t - L_t) >= scale_D)


# ------------------------------------------------------------ raw outcomes --
def raw_outcomes(arrs, T, V, h):
    close_h = arrs["close"][T + h]
    raw_close_displacement = close_h - V
    seg_hi = arrs["high"][T + 1:T + h + 1]
    seg_lo = arrs["low"][T + 1:T + h + 1]
    raw_up_ext = np.max(seg_hi) - V
    raw_down_ext = V - np.min(seg_lo)
    post_touch_retouch = int(np.any((seg_lo <= V) & (seg_hi >= V)))
    return {
        "close_h": close_h, "raw_close_displacement": raw_close_displacement,
        "raw_up_ext": raw_up_ext, "raw_down_ext": raw_down_ext,
        "post_touch_retouch": post_touch_retouch,
    }


# ------------------------------------------------------ normalized outcomes --
def normalized_outcomes(arrs, T, V, h, dir_, orientation, scale_U, scale_D):
    close_h = arrs["close"][T + h]
    seg_hi = arrs["high"][T + 1:T + h + 1]
    seg_lo = arrs["low"][T + 1:T + h + 1]
    up_ext = np.max(seg_hi) - V
    down_ext = V - np.min(seg_lo)
    side_scale = scale_U if orientation == "ABOVE_OPEN" else scale_D
    D_h = dir_ * (close_h - V) / side_scale
    if orientation == "ABOVE_OPEN":
        MFE_h = max(0.0, up_ext) / scale_U
        MAE_h = max(0.0, down_ext) / scale_U
    else:
        MFE_h = max(0.0, down_ext) / scale_D
        MAE_h = max(0.0, up_ext) / scale_D
    denom = MFE_h + MAE_h
    Q_h = (MFE_h - MAE_h) / denom if denom > 0 else np.nan
    return {"D_h": D_h, "MFE_h": MFE_h, "MAE_h": MAE_h, "Q_h": Q_h}


def directional_close_recross(arrs, T, h, orientation, V):
    """continuation side: close on the 'away from open' side; rejection
    side: close back on the 'toward/through open' side. Strict inequality;
    a close exactly at V counts as neither."""
    closes = arrs["close"][T + 1:T + h + 1]
    if orientation == "ABOVE_OPEN":
        cont_mask = closes > V
        rej_mask = closes < V
    else:
        cont_mask = closes < V
        rej_mask = closes > V
    cont_idx = np.where(cont_mask)[0]
    if len(cont_idx) == 0:
        return {"directional_close_recross": 0, "first_continuation_side_close_bar": np.nan,
               "first_rejection_side_close_after_continuation_bar": np.nan}
    first_cont = cont_idx[0]
    rej_after = np.where(rej_mask[first_cont + 1:])[0]
    if len(rej_after) == 0:
        return {"directional_close_recross": 0,
               "first_continuation_side_close_bar": T + 1 + first_cont,
               "first_rejection_side_close_after_continuation_bar": np.nan}
    first_rej = first_cont + 1 + rej_after[0]
    return {"directional_close_recross": 1,
           "first_continuation_side_close_bar": T + 1 + first_cont,
           "first_rejection_side_close_after_continuation_bar": T + 1 + first_rej}


def continuation_rejection_labels(D_h, thresholds=LABEL_THRESHOLDS):
    out = {}
    for tau in thresholds:
        if D_h >= tau:
            out[tau] = "CONTINUATION"
        elif D_h <= -tau:
            out[tau] = "REJECTION"
        else:
            out[tau] = "INCONCLUSIVE"
    return out


# ---------------------------------------------------------- barrier outcomes --
def barrier_outcomes(arrs, T, h, k, orientation, V, scale_U, scale_D):
    seg_hi = arrs["high"][T + 1:T + h + 1]
    seg_lo = arrs["low"][T + 1:T + h + 1]
    if orientation == "ABOVE_OPEN":
        cont_barrier = V + k * scale_U
        rej_barrier = V - k * scale_U
        cont_reached = seg_hi >= cont_barrier
        rej_reached = seg_lo <= rej_barrier
    else:
        cont_barrier = V - k * scale_D
        rej_barrier = V + k * scale_D
        cont_reached = seg_lo <= cont_barrier
        rej_reached = seg_hi >= rej_barrier
    cont_idx = np.where(cont_reached)[0]
    rej_idx = np.where(rej_reached)[0]
    first_cont = int(T + 1 + cont_idx[0]) if len(cont_idx) else np.nan
    first_rej = int(T + 1 + rej_idx[0]) if len(rej_idx) else np.nan
    reach_cont = int(len(cont_idx) > 0)
    reach_rej = int(len(rej_idx) > 0)
    if not reach_cont and not reach_rej:
        order = "NEITHER_REACHED"
    elif reach_cont and not reach_rej:
        order = "CONTINUATION_FIRST"
    elif reach_rej and not reach_cont:
        order = "REJECTION_FIRST"
    else:
        if first_cont < first_rej:
            order = "CONTINUATION_FIRST"
        elif first_rej < first_cont:
            order = "REJECTION_FIRST"
        else:
            order = "SAME_BAR_BARRIER_TIE"
    return {"reach_continuation": reach_cont, "reach_rejection": reach_rej,
           "first_continuation_bar": first_cont, "first_rejection_bar": first_rej,
           "barrier_order": order}
