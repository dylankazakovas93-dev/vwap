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


def build_ledger_for_config(leg_df: pd.DataFrame, target_bars_by_leg: dict, config: dict, mapping_id: str):
    """Rebuild profiles/mapping/ledger/controls for ONE mapping under an
    alternate profile config, reusing the already-loaded leg_df. Used
    only for the second-pass bin-width/model sensitivity check
    (DECISIONS.md #11d) -- never for the primary grid."""
    profiles = mp.build_all_profiles(leg_df, config)
    mappings = mp.build_mappings(leg_df, profiles)
    mapping_df = mappings[mapping_id]
    if mapping_df.empty:
        return None, None
    excursion_rows = ev.build_excursion_ledger(mapping_df, target_bars_by_leg)
    excursion_rows = _attach_target_session_date(excursion_rows, mapping_df)
    flat = grid.flatten_ledger(excursion_rows)
    breach_ts_by_profile_side = {
        (mapping_id, side): [r["interaction_ts"] for r in excursion_rows
                              if r["side"] == side and r.get("interaction_kind") == "BREACH"]
        for side in SIDES
    }
    mic = ctl.build_matched_inside_state_controls(mapping_df, target_bars_by_leg, breach_ts_by_profile_side)
    mic = _attach_target_session_date(mic, mapping_df)
    return flat, mic


def evaluate_single_cell_alt_config(leg_df, target_bars_by_leg, series, config, mapping_id, side,
                                     a, b, c, d, e, bands) -> dict:
    flat, mic = build_ledger_for_config(leg_df, target_bars_by_leg, config, mapping_id)
    if flat is None:
        return None
    flat = out.add_primary_outcomes(flat, series)
    mic = out.add_primary_outcomes(mic, series)
    t_rows = cls.add_strata([r for r in flat if r["side"] == side], bands)
    c_rows = cls.add_strata([r for r in mic if r["side"] == side], bands)
    cell_rows = grid.apply_cell(t_rows, a, b, c, d, e)
    return cls.evaluate_cell(cell_rows, c_rows)


def bin_width_and_model_support(leg_df, target_bars_by_leg, series, bands, mapping_id, side, a, b, c, d, e) -> dict:
    """Candidate criteria 8-9: does the cell's positive effect hold under
    alternate bin widths / alternate profile models? PRIMARY itself
    (UNIFORM_RANGE, 0.25) counts as one supporting bin width."""
    bin_width_support = 1
    for bw in (0.50, 1.00):
        cfg = {"model": "UNIFORM_RANGE", "bin_width": bw, "va_pct": 0.70}
        r = evaluate_single_cell_alt_config(leg_df, target_bars_by_leg, series, cfg, mapping_id, side, a, b, c, d, e, bands)
        if r and not np.isnan(r["pooled_diff_h60"]) and r["pooled_diff_h60"] > 0:
            bin_width_support += 1

    model_support = 0
    for model in ("TYPICAL_PRICE_ROW", "CLOSE_PRICE_ROW"):
        cfg = {"model": model, "bin_width": 0.25, "va_pct": 0.70}
        r = evaluate_single_cell_alt_config(leg_df, target_bars_by_leg, series, cfg, mapping_id, side, a, b, c, d, e, bands)
        if r and not np.isnan(r["pooled_diff_h60"]) and r["pooled_diff_h60"] > 0:
            model_support += 1

    return {"bin_width_support": bin_width_support, "model_support": model_support}


