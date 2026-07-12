"""Timing surface, BH correction, coherence/same-bar classification, year
stability, coincident-level audit -- SPEC_EXCURSION_TIMING.md secs
15-19, 21. No profitability, no TP/SL, no entries.
"""
import numpy as np
import pandas as pd
from scipy import stats as sstats

from . import interactions as ix

MIN_TOUCH_EVENTS = 50
MIN_NONTIED_BARRIER = 20
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


# ------------------------------------------------------------ timing surface --
def timing_surface(levels_tbl: pd.DataFrame, events_tbl: pd.DataFrame,
                   outcomes_tbl: pd.DataFrame, barriers_tbl: pd.DataFrame) -> pd.DataFrame:
    """One row per instrument x level_id x activation_window(A) x horizon(H)."""
    b1 = barriers_tbl[barriers_tbl["b"] == ix.PRIMARY_B]
    rows = []
    for instrument in levels_tbl["instrument"].unique():
        lv_i = levels_tbl[levels_tbl["instrument"] == instrument]
        for level_id, lg in lv_i.groupby("level_id"):
            n_eligible = int(lg["level_valid"].sum())
            ev_i = events_tbl[(events_tbl["instrument"] == instrument) & (events_tbl["level_id"] == level_id)]
            oc_i = outcomes_tbl[(outcomes_tbl["instrument"] == instrument) & (outcomes_tbl["level_id"] == level_id)]
            b1_i = b1[(b1["instrument"] == instrument) & (b1["level_id"] == level_id)]

            for A in ix.ACTIVATION_WINDOWS:
                ev_a = ev_i[ev_i["first_touch_elapsed_bar"] <= A]
                n_touch_a = len(ev_a)
                touch_rate_a = n_touch_a / n_eligible if n_eligible else np.nan

                morph = ev_a["same_bar_morphology"]
                n_rev = int((morph == "SAME_BAR_REVERSAL_PROXY").sum())
                n_blast = int((morph == "SAME_BAR_BLAST_THROUGH_PROXY").sum())
                n_nonneutral = n_rev + n_blast
                sb_rev_rate = n_rev / len(ev_a) if len(ev_a) else np.nan
                sb_blast_rate = n_blast / len(ev_a) if len(ev_a) else np.nan
                sb_diff = (n_rev - n_blast) / len(ev_a) if len(ev_a) else np.nan

                for H in ix.HORIZONS:
                    oc = oc_i[(oc_i["horizon"] == H) & (oc_i["first_touch_elapsed_bar"] <= A)]
                    bh1 = b1_i[(b1_i["horizon"] == H) & (b1_i["first_touch_elapsed_bar"] <= A)]

                    n_cont = int((bh1["barrier_first_outcome"] == "CONTINUATION_FIRST").sum())
                    n_rev_b = int((bh1["barrier_first_outcome"] == "REVERSAL_FIRST").sum())
                    n_tie = int((bh1["barrier_first_outcome"] == "SAME_BAR_TIE").sum())
                    n_neither = int((bh1["barrier_first_outcome"] == "NEITHER").sum())
                    n_nontied = n_cont + n_rev_b
                    n_barrier_total = len(bh1)

                    row = {
                        "instrument": instrument, "level_id": level_id, "activation_window": A, "horizon": H,
                        "n_eligible_sessions": n_eligible, "n_touch_in_A": n_touch_a, "touch_rate_in_A": touch_rate_a,
                        "n_nonneutral_samebar": n_nonneutral, "same_bar_reversal_rate": sb_rev_rate,
                        "same_bar_blast_through_rate": sb_blast_rate, "same_bar_rev_minus_blast_diff": sb_diff,
                        "median_signed_close_sd": oc["SIGNED_CLOSE_SD_H"].median() if len(oc) else np.nan,
                        "median_cont_exc_sd": oc["CONT_EXC_SD_H"].median() if len(oc) else np.nan,
                        "median_rev_exc_sd": oc["REV_EXC_SD_H"].median() if len(oc) else np.nan,
                        "median_dominance": oc["DOMINANCE_H"].median() if len(oc) else np.nan,
                        "p_cont_gt_rev": (oc["CONT_EXC_SD_H"] > oc["REV_EXC_SD_H"]).mean() if len(oc) else np.nan,
                        "p_rev_gt_cont": (oc["REV_EXC_SD_H"] > oc["CONT_EXC_SD_H"]).mean() if len(oc) else np.nan,
                        "post_touch_retouch_rate": oc["post_touch_retouch"].mean() if len(oc) else np.nan,
                        "directional_close_recross_rate": oc["directional_rejection_recross"].mean() if len(oc) else np.nan,
                        "n_continuation_first": n_cont, "n_reversal_first": n_rev_b,
                        "n_same_bar_tie": n_tie, "n_neither": n_neither, "n_nontied": n_nontied,
                        "b1_continuation_first_rate": n_cont / n_barrier_total if n_barrier_total else np.nan,
                        "b1_reversal_first_rate": n_rev_b / n_barrier_total if n_barrier_total else np.nan,
                        "b1_same_bar_tie_rate": n_tie / n_barrier_total if n_barrier_total else np.nan,
                        "b1_neither_rate": n_neither / n_barrier_total if n_barrier_total else np.nan,
                        "cont_minus_rev_diff": ((n_cont - n_rev_b) / n_barrier_total) if n_barrier_total else np.nan,
                    }
                    if n_nontied >= 1:
                        k = min(n_cont, n_rev_b)
                        row["p_raw"] = sstats.binomtest(k, n_nontied, 0.5, alternative="two-sided").pvalue
                    else:
                        row["p_raw"] = np.nan
                    if n_touch_a >= MIN_TOUCH_EVENTS and n_nontied >= MIN_NONTIED_BARRIER:
                        row["sample_status"] = "tested"
                    else:
                        row["sample_status"] = "underpowered"
                    rows.append(row)

    out = pd.DataFrame(rows)
    out = bh_within(out, "p_raw", group_cols=("instrument",))
    return out


