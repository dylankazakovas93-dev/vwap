"""Orchestrates generation 8: builds ES/NQ ledgers, runs Family A/B,
secondary grid, year stability, and writes all required output tables.
No profitability, no entries/exits/sizing, no taxonomy conditioning.
"""
import os

import numpy as np
import pandas as pd

from . import build_ledger as bd
from . import families as fam
from . import secondary as sec

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "research", "cash_open_level_interactions", "outputs")
TABLES = os.path.join(REPO, "research", "cash_open_level_interactions", "reports", "tables")
INSTRUMENTS = ("ES", "NQ")


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    lv, bl = bd._load_gen7()
    tx = bl._load_taxonomy_module()
    level_ids = sorted(lv.LEVEL_COLUMNS.keys())

    all_levels, all_events, all_outcomes, all_barriers = [], [], [], []
    for instrument in INSTRUMENTS:
        levels_tbl, events_tbl, outcomes_tbl, barriers_tbl = bd.build_instrument_ledger(instrument, lv, bl, tx)
        levels_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_levels.parquet"), index=False)
        events_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_events.parquet"), index=False)
        outcomes_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_outcomes.parquet"), index=False)
        barriers_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_barriers.parquet"), index=False)
        all_levels.append(levels_tbl); all_events.append(events_tbl)
        all_outcomes.append(outcomes_tbl); all_barriers.append(barriers_tbl)
        print(f"{instrument}: {len(levels_tbl)} unit rows, {len(events_tbl)} event rows, "
             f"{len(outcomes_tbl)} outcome rows, {len(barriers_tbl)} barrier rows", flush=True)

    levels_tbl = pd.concat(all_levels, ignore_index=True)
    events_tbl = pd.concat(all_events, ignore_index=True)
    outcomes_tbl = pd.concat(all_outcomes, ignore_index=True)
    barriers_tbl = pd.concat(all_barriers, ignore_index=True)

    # ---------------------------------------------------- eligibility summary --
    elig_rows = []
    for instrument in INSTRUMENTS:
        g = levels_tbl[levels_tbl["instrument"] == instrument]
        elig_rows.append({
            "instrument": instrument, "n_units": len(g),
            "n_real_valid": int(g["real_level_valid"].sum()),
            "n_synthetic_valid": int(g["synthetic_level_valid"].sum()),
            "n_touch_window_complete": int(g["touch_window_complete"].sum()),
            "n_outcome_window_complete": int(g["outcome_window_complete"].sum()),
            "n_mutually_touch_eligible": int(g["mutually_touch_eligible"].sum()),
            "n_real_normalized_outcome_eligible": int(g["real_normalized_outcome_eligible"].sum()),
            "n_synthetic_normalized_outcome_eligible": int(g["synthetic_normalized_outcome_eligible"].sum()),
            "n_real_isolated": int((g["real_isolated"] == 1).sum()),
            "n_synthetic_isolated": int((g["synthetic_isolated"] == 1).sum()),
            "n_pair_separated": int((g["pair_separated"] == 1).sum()),
        })
    pd.DataFrame(elig_rows).to_csv(os.path.join(TABLES, "eligibility_exclusion_summary.csv"), index=False)

    # ---------------------------------------------------------- touch-rate --
    touch_rows = []
    for (instrument, level_id), g in levels_tbl.groupby(["instrument", "level_id"]):
        mutual = g[g["mutually_touch_eligible"]]
        touch_rows.append({
            "instrument": instrument, "level_id": level_id, "n_mutually_eligible": len(mutual),
            "real_touch_rate": mutual["real_touched"].mean() if len(mutual) else np.nan,
            "synthetic_touch_rate": mutual["synthetic_touched"].mean() if len(mutual) else np.nan,
        })
    pd.DataFrame(touch_rows).to_csv(os.path.join(TABLES, "touch_rate_table.csv"), index=False)

    # ---------------------------------------------------- first-touch timing --
    timing = events_tbl[events_tbl["touched"]].groupby(
        ["instrument", "level_id", "arm", "touch_bucket"]).size().reset_index(name="n")
    timing.to_csv(os.path.join(TABLES, "first_touch_timing_table.csv"), index=False)

    # ------------------------------------------------------ cluster/co-touch --
    cluster_cols = ["instrument", "session_date", "level_id", "cluster_flag", "cluster_id",
                    "cluster_member_level_ids", "co_touch_level_ids_real", "co_touch_level_ids_synthetic",
                    "real_isolated", "synthetic_isolated", "pair_separated"]
    levels_tbl[cluster_cols].to_parquet(os.path.join(OUT, "cluster_co_touch_detail.parquet"), index=False)
    cluster_summary = levels_tbl.groupby(["instrument", "level_id"]).agg(
        cluster_rate=("cluster_flag", "mean"),
        real_isolated_rate=("real_isolated", "mean"),
        synthetic_isolated_rate=("synthetic_isolated", "mean"),
        pair_separated_rate=("pair_separated", "mean"),
    ).reset_index()
    cluster_summary.to_csv(os.path.join(TABLES, "cluster_co_touch_table.csv"), index=False)

    # -------------------------------------------------- Primary Family A --
    family_a = fam.family_a_touch_rate(levels_tbl)
    family_a.to_csv(os.path.join(TABLES, "primary_family_a_results.csv"), index=False)

    # -------------------------------------------------- Primary Family B --
    pairs = fam.build_family_b_pairs(levels_tbl, events_tbl, outcomes_tbl)
    pairs.to_parquet(os.path.join(OUT, "family_b_pairs.parquet"), index=False)
    family_b = fam.family_b_paired_d5(pairs, all_instruments=list(INSTRUMENTS), all_level_ids=level_ids)
    family_b.to_csv(os.path.join(TABLES, "primary_family_b_results.csv"), index=False)

    coverage_rows = []
    for instrument in INSTRUMENTS:
        for level_id in level_ids:
            a_row = family_a[(family_a["instrument"] == instrument) & (family_a["level_id"] == level_id)]
            b_row = family_b[(family_b["instrument"] == instrument) & (family_b["level_id"] == level_id)]
            coverage_rows.append({
                "instrument": instrument, "level_id": level_id,
                "family_a_n_mutual": a_row["n_mutually_eligible"].iloc[0] if len(a_row) else 0,
                "family_a_confirmatory": bool(a_row["confirmatory_eligible"].iloc[0]) if len(a_row) else False,
                "family_b_n_pairs": b_row["n_valid_pairs"].iloc[0] if len(b_row) else 0,
                "family_b_confirmatory": bool(b_row["confirmatory_eligible"].iloc[0]) if len(b_row) else False,
            })
    pd.DataFrame(coverage_rows).to_csv(os.path.join(TABLES, "primary_family_sample_coverage.csv"), index=False)

    # ------------------------------------------------------- secondary grid --
    unpaired_d = sec.unpaired_continuous_grid(outcomes_tbl, INSTRUMENTS, level_ids)
    unpaired_d.to_csv(os.path.join(TABLES, "secondary_unpaired_continuous_grid.csv"), index=False)

    retouch_grid = sec.binary_outcome_grid(outcomes_tbl, "post_touch_retouch", "post_touch_retouch", INSTRUMENTS, level_ids)
    retouch_grid.to_csv(os.path.join(TABLES, "secondary_post_touch_retouch_grid.csv"), index=False)

    recross_grid = sec.binary_outcome_grid(outcomes_tbl, "directional_close_recross", "directional_close_recross", INSTRUMENTS, level_ids)
    recross_grid.to_csv(os.path.join(TABLES, "secondary_directional_close_recross_grid.csv"), index=False)

    label_dist = outcomes_tbl.groupby(["instrument", "level_id", "arm", "horizon", "label_tau1.0"]).size().reset_index(name="n")
    label_dist.to_csv(os.path.join(TABLES, "secondary_label_distribution.csv"), index=False)

    barrier_grid = sec.barrier_reach_grid(barriers_tbl, INSTRUMENTS, level_ids)
    barrier_grid_flat = barrier_grid.drop(columns=["real_barrier_order_dist", "synth_barrier_order_dist"], errors="ignore")
    barrier_grid_flat.to_csv(os.path.join(TABLES, "secondary_barrier_reach_grid.csv"), index=False)

    barrier_order_rows = []
    for _, row in barrier_grid.iterrows():
        for arm_label, col in (("REAL", "real_barrier_order_dist"), ("SYNTHETIC", "synth_barrier_order_dist")):
            dist = row.get(col) or {}
            for order_label, n in dist.items():
                barrier_order_rows.append({"instrument": row["instrument"], "level_id": row["level_id"],
                                          "horizon": row["horizon"], "k": row["k"], "arm": arm_label,
                                          "barrier_order": order_label, "n": n})
    pd.DataFrame(barrier_order_rows).to_csv(os.path.join(TABLES, "barrier_order_table.csv"), index=False)

    # ------------------------------------------------------- year stability --
    yrs = sec.year_stability(levels_tbl, outcomes_tbl, pairs)
    yrs.to_csv(os.path.join(TABLES, "year_stability_table.csv"), index=False)

    # --------------------------------------------------- null / underpowered --
    null_a = family_a[~family_a["bonferroni_survivor"]]
    null_a.to_csv(os.path.join(TABLES, "family_a_null_inventory.csv"), index=False)
    underpowered_a = family_a[~family_a["confirmatory_eligible"]]
    underpowered_a.to_csv(os.path.join(TABLES, "family_a_underpowered_inventory.csv"), index=False)

    null_b = family_b[~family_b["bonferroni_survivor"]]
    null_b.to_csv(os.path.join(TABLES, "family_b_null_inventory.csv"), index=False)
    underpowered_b = family_b[~family_b["confirmatory_eligible"]]
    underpowered_b.to_csv(os.path.join(TABLES, "family_b_underpowered_inventory.csv"), index=False)

    # ------------------------------------------------------- classification --
    classification_rows = []
    for instrument in INSTRUMENTS:
        for level_id in level_ids:
            a_row = family_a[(family_a["instrument"] == instrument) & (family_a["level_id"] == level_id)].iloc[0]
            b_row = family_b[(family_b["instrument"] == instrument) & (family_b["level_id"] == level_id)].iloc[0]
            a_sup = bool(a_row["bonferroni_survivor"])
            b_sup = bool(b_row["bonferroni_survivor"])
            if a_sup and b_sup:
                cls = "SUPPORTED_BOTH"
            elif a_sup:
                cls = "SUPPORTED_TOUCH_RATE_DIFFERENCE"
            elif b_sup:
                cls = "SUPPORTED_PAIRED_POST_TOUCH_DIFFERENCE"
            elif not a_row["confirmatory_eligible"] and not b_row["confirmatory_eligible"]:
                cls = "UNDERPOWERED"
            else:
                cls = "NULL"
            classification_rows.append({"instrument": instrument, "level_id": level_id, "classification": cls,
                                       "family_a_p_bonferroni": a_row["p_bonferroni"],
                                       "family_b_p_bonferroni": b_row["p_bonferroni"]})
    classification = pd.DataFrame(classification_rows)
    classification.to_csv(os.path.join(TABLES, "final_classification.csv"), index=False)

    print("All tables written to reports/tables/.", flush=True)
    return {
        "levels_tbl": levels_tbl, "events_tbl": events_tbl, "outcomes_tbl": outcomes_tbl,
        "barriers_tbl": barriers_tbl, "family_a": family_a, "family_b": family_b,
        "classification": classification, "eligibility": pd.DataFrame(elig_rows),
        "year_stability": yrs,
    }


if __name__ == "__main__":
    main()
