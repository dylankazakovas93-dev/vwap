"""Coherence (timing-region) classification and same-bar classification
-- SPEC_EXCURSION_TIMING.md secs 17-18. Adjacency defined on the frozen,
ordered activation-window/horizon ladders (DECISIONS.md #9-12).
"""
import numpy as np
import pandas as pd

from . import interactions as ix
from . import stats as st

A_LIST = list(ix.ACTIVATION_WINDOWS)
H_LIST = list(ix.HORIZONS)
MIN_YEARS_SIGN = 4


def _adjacent_pairs(values):
    return set(zip(values[:-1], values[1:]))


def _has_adjacent_support(qualifying_values, full_ordered_list):
    present = sorted(set(qualifying_values), key=lambda x: full_ordered_list.index(x))
    idx_present = [full_ordered_list.index(v) for v in present]
    idx_set = set(idx_present)
    for i in idx_present:
        if (i + 1) in idx_set:
            return True
    return False


def classify_timing_region(surface: pd.DataFrame, year_stability_fn) -> pd.DataFrame:
    """surface: output of stats.timing_surface. year_stability_fn(A, H) ->
    stats.year_stability(...) result for that specific cell (memoized by
    caller for efficiency)."""
    rows = []
    for (instrument, level_id), g in surface.groupby(["instrument", "level_id"]):
        best = None
        for direction, sign in (("continuation", 1), ("reversal", -1)):
            qualifying = g[
                (g["q_value"] < st.BH_ALPHA)
                & (g["cont_minus_rev_diff"].abs() >= 0.05)
                & (np.sign(g["cont_minus_rev_diff"]) == sign)
                & (np.sign(g["median_signed_close_sd"]) == sign)
                & (g["n_touch_in_A"] >= st.MIN_TOUCH_EVENTS)
                & (g["n_nontied"] >= st.MIN_NONTIED_BARRIER)
            ]
            if len(qualifying) == 0:
                continue

            a_ok = _has_adjacent_support(qualifying["activation_window"].tolist(), A_LIST)
            h_ok = _has_adjacent_support(qualifying["horizon"].tolist(), H_LIST)

            anchor = qualifying.sort_values("activation_window").iloc[0]
            anchor_A, anchor_H = int(anchor["activation_window"]), int(anchor["horizon"])
            yrs = year_stability_fn(anchor_A, anchor_H)
            yrs_row = yrs[(yrs.instrument == instrument) & (yrs.level_id == level_id)]
            year_ok = False
            if len(yrs_row):
                n_same = yrs_row.iloc[0]["n_years_with_pooled_sign"]
                mean_eff = yrs_row.iloc[0]["mean_annual_effect"]
                year_ok = bool(n_same >= MIN_YEARS_SIGN and np.isfinite(mean_eff) and np.sign(mean_eff) == sign)

            coherent = a_ok and h_ok and year_ok
            n_isolated = len(qualifying)

            candidate = {
                "instrument": instrument, "level_id": level_id, "direction": direction,
                "n_qualifying_cells": n_isolated, "adjacent_activation_ok": a_ok,
                "adjacent_horizon_ok": h_ok, "year_sign_ok": year_ok,
                "anchor_activation_window": anchor_A, "anchor_horizon": anchor_H,
                "coherent": coherent,
            }
            if best is None or (candidate["coherent"] and not best.get("coherent")):
                best = candidate

        n_total_cells = len(g)
        n_tested = int((g["sample_status"] == "tested").sum())
        if best is None:
            cls = "UNDERPOWERED" if n_tested == 0 else "MIXED_OR_NULL"
            rows.append({"instrument": instrument, "level_id": level_id, "classification": cls,
                        "direction": None, "anchor_activation_window": None, "anchor_horizon": None,
                        "n_qualifying_cells": 0})
            continue

        if best["coherent"]:
            is_open = best["anchor_activation_window"] <= 30
            if best["direction"] == "continuation":
                cls = "COHERENT_OPEN_CONTINUATION" if is_open else "LATE_MORNING_CONTINUATION_ONLY"
            else:
                cls = "COHERENT_OPEN_REVERSAL" if is_open else "LATE_MORNING_REVERSAL_ONLY"
        else:
            cls = "ISOLATED_SIGNIFICANT_CELL"
        rows.append({"instrument": instrument, "level_id": level_id, "classification": cls,
                    "direction": best["direction"], "anchor_activation_window": best["anchor_activation_window"],
                    "anchor_horizon": best["anchor_horizon"], "n_qualifying_cells": best["n_qualifying_cells"]})
    return pd.DataFrame(rows)


def classify_same_bar(same_bar_surface: pd.DataFrame, year_stability_fn) -> pd.DataFrame:
    rows = []
    for (instrument, level_id), g in same_bar_surface.groupby(["instrument", "level_id"]):
        best = None
        for direction, sign in (("reversal", 1), ("blast_through", -1)):
            qualifying = g[
                (g["q_value"] < st.BH_ALPHA)
                & (g["same_bar_rev_minus_blast_diff"].abs() >= 0.05)
                & (np.sign(g["same_bar_rev_minus_blast_diff"]) == sign)
                & (g["n_nonneutral_samebar"] >= st.MIN_TOUCH_EVENTS)
            ]
            if len(qualifying) == 0:
                continue
            a_ok = _has_adjacent_support(qualifying["activation_window"].tolist(), A_LIST)
            anchor = qualifying.sort_values("activation_window").iloc[0]
            anchor_A = int(anchor["activation_window"])
            yrs = year_stability_fn(anchor_A, 30)
            yrs_row = yrs[(yrs.instrument == instrument) & (yrs.level_id == level_id)]
            year_ok = False
            if len(yrs_row):
                same_bar_effect = yrs_row["same_bar_reversal_rate"] - yrs_row["same_bar_blast_through_rate"]
                pooled_mean = same_bar_effect.mean()
                n_same = int((np.sign(same_bar_effect) == np.sign(pooled_mean)).sum()) if np.isfinite(pooled_mean) else 0
                year_ok = bool(n_same >= MIN_YEARS_SIGN and np.isfinite(pooled_mean) and np.sign(pooled_mean) == sign)
            coherent = a_ok and year_ok
            candidate = {"direction": direction, "coherent": coherent, "anchor_A": anchor_A,
                        "n_qualifying": len(qualifying)}
            if best is None or (candidate["coherent"] and not best.get("coherent")):
                best = candidate

        if best is None:
            n_tested = int((g["n_nonneutral_samebar"] >= st.MIN_TOUCH_EVENTS).sum())
            cls = "SAME_BAR_UNDERPOWERED" if n_tested == 0 else "SAME_BAR_MIXED"
            rows.append({"instrument": instrument, "level_id": level_id, "same_bar_classification": cls,
                        "direction": None, "anchor_activation_window": None, "n_qualifying_cells": 0})
            continue
        if best["coherent"]:
            cls = "SAME_BAR_REVERSAL_BIASED" if best["direction"] == "reversal" else "SAME_BAR_BLAST_THROUGH_BIASED"
        else:
            cls = "SAME_BAR_MIXED"
        rows.append({"instrument": instrument, "level_id": level_id, "same_bar_classification": cls,
                    "direction": best["direction"], "anchor_activation_window": best["anchor_A"],
                    "n_qualifying_cells": best["n_qualifying"]})
    return pd.DataFrame(rows)