def same_bar_surface_table(timing_surface_tbl: pd.DataFrame) -> pd.DataFrame:
    """Same-bar BH within instrument across (8 levels x 11 activation
    windows) -- independent p-value family from the barrier surface."""
    rows = []
    for (instrument, level_id, A), g in timing_surface_tbl.groupby(["instrument", "level_id", "activation_window"]):
        row = g.iloc[0][["instrument", "level_id", "activation_window", "n_touch_in_A",
                         "n_nonneutral_samebar", "same_bar_reversal_rate",
                         "same_bar_blast_through_rate", "same_bar_rev_minus_blast_diff"]].to_dict()
        n_nonneutral = row["n_nonneutral_samebar"]
        if n_nonneutral >= 1:
            n_rev = round(row["same_bar_reversal_rate"] * row["n_touch_in_A"]) if np.isfinite(row["same_bar_reversal_rate"]) else 0
            n_blast = int(n_nonneutral - n_rev)
            k = min(n_rev, n_blast)
            row["p_raw"] = sstats.binomtest(k, int(n_nonneutral), 0.5, alternative="two-sided").pvalue
        else:
            row["p_raw"] = np.nan
        rows.append(row)
    out = pd.DataFrame(rows)
    out = bh_within(out, "p_raw", group_cols=("instrument",))
    return out


