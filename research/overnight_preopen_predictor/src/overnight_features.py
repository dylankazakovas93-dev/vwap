"""Overnight and pre-open features — SPEC_OVERNIGHT.md Sec. 2-6.

Self-contained (no cross-import from generation 2 or 4; the early-close
flag and previous-session mapping are small, independently reimplemented
utilities here, consistent with keeping generations decoupled).
"""
import numpy as np
import pandas as pd

WINDOWS = (5, 10, 15, 30, 60)
WIN_MAX = max(WINDOWS)
RTH_OPEN_MIN = 570   # 09:30 ET
RTH_CLOSE_MIN = 959  # closes at 16:00 ET
PREOPEN_START = RTH_OPEN_MIN - 2 * WIN_MAX  # 450
BASELINE_WINDOW = 60
BASELINE_MIN = 20
VWAP_MIN_BARS = 30


def _session_early_close_flags(df: pd.DataFrame) -> pd.Series:
    rth = df[(df["et_minute"] >= RTH_OPEN_MIN) & (df["et_minute"] <= RTH_CLOSE_MIN)]
    last_min = rth.groupby("session_date")["et_minute"].max()
    return last_min < RTH_CLOSE_MIN


def _prior_rth_reference(df: pd.DataFrame) -> pd.DataFrame:
    """Per session: prior_rth_open/close/high/low from the nearest earlier
    non-early-close session_date; NaN if none or predecessor is early
    close."""
    rth = df[(df["et_minute"] >= RTH_OPEN_MIN) & (df["et_minute"] <= RTH_CLOSE_MIN)]
    agg = rth.groupby("session_date").agg(
        rth_open=("open", "first"), rth_close=("close", "last"),
        rth_high=("high", "max"), rth_low=("low", "min"))
    early = _session_early_close_flags(df)
    agg = agg.sort_index()
    sessions = agg.index.to_list()
    out = {}
    for i, sd in enumerate(sessions):
        if i == 0 or early.get(sessions[i - 1], True):
            out[sd] = {"prior_rth_open": np.nan, "prior_rth_close": np.nan,
                      "prior_rth_high": np.nan, "prior_rth_low": np.nan}
        else:
            p = sessions[i - 1]
            out[sd] = {"prior_rth_open": agg.loc[p, "rth_open"],
                      "prior_rth_close": agg.loc[p, "rth_close"],
                      "prior_rth_high": agg.loc[p, "rth_high"],
                      "prior_rth_low": agg.loc[p, "rth_low"]}
    return pd.DataFrame.from_dict(out, orient="index")


def _overnight_features_one_session(g: pd.DataFrame):
    """g: full session rows sorted by ts_event. Returns dict or None if no
    overnight bars / no 09:30 bar."""
    idx0930 = g.index[g["et_minute"] == RTH_OPEN_MIN]
    if len(idx0930) == 0:
        return None
    i0930 = g.index.get_loc(idx0930[0])
    pre = g.iloc[:i0930]
    if len(pre) == 0:
        return None
    globex_open = float(pre["open"].iloc[0])
    close_0929 = float(pre["close"].iloc[-1])
    hi, lo, cl, vol = (pre[c].to_numpy(float) for c in ("high", "low", "close", "volume"))
    row = {}
    row["overnight_return"] = close_0929 - globex_open
    row["overnight_high"] = float(np.max(hi))
    row["overnight_low"] = float(np.min(lo))
    row["overnight_range"] = row["overnight_high"] - row["overnight_low"]
    rng = row["overnight_range"]
    row["range_position_0929"] = (2 * (close_0929 - row["overnight_low"]) / rng - 1) if rng > 0 else np.nan
    diffs = np.diff(cl)
    d = np.empty(len(cl))
    d[0] = cl[0] - pre["open"].iloc[0]
    if len(cl) > 1:
        d[1:] = diffs
    sumabs = float(np.sum(np.abs(d)))
    row["signed_path_efficiency_on"] = (row["overnight_return"] / sumabs) if sumabs > 0 else np.nan
    row["dist_from_overnight_high"] = row["overnight_high"] - close_0929
    row["dist_from_overnight_low"] = close_0929 - row["overnight_low"]
    row["overnight_total_volume"] = float(np.sum(vol))
    row["close_0929"] = close_0929
    row["globex_open"] = globex_open
    row["n_overnight_bars"] = len(pre)

    if len(pre) >= VWAP_MIN_BARS:
        pbar = (hi + lo + cl) / 3.0
        vsum = float(np.sum(vol))
        vwap = float(np.sum(pbar * vol) / vsum) if vsum > 0 else np.nan
        var = float(np.sum(vol * pbar ** 2) / vsum - vwap ** 2) if vsum > 0 else np.nan
        sigma = float(np.sqrt(max(var, 0.0))) if np.isfinite(var) else np.nan
        row["vwap_on"] = vwap
        row["dist_0929_from_vwap"] = close_0929 - vwap if np.isfinite(vwap) else np.nan
        row["normalized_dist_from_vwap"] = (row["dist_0929_from_vwap"] / sigma) if (sigma and sigma > 0) else np.nan
        row["vwap_location_in_range"] = (2 * (vwap - row["overnight_low"]) / rng - 1) if (rng > 0 and np.isfinite(vwap)) else np.nan
    else:
        for k in ("vwap_on", "dist_0929_from_vwap", "normalized_dist_from_vwap", "vwap_location_in_range"):
            row[k] = np.nan
    return row


