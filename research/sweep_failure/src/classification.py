"""Primary matched comparison (stratified permutation test), BH
correction, year stability, and cell classification.
See SPEC_SWEEP_FAILURE.md sections 17, 19-20.
"""
import numpy as np
import pandas as pd

from .outcomes import HORIZONS, PRIMARY_CLASSES
from .permutation import stratified_permutation_test
from .summary import TIME_STRATA

# --- Benjamini-Hochberg (local copy, same algorithm as prior generations) ---

def benjamini_hochberg(pvals, alpha=0.05):
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    out_adj = np.full(n, np.nan)
    out_rej = np.zeros(n, dtype=bool)
    idx = np.where(np.isfinite(p))[0]
    if len(idx) == 0:
        return out_adj, out_rej
    order = idx[np.argsort(p[idx])]
    m = len(order)
    prev = 1.0
    adj_sorted = np.empty(m)
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        val = min(p[i] * m / rank, prev)
        prev = val
        adj_sorted[rank - 1] = val
    for j, i in enumerate(order):
        out_adj[i] = adj_sorted[j]
    out_rej[idx] = out_adj[idx] < alpha
    return out_adj, out_rej


YEARS = (2018, 2019, 2020, 2021, 2022)
COMPARE_CLASSES = PRIMARY_CLASSES + ("SUCCESSFUL_BREACH_CONTROL",)
MIN_FAILED, MIN_SUCCESS, MIN_NONTIED_EACH = 100, 100, 50
MIN_EFFECT_PP = 5.0