# --------------------------------------------------------- year stability --
def year_stability(barriers_tbl: pd.DataFrame, events_tbl: pd.DataFrame,
                   outcomes_tbl: pd.DataFrame, activation_window: int, horizon: int, b=ix.PRIMARY_B) -> pd.DataFrame:
    sub = barriers_tbl[(barriers_tbl["b"] == b) & (barriers_tbl["horizon"] == horizon)
                       & (barriers_tbl["first_touch_elapsed_bar"] <= activation_window)]
    ev = events_tbl[events_tbl["first_touch_elapsed_bar"] <= activation_window]
    oc = outcomes_tbl[(outcomes_tbl["horizon"] == horizon) & (outcomes_tbl["first_touch_elapsed_bar"] <= activation_window)]
    rows = []
    for (instrument, level_id, year), g in sub.groupby(["instrument", "level_id", "calendar_year"]):
        n_cont = int((g["barrier_first_outcome"] == "CONTINUATION_FIRST").sum())
        n_rev = int((g["barrier_first_outcome"] == "REVERSAL_FIRST").sum())
        n_total = len(g)
        ev_y = ev[(ev.instrument == instrument) & (ev.level_id == level_id) & (ev.calendar_year == year)]
        oc_y = oc[(oc.instrument == instrument) & (oc.level_id == level_id) & (oc.calendar_year == year)]
        n_srev = int((ev_y["same_bar_morphology"] == "SAME_BAR_REVERSAL_PROXY").sum())
        n_sblast = int((ev_y["same_bar_morphology"] == "SAME_BAR_BLAST_THROUGH_PROXY").sum())
        rows.append({"instrument": instrument, "level_id": level_id, "year": year,
                    "activation_window": activation_window, "horizon": horizon,
                    "touches": len(ev_y), "continuation_first_rate": n_cont / n_total if n_total else np.nan,
                    "reversal_first_rate": n_rev / n_total if n_total else np.nan,
                    "cont_minus_rev_diff": (n_cont - n_rev) / n_total if n_total else np.nan,
                    "median_signed_close": oc_y["SIGNED_CLOSE_H"].median(),
                    "same_bar_reversal_rate": n_srev / (n_srev + n_sblast) if (n_srev + n_sblast) else np.nan,
                    "same_bar_blast_through_rate": n_sblast / (n_srev + n_sblast) if (n_srev + n_sblast) else np.nan})
    out = pd.DataFrame(rows)
    if len(out) == 0:
        return out
    summary_rows = []
    for (instrument, level_id), g in out.groupby(["instrument", "level_id"]):
        effects = g["cont_minus_rev_diff"].dropna()
        mean_eff = effects.mean() if len(effects) else np.nan
        sd_eff = effects.std(ddof=1) if len(effects) > 1 else np.nan
        within_1sd = ((effects - mean_eff).abs() <= sd_eff) if np.isfinite(sd_eff) else pd.Series(dtype=bool)
        pooled_sign = np.sign(mean_eff) if np.isfinite(mean_eff) else 0
        n_same_sign = int((np.sign(effects) == pooled_sign).sum())
        total_touches = g["touches"].sum()
        max_year_touches_frac = (g["touches"].max() / total_touches) if total_touches else np.nan
        summary_rows.append({
            "instrument": instrument, "level_id": level_id,
            "mean_annual_effect": mean_eff, "sd_annual_effect": sd_eff,
            "n_years_within_1sd": int(within_1sd.sum()) if len(within_1sd) else 0,
            "n_years_with_pooled_sign": n_same_sign,
            "max_annual_effect": effects.max() if len(effects) else np.nan,
            "min_annual_effect": effects.min() if len(effects) else np.nan,
            "is_2020_largest_abs": bool(g[g.year == 2020]["cont_minus_rev_diff"].abs().max() ==
                                       g["cont_minus_rev_diff"].abs().max()) if 2020 in g["year"].values else False,
            "one_year_gt_35pct_touches": bool(max_year_touches_frac > 0.35) if np.isfinite(max_year_touches_frac) else False,
        })
    return out.merge(pd.DataFrame(summary_rows), on=["instrument", "level_id"], how="left")


# --------------------------------------------------------------- alias audit --
def coincident_levels(levels_tbl: pd.DataFrame, tick: float) -> pd.DataFrame:
    rows = []
    for (instrument, session), g in levels_tbl[levels_tbl["level_valid"]].groupby(["instrument", "session_date"]):
        vals = g[["level_id", "level_value", "first_touch_found"]].reset_index(drop=True)
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
            any_touched = bool(vals.loc[members, "first_touch_found"].any())
            rows.append({"instrument": instrument, "session_date": session, "cluster_size": size,
                        "member_level_ids": ",".join(member_ids), "any_touched": any_touched})
    return pd.DataFrame(rows)
