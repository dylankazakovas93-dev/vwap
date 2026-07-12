"""Orchestrates the frozen NQ upper-excursion continuation validation.
Computes exactly the named cells from SPEC_VALIDATION.md -- no other
timing cell, lookback, or filter. No profitability, no trading-rule
outcomes. No further research generation begins after this one.
"""
import os

import numpy as np
import pandas as pd

from . import build_ledger as bd
from . import validation_stats as vs
from . import validation_rolling_state as vrs

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "research", "validation_nq_excursion_continuation", "outputs")
TABLES = os.path.join(REPO, "research", "validation_nq_excursion_continuation", "reports", "tables")

PRIMARY = ("NQ", "UPPER_k0", 2, 2)
SUPPORTING = [("NQ", "UPPER_k1", 2, 1), ("NQ", "UPPER_k2", 5, 2)]
NEG_CONTROLS = [
    ("NQ", "LOWER_k0", 2, 2), ("NQ", "LOWER_k1", 2, 1), ("NQ", "LOWER_k2", 5, 2),
    ("ES", "UPPER_k0", 2, 2), ("ES", "UPPER_k1", 2, 1), ("ES", "UPPER_k2", 5, 2),
]
K3_NULL_CHECK = ("NQ", "UPPER_k3", 5, 2)

