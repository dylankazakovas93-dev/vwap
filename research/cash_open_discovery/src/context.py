"""Overnight positioning/path proxies (available by 09:29 ET) and
prior-session final-window direction variables. All causal: only bars
strictly before the current session's 09:30 bar, or bars from the prior
session, are used. et_minute wraps at midnight within a session, so
chronological order is taken from ts_event (already sorted), not et_minute.
"""
import numpy as np
import pandas as pd

RTH_CLOSE_MIN = 960   # 16:00 ET
MAINT_BOUNDARY_MIN = 1020  # 17:00 ET (last tradeable bar closes at 17:00)


def _seg_stats(sub_close, sub_high, sub_low, label):
    out = {}
    n = len(sub_close)
    if n == 0:
        return {f"{label}_return": np.nan, f"{label}_netdisp": np.nan,
                f"{label}_path_eff": np.nan, f"{label}_dirbars": np.nan,
                f"{label}_runlen": np.nan, f"{label}_closeloc": np.nan}
    ret = sub_close[-1] - sub_close[0]
    diffs = np.diff(sub_close)
    sumabs = np.nansum(np.abs(diffs))
    out[f"{label}_return"] = float(ret)
    out[f"{label}_netdisp"] = float(ret)
    out[f"{label}_path_eff"] = float(abs(ret) / sumabs) if sumabs > 0 else np.nan
    out[f"{label}_dirbars"] = float(np.mean(diffs > 0)) if len(diffs) else np.nan
    s = np.sign(diffs)
    if len(s):
        run = 1
        for k in range(len(s) - 1, 0, -1):
            if s[k] == s[-1] and s[k] != 0:
                run += 1
            else:
                break
        out[f"{label}_runlen"] = float(run if s[-1] != 0 else 0)
    else:
        out[f"{label}_runlen"] = np.nan
    rng = np.nanmax(sub_high) - np.nanmin(sub_low)
    out[f"{label}_closeloc"] = float((sub_close[-1] - np.nanmin(sub_low)) / rng) if rng > 0 else np.nan
    return out


def build_context(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["session_date", "ts_event"]).reset_index(drop=True)
    sessions = df["session_date"].drop_duplicates().sort_values().to_list()
    by_session = {sd: g.reset_index(drop=True) for sd, g in df.groupby("session_date", sort=True)}

    # prior-session RTH close/high/low and final-window stats (session s uses session s-1's data)
    prior_rth_close, prior_rth_high, prior_rth_low = {}, {}, {}
    prior_final10_rth, prior_final10_boundary = {}, {}
    for sd in sessions:
        g = by_session[sd]
        rth = g[(g["et_minute"] >= 570) & (g["et_minute"] <= RTH_CLOSE_MIN - 1)]
        if len(rth):
            prior_rth_close[sd] = float(rth["close"].iloc[-1])
            prior_rth_high[sd] = float(rth["high"].max())
            prior_rth_low[sd] = float(rth["low"].min())
        last10_rth = rth.tail(10)
        prior_final10_rth[sd] = _seg_stats(
            last10_rth["close"].to_numpy(), last10_rth["high"].to_numpy(),
            last10_rth["low"].to_numpy(), "final10min_priorclose")
        boundary = g[(g["et_minute"] >= 570) & (g["et_minute"] <= MAINT_BOUNDARY_MIN - 1)]
        last10_bnd = boundary.tail(10)
        prior_final10_boundary[sd] = _seg_stats(
            last10_bnd["close"].to_numpy(), last10_bnd["high"].to_numpy(),
            last10_bnd["low"].to_numpy(), "final10min_sessionend")

    rows = []
    for i, sd in enumerate(sessions):
        g = by_session[sd]
        idx0930 = g.index[g["et_minute"] == 570]
        if len(idx0930) == 0:
            continue
        i0930 = idx0930[0]
        pre = g.iloc[:i0930]
        if len(pre) == 0:
            continue
        row = {"session_date": sd}
        globex_open = float(pre["open"].iloc[0])
        pre_close = float(pre["close"].iloc[-1])
        hi, lo, cl = pre["high"].to_numpy(), pre["low"].to_numpy(), pre["close"].to_numpy()
        row["globex_open_to_0929_return"] = pre_close - globex_open
        row["overnight_high"] = float(np.nanmax(hi))
        row["overnight_low"] = float(np.nanmin(lo))
        row["overnight_range"] = row["overnight_high"] - row["overnight_low"]
        rng = row["overnight_range"]
        row["position_in_overnight_range"] = (pre_close - row["overnight_low"]) / rng if rng > 0 else np.nan
        row["dist_from_overnight_high"] = row["overnight_high"] - pre_close
        row["dist_from_overnight_low"] = pre_close - row["overnight_low"]
        diffs = np.diff(cl)
        sumabs = np.nansum(np.abs(diffs))
        row["overnight_path_efficiency"] = abs(pre_close - globex_open) / sumabs if sumabs > 0 else np.nan
        row["overnight_pct_bars_up"] = float(np.mean(diffs > 0)) if len(diffs) else np.nan
        for mins in (10, 30, 60):
            seg = pre.tail(mins)
            if len(seg) >= 2:
                sret = float(seg["close"].iloc[-1] - seg["close"].iloc[0])
                sdiffs = np.diff(seg["close"].to_numpy())
                ssum = np.nansum(np.abs(sdiffs))
                row[f"final{mins}min_return"] = sret
                if mins == 10:
                    row["final10min_path_efficiency"] = abs(sret) / ssum if ssum > 0 else np.nan
            else:
                row[f"final{mins}min_return"] = np.nan
                if mins == 10:
                    row["final10min_path_efficiency"] = np.nan
        # frozen VWAP through 09:29 (Sec. 9), volume-weighted (H+L+C)/3 over the whole prefix
        vol = pre["volume"].to_numpy(float)
        pbar = (pre["high"].to_numpy() + pre["low"].to_numpy() + pre["close"].to_numpy()) / 3.0
        vsum = np.nansum(vol)
        row["vwap_0929"] = float(np.nansum(pbar * vol) / vsum) if vsum > 0 else np.nan
        row["dist_from_vwap_0929_at_open"] = (globex_open - row["vwap_0929"]) if np.isfinite(row["vwap_0929"]) else np.nan

        prev_sd = sessions[i - 1] if i > 0 else None
        row["prior_rth_close"] = prior_rth_close.get(prev_sd, np.nan) if prev_sd else np.nan
        prh = prior_rth_high.get(prev_sd, np.nan) if prev_sd else np.nan
        prl = prior_rth_low.get(prev_sd, np.nan) if prev_sd else np.nan
        row["prior_close_to_0929_gap"] = (pre_close - row["prior_rth_close"]) if np.isfinite(row["prior_rth_close"]) else np.nan
        row["overnight_break_and_return"] = bool(
            np.isfinite(prh) and np.isfinite(prl) and
            (row["overnight_high"] > prh or row["overnight_low"] < prl) and
            (prl <= pre_close <= prh))
        if prev_sd and prev_sd in prior_final10_rth:
            row.update(prior_final10_rth[prev_sd])
            row.update(prior_final10_boundary[prev_sd])
        rows.append(row)
    return pd.DataFrame(rows).set_index("session_date")
