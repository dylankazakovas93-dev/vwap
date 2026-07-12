"""Orchestrates generation 9: builds ES/NQ ledgers, runs same-bar and
post-touch statistics, behavior classification, year stability, alias
detection, and writes all required output tables.
"""
import os

import numpy as np
import pandas as pd

from . import build_ledger as bd
from . import levels as lv
from . import stats as st

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "research", "simple_cash_open_levels", "outputs")
TABLES = os.path.join(REPO, "research", "simple_cash_open_levels", "reports", "tables")
INSTRUMENTS = ("ES", "NQ")
TICK = 0.25


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    all_levels, all_events, all_outcomes, all_barriers = [], [], [], []
    for instrument in INSTRUMENTS:
        levels_tbl, events_tbl, outcomes_tbl, barriers_tbl = bd.build_instrument_ledger(instrument)
        levels_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_levels.parquet"), index=False)
        events_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_events.parquet"), index=False)
        outcomes_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_outcomes.parquet"), index=False)
        barriers_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_barriers.parquet"), index=False)
        all_levels.append(levels_tbl); all_events.append(events_tbl)
        all_outcomes.append(outcomes_tbl); all_barriers.append(barriers_tbl)
        print(f"{instrument}: {len(levels_tbl)} level rows, {len(events_tbl)} touch events, "
             f"{len(outcomes_tbl)} outcome rows, {len(barriers_tbl)} barrier rows", flush=True)

    levels_tbl = pd.concat(all_levels, ignore_index=True)
    events_tbl = pd.concat(all_events, ignore_index=True)
    outcomes_tbl = pd.concat(all_outcomes, ignore_index=True)
    barriers_tbl = pd.concat(all_barriers, ignore_index=True)

    # ------------------------------------------------------- inventory --
    inv_rows = []
    for lid in lv.all_level_ids():
        family, anchor, N, center, k = lv.LEVEL_META[lid]
        inv_rows.append({"level_id": lid, "level_family": family, "anchor_type": anchor,
                        "lookback_N": N, "center_estimator": center, "k_or_j": k})
    pd.DataFrame(inv_rows).to_csv(os.path.join(TABLES, "level_inventory_table.csv"), index=False)
    assert len(inv_rows) == 86

    # ---------------------------------------------------- availability --
    avail_rows = []
    for (instrument, level_id), g in levels_tbl.groupby(["instrument", "level_id"]):
        avail_rows.append({"instrument": instrument, "level_id": level_id,
                          "n_sessions": len(g), "n_valid": int(g["level_valid"].sum()),
                          "pct_valid": g["level_valid"].mean() * 100})
    pd.DataFrame(avail_rows).to_csv(os.path.join(TABLES, "level_availability_table.csv"), index=False)

    # ---------------------------------------------------------- touch-rate --
    touch_rows = []
    for (instrument, level_id), g in levels_tbl.groupby(["instrument", "level_id"]):
        valid = g[g["level_valid"]]
        touch_rows.append({"instrument": instrument, "level_id": level_id,
                          "n_valid": len(valid), "n_touched": int(valid["touched"].sum()),
                          "touch_rate": valid["touched"].mean() if len(valid) else np.nan,
                          "touch_by_30_rate": valid["touch_by_30"].mean() if len(valid) else np.nan,
                          "touch_by_60_rate": valid["touch_by_60"].mean() if len(valid) else np.nan,
                          "touch_by_120_rate": valid["touch_by_120"].mean() if len(valid) else np.nan})
    pd.DataFrame(touch_rows).to_csv(os.path.join(TABLES, "touch_rate_table.csv"), index=False)

    # -------------------------------------------------------- timing table --
    timing = events_tbl.groupby(["instrument", "level_id", "timing_bin"]).size().reset_index(name="n")
    timing.to_csv(os.path.join(TABLES, "touch_timing_table.csv"), index=False)

    # -------------------------------------------------- same-bar morphology --
    same_bar = st.same_bar_morphology_table(events_tbl)
    same_bar_cls = st.same_bar_classification(same_bar)
    same_bar_cls.to_csv(os.path.join(TABLES, "same_bar_morphology_table.csv"), index=False)

    # -------------------------------------------------- post-touch outcome --
    outcome_summary_rows = []
    for (instrument, level_id, horizon), g in outcomes_tbl.groupby(["instrument", "level_id", "horizon"]):
        n = len(g)
        cont_gt_rev = (g["CONT_EXC_SD_h"] > g["REV_EXC_SD_h"])
        rev_gt_cont = (g["REV_EXC_SD_h"] > g["CONT_EXC_SD_h"])
        outcome_summary_rows.append({
            "instrument": instrument, "level_id": level_id, "horizon": horizon, "n": n,
            "median_raw_signed_close": g["raw_close_displacement"].median(),
            "mean_raw_signed_close": g["raw_close_displacement"].mean(),
            "median_norm_signed_close": g["SIGNED_CLOSE_SD_h"].median(),
            "mean_norm_signed_close": g["SIGNED_CLOSE_SD_h"].mean(),
            "median_cont_exc": g["CONT_EXC_h"].median(), "median_rev_exc": g["REV_EXC_h"].median(),
            "median_cont_exc_sd": g["CONT_EXC_SD_h"].median(), "median_rev_exc_sd": g["REV_EXC_SD_h"].median(),
            "median_dominance": g["DOMINANCE_h"].median(),
            "p_cont_gt_rev": cont_gt_rev.mean(), "p_rev_gt_cont": rev_gt_cont.mean(),
            "post_touch_retouch_rate": g["post_touch_retouch"].mean(),
            "directional_close_recross_rate": g["directional_rejection_recross"].mean(),
        })
    outcome_summary = pd.DataFrame(outcome_summary_rows)
    outcome_summary.to_csv(os.path.join(TABLES, "post_touch_outcome_table.csv"), index=False)

    # ------------------------------------------------------------ barriers --
    barrier_1sd = st.barrier_test_table(barriers_tbl, 1.0, (30, 60, 120))
    barrier_1sd.to_csv(os.path.join(TABLES, "barrier_1sd_test_table.csv"), index=False)

    barrier_full_rows = []
    for bval in (0.5, 1.0, 2.0, 3.0):
        tbl = st.barrier_test_table(barriers_tbl, bval, (30, 60, 120))
        tbl["b"] = bval
        barrier_full_rows.append(tbl)
    barrier_order_table = pd.concat(barrier_full_rows, ignore_index=True)
    barrier_order_table.to_csv(os.path.join(TABLES, "barrier_order_table.csv"), index=False)

    # -------------------------------------------------------- year stability --
    year_barrier = st.year_stability_barrier(barriers_tbl, b=1.0)
    year_barrier.to_csv(os.path.join(TABLES, "year_stability_barrier_table.csv"), index=False)
    year_touch = st.year_stability_touch(levels_tbl)
    year_touch.to_csv(os.path.join(TABLES, "year_stability_touch_table.csv"), index=False)

    # --------------------------------------------------- behavior classification --
    behavior = st.behavior_classification(barrier_1sd, outcomes_tbl, year_barrier, levels_tbl)
    behavior.to_csv(os.path.join(TABLES, "behavior_classification_table.csv"), index=False)

    # --------------------------------------------------------- coincident levels --
    coincident = st.coincident_levels(levels_tbl, TICK)
    coincident.to_parquet(os.path.join(OUT, "coincident_level_detail.parquet"), index=False)
    alias_summary_rows = []
    for instrument, g in coincident.groupby("instrument"):
        multi = g[g["cluster_size"] > 1]
        alias_summary_rows.append({
            "instrument": instrument, "n_sessions": g["session_date"].nunique(),
            "avg_aliases_per_physical_level": g["cluster_size"].mean(),
            "pct_touch_events_in_multialias_cluster": (
                multi["any_touched"].sum() / g["any_touched"].sum() * 100 if g["any_touched"].sum() else np.nan),
        })
    pd.DataFrame(alias_summary_rows).to_csv(os.path.join(TABLES, "coincident_level_alias_table.csv"), index=False)

    from collections import Counter
    collision_counter = Counter()
    for _, row in coincident[coincident["cluster_size"] > 1].iterrows():
        collision_counter[row["member_level_ids"]] += 1
    collisions = pd.DataFrame(collision_counter.most_common(30), columns=["member_level_ids", "n_sessions"])
    collisions.to_csv(os.path.join(TABLES, "coincident_level_top_collisions.csv"), index=False)

    # ----------------------------------------------------- null/underpowered --
    null_behavior = behavior[behavior["classification"] == "MIXED_OR_NULL"]
    null_behavior.to_csv(os.path.join(TABLES, "behavior_null_inventory.csv"), index=False)
    underpowered_behavior = behavior[behavior["classification"] == "UNDERPOWERED"]
    underpowered_behavior.to_csv(os.path.join(TABLES, "behavior_underpowered_inventory.csv"), index=False)
    null_same_bar = same_bar_cls[same_bar_cls["same_bar_classification"] == "SAME_BAR_MIXED"]
    null_same_bar.to_csv(os.path.join(TABLES, "same_bar_null_inventory.csv"), index=False)
    underpowered_same_bar = same_bar_cls[same_bar_cls["same_bar_classification"] == "SAME_BAR_UNDERPOWERED"]
    underpowered_same_bar.to_csv(os.path.join(TABLES, "same_bar_underpowered_inventory.csv"), index=False)

    print("All tables written to reports/tables/.", flush=True)
    return {
        "levels_tbl": levels_tbl, "events_tbl": events_tbl, "outcomes_tbl": outcomes_tbl,
        "barriers_tbl": barriers_tbl, "behavior": behavior, "same_bar_cls": same_bar_cls,
        "coincident": coincident,
    }


if __name__ == "__main__":
    main()