def _dense_preopen_bars(df: pd.DataFrame):
    sub = df[(df["et_minute"] >= PREOPEN_START) & (df["et_minute"] <= RTH_OPEN_MIN - 1)].copy()
    sub["tau3"] = sub["et_minute"] - PREOPEN_START
    n = RTH_OPEN_MIN - PREOPEN_START  # 120
    out = {}
    for sd, g in sub.groupby("session_date", sort=True):
        arrs = {k: np.full(n, np.nan) for k in ("open", "high", "low", "close", "volume")}
        idx = g["tau3"].to_numpy(int)
        for k in arrs:
            arrs[k][idx] = g[k].to_numpy(float)
        out[sd] = arrs
    return out


def _window_feature(arrs, lo_idx, hi_idx_excl):
    """Bars at tau3 in [lo_idx, hi_idx_excl)."""
    seg_o = arrs["open"][lo_idx:hi_idx_excl]
    seg_h = arrs["high"][lo_idx:hi_idx_excl]
    seg_l = arrs["low"][lo_idx:hi_idx_excl]
    seg_c = arrs["close"][lo_idx:hi_idx_excl]
    seg_v = arrs["volume"][lo_idx:hi_idx_excl]
    if np.any(np.isnan(seg_o)) or np.any(np.isnan(seg_h)) or np.any(np.isnan(seg_l)) or \
       np.any(np.isnan(seg_c)) or np.any(np.isnan(seg_v)):
        return None
    ret = float(seg_c[-1] - seg_o[0])
    rng = float(np.max(seg_h) - np.min(seg_l))
    close_loc = float(2 * (seg_c[-1] - np.min(seg_l)) / rng - 1) if rng > 0 else np.nan
    d = np.empty(len(seg_c))
    d[0] = seg_c[0] - seg_o[0]
    if len(seg_c) > 1:
        d[1:] = np.diff(seg_c)
    sumabs = float(np.sum(np.abs(d)))
    sig_eff = float(ret / sumabs) if sumabs > 0 else np.nan
    vol_sum = float(np.sum(seg_v))
    return {"ret": ret, "range": rng, "close_location": close_loc,
           "signed_path_eff": sig_eff, "volume_sum": vol_sum}


