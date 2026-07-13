"""Primary-family BH correction, year stability, cell classification, and
coherent-mechanism rollup for Module A and Module B.
See SPEC_TEN_AM_BLOCKS.md sections 11-13.
"""
import numpy as np
import pandas as pd

from .module_a import HORIZONS as HORIZONS_A
from .module_b import HORIZONS as HORIZONS_B, ACTIVATION_WINDOWS
from .summary import binom_p, benjamini_hochberg

PRIMARY_HORIZON = 15
PRIMARY_BARRIER = 0.50
MIN_OBS = 50
MIN_NONTIED = 20
MIN_EFFECT_PP = 5.0
YEARS = (2018, 2019, 2020, 2021, 2022)
HORIZON_ORDER_A = {h: i for i, h in enumerate(HORIZONS_A)}
HORIZON_ORDER_B = {h: i for i, h in enumerate(HORIZONS_B)}
WINDOW_ORDER = {w: i for i, w in enumerate(ACTIVATION_WINDOWS)}


# ---------- Module A ----------

def module_a_all_horizon_cells(events_a: pd.DataFrame) -> pd.DataFrame:
    """instrument x candle_state x horizon, barrier=0.50, all horizons."""
    rows = []
    dir_events = events_a.loc[events_a["directional"]]
    for (instrument, state), g in dir_events.groupby(["instrument", "candle_state"]):
        for H in HORIZONS_A:
            col = f"b{PRIMARY_BARRIER}_h{H}_outcome"
            vc = g[col].value_counts()
            n_cont = int(vc.get("CONTINUATION_FIRST", 0))
            n_rev = int(vc.get("REVERSAL_FIRST", 0))
            n_nontied = n_cont + n_rev
            n_obs = len(g)
            valid_h = g.loc[g[f"horizon_{H}_complete"]]
            med_signed = float(valid_h[f"signed_close_atr_h{H}"].median()) if len(valid_h) else np.nan
            rows.append({
                "instrument": instrument, "candle_state": state, "horizon_min": H,
                "n_observations": n_obs, "n_nontied": n_nontied,
                "cont_minus_rev_first_rate": (n_cont - n_rev) / n_obs if n_obs else np.nan,
                "median_signed_close_atr": med_signed,
                "binom_p": binom_p(n_cont, n_nontied) if n_nontied else np.nan,
                "is_primary": H == PRIMARY_HORIZON,
            })
    return pd.DataFrame(rows)


def apply_bh_module_a(cells: pd.DataFrame) -> pd.DataFrame:
    cells = cells.copy()
    cells["q_value"] = np.nan
    for instrument, idx in cells.groupby("instrument").groups.items():
        sub = cells.loc[idx]
        adj, _ = benjamini_hochberg(sub["binom_p"].to_numpy())
        cells.loc[idx, "q_value"] = adj
    return cells


def module_a_year_stability(events_a: pd.DataFrame) -> pd.DataFrame:
    rows = []
    dir_events = events_a.loc[events_a["directional"]]
    for (instrument, state), g in dir_events.groupby(["instrument", "candle_state"]):
        for H in HORIZONS_A:
            for year in YEARS:
                gy = g.loc[g["year"] == year]
                n = len(gy)
                col = f"b{PRIMARY_BARRIER}_h{H}_outcome"
                n_cont = n_rev = 0
                if n and col in gy.columns:
                    vc = gy[col].value_counts()
                    n_cont = int(vc.get("CONTINUATION_FIRST", 0))
                    n_rev = int(vc.get("REVERSAL_FIRST", 0))
                valid_h = gy.loc[gy[f"horizon_{H}_complete"]] if n else gy
                med_signed = float(valid_h[f"signed_close_atr_h{H}"].median()) if len(valid_h) else np.nan
                rows.append({
                    "instrument": instrument, "candle_state": state, "horizon_min": H, "year": year,
                    "n_observations": n, "cont_minus_rev_first_rate": (n_cont - n_rev) / n if n else np.nan,
                    "median_signed_close_atr": med_signed,
                    "sign": np.sign(med_signed) if pd.notna(med_signed) else np.nan,
                })
    return pd.DataFrame(rows)


def _year_flags(yr_sub: pd.DataFrame) -> dict:
    signs = yr_sub["sign"].dropna()
    n_years_10 = int((yr_sub["n_observations"] >= 10).sum())
    agree = 0
    if len(signs) > 0:
        mode_sign = signs.mode()
        if len(mode_sign):
            agree = int((signs == mode_sign.iloc[0]).sum())
    return {"n_years_ge10": n_years_10, "max_year_sign_agreement": agree}


