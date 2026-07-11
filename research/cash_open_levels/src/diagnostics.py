"""Diagnostics for the generation-7 level library: level counts,
missingness, structural duplicates, empirical clustering, coverage,
overlap. No touch/reaction/return/outcome computation anywhere here.
"""
import numpy as np
import pandas as pd

from .levels import CLUSTER_THRESHOLD_FRAC


def level_counts(long_df: pd.DataFrame) -> pd.DataFrame:
    g = long_df.groupby(["instrument", "family", "level_id"])
    out = g["value"].apply(lambda s: int(s.notna().sum())).rename("n_valid").reset_index()
    total = long_df.groupby(["instrument", "family", "level_id"])["value"].size().rename("n_total")
    out = out.merge(total.reset_index(), on=["instrument", "family", "level_id"])
    return out


def missingness_reason(family: str) -> str:
    return {
        "family1": "60-session warm-up (exact-window causal scale invalid)",
        "family2": "<30 valid overnight bars",
        "family3": "predecessor session was an early close (or no predecessor)",
        "family4": "no overnight bars (raw levels) / <30 overnight bars (VWAP-deviation fields)",
    }[family]


def missingness_table(long_df: pd.DataFrame) -> pd.DataFrame:
    g = long_df.groupby(["instrument", "family"])
    rows = []
    for (instr, fam), d in g:
        n_total = len(d)
        n_missing = int(d["value"].isna().sum())
        rows.append({"instrument": instr, "family": fam, "n_total": n_total,
                    "n_missing": n_missing,
                    "missing_frac": n_missing / n_total if n_total else np.nan,
                    "reason": missingness_reason(fam)})
    return pd.DataFrame(rows)


def structural_duplicates(fam1: pd.DataFrame) -> pd.DataFrame:
    """Confirms mult_U_1.0/mult_D_1.0 == the trailing p50 quantile level
    (bit-for-bit, since scale_U/scale_D ARE the trailing median) and
    reports it once with both aliases, per instrument-level frame."""
    valid = fam1[["mult_U_1.0", "scale_U"]].dropna()
    quantile_equiv_U = valid["mult_U_1.0"] - (fam1.loc[valid.index, "open"] + fam1.loc[valid.index, "scale_U"])
    valid_d = fam1[["mult_D_1.0", "scale_D"]].dropna()
    quantile_equiv_D = valid_d["mult_D_1.0"] - (fam1.loc[valid_d.index, "open"] - fam1.loc[valid_d.index, "scale_D"])
    return pd.DataFrame([
        {"level_id": "mult_U_1.0", "alias": "quantile_p50_U",
         "n_checked": len(valid), "max_abs_diff": float(quantile_equiv_U.abs().max()) if len(valid) else np.nan,
         "is_structural_duplicate": bool(len(valid) and quantile_equiv_U.abs().max() < 1e-9)},
        {"level_id": "mult_D_1.0", "alias": "quantile_p50_D",
         "n_checked": len(valid_d), "max_abs_diff": float(quantile_equiv_D.abs().max()) if len(valid_d) else np.nan,
         "is_structural_duplicate": bool(len(valid_d) and quantile_equiv_D.abs().max() < 1e-9)},
    ])


def empirical_clustering(long_df: pd.DataFrame) -> pd.DataFrame:
    """Per-session pairwise clustering of distinct (non structurally
    duplicate) levels: |value_a - value_b| < 0.1 * scale, side-appropriate
    scale (average of scale_U/scale_D for cross-side/neutral pairs)."""
    rows = []
    scale_lookup = long_df.drop_duplicates(["instrument", "session_date"])[
        ["instrument", "session_date"]].copy()
    for (instr, sd), d in long_df.dropna(subset=["value"]).groupby(["instrument", "session_date"]):
        levels = d[["level_id", "family", "side", "value"]].drop_duplicates("level_id").reset_index(drop=True)
        n = len(levels)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = levels.iloc[i], levels.iloc[j]
                rows.append({"instrument": instr, "session_date": sd,
                            "level_a": a["level_id"], "level_b": b["level_id"],
                            "family_a": a["family"], "family_b": b["family"],
                            "diff": abs(a["value"] - b["value"])})
    if not rows:
        return pd.DataFrame(columns=["instrument", "session_date", "level_a", "level_b",
                                     "family_a", "family_b", "diff", "clustered"])
    pairs = pd.DataFrame(rows)
    return pairs


def empirical_clustering_flagged(long_df: pd.DataFrame, fam1: pd.DataFrame) -> pd.DataFrame:
    pairs = empirical_clustering(long_df)
    if pairs.empty:
        pairs["clustered"] = pd.Series(dtype=bool)
        return pairs
    avg_scale = (fam1["scale_U"] + fam1["scale_D"]) / 2.0
    scale_vals = avg_scale.reindex(pairs["session_date"]).to_numpy()
    pairs["scale_used"] = scale_vals
    pairs["clustered"] = pairs["diff"] < CLUSTER_THRESHOLD_FRAC * pairs["scale_used"]
    return pairs


def clustering_summary(pairs: pd.DataFrame) -> pd.DataFrame:
    if pairs.empty:
        return pd.DataFrame(columns=["instrument", "family_a", "family_b", "n_pairs", "n_clustered", "clustered_rate"])
    g = pairs.groupby(["instrument", "family_a", "family_b"])
    out = g.agg(n_pairs=("clustered", "size"), n_clustered=("clustered", "sum")).reset_index()
    out["clustered_rate"] = out["n_clustered"] / out["n_pairs"]
    return out


def coverage_table(long_df: pd.DataFrame) -> pd.DataFrame:
    long_df = long_df.copy()
    long_df["year"] = pd.to_datetime(long_df["session_date"]).dt.year
    rows = []
    for (instr, year), d in long_df.groupby(["instrument", "year"]):
        sessions = d["session_date"].unique()
        n_sessions = len(sessions)
        per_family_valid = {}
        for fam in ["family1", "family2", "family3", "family4"]:
            fam_d = d[d["family"] == fam]
            valid_sessions = fam_d[fam_d["value"].notna()]["session_date"].unique()
            per_family_valid[fam] = set(valid_sessions)
        all_families_valid = set.intersection(*per_family_valid.values()) if per_family_valid else set()
        row = {"instrument": instr, "year": year, "n_sessions": n_sessions,
              "n_all_families_valid": len(all_families_valid)}
        for fam, s in per_family_valid.items():
            row[f"n_{fam}_valid"] = len(s)
        rows.append(row)
    return pd.DataFrame(rows)


def overlap_per_session(pairs: pd.DataFrame) -> pd.DataFrame:
    """Session-level 'crowdedness': count of clustered pairs per session."""
    if pairs.empty:
        return pd.DataFrame(columns=["instrument", "session_date", "n_clustered_pairs"])
    g = pairs.groupby(["instrument", "session_date"])["clustered"].sum().rename("n_clustered_pairs").reset_index()
    return g