def build_overnight_ledger(df: pd.DataFrame, instrument: str) -> pd.DataFrame:
    df = df.sort_values(["session_date", "ts_event"]).reset_index(drop=True)
    prior_ref = _prior_rth_reference(df)
    preopen_bars = _dense_preopen_bars(df)

    rows = []
    for sd, g in df.groupby("session_date", sort=True):
        g = g.reset_index(drop=True)
        on = _overnight_features_one_session(g)
        if on is None:
            continue
        row = {"instrument": instrument, "session_date": sd, "year": pd.Timestamp(sd).year}
        row.update(on)

        arrs = preopen_bars.get(sd)
        if arrs is not None:
            for W in WINDOWS:
                cur = _window_feature(arrs, 120 - W, 120)
                prev = _window_feature(arrs, 120 - 2 * W, 120 - W)
                if cur is not None:
                    row[f"signed_return_{W}"] = cur["ret"]
                    row[f"range_{W}"] = cur["range"]
                    row[f"close_location_{W}"] = cur["close_location"]
                    row[f"signed_path_eff_{W}"] = cur["signed_path_eff"]
                    row[f"volume_sum_{W}"] = cur["volume_sum"]
                if cur is not None and prev is not None:
                    row[f"return_acceleration_{W}"] = cur["ret"] - prev["ret"]

        if sd in prior_ref.index:
            pref = prior_ref.loc[sd]
            if pd.notna(pref["prior_rth_close"]):
                row["prior_rth_open"] = pref["prior_rth_open"]
                row["prior_rth_close"] = pref["prior_rth_close"]
                row["prior_rth_high"] = pref["prior_rth_high"]
                row["prior_rth_low"] = pref["prior_rth_low"]
        rows.append(row)

    feat = pd.DataFrame(rows).sort_values("session_date").reset_index(drop=True)
    for c in ("prior_rth_open", "prior_rth_close", "prior_rth_high", "prior_rth_low"):
        if c not in feat.columns:
            feat[c] = np.nan

    # Sec. 6 relationship variables
    has_prior = feat["prior_rth_close"].notna()
    feat["prior_rth_close_to_0929_return"] = np.where(has_prior, feat["close_0929"] - feat["prior_rth_close"], np.nan)
    on_dir = np.sign(feat["overnight_return"])
    rth_dir = np.where(has_prior, np.sign(feat["prior_rth_close"] - feat["prior_rth_open"]), np.nan)
    agree = np.where(~has_prior, np.nan,
                    np.where((on_dir == 0) | (rth_dir == 0), 0.0,
                            np.where(on_dir == rth_dir, 1.0, -1.0)))
    feat["overnight_agrees_with_prior_rth"] = agree
    diff_raw = np.where(has_prior, feat["overnight_return"] - feat["prior_rth_close_to_0929_return"], np.nan)
    feat["_diff_raw_for_norm"] = diff_raw
    feat["above_below_prior_close"] = np.where(~has_prior, np.nan,
                                               np.sign(feat["close_0929"] - feat["prior_rth_close"]))
    feat["broke_prior_rth_high_or_low"] = np.where(~has_prior, np.nan,
                                                   ((feat["overnight_high"] > feat["prior_rth_high"]) |
                                                    (feat["overnight_low"] < feat["prior_rth_low"])).astype(float))
    feat["finished_inside_prior_rth_range"] = np.where(~has_prior, np.nan,
                                                       ((feat["prior_rth_low"] <= feat["close_0929"]) &
                                                        (feat["close_0929"] <= feat["prior_rth_high"])).astype(float))

    # causal trailing normalization (Sec. 7)
    diff_series = feat["_diff_raw_for_norm"]
    med_abs = diff_series.abs().rolling(BASELINE_WINDOW, min_periods=BASELINE_MIN).median().shift(1)
    feat["overnight_minus_priorrth_norm"] = feat["_diff_raw_for_norm"] / (med_abs * 1.4826)
    feat = feat.drop(columns=["_diff_raw_for_norm"])

    med_vol_on = feat["overnight_total_volume"].rolling(BASELINE_WINDOW, min_periods=BASELINE_MIN).median().shift(1)
    feat["normalized_overnight_volume"] = feat["overnight_total_volume"] / med_vol_on
    for W in WINDOWS:
        col = f"volume_sum_{W}"
        if col in feat.columns:
            med = feat[col].rolling(BASELINE_WINDOW, min_periods=BASELINE_MIN).median().shift(1)
            feat[f"relative_volume_{W}"] = feat[col] / med
    return feat