def classify_module_a(cells: pd.DataFrame, yr: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, row in cells.iterrows():
        n_obs, n_nontied = row["n_observations"], row["n_nontied"]
        yr_sub = yr.loc[
            (yr["instrument"] == row["instrument"]) & (yr["candle_state"] == row["candle_state"])
            & (yr["horizon_min"] == row["horizon_min"])
        ]
        flags = _year_flags(yr_sub) if len(yr_sub) else {"n_years_ge10": 0, "max_year_sign_agreement": 0}
        min_sample = n_obs >= MIN_OBS and n_nontied >= MIN_NONTIED
        effect_pp = row["cont_minus_rev_first_rate"] * 100 if pd.notna(row["cont_minus_rev_first_rate"]) else np.nan
        effect_ok = pd.notna(effect_pp) and abs(effect_pp) >= MIN_EFFECT_PP
        q_ok = pd.notna(row["q_value"]) and row["q_value"] < 0.05
        sign_matches = (
            pd.notna(row["median_signed_close_atr"]) and pd.notna(effect_pp) and effect_pp != 0
            and np.sign(row["median_signed_close_atr"]) == np.sign(effect_pp)
        )
        year_ok = flags["max_year_sign_agreement"] >= 4
        if not min_sample:
            label = "UNDERPOWERED"
        elif effect_ok and q_ok and sign_matches and year_ok:
            label = "TEN_AM_CONTINUATION" if effect_pp > 0 else "TEN_AM_REVERSAL"
        else:
            label = "TEN_AM_MIXED_OR_NULL"
        d = row.to_dict()
        d.update(flags)
        d["effect_pp"] = effect_pp
        d["classification"] = label
        out.append(d)
    return pd.DataFrame(out)


# ---------- Module B ----------

def module_b_primary_style_cells(events_b: pd.DataFrame) -> pd.DataFrame:
    """instrument x side x freshness x activation_window x horizon,
    barrier=0.50, APPROACH_SIDE opens only."""
    rows = []
    ge = events_b.loc[events_b["open_location"] == "APPROACH_SIDE"]
    for (instrument, side, fresh), g in ge.groupby(["instrument", "side", "freshness"]):
        for window in ACTIVATION_WINDOWS:
            gw = g.loc[g[window]]
            for H in HORIZONS_B:
                col = f"b{PRIMARY_BARRIER}_h{H}_outcome"
                vc = gw[col].value_counts()
                n_rev = int(vc.get("REVERSAL_FIRST", 0))
                n_brk = int(vc.get("BREAKTHROUGH_FIRST", 0))
                n_nontied = n_rev + n_brk
                n_obs = len(gw)
                valid_h = gw.loc[gw[f"horizon_{H}_complete"]]
                med_signed = float(valid_h[f"signed_close_atr_h{H}"].median()) if len(valid_h) else np.nan
                rows.append({
                    "instrument": instrument, "side": side, "freshness": fresh,
                    "activation_window": window, "horizon_min": H,
                    "n_observations": n_obs, "n_nontied": n_nontied,
                    "rev_minus_brk_first_rate": (n_rev - n_brk) / n_obs if n_obs else np.nan,
                    "median_signed_close_atr": med_signed,
                    "binom_p": binom_p(n_rev, n_nontied) if n_nontied else np.nan,
                    "is_primary": (H == PRIMARY_HORIZON and window == "WITHIN_30MIN"),
                })
    return pd.DataFrame(rows)


def apply_bh_module_b(cells: pd.DataFrame) -> pd.DataFrame:
    cells = cells.copy()
    cells["q_value"] = np.nan
    for instrument, idx in cells.groupby("instrument").groups.items():
        sub = cells.loc[idx]
        adj, _ = benjamini_hochberg(sub["binom_p"].to_numpy())
        cells.loc[idx, "q_value"] = adj
    return cells


def module_b_year_stability(events_b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ge = events_b.loc[events_b["open_location"] == "APPROACH_SIDE"]
    for (instrument, side, fresh), g in ge.groupby(["instrument", "side", "freshness"]):
        for window in ACTIVATION_WINDOWS:
            gw = g.loc[g[window]]
            for H in HORIZONS_B:
                for year in YEARS:
                    gy = gw.loc[gw["year"] == year]
                    n = len(gy)
                    col = f"b{PRIMARY_BARRIER}_h{H}_outcome"
                    n_rev = n_brk = 0
                    if n and col in gy.columns:
                        vc = gy[col].value_counts()
                        n_rev = int(vc.get("REVERSAL_FIRST", 0))
                        n_brk = int(vc.get("BREAKTHROUGH_FIRST", 0))
                    valid_h = gy.loc[gy[f"horizon_{H}_complete"]] if n else gy
                    med_signed = float(valid_h[f"signed_close_atr_h{H}"].median()) if len(valid_h) else np.nan
                    same_bar_rev = float((gy["same_bar_morphology"] == "REVERSAL_PROXY").mean()) if n else np.nan
                    same_bar_brk = float((gy["same_bar_morphology"] == "BREAKTHROUGH_PROXY").mean()) if n else np.nan
                    rows.append({
                        "instrument": instrument, "side": side, "freshness": fresh,
                        "activation_window": window, "horizon_min": H, "year": year,
                        "n_observations": n, "rev_minus_brk_first_rate": (n_rev - n_brk) / n if n else np.nan,
                        "median_signed_close_atr": med_signed,
                        "same_bar_reversal_rate": same_bar_rev, "same_bar_breakthrough_rate": same_bar_brk,
                        "sign": np.sign(med_signed) if pd.notna(med_signed) else np.nan,
                    })
    return pd.DataFrame(rows)


def classify_module_b(cells: pd.DataFrame, yr: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, row in cells.iterrows():
        n_obs, n_nontied = row["n_observations"], row["n_nontied"]
        yr_sub = yr.loc[
            (yr["instrument"] == row["instrument"]) & (yr["side"] == row["side"])
            & (yr["freshness"] == row["freshness"]) & (yr["activation_window"] == row["activation_window"])
            & (yr["horizon_min"] == row["horizon_min"])
        ]
        flags = _year_flags(yr_sub) if len(yr_sub) else {"n_years_ge10": 0, "max_year_sign_agreement": 0}
        min_sample = n_obs >= MIN_OBS and n_nontied >= MIN_NONTIED
        effect_pp = row["rev_minus_brk_first_rate"] * 100 if pd.notna(row["rev_minus_brk_first_rate"]) else np.nan
        effect_ok = pd.notna(effect_pp) and abs(effect_pp) >= MIN_EFFECT_PP
        q_ok = pd.notna(row["q_value"]) and row["q_value"] < 0.05
        sign_matches = (
            pd.notna(row["median_signed_close_atr"]) and pd.notna(effect_pp) and effect_pp != 0
            and np.sign(row["median_signed_close_atr"]) == np.sign(effect_pp)
        )
        year_ok = flags["max_year_sign_agreement"] >= 4
        if not min_sample:
            label = "UNDERPOWERED"
        elif effect_ok and q_ok and sign_matches and year_ok:
            label = "REJECTION_BLOCK_REVERSAL_DOMINANT" if effect_pp > 0 else "REJECTION_BLOCK_BREAKTHROUGH_DOMINANT"
        else:
            label = "MIXED_OR_NULL"
        d = row.to_dict()
        d.update(flags)
        d["effect_pp"] = effect_pp
        d["classification"] = label
        out.append(d)
    return pd.DataFrame(out)


# ---------- coherent-mechanism rollup ----------

def coherent_mechanism_a(classified_a: pd.DataFrame) -> pd.DataFrame:
    rows = []
    directional = {"TEN_AM_CONTINUATION", "TEN_AM_REVERSAL"}
    for (instrument, state), g in classified_a.groupby(["instrument", "candle_state"]):
        label = "NO_COHERENT_MECHANISM"
        for direction in ("TEN_AM_CONTINUATION", "TEN_AM_REVERSAL"):
            dd = g.loc[g["classification"] == direction]
            if dd.empty:
                continue
            horizons_here = sorted(dd["horizon_min"].unique(), key=lambda h: HORIZON_ORDER_A[h])
            adj = any(
                HORIZON_ORDER_A[horizons_here[k + 1]] - HORIZON_ORDER_A[horizons_here[k]] == 1
                for k in range(len(horizons_here) - 1)
            )
            if adj and (dd["max_year_sign_agreement"] >= 4).any():
                label = direction
                break
        rows.append({"instrument": instrument, "candle_state": state, "mechanism": label})
    return pd.DataFrame(rows)


def coherent_mechanism_b(classified_b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (instrument, side, fresh), g in classified_b.groupby(["instrument", "side", "freshness"]):
        label = "NO_COHERENT_MECHANISM"
        for direction, name in (
            ("REJECTION_BLOCK_REVERSAL_DOMINANT", "REVERSAL_DOMINANT"),
            ("REJECTION_BLOCK_BREAKTHROUGH_DOMINANT", "BREAKTHROUGH_DOMINANT"),
        ):
            dd = g.loc[g["classification"] == direction]
            if dd.empty:
                continue
            found = False
            for window in dd["activation_window"].unique():
                dw = dd.loc[dd["activation_window"] == window]
                horizons_here = sorted(dw["horizon_min"].unique(), key=lambda h: HORIZON_ORDER_B[h])
                adj_h = any(
                    HORIZON_ORDER_B[horizons_here[k + 1]] - HORIZON_ORDER_B[horizons_here[k]] == 1
                    for k in range(len(horizons_here) - 1)
                )
                if not adj_h:
                    continue
                if window == "WITHIN_10AM_CANDLE":
                    if (dw["max_year_sign_agreement"] >= 4).any():
                        found = True
                        break
                    continue
                windows_here = sorted(dd["activation_window"].unique(), key=lambda w: WINDOW_ORDER[w])
                adj_w = any(
                    WINDOW_ORDER[windows_here[k + 1]] - WINDOW_ORDER[windows_here[k]] == 1
                    for k in range(len(windows_here) - 1)
                )
                if adj_w and (dd["max_year_sign_agreement"] >= 4).any():
                    found = True
                    break
            if found:
                label = name
                break
        rows.append({"instrument": instrument, "side": side, "freshness": fresh, "mechanism": label})
    return pd.DataFrame(rows)
