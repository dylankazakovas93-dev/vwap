"""Primary matched comparison, BH correction, year stability, and cell
classification. See SPEC_UNSUPPORTED_MOVE.md sections 10-11.
"""
import numpy as np
import pandas as pd

from .permutation import stratified_permutation_test

YEARS = (2018, 2019, 2020, 2021, 2022)
MIN_EFFECT_PP = 5.0


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


def _label(events_out: pd.DataFrame) -> pd.DataFrame:
    df = events_out.loc[events_out["event_class"].isin(
        ("EXTREME_UNSUPPORTED_MOVE", "MODERATE_UNSUPPORTED_MOVE")
    )].copy()
    df["label"] = np.where(df["event_class"] == "EXTREME_UNSUPPORTED_MOVE", "extreme", "moderate")
    df["clock_hour"] = df["et_minute"].astype(int) // 60
    df["year"] = pd.to_datetime(df["session_date"]).dt.year
    df["resolved_nonambiguous_h15"] = df["outcome_h15"].isin(
        ("RESIDUAL_CLOSURE_FIRST", "RESIDUAL_EXPANSION_FIRST")
    )
    return df


def primary_comparison(events_out: pd.DataFrame) -> pd.DataFrame:
    df = _label(events_out)
    rows = []
    for (leg, leader, direction), g in df.groupby(["leg", "leader", "leader_direction"]):
        resolved = g.loc[g["resolved_nonambiguous_h15"]]
        n_extreme_raw = int((g["label"] == "extreme").sum())
        n_moderate_raw = int((g["label"] == "moderate").sum())
        n_ambiguous = int((g["outcome_h15"] == "SAME_BAR_AMBIGUOUS").sum())
        n_neither = int((g["outcome_h15"] == "NEITHER_WITHIN_HORIZON").sum())
        n_incomplete = int((g["outcome_h15"] == "INCOMPLETE_HORIZON").sum())
        if resolved["label"].nunique() == 2:
            perm = stratified_permutation_test(resolved, "label", "outcome_h15", "clock_hour")
        else:
            perm = {"observed_diff": np.nan, "p_value": np.nan, "n_extreme": 0, "n_moderate": 0,
                    "closure_rate_extreme": np.nan, "closure_rate_moderate": np.nan,
                    "n_matched_strata": 0, "n_perms": None, "seed": None}
        rows.append({
            "leg": leg, "leader_instrument": leader, "leader_direction": direction,
            "n_extreme_raw": n_extreme_raw, "n_moderate_raw": n_moderate_raw,
            "n_resolved_extreme": perm["n_extreme"], "n_resolved_moderate": perm["n_moderate"],
            "n_ambiguous": n_ambiguous, "n_neither": n_neither, "n_incomplete": n_incomplete,
            "n_matched_strata": perm["n_matched_strata"],
            "closure_rate_extreme": perm["closure_rate_extreme"],
            "closure_rate_moderate": perm["closure_rate_moderate"],
            "effect_pp": (perm["observed_diff"] * 100) if pd.notna(perm["observed_diff"]) else np.nan,
            "raw_p_value": perm["p_value"], "n_perms": perm["n_perms"], "seed": perm["seed"],
        })
    return pd.DataFrame(rows)


def apply_bh_primary(pc: pd.DataFrame) -> pd.DataFrame:
    pc = pc.copy()
    adj, _ = benjamini_hochberg(pc["raw_p_value"].to_numpy())
    pc["q_value"] = adj
    return pc


def year_stability(events_out: pd.DataFrame) -> pd.DataFrame:
    df = _label(events_out)
    rows = []
    for (leg, leader, direction), g in df.groupby(["leg", "leader", "leader_direction"]):
        for year in YEARS:
            gy = g.loc[g["year"] == year]
            resolved = gy.loc[gy["resolved_nonambiguous_h15"]]
            n_e = int((resolved["label"] == "extreme").sum())
            n_m = int((resolved["label"] == "moderate").sum())
            rate_e = (resolved.loc[resolved["label"] == "extreme", "outcome_h15"] == "RESIDUAL_CLOSURE_FIRST").mean() if n_e else np.nan
            rate_m = (resolved.loc[resolved["label"] == "moderate", "outcome_h15"] == "RESIDUAL_CLOSURE_FIRST").mean() if n_m else np.nan
            diff = rate_e - rate_m if (pd.notna(rate_e) and pd.notna(rate_m)) else np.nan
            rows.append({
                "leg": leg, "leader_instrument": leader, "leader_direction": direction, "year": year,
                "n_extreme": n_e, "n_moderate": n_m,
                "closure_rate_extreme": rate_e, "closure_rate_moderate": rate_m,
                "diff": diff, "sign": np.sign(diff) if pd.notna(diff) else np.nan,
            })
    return pd.DataFrame(rows)


def classify_primary(pc: pd.DataFrame, yr: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, row in pc.iterrows():
        yr_sub = yr.loc[
            (yr["leg"] == row["leg"]) & (yr["leader_instrument"] == row["leader_instrument"])
            & (yr["leader_direction"] == row["leader_direction"])
        ]
        signs = yr_sub["sign"].dropna()
        agree = 0
        if len(signs):
            mode_sign = signs.mode()
            if len(mode_sign):
                agree = int((signs == mode_sign.iloc[0]).sum())
        sample_ok = row["n_resolved_extreme"] >= 30 and row["n_resolved_moderate"] >= 30 and row["n_matched_strata"] >= 1
        effect_ok = pd.notna(row["effect_pp"]) and row["effect_pp"] >= MIN_EFFECT_PP
        q_ok = pd.notna(row["q_value"]) and row["q_value"] < 0.05
        year_ok = agree >= 4
        if not sample_ok:
            label = "UNDERPOWERED"
        elif effect_ok and q_ok and year_ok:
            label = "EXTREME_CONVERGES_MORE_SUPPORTED"
        else:
            label = "MIXED_OR_NULL"
        d = row.to_dict()
        d["max_year_sign_agreement"] = agree
        d["sample_ok"] = sample_ok
        d["classification"] = label
        out.append(d)
    return pd.DataFrame(out)
