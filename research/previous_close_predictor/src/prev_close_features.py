"""Previous-RTH-session closing-window features — SPEC_PREDICTOR.md Sec. 2-5.

One row per (instrument, session_date=p) with early-close flag and, for
each W in {1,5,10,15,30,60}: ret_W, range_W, close_location_W,
signed_efficiency_W, volume_sum_W (raw), plus causal trailing-normalized
norm_ret_W, range_ratio_W, volume_ratio_W.
"""
import numpy as np
import pandas as pd

WINDOWS = (1, 5, 10, 15, 30, 60)
RTH_CLOSE_MIN = 959  # et_minute of the bar that closes at 16:00 ET
WIN_START = RTH_CLOSE_MIN - max(WINDOWS) + 1  # 900
BASELINE_WINDOW = 60
BASELINE_MIN = 20


def _session_early_close_flags(df: pd.DataFrame) -> pd.Series:
    rth = df[(df["et_minute"] >= 570) & (df["et_minute"] <= RTH_CLOSE_MIN)]
    last_min = rth.groupby("session_date")["et_minute"].max()
    return last_min < RTH_CLOSE_MIN  # True = early close


def _dense_window_bars(df: pd.DataFrame):
    """Dense arrays tau2=0..59 (et_minute WIN_START..RTH_CLOSE_MIN) per
    session, NaN where missing. tau2=59 == et_minute 959 (the close bar)."""
    sub = df[(df["et_minute"] >= WIN_START) & (df["et_minute"] <= RTH_CLOSE_MIN)].copy()
    sub["tau2"] = sub["et_minute"] - WIN_START
    n = RTH_CLOSE_MIN - WIN_START + 1
    out = {}
    for sd, g in sub.groupby("session_date", sort=True):
        arrs = {k: np.full(n, np.nan) for k in ("open", "high", "low", "close", "volume")}
        idx = g["tau2"].to_numpy(int)
        for k in arrs:
            arrs[k][idx] = g[k].to_numpy(float)
        out[sd] = arrs
    return out


def _features_for_window(arrs, W):
    n = len(arrs["close"])
    lo_idx = n - W  # tau2 index of first_bar_open_W
    seg_o, seg_h, seg_l, seg_c, seg_v = (arrs[k][lo_idx:n] for k in ("open", "high", "low", "close", "volume"))
    if np.any(np.isnan(seg_o)) or np.any(np.isnan(seg_h)) or np.any(np.isnan(seg_l)) or \
       np.any(np.isnan(seg_c)) or np.any(np.isnan(seg_v)):
        return None
    first_open = seg_o[0]
    official_close = seg_c[-1]
    ret = float(official_close - first_open)
    rng = float(np.max(seg_h) - np.min(seg_l))
    close_loc = float(2 * (official_close - np.min(seg_l)) / rng - 1) if rng > 0 else np.nan
    d = np.empty(W)
    d[0] = seg_c[0] - seg_o[0]
    if W > 1:
        d[1:] = np.diff(seg_c)
    sumabs = float(np.sum(np.abs(d)))
    sig_eff = float(ret / sumabs) if sumabs > 0 else np.nan
    vol_sum = float(np.sum(seg_v))
    return {"ret": ret, "range": rng, "close_location": close_loc,
           "signed_efficiency": sig_eff, "volume_sum": vol_sum}


def build_prev_close_features(df: pd.DataFrame, instrument: str) -> pd.DataFrame:
    early = _session_early_close_flags(df)
    bar_frames = _dense_window_bars(df)
    rows = []
    for sd, arrs in bar_frames.items():
        is_ec = bool(early.get(sd, True))
        row = {"instrument": instrument, "session_date": sd, "is_early_close": is_ec}
        if not is_ec:
            for W in WINDOWS:
                t = _features_for_window(arrs, W)
                if t is not None:
                    for k, v in t.items():
                        row[f"{k}_{W}"] = v
        rows.append(row)
    feat = pd.DataFrame(rows).sort_values("session_date").reset_index(drop=True)

    for W in WINDOWS:
        for base_col, out_col, use_mad in (
                (f"ret_{W}", f"norm_ret_{W}", True),
                (f"range_{W}", f"range_ratio_{W}", False),
                (f"volume_sum_{W}", f"volume_ratio_{W}", False)):
            if base_col not in feat.columns:
                feat[out_col] = np.nan
                continue
            series = feat[base_col].where(~feat["is_early_close"])
            if use_mad:
                med_abs = series.abs().rolling(BASELINE_WINDOW, min_periods=BASELINE_MIN).median().shift(1)
                scale = med_abs * 1.4826
                feat[out_col] = feat[base_col] / scale
            else:
                med = series.rolling(BASELINE_WINDOW, min_periods=BASELINE_MIN).median().shift(1)
                feat[out_col] = feat[base_col] / med
    return feat
