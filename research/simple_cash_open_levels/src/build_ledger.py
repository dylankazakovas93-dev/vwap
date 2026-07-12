"""Builds the generation-9 level/event/outcome/barrier ledgers for one
instrument. Development partition only. Self-contained.
"""
import os

import numpy as np
import pandas as pd

from . import levels as lv
from . import interactions as ix

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "simple_cash_open_levels", "outputs")

TICK_SIZE = {"ES": 0.25, "NQ": 0.25}


def build_levels_wide(instrument: str, df: pd.DataFrame):
    a1 = lv.build_family_a1_overnight(df)
    a2 = lv.build_family_a2_prior_rth(df)
    b = lv.build_family_b_excursions(df)
    return a1, a2, b


def _native_center_sd(level_id, a1, a2, b, session):
    family, anchor, N, center, k_or_j = lv.LEVEL_META[level_id]
    if family == "family_a1_overnight_vwap":
        return a1.loc[session, "VWAP_ON"], a1.loc[session, "SD_ON"]
    if family == "family_a2_prior_rth_vwap":
        return a2.loc[session, "VWAP_PR"], a2.loc[session, "SD_PR"]
    side = "U" if anchor == "upper_09_30_excursion" else "D"
    return b.loc[session, f"CENTER_{side}_{center}_N{N}"], b.loc[session, f"SD_{side}_N{N}"]


