"""Development-only orchestration: build ledgers, apply the 432-cell x
4-mapping x 2-side grid, classify candidate families. Never touches OOS
or 2026 data. See SPEC_AUCTION_VALUE.md sections 4, 8, 9.
"""
import itertools
import json
import os

import numpy as np
import pandas as pd

from . import classification as cls
from . import controls as ctl
from . import data as dat
from . import events as ev
from . import grid
from . import mapping as mp
from . import outcomes as out
from . import profiles as prof

MAPPINGS = ("M1_ASIA_TO_LONDON", "M2_LONDON_TO_NY", "M3_RTH_TO_OVERNIGHT", "M4_RTH_TO_NEXT_RTH")
SIDES = ("long", "short")


def build_dev_state(root: str) -> dict:
    """Loads dev-year data for one instrument and builds every artifact
    needed by the grid: leg-tagged bars, PRIMARY profiles, mappings,
    per-(mapping,side) excursion ledgers with outcomes attached, and
    MATCHED_INSIDE_STATE controls with outcomes attached."""
    df1m = dat.load_1m(root)
    df1m = dat.add_causal_atr(df1m)
    df1m_dev = dat.filter_partition(df1m, dat.DEV_YEARS)
    dat.log_timestamp_boundary(f"{root}_dev_1m_raw", df1m_dev)

    leg_df = dat.add_leg_instances(df1m_dev)
    series = out.GlobalSeries(df1m_dev)

    profiles = mp.build_all_profiles(leg_df, prof.PRIMARY)
    mappings = mp.build_mappings(leg_df, profiles)

    target_bars_by_leg = {lid: g for lid, g in leg_df.groupby("session_leg_id", sort=False)}

    ledgers = {}
    flat_by_cell_key = {}
    breach_ts_by_profile_side = {}
    control_rows = {}

    for mapping_id in MAPPINGS:
        mapping_df = mappings[mapping_id]
        if mapping_df.empty:
            continue
        excursion_rows = ev.build_excursion_ledger(mapping_df, target_bars_by_leg)
        excursion_rows = _attach_target_session_date(excursion_rows, mapping_df)
        flat = grid.flatten_ledger(excursion_rows)
        flat = out.add_primary_outcomes(flat, series)
        flat = out.add_opposite_edge_completion(flat, series)
        ledgers[mapping_id] = flat

        for side in SIDES:
            key = (mapping_id, side)
            breach_ts_by_profile_side[key] = [
                r["interaction_ts"] for r in excursion_rows
                if r["mapping_id"] == mapping_id and r["side"] == side and r.get("interaction_kind") == "BREACH"
            ]

        mic = ctl.build_matched_inside_state_controls(mapping_df, target_bars_by_leg, breach_ts_by_profile_side)
        mic = _attach_target_session_date(mic, mapping_df)
        mic = out.add_primary_outcomes(mic, series)
        control_rows[mapping_id] = mic

    return {
        "root": root, "leg_df": leg_df, "series": series, "profiles": profiles,
        "mappings": mappings, "target_bars_by_leg": target_bars_by_leg,
        "ledgers": ledgers, "control_rows": control_rows,
    }


def _attach_target_session_date(rows: list, mapping_df: pd.DataFrame) -> list:
    lookup = dict(zip(mapping_df["target_session_leg_id"], mapping_df["target_session_date"]))
    out_rows = []
    for r in rows:
        r = dict(r)
        r["target_session_date"] = lookup.get(r["target_session_leg_id"])
        out_rows.append(r)
    return out_rows


def run_grid_for_mapping(mapping_id: str, flat_rows: list, control_rows: list, bands: dict) -> list:
    treat_by_side = {s: [r for r in flat_rows if r["side"] == s] for s in SIDES}
    control_by_side = {s: [r for r in control_rows if r["side"] == s] for s in SIDES}
    treat_by_side = {s: cls.add_strata(rows, bands) for s, rows in treat_by_side.items()}
    control_by_side = {s: cls.add_strata(rows, bands) for s, rows in control_by_side.items()}

    results = []
    for side in SIDES:
        t_rows, c_rows = treat_by_side[side], control_by_side[side]
        for a, b, c, d, e in grid.iter_grid_cells():
            cell_rows = grid.apply_cell(t_rows, a, b, c, d, e)
            stat = cls.evaluate_cell(cell_rows, c_rows)
            stat.update({"mapping_id": mapping_id, "side": side, "A": a, "B": b, "C": c, "D": d, "E": e})
            results.append(stat)
    return results


def run_development(root: str, out_dir: str) -> dict:
    state = build_dev_state(root)
    all_treat_rows = list(itertools.chain.from_iterable(state["ledgers"].values()))
    all_control_rows = list(itertools.chain.from_iterable(state["control_rows"].values()))
    bands = cls.compute_frozen_bands(all_treat_rows + all_control_rows)

    all_results = []
    for mapping_id in MAPPINGS:
        if mapping_id not in state["ledgers"]:
            continue
        mapping_results = run_grid_for_mapping(
            mapping_id, state["ledgers"][mapping_id], state["control_rows"][mapping_id], bands
        )
        mapping_results = cls.apply_bh_within_mapping(mapping_results)
        all_results.extend(mapping_results)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{root}_frozen_bands.json"), "w") as fh:
        json.dump(bands, fh, indent=2, default=str)

    return {"state": state, "bands": bands, "grid_results": all_results}
