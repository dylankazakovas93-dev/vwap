"""Touch search, nested activation windows, same-bar morphology, post-
touch outcomes, barriers, close-recross -- SPEC_EXCURSION_TIMING.md
secs 7-14. Self-contained.
"""
import numpy as np
import pandas as pd

TOUCH_START = 570          # 09:30 ET
TOUCH_END = 689              # 11:29 ET (inclusive), 120 bars
TAU_MAX = 239                 # 809 - 570 = 239 (13:29 ET)

ACTIVATION_WINDOWS = (1, 2, 3, 4, 5, 10, 15, 20, 30, 60, 120)
HORIZONS = (1, 2, 3, 4, 5, 10, 15, 20, 30, 60, 120)
BARRIER_B = (0.5, 1.0, 2.0, 3.0)
PRIMARY_B = 1.0
TICK_SIZE = 0.25

TIMING_BINS = [
    ("BAR_0930", 0, 0), ("MINUTE_2", 1, 1), ("MINUTE_3", 2, 2), ("MINUTE_4", 3, 3),
    ("MINUTE_5", 4, 4), ("MINUTES_6_TO_10", 5, 9), ("MINUTES_11_TO_15", 10, 14),
    ("MINUTES_16_TO_20", 15, 19), ("MINUTES_21_TO_30", 20, 29),
    ("MINUTES_31_TO_60", 30, 59), ("MINUTES_61_TO_120", 60, 119),
]


def timing_bin_for_tau(tau: int):
    for name, lo, hi in TIMING_BINS:
        if lo <= tau <= hi:
            return name
    return None


def build_dense_bars_with_volume(df: pd.DataFrame, tau_max: int = TAU_MAX) -> dict:
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


def _window_complete(arrs, lo_tau, hi_tau, fields=("open", "high", "low", "close")):
    for f in fields:
        seg = arrs[f][lo_tau:hi_tau + 1]
        if np.any(np.isnan(seg)):
            return False
    return True


def same_bar_morphology(side, close_T, level_value):
    if side == "upper":
        if close_T < level_value:
            return "SAME_BAR_REVERSAL_PROXY"
        if close_T > level_value:
            return "SAME_BAR_BLAST_THROUGH_PROXY"
        return "SAME_BAR_NEUTRAL"
    else:  # lower
        if close_T > level_value:
            return "SAME_BAR_REVERSAL_PROXY"
        if close_T < level_value:
            return "SAME_BAR_BLAST_THROUGH_PROXY"
        return "SAME_BAR_NEUTRAL"


def touch_bar_fields(O_t, H_t, L_t, C_t, V_t, level_value):
    rng = H_t - L_t
    close_loc = (C_t - L_t) / rng if rng > 0 else np.nan
    body = abs(C_t - O_t)
    body_ratio = body / rng if rng > 0 else np.nan
    upper_wick = H_t - max(O_t, C_t)
    lower_wick = min(O_t, C_t) - L_t
    upper_wick_ratio = upper_wick / rng if rng > 0 else np.nan
    lower_wick_ratio = lower_wick / rng if rng > 0 else np.nan
    return {
        "touch_bar_open": O_t, "touch_bar_high": H_t, "touch_bar_low": L_t,
        "touch_bar_close": C_t, "touch_bar_volume": V_t,
        "touch_bar_close_minus_level": C_t - level_value,
        "touch_bar_close_location": close_loc, "touch_bar_body_ratio": body_ratio,
        "touch_bar_upper_wick_ratio": upper_wick_ratio, "touch_bar_lower_wick_ratio": lower_wick_ratio,
    }


def raw_outcomes(arrs, T, level_value, H):
    close_H = arrs["close"][T + H]
    raw_close_displacement = close_H - level_value
    seg_hi = arrs["high"][T + 1:T + H + 1]
    seg_lo = arrs["low"][T + 1:T + H + 1]
    raw_up_excursion = np.max(seg_hi) - level_value
    raw_down_excursion = level_value - np.min(seg_lo)
    post_touch_retouch = int(np.any((seg_lo <= level_value) & (seg_hi >= level_value)))
    return {"close_H": close_H, "raw_close_displacement": raw_close_displacement,
           "raw_up_excursion": raw_up_excursion, "raw_down_excursion": raw_down_excursion,
           "post_touch_retouch": post_touch_retouch}


