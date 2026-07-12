"""Builds the generation-10 level/event/outcome/barrier ledgers for one
instrument (NQ primary, ES negative control). Development partition
only. Self-contained.
"""
import os

import numpy as np
import pandas as pd

from . import levels as lv
from . import interactions as ix

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "nq_excursion_level_timing", "outputs")


def build_instrument_ledger(instrument: str):
    df = lv.load_dev(instrument, PROC)
    levels_wide = lv.build_levels(df)
    dense = ix.build_dense_bars_with_volume(df, ix.TAU_MAX)
    level_ids = lv.level_ids()
    n_levels = len(level_ids)

    sessions = sorted(levels_wide.index)
    levels_rows = []
    events_rows = []
    outcomes_rows = []
    barriers_rows = []

    for s in sessions:
        arrs = dense.get(s)
        touch_window_complete = arrs is not None and ix._window_complete(arrs, 0, 119, ("open", "high", "low", "close"))
        outcome_window_complete = arrs is not None and ix._window_complete(arrs, 0, 239, ("open", "high", "low", "close"))
        O = levels_wide.loc[s, "O_0930"]
        mean_U, mean_D = levels_wide.loc[s, "mean_U_10"], levels_wide.loc[s, "mean_D_10"]
        sd_U, sd_D = levels_wide.loc[s, "sd_U_10"], levels_wide.loc[s, "sd_D_10"]
        year = pd.Timestamp(s).year

        V = np.array([levels_wide.loc[s, lid] for lid in level_ids])
        valid = np.isfinite(V) & np.isfinite(O)

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
            side, k = lv.LEVEL_META[lid]
            native_mean = mean_U if side == "upper" else mean_D
            native_sd = sd_U if side == "upper" else sd_D

            invalid_reason = "" if valid[i] else ("level_value_unavailable" if not np.isfinite(V[i]) else "open_unavailable")

            level_row = {
                "instrument": instrument, "session_date": s, "calendar_year": year,
                "level_id": lid, "side": side, "k_std": k,
                "O_0930": O, "mean_U_10": mean_U, "mean_D_10": mean_D,
                "sd_U_10": sd_U, "sd_D_10": sd_D,
                "native_mean": native_mean, "native_sd": native_sd,
                "level_value": V[i], "level_valid": bool(valid[i]), "invalid_reason": invalid_reason,
                "distance_from_open_points": (V[i] - O) if valid[i] else np.nan,
                "distance_from_open_native_sd": ((V[i] - O) / native_sd) if (valid[i] and native_sd and np.isfinite(native_sd) and native_sd > 0) else np.nan,
                "touch_window_complete": bool(touch_window_complete),
                "outcome_window_complete": bool(outcome_window_complete),
            }

            is_touched = bool(valid[i] and touch_window_complete and touched[i])
            level_row["first_touch_found"] = is_touched
            if is_touched:
                T = int(first_tau[i])
                et_minute = ix.TOUCH_START + T
                elapsed_bar = T + 1
                level_row["first_touch_et_minute"] = et_minute
                level_row["first_touch_elapsed_bar"] = elapsed_bar
                level_row["first_touch_exact_bin"] = ix.timing_bin_for_tau(T)

                O_t, H_t, L_t, C_t, Vol_t = arrs["open"][T], arrs["high"][T], arrs["low"][T], arrs["close"][T], arrs["volume"][T]
                morph = ix.same_bar_morphology(side, C_t, V[i])

                event_row = {"instrument": instrument, "session_date": s, "calendar_year": year,
                            "level_id": lid, "side": side, "k_std": k,
                            "first_touch_et_minute": et_minute, "first_touch_elapsed_bar": elapsed_bar,
                            "first_touch_exact_bin": ix.timing_bin_for_tau(T),
                            "same_bar_morphology": morph}
                event_row.update(ix.touch_bar_fields(O_t, H_t, L_t, C_t, Vol_t, V[i]))
                events_rows.append(event_row)

                if outcome_window_complete:
                    for H in ix.HORIZONS:
                        orow = {"instrument": instrument, "session_date": s, "calendar_year": year,
                               "level_id": lid, "side": side, "k_std": k,
                               "first_touch_elapsed_bar": elapsed_bar, "horizon": H}
                        orow.update(ix.raw_outcomes(arrs, T, V[i], H))
                        orow.update(ix.oriented_outcomes(arrs, T, V[i], H, side, native_sd))
                        orow.update(ix.directional_close_recross(arrs, T, H, side, V[i]))
                        outcomes_rows.append(orow)
                        if native_sd and np.isfinite(native_sd) and native_sd > 0:
                            for bnd in ix.BARRIER_B:
                                brow = {"instrument": instrument, "session_date": s, "calendar_year": year,
                                       "level_id": lid, "side": side, "k_std": k,
                                       "first_touch_elapsed_bar": elapsed_bar, "horizon": H, "b": bnd}
                                brow.update(ix.barrier_outcomes(arrs, T, H, bnd, side, V[i], native_sd))
                                barriers_rows.append(brow)
            else:
                level_row["first_touch_et_minute"] = np.nan
                level_row["first_touch_elapsed_bar"] = np.nan
                level_row["first_touch_exact_bin"] = None

            levels_rows.append(level_row)

    levels_tbl = pd.DataFrame(levels_rows)
    events_tbl = pd.DataFrame(events_rows)
    outcomes_tbl = pd.DataFrame(outcomes_rows)
    barriers_tbl = pd.DataFrame(barriers_rows)
    return levels_tbl, events_tbl, outcomes_tbl, barriers_tbl


def main():
    os.makedirs(OUT, exist_ok=True)
    for instrument in ("NQ", "ES"):
        levels_tbl, events_tbl, outcomes_tbl, barriers_tbl = build_instrument_ledger(instrument)
        levels_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_levels.parquet"), index=False)
        events_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_events.parquet"), index=False)
        outcomes_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_outcomes.parquet"), index=False)
        barriers_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_barriers.parquet"), index=False)
        print(f"{instrument}: {len(levels_tbl)} level rows, {len(events_tbl)} touch events, "
             f"{len(outcomes_tbl)} outcome rows, {len(barriers_tbl)} barrier rows", flush=True)


if __name__ == "__main__":
    main()
