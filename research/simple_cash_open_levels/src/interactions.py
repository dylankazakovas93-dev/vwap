"""Touch search, orientation, same-bar morphology, post-touch outcomes,
barriers -- SPEC_SIMPLE_LEVELS.md secs 8-15. Self-contained.
"""
import numpy as np
import pandas as pd

TOUCH_START = 570          # 09:30 ET
TOUCH_END = 689              # 11:29 ET (inclusive), 120 bars
TAU_MAX = 239                 # 809 - 570 = 239 (13:29 ET; touch at tau=119 + h=120)
HORIZONS = (5, 15, 30, 60, 120)
PRIMARY_HORIZONS = (30, 60, 120)
BARRIER_B = (0.5, 1.0, 2.0, 3.0)
TICK_SIZE = 0.25  # ES and NQ both

TIMING_BINS = [
    ("BAR_0930", 0, 0), ("MINUTES_2_TO_5", 1, 4), ("MINUTES_6_TO_15", 5, 14),
    ("MINUTES_16_TO_30", 15, 29), ("MINUTES_31_TO_60", 30, 59), ("MINUTES_61_TO_120", 60, 119),
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


def orientation_for(level_value, O_0930, tick=TICK_SIZE):
    if not (np.isfinite(level_value) and np.isfinite(O_0930)):
        return None
    if level_value >= O_0930 + tick:
        return "UPPER_LEVEL"
    if level_value <= O_0930 - tick:
        return "LOWER_LEVEL"
    return "AT_OPEN_AMBIGUOUS"


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


def same_bar_morphology(orientation, close_T, level_value):
    if orientation == "UPPER_LEVEL":
        if close_T < level_value:
            return "SAME_BAR_REVERSAL_PROXY"
        if close_T > level_value:
            return "SAME_BAR_BLAST_THROUGH_PROXY"
        return "SAME_BAR_NEUTRAL"
    else:  # LOWER_LEVEL
        if close_T > level_value:
            return "SAME_BAR_REVERSAL_PROXY"
        if close_T < level_value:
            return "SAME_BAR_BLAST_THROUGH_PROXY"
        return "SAME_BAR_NEUTRAL"


def raw_outcomes(arrs, T, level_value, h):
    close_h = arrs["close"][T + h]
    raw_close_displacement = close_h - level_value
    seg_hi = arrs["high"][T + 1:T + h + 1]
    seg_lo = arrs["low"][T + 1:T + h + 1]
    raw_up_excursion = np.max(seg_hi) - level_value
    raw_down_excursion = level_value - np.min(seg_lo)
    post_touch_retouch = int(np.any((seg_lo <= level_value) & (seg_hi >= level_value)))
    return {"close_h": close_h, "raw_close_displacement": raw_close_displacement,
           "raw_up_excursion": raw_up_excursion, "raw_down_excursion": raw_down_excursion,
           "post_touch_retouch": post_touch_retouch}


def oriented_outcomes(arrs, T, level_value, h, orientation, native_sd):
    close_h = arrs["close"][T + h]
    seg_hi = arrs["high"][T + 1:T + h + 1]
    seg_lo = arrs["low"][T + 1:T + h + 1]
    up_ext = np.max(seg_hi) - level_value
    down_ext = level_value - np.min(seg_lo)
    if orientation == "UPPER_LEVEL":
        CONT_EXC = max(0.0, up_ext)
        REV_EXC = max(0.0, down_ext)
        SIGNED_CLOSE = close_h - level_value
    else:
        CONT_EXC = max(0.0, down_ext)
        REV_EXC = max(0.0, up_ext)
        SIGNED_CLOSE = level_value - close_h
    out = {"CONT_EXC_h": CONT_EXC, "REV_EXC_h": REV_EXC, "SIGNED_CLOSE_h": SIGNED_CLOSE}
    if native_sd is not None and np.isfinite(native_sd) and native_sd > 0:
        c_sd = CONT_EXC / native_sd
        r_sd = REV_EXC / native_sd
        s_sd = SIGNED_CLOSE / native_sd
        denom = c_sd + r_sd
        dom = (c_sd - r_sd) / denom if denom > 0 else np.nan
        out.update({"CONT_EXC_SD_h": c_sd, "REV_EXC_SD_h": r_sd, "SIGNED_CLOSE_SD_h": s_sd, "DOMINANCE_h": dom})
    else:
        out.update({"CONT_EXC_SD_h": np.nan, "REV_EXC_SD_h": np.nan, "SIGNED_CLOSE_SD_h": np.nan, "DOMINANCE_h": np.nan})
    return out


def directional_close_recross(arrs, T, h, orientation, level_value):
    closes = arrs["close"][T + 1:T + h + 1]
    if orientation == "UPPER_LEVEL":
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


def barrier_outcomes(arrs, T, h, b, orientation, level_value, native_sd):
    seg_hi = arrs["high"][T + 1:T + h + 1]
    seg_lo = arrs["low"][T + 1:T + h + 1]
    if orientation == "UPPER_LEVEL":
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