SAME_BAR_CELLS = [
    ("NQ", "UPPER_k0", 2), ("NQ", "UPPER_k1", 2), ("NQ", "UPPER_k2", 5), ("NQ", "UPPER_k3", 5),
    ("NQ", "LOWER_k0", 2), ("NQ", "LOWER_k1", 2), ("NQ", "LOWER_k2", 5),
    ("ES", "UPPER_k0", 2), ("ES", "UPPER_k1", 2), ("ES", "UPPER_k2", 5),
]
ROLLING_STATE_LEVELS = [
    ("NQ", "UPPER_k0"), ("NQ", "UPPER_k1"), ("NQ", "UPPER_k2"), ("NQ", "UPPER_k3"),
    ("NQ", "LOWER_k0"), ("NQ", "LOWER_k1"), ("NQ", "LOWER_k2"),
    ("ES", "UPPER_k0"), ("ES", "UPPER_k1"), ("ES", "UPPER_k2"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    ledgers = {}
    max_dates = {}
    for instrument in ("NQ", "ES"):
        levels_tbl, events_tbl, outcomes_tbl, barriers_tbl, maxd = bd.build_instrument_ledger(instrument)
        levels_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_levels.parquet"), index=False)
        events_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_events.parquet"), index=False)
        outcomes_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_outcomes.parquet"), index=False)
        barriers_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_barriers.parquet"), index=False)
        ledgers[instrument] = (levels_tbl, events_tbl, outcomes_tbl, barriers_tbl)
        max_dates[instrument] = maxd
        print(f"{instrument}: {len(levels_tbl)} level rows, {len(events_tbl)} touch events, "
             f"{len(outcomes_tbl)} outcome rows, {len(barriers_tbl)} barrier rows, max_date={maxd}", flush=True)

    def compute_cell(instrument, level_id, A, H):
        lt, et, ot, bt = ledgers[instrument]
        return vs.cell_stats(lt, et, ot, bt, instrument, level_id, A, H, b=1.0)

    # ------------------------------------------------------------- primary --
    primary_stat = compute_cell(*PRIMARY)
    primary_eval = vs.evaluate_success_criteria(primary_stat)
    primary_stat["classification"] = primary_eval["classification"]
    primary_stat["criteria"] = primary_eval["criteria"]
    primary_stat["p_final"] = primary_stat["p_raw_one_sided"]

    primary_row = {k: v for k, v in primary_stat.items() if k not in ("year_table", "criteria")}
    primary_row.update({f"pass_{k}": v for k, v in primary_eval["criteria"].items()})
    pd.DataFrame([primary_row]).to_csv(os.path.join(TABLES, "primary_validation_result.csv"), index=False)
    primary_stat["year_table"].assign(instrument=PRIMARY[0], level_id=PRIMARY[1]).to_csv(
        os.path.join(TABLES, "primary_year_table.csv"), index=False)

    # ------------------------------------------------------------ supporting --
    supporting_stats = [compute_cell(*cell) for cell in SUPPORTING]
    holm_q = vs.holm_adjust([s["p_raw_one_sided"] if np.isfinite(s["p_raw_one_sided"]) else 1.0 for s in supporting_stats])
    supporting_rows = []
    for s, q in zip(supporting_stats, holm_q):
        s["p_final"] = q
        ev = vs.evaluate_success_criteria(s)
        s["classification"] = ev["classification"]
        row = {k: v for k, v in s.items() if k not in ("year_table",)}
        row.update({f"pass_{k}": v for k, v in ev["criteria"].items()})
        row["holm_adjusted_p"] = q
        supporting_rows.append(row)
    pd.DataFrame(supporting_rows).to_csv(os.path.join(TABLES, "supporting_candidate_result.csv"), index=False)
    pd.concat([s["year_table"].assign(instrument=cell[0], level_id=cell[1])
              for s, cell in zip(supporting_stats, SUPPORTING)], ignore_index=True).to_csv(
        os.path.join(TABLES, "supporting_year_table.csv"), index=False)

    # -------------------------------------------------------- negative controls --
    control_rows = []
    control_year_frames = []
    for cell in NEG_CONTROLS + [K3_NULL_CHECK]:
        s = compute_cell(*cell)
        row = {k: v for k, v in s.items() if k not in ("year_table",)}
        control_rows.append(row)
        control_year_frames.append(s["year_table"].assign(instrument=cell[0], level_id=cell[1]))
    pd.DataFrame(control_rows).to_csv(os.path.join(TABLES, "negative_control_result.csv"), index=False)
    pd.concat(control_year_frames, ignore_index=True).to_csv(os.path.join(TABLES, "negative_control_year_table.csv"), index=False)

    # ------------------------------------------------------------ same-bar --
    same_bar_rows = []
    same_bar_year_frames = []
    for instrument, level_id, A in SAME_BAR_CELLS:
        _, et, _, _ = ledgers[instrument]
        sb = vs.same_bar_stats(et, instrument, level_id, A)
        row = {k: v for k, v in sb.items() if k != "year_table"}
        same_bar_rows.append(row)
        same_bar_year_frames.append(sb["year_table"].assign(instrument=instrument, level_id=level_id))
    pd.DataFrame(same_bar_rows).to_csv(os.path.join(TABLES, "same_bar_morphology_table.csv"), index=False)
    pd.concat(same_bar_year_frames, ignore_index=True).to_csv(os.path.join(TABLES, "same_bar_year_table.csv"), index=False)

    # -------------------------------------------------------- rolling state --
    full_barriers = {}
    for instrument in ("NQ", "ES"):
        full_barriers[instrument] = bd.build_full_history_barriers_for_state(instrument)
        full_barriers[instrument].to_parquet(os.path.join(OUT, f"{instrument.lower()}_full_barriers_state.parquet"), index=False)

    state_rows = []
    state_year_frames = []
    for instrument, level_id in ROLLING_STATE_LEVELS:
        fb = full_barriers[instrument]
        fb_level = fb[fb["level_id"] == level_id]
        state_events = vrs.build_validation_state_events(fb_level)
        summary = vrs.summarize(state_events)
        if len(summary):
            row = {k: v for k, v in summary.iloc[0].to_dict().items() if k != "year_table"}
            state_rows.append(row)
            state_year_frames.append(summary.iloc[0]["year_table"].assign(instrument=instrument, level_id=level_id))
        else:
            state_rows.append({"instrument": instrument, "level_id": level_id, "classification": "STATE_UNDERPOWERED",
                              "n_continuation_state": 0, "n_reversal_state": 0})
    pd.DataFrame(state_rows).to_csv(os.path.join(TABLES, "rolling_state_replication_table.csv"), index=False)
    if state_year_frames:
        pd.concat(state_year_frames, ignore_index=True).to_csv(os.path.join(TABLES, "rolling_state_year_table.csv"), index=False)

    # ----------------------------------------------------- null/underpowered --
    all_cells = pd.concat([
        pd.DataFrame([primary_row]).assign(role="primary"),
        pd.DataFrame(supporting_rows).assign(role="supporting"),
        pd.DataFrame(control_rows).assign(role="negative_control"),
    ], ignore_index=True)
    null_rows = all_cells[all_cells.get("classification").isin(["FAILED_VALIDATION", None]) | all_cells["classification"].isna()] \
        if "classification" in all_cells.columns else all_cells
    all_cells.to_csv(os.path.join(TABLES, "null_and_underpowered_inventory.csv"), index=False)

    print("All tables written to reports/tables/.", flush=True)
    return {"primary": primary_stat, "supporting": supporting_stats, "controls": control_rows,
           "same_bar": same_bar_rows, "state": state_rows, "max_dates": max_dates}


if __name__ == "__main__":
    main()
