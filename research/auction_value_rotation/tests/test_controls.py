import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import controls as ctl


def make_bars(closes, start="2024-01-02 09:30"):
    n = len(closes)
    ts = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({
        "ts_event": ts, "close": closes, "low": [c - 0.1 for c in closes], "high": [c + 0.1 for c in closes],
        "local_rank": range(1, n + 1), "et_minute": range(9 * 60 + 30, 9 * 60 + 30 + n), "atr20_event": [1.0] * n,
    })


def test_touch_controls_filters_touch_only():
    rows = [{"interaction_kind": "TOUCH"}, {"interaction_kind": "BREACH"}, {"interaction_kind": None}]
    out = ctl.build_touch_controls(rows)
    assert len(out) == 1


def test_successful_discovery_controls_filters_breach_and_flag():
    rows = [
        {"interaction_kind": "BREACH", "successful_discovery": True},
        {"interaction_kind": "BREACH", "successful_discovery": False},
        {"interaction_kind": "TOUCH", "successful_discovery": True},
    ]
    out = ctl.build_successful_discovery_controls(rows)
    assert len(out) == 1


def test_matched_inside_state_picks_last_qualifying_bar_no_recent_breach():
    # poc=101, val=100, vah=102; long half is (val,poc)=(100,101)
    closes = [100.5] * 5 + [100.6] * 5  # all inside long-half the whole time
    bars = make_bars(closes)
    mapping_df = pd.DataFrame([{
        "mapping_id": "M1_ASIA_TO_LONDON", "target_session_leg_id": "T1",
        "poc": 101.0, "val": 100.0, "vah": 102.0, "va_width": 2.0,
        "completion_ts": bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
        "expiry_ts": bars["ts_event"].iloc[-1] + pd.Timedelta(minutes=5),
    }])
    target_bars_by_leg = {"T1": bars}
    breach_ts_by_profile_side = {("T1", "long"): [], ("T1", "short"): []}
    out = ctl.build_matched_inside_state_controls(mapping_df, target_bars_by_leg, breach_ts_by_profile_side)
    long_rows = [r for r in out if r["side"] == "long"]
    assert len(long_rows) == 1
    assert long_rows[0]["confirmation_close"] == pytest.approx(100.6)  # last bar


def test_matched_inside_state_excludes_bars_within_lookback_of_breach():
    closes = [100.5] * 10
    bars = make_bars(closes)
    mapping_df = pd.DataFrame([{
        "mapping_id": "M1_ASIA_TO_LONDON", "target_session_leg_id": "T1",
        "poc": 101.0, "val": 100.0, "vah": 102.0, "va_width": 2.0,
        "completion_ts": bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
        "expiry_ts": bars["ts_event"].iloc[-1] + pd.Timedelta(minutes=5),
    }])
    target_bars_by_leg = {"T1": bars}
    # a breach occurred exactly at the next-to-last bar's timestamp -> both the
    # last bar (1 min after) and the next-to-last bar itself (0 min after,
    # inclusive lower bound) fall inside the 6h lookback and are excluded; the
    # scan walks backward from the end, so it should fall through to the
    # third-to-last bar, which precedes the breach entirely
    recent_breach_ts = bars["ts_event"].iloc[-2]
    breach_ts_by_profile_side = {("T1", "long"): [recent_breach_ts], ("T1", "short"): []}
    out = ctl.build_matched_inside_state_controls(mapping_df, target_bars_by_leg, breach_ts_by_profile_side)
    long_rows = [r for r in out if r["side"] == "long"]
    assert len(long_rows) == 1
    assert long_rows[0]["confirmation_ts"] == bars["ts_event"].iloc[-3]


def test_matched_inside_state_no_qualifying_bar_returns_nothing_for_that_side():
    closes = [102.5] * 5  # always above vah -> never inside either half
    bars = make_bars(closes)
    mapping_df = pd.DataFrame([{
        "mapping_id": "M1_ASIA_TO_LONDON", "target_session_leg_id": "T1",
        "poc": 101.0, "val": 100.0, "vah": 102.0, "va_width": 2.0,
        "completion_ts": bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
        "expiry_ts": bars["ts_event"].iloc[-1] + pd.Timedelta(minutes=5),
    }])
    target_bars_by_leg = {"T1": bars}
    breach_ts_by_profile_side = {("T1", "long"): [], ("T1", "short"): []}
    out = ctl.build_matched_inside_state_controls(mapping_df, target_bars_by_leg, breach_ts_by_profile_side)
    assert len(out) == 0
