"""Secondary/exploratory outcome grid. Every cell reported, including
nulls; Benjamini-Hochberg within each (instrument, outcome_name, horizon)
family across the 38 level_ids. Never promoted to a confirmatory finding.
"""
import numpy as np
import pandas as pd
from scipy import stats

from . import families as fam

CONTINUOUS_OUTCOMES = ("D_h", "MFE_h", "MAE_h", "Q_h")
SECONDARY_HORIZONS = (1, 3, 5, 10, 15)


def unpaired_continuous_grid(outcomes_tbl: pd.DataFrame, all_instruments, all_level_ids) -> pd.DataFrame:
    """Unpaired real-vs-synthetic Mann-Whitney U per (instrument, level_id,
    outcome_name, horizon), using all normalized-eligible touched events
    (not restricted to isolated/paired). Reports every cell including
    nulls (insufficient sample -> status='insufficient_sample')."""
    rows = []
    grp = outcomes_tbl.dropna(subset=["D_h"]).groupby(["instrument", "level_id", "arm"])
    for outcome in CONTINUOUS_OUTCOMES:
        for instrument in all_instruments:
            for level_id in all_level_ids:
                for h in SECONDARY_HORIZONS:
                    sub = outcomes_tbl[(outcomes_tbl["instrument"] == instrument)
                                       & (outcomes_tbl["level_id"] == level_id)
                                       & (outcomes_tbl["horizon"] == h)]
                    real_vals = sub[sub["arm"] == "REAL"][outcome].dropna().to_numpy()
                    synth_vals = sub[sub["arm"] == "SYNTHETIC"][outcome].dropna().to_numpy()
                    row = {"instrument": instrument, "level_id": level_id,
                          "outcome_name": outcome, "horizon": h,
                          "n_real": len(real_vals), "n_synth": len(synth_vals)}
                    if len(real_vals) < 20 or len(synth_vals) < 20:
                        row["status"] = "insufficient_sample"
                        row["p_raw"] = np.nan
                    else:
                        try:
                            _, p = stats.mannwhitneyu(real_vals, synth_vals, alternative="two-sided")
                        except ValueError:
                            p = np.nan
                        row["status"] = "tested"
                        row["p_raw"] = p
                        row["median_real"] = float(np.median(real_vals))
                        row["median_synth"] = float(np.median(synth_vals))
                    rows.append(row)
    out = pd.DataFrame(rows)
    out = fam.secondary_bh(out, "p_raw", group_cols=("instrument", "outcome_name", "horizon"))
    return out


def binary_outcome_grid(outcomes_tbl: pd.DataFrame, col: str, outcome_name: str,
                        all_instruments, all_level_ids) -> pd.DataFrame:
    """Fisher exact test on a binary post-touch outcome (post_touch_retouch,
    directional_close_recross), real vs synthetic, per (instrument,
    level_id, horizon)."""
    rows = []
    for instrument in all_instruments:
        for level_id in all_level_ids:
            for h in SECONDARY_HORIZONS:
                sub = outcomes_tbl[(outcomes_tbl["instrument"] == instrument)
                                   & (outcomes_tbl["level_id"] == level_id)
                                   & (outcomes_tbl["horizon"] == h)]
                real = sub[sub["arm"] == "REAL"][col].dropna()
                synth = sub[sub["arm"] == "SYNTHETIC"][col].dropna()
                row = {"instrument": instrument, "level_id": level_id,
                      "outcome_name": outcome_name, "horizon": h,
                      "n_real": len(real), "n_synth": len(synth)}
                if len(real) < 20 or len(synth) < 20:
                    row["status"] = "insufficient_sample"
                    row["p_raw"] = np.nan
                else:
                    a = int(real.sum()); b = len(real) - a
                    c = int(synth.sum()); d = len(synth) - c
                    _, p = stats.fisher_exact([[a, b], [c, d]])
                    row["status"] = "tested"
                    row["p_raw"] = p
                    row["real_rate"] = a / len(real)
                    row["synth_rate"] = c / len(synth)
                rows.append(row)
    out = pd.DataFrame(rows)
    out = fam.secondary_bh(out, "p_raw", group_cols=("instrument", "outcome_name", "horizon"))
    return out


