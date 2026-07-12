"""Benjamini-Hochberg, behavior classification, alias/coincident-level
detection, year stability -- SPEC_SIMPLE_LEVELS.md secs 16-19. No
profitability, no TP/SL, no entries.
"""
import numpy as np
import pandas as pd
from scipy import stats as sstats

MIN_TOUCH_EVENTS = 50
MIN_NONTIED_BARRIER = 20
MIN_YEARS_WITH_TOUCHES = 4
MIN_TOUCHES_PER_YEAR = 10
RATE_DIFF_THRESHOLD = 0.05
BH_ALPHA = 0.05


def _bh_adjust(pvals: np.ndarray) -> np.ndarray:
    out = np.full(len(pvals), np.nan)
    valid_mask = ~np.isnan(pvals)
    p = pvals[valid_mask]
    m = len(p)
    if m == 0:
        return out
    order = np.argsort(p)
    ranked = p[order]
    ranks = np.arange(1, m + 1)
    adj_sorted = np.minimum.accumulate((ranked * m / ranks)[::-1])[::-1]
    adj_sorted = np.clip(adj_sorted, 0, 1)
    adj = np.empty(m)
    adj[order] = adj_sorted
    out[valid_mask] = adj
    return out


def bh_within(df: pd.DataFrame, pval_col: str, group_cols) -> pd.DataFrame:
    df = df.copy()
    df["q_value"] = np.nan
    for _, g in df.groupby(list(group_cols)):
        df.loc[g.index, "q_value"] = _bh_adjust(g[pval_col].to_numpy())
    return df


# --------------------------------------------------------- barrier tests --
def barrier_test_table(barriers_tbl: pd.DataFrame, b: float, primary_horizons) -> pd.DataFrame:
    sub = barriers_tbl[barriers_tbl["b"] == b]
    rows = []
    for (instrument, level_id, horizon), g in sub.groupby(["instrument", "level_id", "horizon"]):
        if horizon not in primary_horizons:
            continue
        n_cont = int((g["barrier_first_outcome"] == "CONTINUATION_FIRST").sum())
        n_rev = int((g["barrier_first_outcome"] == "REVERSAL_FIRST").sum())
        n_tie = int((g["barrier_first_outcome"] == "SAME_BAR_TIE").sum())
        n_neither = int((g["barrier_first_outcome"] == "NEITHER").sum())
        n_nontied = n_cont + n_rev
        row = {"instrument": instrument, "level_id": level_id, "horizon": horizon, "b": b,
              "n_continuation_first": n_cont, "n_reversal_first": n_rev,
              "n_same_bar_tie": n_tie, "n_neither": n_neither, "n_nontied": n_nontied}
        n_total = len(g)
        row["continuation_first_rate"] = n_cont / n_total if n_total else np.nan
        row["reversal_first_rate"] = n_rev / n_total if n_total else np.nan
        row["same_bar_tie_rate"] = n_tie / n_total if n_total else np.nan
        row["neither_rate"] = n_neither / n_total if n_total else np.nan
        row["cont_minus_rev_diff"] = row["continuation_first_rate"] - row["reversal_first_rate"]
        if n_nontied >= 1:
            k = min(n_cont, n_rev)
            row["p_raw"] = sstats.binomtest(k, n_nontied, 0.5, alternative="two-sided").pvalue
        else:
            row["p_raw"] = np.nan
        rows.append(row)
    out = pd.DataFrame(rows)
    out = bh_within(out, "p_raw", group_cols=("instrument", "horizon"))
    return out


