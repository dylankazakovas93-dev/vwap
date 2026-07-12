"""Builds validation ledgers for one instrument, reusing generation 10's
frozen level/touch/outcome/barrier formulas exactly (imported, not
re-derived). Only H in {1,2} and b=1.0 are computed (the only values any
named frozen cell in this validation needs). Level construction uses the
FULL available history (2018+) for causal warm-up; level/touch/outcome
rows are filtered to session_date >= 2023-01-01 before being returned.
"""
import os

import numpy as np
import pandas as pd

from research.nq_excursion_level_timing.src import levels as lv10
from research.nq_excursion_level_timing.src import interactions as ix10

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "validation_nq_excursion_continuation", "outputs")

VALIDATION_START = pd.Timestamp("2023-01-01")
NEEDED_HORIZONS = (1, 2)
NEEDED_B = (1.0,)


def load_full_history(instrument: str) -> pd.DataFrame:
    """No DEV_END assertion -- reads all available history so causal
    10-session warm-up crosses the 2022/2023 boundary correctly."""
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    assert df["session_date"].min() >= lv10.DEV_START
    return df


def build_instrument_ledger(instrument: str):
    """Returns (levels_tbl, events_tbl, outcomes_tbl, barriers_tbl,
    max_session_date) -- all four tables restricted to session_date >=
    2023-01-01; levels_wide/dense bars are built over the FULL history so
    the first 2023 sessions have a fully warmed-up causal input."""
    df = load_full_history(instrument)
    max_session_date = df["session_date"].max()
    levels_wide = lv10.build_levels(df)  # unmodified generation-10 formula, full history
    dense = ix10.build_dense_bars_with_volume(df, ix10.TAU_MAX)
    level_ids = lv10.level_ids()
    n_levels = len(level_ids)

    sessions = sorted(s for s in levels_wide.index if s >= VALIDATION_START)
    levels_rows, events_rows, outcomes_rows, barriers_rows = [], [], [], []

    for s in sessions:
        arrs = dense.get(s)
        touch_window_complete = arrs is not None and ix10._window_complete(arrs, 0, 119, ("open", "high", "low", "close"))
        outcome_window_complete = arrs is not None and ix10._window_complete(arrs, 0, 239, ("open", "high", "low", "close"))
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
            side, k = lv10.LEVEL_META[lid]
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
                "touch_window_complete": bool(touch_window_complete),
                "outcome_window_complete": bool(outcome_window_complete),
            }
            is_touched = bool(valid[i] and touch_window_complete and touched[i])
            level_row["first_touch_found"] = is_touched
            if is_touched:
                T = int(first_tau[i])
                et_minute = ix10.TOUCH_START + T
                elapsed_bar = T + 1
                level_row["first_touch_et_minute"] = et_minute
                level_row["first_touch_elapsed_bar"] = elapsed_bar

                O_t, H_t, L_t, C_t, Vol_t = arrs["open"][T], arrs["high"][T], arrs["low"][T], arrs["close"][T], arrs["volume"][T]
                morph = ix10.same_bar_morphology(side, C_t, V[i])
                event_row = {"instrument": instrument, "session_date": s, "calendar_year": year,
                            "level_id": lid, "side": side, "k_std": k,
                            "first_touch_et_minute": et_minute, "first_touch_elapsed_bar": elapsed_bar,
                            "same_bar_morphology": morph}
                event_row.update(ix10.touch_bar_fields(O_t, H_t, L_t, C_t, Vol_t, V[i]))
                events_rows.append(event_row)

                if outcome_window_complete:
                    for H in NEEDED_HORIZONS:
                        orow = {"instrument": instrument, "session_date": s, "calendar_year": year,
                               "level_id": lid, "side": side, "k_std": k,
                               "first_touch_elapsed_bar": elapsed_bar, "horizon": H}
                        orow.update(ix10.raw_outcomes(arrs, T, V[i], H))
                        orow.update(ix10.oriented_outcomes(arrs, T, V[i], H, side, native_sd))
                        orow.update(ix10.directional_close_recross(arrs, T, H, side, V[i]))
                        outcomes_rows.append(orow)
                        if native_sd and np.isfinite(native_sd) and native_sd > 0:
                            for bnd in NEEDED_B:
                                brow = {"instrument": instrument, "session_date": s, "calendar_year": year,
                                       "level_id": lid, "side": side, "k_std": k,
                                       "first_touch_elapsed_bar": elapsed_bar, "horizon": H, "b": bnd}
                                brow.update(ix10.barrier_outcomes(arrs, T, H, bnd, side, V[i], native_sd))
                                barriers_rows.append(brow)
            else:
                level_row["first_touch_et_minute"] = np.nan
                level_row["first_touch_elapsed_bar"] = np.nan
            levels_rows.append(level_row)

    levels_tbl = pd.DataFrame(levels_rows)
    events_tbl = pd.DataFrame(events_rows)
    outcomes_tbl = pd.DataFrame(outcomes_rows)
    barriers_tbl = pd.DataFrame(barriers_rows)
    for tbl in (levels_tbl, events_tbl, outcomes_tbl, barriers_tbl):
        if len(tbl):
            assert tbl["session_date"].min() >= VALIDATION_START, "2018-2022 session leaked into validation outcome"
    return levels_tbl, events_tbl, outcomes_tbl, barriers_tbl, max_session_date


