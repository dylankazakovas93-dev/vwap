"""Required result tables (touch control, delayed failure, volume,
previous test, cross-market, same-bar/null retention).
"""
import numpy as np
import pandas as pd
from scipy import stats

from .outcomes import HORIZONS, BARRIERS, PRIMARY_CLASSES

TIME_STRATA = ("OPEN", "MID_MORNING", "MIDDAY", "AFTERNOON", "ALL_RTH")


def binom_p(k, n):
    if n == 0:
        return np.nan
    return float(stats.binomtest(k, n, 0.5, alternative="two-sided").pvalue)


def _rate_table(df: pd.DataFrame, group_cols, horizon=15, barrier=0.50) -> pd.DataFrame:
    col = f"b{barrier}_h{horizon}_outcome"
    rows = []
    if df.empty or col not in df.columns:
        return pd.DataFrame(rows)
    for gvals, g in df.groupby(group_cols):
        vc = g[col].value_counts()
        n_rot = int(vc.get("ROTATION_FIRST", 0))
        n_brk = int(vc.get("BREAKOUT_FIRST", 0))
        n_tie = int(vc.get("SAME_BAR_TIE", 0))
        n_neither = int(vc.get("NEITHER", 0))
        n = len(g)
        n_nontied = n_rot + n_brk
        row = dict(zip(group_cols, gvals if isinstance(gvals, tuple) else (gvals,)))
        row.update({
            "n_events": n, "rotation_first_n": n_rot, "breakout_first_n": n_brk,
            "tie_n": n_tie, "neither_n": n_neither, "n_nontied": n_nontied,
            "rotation_first_rate": n_rot / n if n else np.nan,
            "breakout_first_rate": n_brk / n if n else np.nan,
            "rot_minus_brk_first_rate": (n_rot - n_brk) / n if n else np.nan,
            "binom_p": binom_p(n_rot, n_nontied) if n_nontied else np.nan,
            "sample_status": "OK" if (n >= 50 and n_nontied >= 20) else "UNDERPOWERED",
        })
        out_cols = [f"median_signed_close_atr_h{horizon}", f"median_rotation_exc_atr_h{horizon}",
                    f"median_breakout_exc_atr_h{horizon}", f"median_dominance_h{horizon}"]
        for oc, src in zip(out_cols, [f"signed_close_atr_h{horizon}", f"rotation_exc_atr_h{horizon}",
                                       f"breakout_exc_atr_h{horizon}", f"dominance_h{horizon}"]):
            row[oc] = float(g[src].median()) if src in g.columns and g[src].notna().any() else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def build_touch_control_table(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"] == "TOUCH_WITHOUT_BREACH"]
    tables = []
    for H in HORIZONS:
        for b in BARRIERS:
            t = _rate_table(df, ["instrument", "level_type", "side", "touch_sub"], horizon=H, barrier=b)
            t["horizon_min"], t["barrier"] = H, b
            tables.append(t)
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def build_delayed_failure_table(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"] == "DELAYED_FAILURE_CONTROL"]
    tables = []
    for H in HORIZONS:
        for b in BARRIERS:
            t = _rate_table(df, ["instrument", "level_type", "side"], horizon=H, barrier=b)
            t["horizon_min"], t["barrier"] = H, b
            tables.append(t)
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def build_volume_table(events_df: pd.DataFrame, horizon=15, barrier=0.50) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"].isin(PRIMARY_CLASSES) & events_df["volume_stratum"].notna()]
    return _rate_table(df, ["instrument", "level_type", "side", "volume_stratum"], horizon=horizon, barrier=barrier)


def build_previous_test_table(events_df: pd.DataFrame, horizon=15, barrier=0.50) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"].isin(PRIMARY_CLASSES)]
    return _rate_table(df, ["instrument", "level_type", "side", "prior_test_category"], horizon=horizon, barrier=barrier)


def build_cross_market_table(events_df: pd.DataFrame, horizon=15, barrier=0.50) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"].isin(PRIMARY_CLASSES)]
    return _rate_table(df, ["instrument", "level_type", "side", "confirmation"], horizon=horizon, barrier=barrier)


def build_failure_delay_table(events_df: pd.DataFrame, horizon=15, barrier=0.50) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"].isin(PRIMARY_CLASSES)]
    return _rate_table(df, ["instrument", "level_type", "side", "event_class"], horizon=horizon, barrier=barrier)


def build_breach_magnitude_table(events_df: pd.DataFrame, horizon=15, barrier=0.50) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"].isin(PRIMARY_CLASSES) & events_df["breach_magnitude_band"].notna()]
    return _rate_table(df, ["instrument", "level_type", "side", "breach_magnitude_band"], horizon=horizon, barrier=barrier)


def build_same_bar_table(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"].isin(PRIMARY_CLASSES + ("SUCCESSFUL_BREACH_CONTROL",))]
    rows = []
    for gvals, g in df.groupby(["instrument", "level_type", "side", "event_class"]):
        vc = g["same_bar_morphology"].value_counts()
        n = len(g)
        rows.append({
            "instrument": gvals[0], "level_type": gvals[1], "side": gvals[2], "event_class": gvals[3],
            "n": n, "failure_proxy_rate": vc.get("FAILURE_PROXY", 0) / n if n else np.nan,
            "outside_close_proxy_rate": vc.get("OUTSIDE_CLOSE_PROXY", 0) / n if n else np.nan,
            "neutral_rate": vc.get("NEUTRAL", 0) / n if n else np.nan,
        })
    return pd.DataFrame(rows)