def build_instrument_ledger(instrument: str):
    df = lv.load_dev(instrument, PROC)
    a1, a2, b = build_levels_wide(instrument, df)
    dense = ix.build_dense_bars_with_volume(df, ix.TAU_MAX)
    level_ids = lv.all_level_ids()
    n_levels = len(level_ids)
    tick = TICK_SIZE[instrument]

    O_series = b["O_0930"]
    sessions = sorted(set(a1.index) | set(a2.index) | set(b.index))

    # value matrix builder: level_id -> per-session value series (aligned)
    value_lookup = {}
    for lid in level_ids:
        family, anchor, N, center, k_or_j = lv.LEVEL_META[lid]
        if family == "family_a1_overnight_vwap":
            value_lookup[lid] = a1[lid] if lid in a1.columns else pd.Series(np.nan, index=a1.index)
        elif family == "family_a2_prior_rth_vwap":
            value_lookup[lid] = a2[lid] if lid in a2.columns else pd.Series(np.nan, index=a2.index)
        else:
            value_lookup[lid] = b[lid]

    levels_rows = []
    events_rows = []
    outcomes_rows = []
    barriers_rows = []

    for s in sessions:
        arrs = dense.get(s)
        touch_window_complete = arrs is not None and ix._window_complete(arrs, 0, 119, ("open", "high", "low", "close"))
        outcome_window_complete = arrs is not None and ix._window_complete(arrs, 0, 239, ("open", "high", "low", "close"))
        O = O_series.get(s, np.nan)

        V = np.array([value_lookup[lid].get(s, np.nan) for lid in level_ids])
        valid = np.isfinite(V)

        touched = np.zeros(n_levels, dtype=bool)
        first_tau = np.full(n_levels, -1, dtype=int)
        if touch_window_complete:
            low120 = arrs["low"][0:120]
            high120 = arrs["high"][0:120]
            Vm = np.where(valid, V, np.nan)
            cond = (low120[:, None] <= Vm[None, :]) & (high120[:, None] >= Vm[None, :])
            any_touch = cond.any(axis=0)
            idx = cond.argmax(axis=0)
            touched = any_touch
            first_tau = np.where(any_touch, idx, -1)

        for i, lid in enumerate(level_ids):
            family, anchor, N, center, k_or_j = lv.LEVEL_META[lid]
            native_center, native_sd = (np.nan, np.nan)
            if valid[i]:
                native_center, native_sd = _native_center_sd(lid, a1, a2, b, s)
            orientation = ix.orientation_for(V[i], O, tick) if valid[i] else None

            invalid_reason = ""
            if not valid[i]:
                invalid_reason = "level_value_unavailable"
            elif not np.isfinite(O):
                invalid_reason = "open_unavailable"

            level_row = {
                "instrument": instrument, "session_date": s, "level_id": lid,
                "level_family": family, "anchor_type": anchor,
                "side_formula": "upper" if "upper" in lid else ("lower" if "lower" in lid else "vwap_j"),
                "lookback_N": N, "center_estimator": center,
                "k_std": k_or_j if family == "family_b_excursion" else None,
                "vwap_j": k_or_j if family != "family_b_excursion" else None,
                "level_value": V[i], "O_0930": O, "native_center": native_center, "native_sd": native_sd,
                "level_valid": bool(valid[i] and np.isfinite(O)), "invalid_reason": invalid_reason,
                "orientation": orientation,
                "distance_from_open_points": (V[i] - O) if (valid[i] and np.isfinite(O)) else np.nan,
                "distance_from_open_native_sd": ((V[i] - O) / native_sd) if (valid[i] and np.isfinite(O) and native_sd and np.isfinite(native_sd) and native_sd > 0) else np.nan,
                "touch_window_complete": bool(touch_window_complete),
                "outcome_window_complete": bool(outcome_window_complete),
            }

            is_touched = bool(valid[i] and touch_window_complete and touched[i])
            level_row["touched"] = is_touched
            if is_touched:
                T = int(first_tau[i])
                et_minute = ix.TOUCH_START + T
                level_row["first_touch_minute"] = et_minute
                level_row["first_touch_elapsed_minutes"] = T + 1
                level_row["touch_bar_index"] = T
                level_row["touch_by_30"] = int(T <= 29)
                level_row["touch_by_60"] = int(T <= 59)
                level_row["touch_by_120"] = 1
                timing_bin = ix.timing_bin_for_tau(T)

                O_t, H_t, L_t, C_t, Vol_t = arrs["open"][T], arrs["high"][T], arrs["low"][T], arrs["close"][T], arrs["volume"][T]
                morph = ix.same_bar_morphology(orientation, C_t, V[i]) if orientation in ("UPPER_LEVEL", "LOWER_LEVEL") else None

                event_row = {"instrument": instrument, "session_date": s, "level_id": lid,
                            "level_family": family, "orientation": orientation,
                            "first_touch_minute": et_minute, "first_touch_elapsed_minutes": T + 1,
                            "touch_bar_index": T, "touch_by_30": level_row["touch_by_30"],
                            "touch_by_60": level_row["touch_by_60"], "touch_by_120": 1,
                            "timing_bin": timing_bin, "same_bar_morphology": morph}
                event_row.update(ix.touch_bar_fields(O_t, H_t, L_t, C_t, Vol_t, V[i]))
                events_rows.append(event_row)

                if outcome_window_complete and orientation in ("UPPER_LEVEL", "LOWER_LEVEL"):
                    for h in ix.HORIZONS:
                        orow = {"instrument": instrument, "session_date": s, "level_id": lid, "horizon": h}
                        orow.update(ix.raw_outcomes(arrs, T, V[i], h))
                        orow.update(ix.oriented_outcomes(arrs, T, V[i], h, orientation, native_sd))
                        orow.update(ix.directional_close_recross(arrs, T, h, orientation, V[i]))
                        outcomes_rows.append(orow)
                        if native_sd and np.isfinite(native_sd) and native_sd > 0:
                            for bnd in ix.BARRIER_B:
                                brow = {"instrument": instrument, "session_date": s, "level_id": lid,
                                       "horizon": h, "b": bnd}
                                brow.update(ix.barrier_outcomes(arrs, T, h, bnd, orientation, V[i], native_sd))
                                barriers_rows.append(brow)
            else:
                level_row["first_touch_minute"] = np.nan
                level_row["first_touch_elapsed_minutes"] = np.nan
                level_row["touch_bar_index"] = np.nan
                level_row["touch_by_30"] = 0
                level_row["touch_by_60"] = 0
                level_row["touch_by_120"] = 0

            levels_rows.append(level_row)

    levels_tbl = pd.DataFrame(levels_rows)
    events_tbl = pd.DataFrame(events_rows)
    outcomes_tbl = pd.DataFrame(outcomes_rows)
    barriers_tbl = pd.DataFrame(barriers_rows)
    return levels_tbl, events_tbl, outcomes_tbl, barriers_tbl


def main():
    os.makedirs(OUT, exist_ok=True)
    for instrument in ("ES", "NQ"):
        levels_tbl, events_tbl, outcomes_tbl, barriers_tbl = build_instrument_ledger(instrument)
        levels_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_levels.parquet"), index=False)
        events_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_events.parquet"), index=False)
        outcomes_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_outcomes.parquet"), index=False)
        barriers_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_barriers.parquet"), index=False)
        print(f"{instrument}: {len(levels_tbl)} level rows, {len(events_tbl)} touch events, "
             f"{len(outcomes_tbl)} outcome rows, {len(barriers_tbl)} barrier rows", flush=True)


if __name__ == "__main__":
    main()