def build_full_history_barriers_for_state(instrument: str):
    """For the rolling-state test only: builds the b=1.0/H=30 barrier
    stream over the FULL history (2018+), so early-2023 current events
    can draw a causal prior state from legitimate pre-2023 touches
    (DECISIONS.md #9). Returns (barriers_tbl_full, events_tbl_full) with
    NO validation-partition filter applied -- callers must filter the
    CURRENT-event axis themselves."""
    df = load_full_history(instrument)
    levels_wide = lv10.build_levels(df)
    dense = ix10.build_dense_bars_with_volume(df, ix10.TAU_MAX)
    level_ids = lv10.level_ids()
    n_levels = len(level_ids)

    sessions = sorted(levels_wide.index)
    barriers_rows = []
    events_rows = []

    for s in sessions:
        arrs = dense.get(s)
        touch_window_complete = arrs is not None and ix10._window_complete(arrs, 0, 29, ("open", "high", "low", "close"))
        outcome_window_complete = arrs is not None and ix10._window_complete(arrs, 0, 59, ("open", "high", "low", "close"))
        O = levels_wide.loc[s, "O_0930"]
        mean_U, mean_D = levels_wide.loc[s, "mean_U_10"], levels_wide.loc[s, "mean_D_10"]
        sd_U, sd_D = levels_wide.loc[s, "sd_U_10"], levels_wide.loc[s, "sd_D_10"]
        year = pd.Timestamp(s).year
        V = np.array([levels_wide.loc[s, lid] for lid in level_ids])
        valid = np.isfinite(V) & np.isfinite(O)

        if not touch_window_complete:
            continue
        low30 = arrs["low"][0:30]
        high30 = arrs["high"][0:30]
        Vm = np.where(valid, V, np.nan)
        cond = (low30[:, None] <= Vm[None, :]) & (high30[:, None] >= Vm[None, :])
        any_touch = cond.any(axis=0)
        idx = cond.argmax(axis=0)

        for i, lid in enumerate(level_ids):
            if not (valid[i] and any_touch[i]):
                continue
            T = int(idx[i])
            if T > 29:
                continue
            side, k = lv10.LEVEL_META[lid]
            native_sd = sd_U if side == "upper" else sd_D
            if not (native_sd and np.isfinite(native_sd) and native_sd > 0):
                continue
            if not outcome_window_complete:
                continue
            b_out = ix10.barrier_outcomes(arrs, T, 30, 1.0, side, V[i], native_sd)
            barriers_rows.append({"instrument": instrument, "level_id": lid, "session_date": s,
                                 "calendar_year": year, "b": 1.0, "horizon": 30,
                                 "first_touch_elapsed_bar": T + 1,
                                 "barrier_first_outcome": b_out["barrier_first_outcome"]})
    return pd.DataFrame(barriers_rows)