def _label(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.loc[events_df["event_class"].isin(COMPARE_CLASSES)].copy()
    df["label"] = np.where(df["event_class"].isin(PRIMARY_CLASSES), "failed", "successful")
    df["stratum_key"] = df["breach_magnitude_band"].astype(str) + "|" + df["prior_test_category"].astype(str)
    df["year"] = pd.to_datetime(df["session_date"]).dt.year
    return df


def _horizon_direction(sub: pd.DataFrame, horizon: int) -> float:
    col = f"b0.5_h{horizon}_outcome"
    if col not in sub.columns:
        return np.nan
    nt = sub.loc[sub[col].isin(["ROTATION_FIRST", "BREAKOUT_FIRST"])]
    f = nt.loc[nt["label"] == "failed", col]
    s = nt.loc[nt["label"] == "successful", col]
    if len(f) == 0 or len(s) == 0:
        return np.nan
    return (f == "ROTATION_FIRST").mean() - (s == "ROTATION_FIRST").mean()


def primary_comparison(events_df: pd.DataFrame) -> pd.DataFrame:
    df = _label(events_df)
    rows = []
    for (instrument, level_type, side), g in df.groupby(["instrument", "level_type", "side"]):
        for stratum in TIME_STRATA:
            sub = g if stratum == "ALL_RTH" else g.loc[g["breach_time_stratum"] == stratum]
            n_failed = int((sub["label"] == "failed").sum())
            n_success = int((sub["label"] == "successful").sum())
            col15 = "b0.5_h15_outcome"
            nontied = sub.loc[sub[col15].isin(["ROTATION_FIRST", "BREAKOUT_FIRST"])] if col15 in sub.columns else sub.iloc[0:0]
            if len(nontied) and nontied["label"].nunique() == 2:
                perm = stratified_permutation_test(nontied, "label", col15, "stratum_key")
            else:
                perm = {"observed_diff": np.nan, "p_value": np.nan, "n_failed_nontied": 0,
                        "n_successful_nontied": 0, "rotation_rate_failed": np.nan,
                        "rotation_rate_successful": np.nan}
            med_failed = float(sub.loc[sub["label"] == "failed", "signed_close_atr_h15"].median()) if n_failed else np.nan
            med_success = float(sub.loc[sub["label"] == "successful", "signed_close_atr_h15"].median()) if n_success else np.nan
            dir10 = _horizon_direction(sub, 10)
            dir30 = _horizon_direction(sub, 30)
            dir15 = perm["rotation_rate_failed"] - perm["rotation_rate_successful"] if pd.notna(perm.get("rotation_rate_failed")) else np.nan

            rows.append({
                "instrument": instrument, "level_type": level_type, "side": side, "time_stratum": stratum,
                "n_failed": n_failed, "n_successful": n_success,
                "n_failed_nontied": perm["n_failed_nontied"], "n_successful_nontied": perm["n_successful_nontied"],
                "rotation_rate_failed": perm["rotation_rate_failed"], "rotation_rate_successful": perm["rotation_rate_successful"],
                "effect_pp": (perm["observed_diff"] * 100) if pd.notna(perm["observed_diff"]) else np.nan,
                "raw_p_value": perm["p_value"], "n_perms": perm.get("n_perms"), "seed": perm.get("seed"),
                "median_signed_close_atr_failed": med_failed, "median_signed_close_atr_successful": med_success,
                "median_signed_close_contrast": (med_failed - med_success) if (pd.notna(med_failed) and pd.notna(med_success)) else np.nan,
                "direction_h10": dir10, "direction_h15": dir15, "direction_h30": dir30,
            })
    return pd.DataFrame(rows)


def apply_bh_primary(pc: pd.DataFrame) -> pd.DataFrame:
    pc = pc.copy()
    adj, _ = benjamini_hochberg(pc["raw_p_value"].to_numpy())
    pc["q_value"] = adj
    return pc


def year_stability(events_df: pd.DataFrame) -> pd.DataFrame:
    df = _label(events_df)
    rows = []
    for (instrument, level_type, side), g in df.groupby(["instrument", "level_type", "side"]):
        for stratum in TIME_STRATA:
            sub = g if stratum == "ALL_RTH" else g.loc[g["breach_time_stratum"] == stratum]
            for year in YEARS:
                sy = sub.loc[sub["year"] == year]
                col15 = "b0.5_h15_outcome"
                n_failed = int((sy["label"] == "failed").sum())
                n_success = int((sy["label"] == "successful").sum())
                nt = sy.loc[sy[col15].isin(["ROTATION_FIRST", "BREAKOUT_FIRST"])] if col15 in sy.columns else sy.iloc[0:0]
                f = nt.loc[nt["label"] == "failed", col15]
                s = nt.loc[nt["label"] == "successful", col15]
                rot_f = (f == "ROTATION_FIRST").mean() if len(f) else np.nan
                rot_s = (s == "ROTATION_FIRST").mean() if len(s) else np.nan
                diff = rot_f - rot_s if (pd.notna(rot_f) and pd.notna(rot_s)) else np.nan
                med_f = float(sy.loc[sy["label"] == "failed", "signed_close_atr_h15"].median()) if n_failed else np.nan
                med_s = float(sy.loc[sy["label"] == "successful", "signed_close_atr_h15"].median()) if n_success else np.nan
                contrast = (med_f - med_s) if (pd.notna(med_f) and pd.notna(med_s)) else np.nan
                rows.append({
                    "instrument": instrument, "level_type": level_type, "side": side, "time_stratum": stratum,
                    "year": year, "n_failed": n_failed, "n_successful": n_success,
                    "rotation_first_rate_failed": rot_f, "rotation_first_rate_successful": rot_s,
                    "failed_minus_successful_rotation_rate": diff,
                    "median_signed_close_contrast": contrast,
                    "sign": np.sign(diff) if pd.notna(diff) else np.nan,
                })
    return pd.DataFrame(rows)


def _year_flags(yr_sub: pd.DataFrame) -> dict:
    signs = yr_sub["sign"].dropna()
    n_years_10 = int(((yr_sub["n_failed"] >= 10) & (yr_sub["n_successful"] >= 10)).sum())
    agree = 0
    if len(signs) > 0:
        mode_sign = signs.mode()
        if len(mode_sign):
            agree = int((signs == mode_sign.iloc[0]).sum())
    total_failed = yr_sub["n_failed"].sum()
    year_2020 = yr_sub.loc[yr_sub["year"] == 2020, "n_failed"].sum()
    conc_2020 = bool(total_failed > 0 and year_2020 / total_failed >= 0.5)
    one_year_dom = bool(total_failed > 0 and yr_sub["n_failed"].max() / total_failed >= 0.5)
    return {
        "n_years_ge10_each": n_years_10, "max_year_sign_agreement": agree,
        "year_2020_concentration": conc_2020, "one_year_dominance": one_year_dom,
    }


def classify_primary(pc: pd.DataFrame, yr: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, row in pc.iterrows():
        yr_sub = yr.loc[
            (yr["instrument"] == row["instrument"]) & (yr["level_type"] == row["level_type"])
            & (yr["side"] == row["side"]) & (yr["time_stratum"] == row["time_stratum"])
        ]
        flags = _year_flags(yr_sub) if len(yr_sub) else {
            "n_years_ge10_each": 0, "max_year_sign_agreement": 0,
            "year_2020_concentration": False, "one_year_dominance": False,
        }
        sample_ok = (
            row["n_failed"] >= MIN_FAILED and row["n_successful"] >= MIN_SUCCESS
            and row["n_failed_nontied"] >= MIN_NONTIED_EACH and row["n_successful_nontied"] >= MIN_NONTIED_EACH
        )
        effect_ok = pd.notna(row["effect_pp"]) and abs(row["effect_pp"]) >= MIN_EFFECT_PP
        q_ok = pd.notna(row["q_value"]) and row["q_value"] < 0.05
        sign_matches = (
            pd.notna(row["median_signed_close_contrast"]) and pd.notna(row["effect_pp"]) and row["effect_pp"] != 0
            and np.sign(row["median_signed_close_contrast"]) == np.sign(row["effect_pp"])
        )
        year_ok = flags["max_year_sign_agreement"] >= 4
        adj_horizon_ok = False
        for adj in ("direction_h10", "direction_h30"):
            v = row[adj]
            if pd.notna(v) and pd.notna(row["effect_pp"]) and np.sign(v) == np.sign(row["effect_pp"]) and v != 0:
                adj_horizon_ok = True
                break

        if not sample_ok:
            label = "UNDERPOWERED"
        elif effect_ok and q_ok and sign_matches and year_ok and adj_horizon_ok:
            label = "FAILED_BREACH_ROTATION_SUPPORTED" if row["effect_pp"] > 0 else "FAILED_BREACH_BREAKOUT_SUPPORTED"
        else:
            label = "MIXED_OR_NULL"

        d = row.to_dict()
        d.update(flags)
        d["sample_ok"] = sample_ok
        d["adj_horizon_ok"] = adj_horizon_ok
        d["classification"] = label
        out.append(d)
    return pd.DataFrame(out)
