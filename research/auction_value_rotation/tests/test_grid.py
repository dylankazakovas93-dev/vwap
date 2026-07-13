import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import events as ev
from research.auction_value_rotation.src import grid


def test_grid_size_is_432():
    assert grid.GRID_SIZE == 432
    assert len(list(grid.iter_grid_cells())) == 432


def make_excursion_row(rule_confirms: dict, side="long", interaction_kind="BREACH"):
    row = {
        "mapping_id": "M1_ASIA_TO_LONDON", "target_session_leg_id": "T1", "side": side,
        "level": 100.0, "poc": 101.0, "va_width": 1.0, "interaction_kind": interaction_kind,
    }
    if interaction_kind == "BREACH":
        row["rules"] = rule_confirms
        row["successful_discovery"] = all(v is None for v in rule_confirms.values())
    return row


def test_flatten_ledger_skips_touch_and_unconfirmed_rules():
    rows = [
        make_excursion_row({}, interaction_kind="TOUCH"),
        make_excursion_row({"R1_ONE_CLOSE": None, "R2_TWO_CONSECUTIVE_CLOSES": {
            "confirmation_idx": 3, "bars_outside": 2, "breach_depth_ticks": 2.0, "breach_depth_pct_va": 0.05,
            "poc_distance_pct": 0.1, "freshness_hours": 1.0, "confirmation_ts": pd.Timestamp("2024-01-01"),
        }}),
    ]
    flat = grid.flatten_ledger(rows)
    assert len(flat) == 1
    assert flat[0]["rule"] == "R2_TWO_CONSECUTIVE_CLOSES"
    assert flat[0]["bars_outside"] == 2


def test_apply_cell_filters_correctly():
    rows = [
        make_excursion_row({"R1_ONE_CLOSE": {
            "confirmation_idx": 1, "bars_outside": 1, "breach_depth_ticks": 1.0, "breach_depth_pct_va": 0.02,
            "poc_distance_pct": 0.15, "freshness_hours": 1.5, "confirmation_ts": pd.Timestamp("2024-01-01"),
        }}),
        make_excursion_row({"R1_ONE_CLOSE": {
            "confirmation_idx": 10, "bars_outside": 8, "breach_depth_ticks": 1.0, "breach_depth_pct_va": 0.02,
            "poc_distance_pct": 0.15, "freshness_hours": 1.5, "confirmation_ts": pd.Timestamp("2024-01-01"),
        }}),  # bars_outside=8 exceeds B<=5, should be filtered out
    ]
    flat = grid.flatten_ledger(rows)
    cell = grid.apply_cell(flat, "A_GE_1_TICK", 5, "R1_ONE_CLOSE", 0.10, 2.0)
    assert len(cell) == 1
    assert cell[0]["bars_outside"] == 1


def test_apply_cell_freshness_none_means_no_cap():
    rows = [make_excursion_row({"R4_DEPTH_ACCEPTANCE": {
        "confirmation_idx": 1, "bars_outside": 1, "breach_depth_ticks": 1.0, "breach_depth_pct_va": 0.02,
        "poc_distance_pct": 0.0, "freshness_hours": 999.0, "confirmation_ts": pd.Timestamp("2024-01-01"),
    }})]
    flat = grid.flatten_ledger(rows)
    cell_capped = grid.apply_cell(flat, "A_GE_1_TICK", 5, "R4_DEPTH_ACCEPTANCE", 0.0, 2.0)
    cell_uncapped = grid.apply_cell(flat, "A_GE_1_TICK", 5, "R4_DEPTH_ACCEPTANCE", 0.0, None)
    assert len(cell_capped) == 0
    assert len(cell_uncapped) == 1


def test_grid_cell_matches_independent_direct_scan():
    """Spot-check (DECISIONS.md #4): re-derive one grid cell via an
    independent direct pass over a synthetic excursion ledger and confirm
    an identical event set to the flatten+filter grid path."""
    ts = pd.date_range("2024-01-02 09:30", periods=20, freq="1min", tz="UTC")
    lows = np.array([100.5] + [99.6] * 19)
    highs = np.array([100.6] + [99.8] * 19)
    closes = np.array([100.55] + [100.1] * 2 + [99.7] * 17)
    bars = pd.DataFrame({"ts_event": ts, "low": lows, "high": highs, "close": closes,
                          "et_minute": range(9 * 60 + 30, 9 * 60 + 50), "atr20_event": [1.0] * 20})
    prow = pd.Series({"mapping_id": "M1_ASIA_TO_LONDON", "target_session_leg_id": "T1", "source_session_leg_id": "S1",
                       "val": 100.0, "vah": 101.0, "poc": 100.8, "va_width": 1.0,
                       "completion_ts": ts[0] - pd.Timedelta(minutes=1), "expiry_ts": ts[-1] + pd.Timedelta(minutes=5)})
    direct = ev.scan_profile_side(bars, prow, side="long")
    ledger = [direct]
    flat = grid.flatten_ledger(ledger)
    cell = grid.apply_cell(flat, "A_GE_1_TICK", 5, "R2_TWO_CONSECUTIVE_CLOSES", 0.0, None)
    direct_confirmed = direct["rules"]["R2_TWO_CONSECUTIVE_CLOSES"] is not None
    assert (len(cell) == 1) == direct_confirmed