def oriented_outcomes(arrs, T, level_value, H, side, native_sd):
    close_H = arrs["close"][T + H]
    seg_hi = arrs["high"][T + 1:T + H + 1]
    seg_lo = arrs["low"][T + 1:T + H + 1]
    up_ext = np.max(seg_hi) - level_value
    down_ext = level_value - np.min(seg_lo)
    if side == "upper":
        CONT_EXC = max(0.0, up_ext)
        REV_EXC = max(0.0, down_ext)
        SIGNED_CLOSE = close_H - level_value
    else:
        CONT_EXC = max(0.0, down_ext)
        REV_EXC = max(0.0, up_ext)
        SIGNED_CLOSE = level_value - close_H
    out = {"CONT_EXC_H": CONT_EXC, "REV_EXC_H": REV_EXC, "SIGNED_CLOSE_H": SIGNED_CLOSE}
    if native_sd is not None and np.isfinite(native_sd) and native_sd > 0:
        c_sd = CONT_EXC / native_sd
        r_sd = REV_EXC / native_sd
        s_sd = SIGNED_CLOSE / native_sd
        denom = c_sd + r_sd
        dom = (c_sd - r_sd) / denom if denom > 0 else np.nan
        out.update({"CONT_EXC_SD_H": c_sd, "REV_EXC_SD_H": r_sd, "SIGNED_CLOSE_SD_H": s_sd, "DOMINANCE_H": dom})
    else:
        out.update({"CONT_EXC_SD_H": np.nan, "REV_EXC_SD_H": np.nan, "SIGNED_CLOSE_SD_H": np.nan, "DOMINANCE_H": np.nan})
    return out


def directional_close_recross(arrs, T, H, side, level_value):
    closes = arrs["close"][T + 1:T + H + 1]
    if side == "upper":
        cont_mask = closes > level_value
        rej_mask = closes < level_value
    else:
        cont_mask = closes < level_value
        rej_mask = closes > level_value
    cont_idx = np.where(cont_mask)[0]
    if len(cont_idx) == 0:
        return {"continuation_side_close_observed": 0, "first_continuation_side_close_bar": np.nan,
               "directional_rejection_recross": 0, "first_rejection_side_close_after_continuation_bar": np.nan}
    first_cont = cont_idx[0]
    rej_after = np.where(rej_mask[first_cont + 1:])[0]
    if len(rej_after) == 0:
        return {"continuation_side_close_observed": 1, "first_continuation_side_close_bar": T + 1 + first_cont,
               "directional_rejection_recross": 0, "first_rejection_side_close_after_continuation_bar": np.nan}
    first_rej = first_cont + 1 + rej_after[0]
    return {"continuation_side_close_observed": 1, "first_continuation_side_close_bar": T + 1 + first_cont,
           "directional_rejection_recross": 1, "first_rejection_side_close_after_continuation_bar": T + 1 + first_rej}


def barrier_outcomes(arrs, T, H, b, side, level_value, native_sd):
    seg_hi = arrs["high"][T + 1:T + H + 1]
    seg_lo = arrs["low"][T + 1:T + H + 1]
    if side == "upper":
        cont_barrier = level_value + b * native_sd
        rej_barrier = level_value - b * native_sd
        cont_reached = seg_hi >= cont_barrier
        rej_reached = seg_lo <= rej_barrier
    else:
        cont_barrier = level_value - b * native_sd
        rej_barrier = level_value + b * native_sd
        cont_reached = seg_lo <= cont_barrier
        rej_reached = seg_hi >= rej_barrier
    cont_idx = np.where(cont_reached)[0]
    rej_idx = np.where(rej_reached)[0]
    first_cont = int(T + 1 + cont_idx[0]) if len(cont_idx) else np.nan
    first_rej = int(T + 1 + rej_idx[0]) if len(rej_idx) else np.nan
    reach_cont = int(len(cont_idx) > 0)
    reach_rej = int(len(rej_idx) > 0)
    if not reach_cont and not reach_rej:
        order = "NEITHER"
    elif reach_cont and not reach_rej:
        order = "CONTINUATION_FIRST"
    elif reach_rej and not reach_cont:
        order = "REVERSAL_FIRST"
    else:
        if first_cont < first_rej:
            order = "CONTINUATION_FIRST"
        elif first_rej < first_cont:
            order = "REVERSAL_FIRST"
        else:
            order = "SAME_BAR_TIE"
    return {"continuation_reached": reach_cont, "reversal_reached": reach_rej,
           "first_continuation_bar": first_cont, "first_reversal_bar": first_rej,
           "barrier_first_outcome": order}