def same_bar_morphology_table(events_tbl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (instrument, level_id), g in events_tbl.groupby(["instrument", "level_id"]):
        n_rev = int((g["same_bar_morphology"] == "SAME_BAR_REVERSAL_PROXY").sum())
        n_blast = int((g["same_bar_morphology"] == "SAME_BAR_BLAST_THROUGH_PROXY").sum())
        n_neutral = int((g["same_bar_morphology"] == "SAME_BAR_NEUTRAL").sum())
        n_total = n_rev + n_blast + n_neutral
        n_nonneutral = n_rev + n_blast
        row = {"instrument": instrument, "level_id": level_id,
              "n_reversal_proxy": n_rev, "n_blast_through_proxy": n_blast, "n_neutral": n_neutral,
              "n_total_touch_bars": n_total, "n_nonneutral": n_nonneutral,
              "reversal_rate": n_rev / n_total if n_total else np.nan,
              "blast_through_rate": n_blast / n_total if n_total else np.nan,
              "neutral_rate": n_neutral / n_total if n_total else np.nan,
              "reversal_minus_blast_diff": (n_rev - n_blast) / n_total if n_total else np.nan}
        if n_nonneutral >= 1:
            k = min(n_rev, n_blast)
            row["p_raw"] = sstats.binomtest(k, n_nonneutral, 0.5, alternative="two-sided").pvalue
        else:
            row["p_raw"] = np.nan
        rows.append(row)
    out = pd.DataFrame(rows)
    out = bh_within(out, "p_raw", group_cols=("instrument",))
    return out


# ------------------------------------------------------- year stability --
def year_stability_barrier(barriers_tbl: pd.DataFrame, b: float = 1.0) -> pd.DataFrame:
    sub = barriers_tbl[barriers_tbl["b"] == b].copy()
    sub["year"] = pd.to_datetime(sub["session_date"]).dt.year
    rows = []
    for (instrument, level_id, horizon, year), g in sub.groupby(["instrument", "level_id", "horizon", "year"]):
        n_cont = int((g["barrier_first_outcome"] == "CONTINUATION_FIRST").sum())
        n_rev = int((g["barrier_first_outcome"] == "REVERSAL_FIRST").sum())
        n_total = len(g)
        rows.append({"instrument": instrument, "level_id": level_id, "horizon": horizon, "year": year,
                    "n_touches": n_total, "n_continuation_first": n_cont, "n_reversal_first": n_rev,
                    "cont_minus_rev_diff": (n_cont - n_rev) / n_total if n_total else np.nan})
    return pd.DataFrame(rows)


def year_stability_touch(levels_tbl: pd.DataFrame) -> pd.DataFrame:
    lt = levels_tbl.copy()
    lt["year"] = pd.to_datetime(lt["session_date"]).dt.year
    rows = []
    for (instrument, level_id, year), g in lt.groupby(["instrument", "level_id", "year"]):
        valid = g[g["level_valid"]]
        rows.append({"instrument": instrument, "level_id": level_id, "year": year,
                    "n_valid": len(valid), "n_touched": int(valid["touched"].sum()),
                    "touch_rate": valid["touched"].mean() if len(valid) else np.nan})
    return pd.DataFrame(rows)


# -------------------------------------------------- behavior classification --
def behavior_classification(barrier_1sd_table: pd.DataFrame, outcomes_tbl: pd.DataFrame,
                            year_stability_tbl: pd.DataFrame, levels_tbl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in barrier_1sd_table.iterrows():
        instrument, level_id, horizon = row["instrument"], row["level_id"], row["horizon"]
        n_events = int(levels_tbl[(levels_tbl.instrument == instrument) & (levels_tbl.level_id == level_id)
                                  & (levels_tbl.touched)].shape[0])
        n_nontied = row["n_nontied"]
        yrs = year_stability_tbl[(year_stability_tbl.instrument == instrument)
                                 & (year_stability_tbl.level_id == level_id)
                                 & (year_stability_tbl.horizon == horizon)]
        yrs_with_floor = yrs[yrs["n_touches"] >= MIN_TOUCHES_PER_YEAR]
        n_years_floor = len(yrs_with_floor)

        underpowered = (n_events < MIN_TOUCH_EVENTS) or (n_nontied < MIN_NONTIED_BARRIER) or (n_years_floor < MIN_YEARS_WITH_TOUCHES)

        med_signed = outcomes_tbl[(outcomes_tbl.instrument == instrument) & (outcomes_tbl.level_id == level_id)
                                  & (outcomes_tbl.horizon == horizon)]["SIGNED_CLOSE_SD_h"].median()

        cls = "UNDERPOWERED"
        if not underpowered:
            diff = row["cont_minus_rev_diff"]
            q = row["q_value"]
            sig = (q is not None) and np.isfinite(q) and q < BH_ALPHA
            year_signs = np.sign(yrs_with_floor["cont_minus_rev_diff"])
            same_sign_cont = int((year_signs > 0).sum())
            same_sign_rev = int((year_signs < 0).sum())

            if (diff >= RATE_DIFF_THRESHOLD and sig and np.isfinite(med_signed) and med_signed > 0
                    and same_sign_cont >= 4):
                cls = "CONTINUATION_DOMINANT"
            elif (-diff >= RATE_DIFF_THRESHOLD and sig and np.isfinite(med_signed) and med_signed < 0
                  and same_sign_rev >= 4):
                cls = "REVERSAL_DOMINANT"
            else:
                cls = "MIXED_OR_NULL"

        rows.append({"instrument": instrument, "level_id": level_id, "horizon": horizon,
                    "n_touch_events": n_events, "n_nontied_barrier": n_nontied,
                    "n_years_with_floor": n_years_floor, "cont_minus_rev_diff": row["cont_minus_rev_diff"],
                    "q_value": row["q_value"], "median_signed_close_sd": med_signed,
                    "classification": cls})
    return pd.DataFrame(rows)


def same_bar_classification(same_bar_tbl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in same_bar_tbl.iterrows():
        underpowered = row["n_nonneutral"] < MIN_TOUCH_EVENTS
        cls = "SAME_BAR_UNDERPOWERED"
        if not underpowered:
            diff = row["reversal_minus_blast_diff"]
            q = row["q_value"]
            sig = (q is not None) and np.isfinite(q) and q < BH_ALPHA
            if diff >= RATE_DIFF_THRESHOLD and sig:
                cls = "SAME_BAR_REVERSAL_BIASED"
            elif -diff >= RATE_DIFF_THRESHOLD and sig:
                cls = "SAME_BAR_BLAST_THROUGH_BIASED"
            else:
                cls = "SAME_BAR_MIXED"
        rows.append({**row.to_dict(), "same_bar_classification": cls})
    return pd.DataFrame(rows)


# --------------------------------------------------------- coincident levels --
def coincident_levels(levels_tbl: pd.DataFrame, tick: float) -> pd.DataFrame:
    """For every session, identify exact duplicates and within-one-tick
    clusters among valid level_values. Returns one row per session with
    cluster assignments (not deduplicated -- every formula row is
    retained elsewhere; this is a diagnostic-only table)."""
    rows = []
    for (instrument, session), g in levels_tbl[levels_tbl["level_valid"]].groupby(["instrument", "session_date"]):
        vals = g[["level_id", "level_value", "touched"]].reset_index(drop=True)
        n = len(vals)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, c):
            ra, rc = find(a), find(c)
            if ra != rc:
                parent[ra] = rc

        v = vals["level_value"].to_numpy()
        for i in range(n):
            for j in range(i + 1, n):
                if abs(v[i] - v[j]) <= tick:
                    union(i, j)

        comp = {}
        for i in range(n):
            comp.setdefault(find(i), []).append(i)

        for members in comp.values():
            size = len(members)
            member_ids = vals.loc[members, "level_id"].tolist()
            any_touched = bool(vals.loc[members, "touched"].any())
            rows.append({"instrument": instrument, "session_date": session, "cluster_size": size,
                        "member_level_ids": ",".join(member_ids), "any_touched": any_touched})
    return pd.DataFrame(rows)
