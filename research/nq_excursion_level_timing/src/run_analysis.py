"""Orchestrates generation 10: builds NQ (primary) and ES (negative
control) ledgers, computes the timing surface, same-bar surface,
coherence/same-bar classification, rolling-state test, alias audit, and
writes all required output tables.
"""
import os

import numpy as np
import pandas as pd

from . import build_ledger as bd
from . import levels as lv
from . import stats as st
from . import classification as cl
from . import rolling_state as rs

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "research", "nq_excursion_level_timing", "outputs")
TABLES = os.path.join(REPO, "research", "nq_excursion_level_timing", "reports", "tables")
INSTRUMENTS = ("NQ", "ES")
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

    # ------------------------------------------------------------ timing surface --
    surface = st.timing_surface(levels_tbl, events_tbl, outcomes_tbl, barriers_tbl)
    surface.to_csv(os.path.join(TABLES, "timing_surface_table.csv"), index=False)
    surface.to_parquet(os.path.join(OUT, "timing_surface_full.parquet"), index=False)
    assert len(surface) == 2 * 8 * 11 * 11

    same_bar_surface = st.same_bar_surface_table(surface)
    same_bar_surface.to_csv(os.path.join(TABLES, "same_bar_surface_table.csv"), index=False)

    # -------------------------------------------------------------- post-touch --
    post_touch_rows = []
    for (instrument, level_id, horizon), g in outcomes_tbl.groupby(["instrument", "level_id", "horizon"]):
        post_touch_rows.append({
            "instrument": instrument, "level_id": level_id, "horizon": horizon, "n": len(g),
            "median_signed_close": g["SIGNED_CLOSE_H"].median(),
            "median_signed_close_sd": g["SIGNED_CLOSE_SD_H"].median(),
            "median_cont_exc_sd": g["CONT_EXC_SD_H"].median(), "median_rev_exc_sd": g["REV_EXC_SD_H"].median(),
            "median_dominance": g["DOMINANCE_H"].median(),
            "post_touch_retouch_rate": g["post_touch_retouch"].mean(),
            "directional_close_recross_rate": g["directional_rejection_recross"].mean(),
        })
    pd.DataFrame(post_touch_rows).to_csv(os.path.join(TABLES, "post_touch_outcome_table.csv"), index=False)

    # ---------------------------------------------------------------- barriers --
    barrier_table_rows = []
    for bval in (0.5, 1.0, 2.0, 3.0):
        sub = barriers_tbl[barriers_tbl["b"] == bval]
        for (instrument, level_id, horizon), g in sub.groupby(["instrument", "level_id", "horizon"]):
            n = len(g)
            barrier_table_rows.append({
                "instrument": instrument, "level_id": level_id, "horizon": horizon, "b": bval, "n": n,
                "continuation_first_rate": (g["barrier_first_outcome"] == "CONTINUATION_FIRST").mean(),
                "reversal_first_rate": (g["barrier_first_outcome"] == "REVERSAL_FIRST").mean(),
                "same_bar_tie_rate": (g["barrier_first_outcome"] == "SAME_BAR_TIE").mean(),
                "neither_rate": (g["barrier_first_outcome"] == "NEITHER").mean(),
            })
    pd.DataFrame(barrier_table_rows).to_csv(os.path.join(TABLES, "barrier_first_table.csv"), index=False)

    # -------------------------------------------------------- year stability --
    year_cache = {}

    def year_stability_fn(A, H):
        key = (A, H)
        if key not in year_cache:
            year_cache[key] = st.year_stability(barriers_tbl, events_tbl, outcomes_tbl, A, H)
        return year_cache[key]

    # ----------------------------------------------------------- classification --
    timing_region = cl.classify_timing_region(surface, year_stability_fn)
    timing_region.to_csv(os.path.join(TABLES, "timing_region_classification_table.csv"), index=False)

    def year_stability_fn_samebar(A, H):
        return year_stability_fn(A, H)

    same_bar_cls = cl.classify_same_bar(same_bar_surface, year_stability_fn_samebar)
    same_bar_cls.to_csv(os.path.join(TABLES, "same_bar_classification_table.csv"), index=False)

    # write the full set of year-stability cells actually used (anchors)
    yearly_rows = [df for df in year_cache.values() if len(df)]
    if yearly_rows:
        pd.concat(yearly_rows, ignore_index=True).drop_duplicates().to_csv(
            os.path.join(TABLES, "yearly_stability_table.csv"), index=False)
    else:
        pd.DataFrame().to_csv(os.path.join(TABLES, "yearly_stability_table.csv"), index=False)

    # -------------------------------------------------------- rolling state --
    state_events = rs.build_rolling_state_events(barriers_tbl, events_tbl)
    state_events.to_parquet(os.path.join(OUT, "rolling_state_events.parquet"), index=False)
    state_summary = rs.rolling_state_summary(state_events)
    state_year = rs.rolling_state_year_stability(state_events)
    state_cls = rs.classify_rolling_state(state_summary, state_year)
    state_cls.to_csv(os.path.join(TABLES, "rolling_state_table.csv"), index=False)
    state_year.to_csv(os.path.join(TABLES, "rolling_state_year_table.csv"), index=False)

    # ------------------------------------------------------------ alias audit --
    coincident = st.coincident_levels(levels_tbl, TICK)
    coincident.to_parquet(os.path.join(OUT, "coincident_level_detail.parquet"), index=False)
    alias_rows = []
    for instrument, g in coincident.groupby("instrument"):
        multi = g[g["cluster_size"] > 1]
        n_sessions = g["session_date"].nunique()
        n_sessions_with_alias = g[g["cluster_size"] > 1]["session_date"].nunique()
        alias_rows.append({
            "instrument": instrument, "n_sessions": n_sessions,
            "pct_sessions_with_alias": n_sessions_with_alias / n_sessions * 100 if n_sessions else np.nan,
            "pct_touches_in_alias_cluster": (multi["any_touched"].sum() / g["any_touched"].sum() * 100
                                             if g["any_touched"].sum() else np.nan),
        })
    pd.DataFrame(alias_rows).to_csv(os.path.join(TABLES, "alias_duplicate_table.csv"), index=False)

    from collections import Counter
    collision_counter = Counter()
    for _, row in coincident[coincident["cluster_size"] > 1].iterrows():
        collision_counter[row["member_level_ids"]] += 1
    pd.DataFrame(collision_counter.most_common(20), columns=["member_level_ids", "n_sessions"]).to_csv(
        os.path.join(TABLES, "alias_top_collisions.csv"), index=False)

    # ----------------------------------------------------------- null/underpowered --
    null_timing = timing_region[timing_region["classification"].isin(["MIXED_OR_NULL", "ISOLATED_SIGNIFICANT_CELL"])]
    null_timing.to_csv(os.path.join(TABLES, "timing_region_null_inventory.csv"), index=False)
    underpowered_timing = timing_region[timing_region["classification"] == "UNDERPOWERED"]
    underpowered_timing.to_csv(os.path.join(TABLES, "timing_region_underpowered_inventory.csv"), index=False)
    null_samebar = same_bar_cls[same_bar_cls["same_bar_classification"] == "SAME_BAR_MIXED"]
    null_samebar.to_csv(os.path.join(TABLES, "same_bar_null_inventory.csv"), index=False)
    underpowered_samebar = same_bar_cls[same_bar_cls["same_bar_classification"] == "SAME_BAR_UNDERPOWERED"]
    underpowered_samebar.to_csv(os.path.join(TABLES, "same_bar_underpowered_inventory.csv"), index=False)

    print("All tables written to reports/tables/.", flush=True)
    return {
        "surface": surface, "same_bar_surface": same_bar_surface, "timing_region": timing_region,
        "same_bar_cls": same_bar_cls, "state_cls": state_cls, "coincident": coincident,
    }


if __name__ == "__main__":
    main()