def adjacent_parameter_stability(grid_results_by_key: dict, mapping_id, side, a, b, c, d, e) -> int:
    """Candidate criterion 10: count of immediate one-step neighbors in
    A/B/D/E (holding C fixed) with the same positive sign, using the
    already-computed PRIMARY grid (no extra computation)."""
    idx_a, idx_b = grid.A_BREACH_DEPTH.index(a), grid.B_MAX_BARS_OUTSIDE.index(b)
    idx_d, idx_e = grid.D_POC_DISTANCE.index(d), grid.E_FRESHNESS_HOURS.index(e)
    neighbors = []
    if idx_a > 0:
        neighbors.append((grid.A_BREACH_DEPTH[idx_a - 1], b, c, d, e))
    if idx_a < len(grid.A_BREACH_DEPTH) - 1:
        neighbors.append((grid.A_BREACH_DEPTH[idx_a + 1], b, c, d, e))
    if idx_b > 0:
        neighbors.append((a, grid.B_MAX_BARS_OUTSIDE[idx_b - 1], c, d, e))
    if idx_b < len(grid.B_MAX_BARS_OUTSIDE) - 1:
        neighbors.append((a, grid.B_MAX_BARS_OUTSIDE[idx_b + 1], c, d, e))
    if idx_d > 0:
        neighbors.append((a, b, c, grid.D_POC_DISTANCE[idx_d - 1], e))
    if idx_d < len(grid.D_POC_DISTANCE) - 1:
        neighbors.append((a, b, c, grid.D_POC_DISTANCE[idx_d + 1], e))
    if idx_e > 0:
        neighbors.append((a, b, c, d, grid.E_FRESHNESS_HOURS[idx_e - 1]))
    if idx_e < len(grid.E_FRESHNESS_HOURS) - 1:
        neighbors.append((a, b, c, d, grid.E_FRESHNESS_HOURS[idx_e + 1]))

    support = 0
    for key in neighbors:
        r = grid_results_by_key.get((mapping_id, side) + key)
        if r and not np.isnan(r["pooled_diff_h60"]) and r["pooled_diff_h60"] > 0:
            support += 1
    return support


def select_candidates(root: str, out_dir: str) -> dict:
    """Full development pipeline + 12-criteria candidate gate. Second-pass
    sensitivity checks (criteria 8-10) are only run for cells that already
    pass criteria 1-7, 11, 12 under the PRIMARY config (DECISIONS.md #11d)."""
    dev = run_development(root, out_dir)
    state, bands, grid_results = dev["state"], dev["bands"], dev["grid_results"]

    grid_results_by_key = {
        (r["mapping_id"], r["side"], r["A"], r["B"], r["C"], r["D"], r["E"]): r for r in grid_results
    }

    near_candidates = [r for r in grid_results
                        if r["n_treat_all"] >= cls.CANDIDATE_MIN_TREAT and r["n_control_matched"] >= cls.CANDIDATE_MIN_CONTROL]

    first_pass = []
    for r in near_candidates:
        gate = cls.gate_12_criteria(r, poc_distance_ok=True, bin_width_support=0, model_support=0, adjacent_sign_support=0)
        first_pass_ok = all(gate[k] for k in gate if k not in (
            "c08_support_2_bin_widths", "c09_support_uniform_and_1_sensitivity", "c10_adjacent_params_same_sign", "ALL_PASS"
        ))
        if first_pass_ok:
            first_pass.append(r)

    candidates = []
    for r in first_pass:
        mapping_id, side = r["mapping_id"], r["side"]
        target_bars_by_leg = state["target_bars_by_leg"]
        series = state["series"]
        leg_df = state["leg_df"]

        treat_rows_side = [x for x in state["ledgers"][mapping_id] if x["side"] == side]
        control_rows_side = [x for x in state["control_rows"][mapping_id] if x["side"] == side]
        t_rows_strat = cls.add_strata(treat_rows_side, bands)
        c_rows_strat = cls.add_strata(control_rows_side, bands)
        cell_rows = grid.apply_cell(t_rows_strat, r["A"], r["B"], r["C"], r["D"], r["E"])
        poc_ok = cls.check_poc_distance_matching(cell_rows, c_rows_strat)

        support = bin_width_and_model_support(leg_df, target_bars_by_leg, series, bands, mapping_id, side,
                                               r["A"], r["B"], r["C"], r["D"], r["E"])
        adj_support = adjacent_parameter_stability(grid_results_by_key, mapping_id, side, r["A"], r["B"], r["C"], r["D"], r["E"])

        gate = cls.gate_12_criteria(r, poc_distance_ok=poc_ok, adjacent_sign_support=adj_support, **support)
        r = dict(r)
        r["gate"] = gate
        r["poc_distance_ok"] = poc_ok
        r.update(support)
        r["adjacent_sign_support"] = adj_support
        if gate["ALL_PASS"]:
            candidates.append(r)

    return {"dev": dev, "near_candidates": near_candidates, "first_pass": first_pass, "candidates": candidates}


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