def barrier_reach_grid(barriers_tbl: pd.DataFrame, all_instruments, all_level_ids,
                       horizons=SECONDARY_HORIZONS, ks=(0.5, 1.0, 1.5, 2.0)) -> pd.DataFrame:
    rows = []
    for instrument in all_instruments:
        for level_id in all_level_ids:
            for h in horizons:
                for k in ks:
                    sub = barriers_tbl[(barriers_tbl["instrument"] == instrument)
                                       & (barriers_tbl["level_id"] == level_id)
                                       & (barriers_tbl["horizon"] == h) & (barriers_tbl["k"] == k)]
                    real = sub[sub["arm"] == "REAL"]
                    synth = sub[sub["arm"] == "SYNTHETIC"]
                    row = {"instrument": instrument, "level_id": level_id, "horizon": h, "k": k,
                          "n_real": len(real), "n_synth": len(synth)}
                    if len(real) < 20 or len(synth) < 20:
                        row["status"] = "insufficient_sample"
                    else:
                        row["status"] = "tested"
                        row["real_reach_continuation_rate"] = real["reach_continuation"].mean()
                        row["synth_reach_continuation_rate"] = synth["reach_continuation"].mean()
                        row["real_reach_rejection_rate"] = real["reach_rejection"].mean()
                        row["synth_reach_rejection_rate"] = synth["reach_rejection"].mean()
                        row["real_barrier_order_dist"] = real["barrier_order"].value_counts().to_dict()
                        row["synth_barrier_order_dist"] = synth["barrier_order"].value_counts().to_dict()
                    rows.append(row)
    return pd.DataFrame(rows)


def year_stability(levels_tbl: pd.DataFrame, outcomes_tbl: pd.DataFrame,
                   family_b_pairs: pd.DataFrame) -> pd.DataFrame:
    lt = levels_tbl.copy()
    lt["year"] = pd.to_datetime(lt["session_date"]).dt.year
    rows = []
    for (instrument, level_id, year), g in lt.groupby(["instrument", "level_id", "year"]):
        mutual = g[g["mutually_touch_eligible"]]
        n_elig = len(mutual)
        real_rate = mutual["real_touched"].mean() if n_elig else np.nan
        synth_rate = mutual["synthetic_touched"].mean() if n_elig else np.nan
        n_real_only = int((mutual["real_touched"] & ~mutual["synthetic_touched"]).sum()) if n_elig else 0
        n_synth_only = int((~mutual["real_touched"] & mutual["synthetic_touched"]).sum()) if n_elig else 0

        d5 = outcomes_tbl[(outcomes_tbl["instrument"] == instrument) & (outcomes_tbl["level_id"] == level_id)
                          & (outcomes_tbl["horizon"] == 5)
                          & (pd.to_datetime(outcomes_tbl["session_date"]).dt.year == year)]
        med_real_d5 = d5[d5["arm"] == "REAL"]["D_h"].median()
        med_synth_d5 = d5[d5["arm"] == "SYNTHETIC"]["D_h"].median()

        fb = family_b_pairs[(family_b_pairs["instrument"] == instrument) & (family_b_pairs["level_id"] == level_id)
                            & (pd.to_datetime(family_b_pairs["session_date"]).dt.year == year)] if len(family_b_pairs) else family_b_pairs
        n_pairs = len(fb)
        med_paired_diff = (fb["D5_real"] - fb["D5_synthetic"]).median() if n_pairs else np.nan

        rows.append({"instrument": instrument, "level_id": level_id, "year": year,
                    "n_eligible_sessions": n_elig, "real_touch_rate": real_rate,
                    "synth_touch_rate": synth_rate, "n_real_only": n_real_only,
                    "n_synth_only": n_synth_only, "n_family_b_pairs": n_pairs,
                    "median_D5_real": med_real_d5, "median_D5_synth": med_synth_d5,
                    "median_paired_D5_diff": med_paired_diff})
    return pd.DataFrame(rows)
