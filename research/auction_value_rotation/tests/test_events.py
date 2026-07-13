import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import events as ev


def make_bars(rows, start="2024-01-02 09:30"):
    # rows: list of (low, high, close)
    ts = pd.date_range(start, periods=len(rows), freq="1min", tz="UTC")
    return pd.DataFrame({
        "ts_event": ts, "low": [r[0] for r in rows], "high": [r[1] for r in rows],
        "close": [r[2] for r in rows], "et_minute": list(range(9 * 60 + 30, 9 * 60 + 30 + len(rows))),
        "atr20_event": [1.0] * len(rows),
    })


def profile_row(level_val, level_vah, poc, va_width, completion_ts, expiry_ts, mapping_id="M1_ASIA_TO_LONDON",
                 target="T1", source="S1"):
    return pd.Series({
        "mapping_id": mapping_id, "target_session_leg_id": target, "source_session_leg_id": source,
        "val": level_val, "vah": level_vah, "poc": poc, "va_width": va_width,
        "completion_ts": completion_ts, "expiry_ts": expiry_ts,
    })


def test_first_interaction_touch_vs_breach_long():
    lows = np.array([100.5, 100.0, 99.9])
    highs = np.array([101.0, 100.6, 100.2])
    # level=100.0 (VAL); bar0 low=100.5 doesn't reach; bar1 low=100.0 exact touch
    idx, kind = ev.first_interaction(lows, highs, level=100.0, side="long")
    assert idx == 1 and kind == "TOUCH"

    lows2 = np.array([100.5, 99.8, 99.9])
    idx2, kind2 = ev.first_interaction(lows2, highs, level=100.0, side="long")
    assert idx2 == 1 and kind2 == "BREACH"


def test_first_interaction_touch_vs_breach_short():
    highs = np.array([99.0, 100.0, 100.3])
    lows = np.array([98.5, 99.5, 99.8])
    idx, kind = ev.first_interaction(lows, highs, level=100.0, side="short")
    assert idx == 1 and kind == "TOUCH"

    highs2 = np.array([99.0, 100.2, 100.3])
    idx2, kind2 = ev.first_interaction(lows, highs2, level=100.0, side="short")
    assert idx2 == 1 and kind2 == "BREACH"


def test_r1_one_close_confirmation():
    closes = np.array([99.5, 99.6, 100.3, 100.4])  # breach at idx0/1, close>=level+TICK at idx2 (100.3>=100.25)
    idx = ev._find_confirmation(closes, breach_idx=0, level=100.0, va_width=1.0, side="long", rule="R1_ONE_CLOSE")
    assert idx == 2


def test_r2_two_consecutive_closes():
    # inside-strict = close>level; bars: 99.9(out),100.1(in),99.9(out),100.1(in),100.2(in)
    closes = np.array([99.9, 100.1, 99.9, 100.1, 100.2])
    idx = ev._find_confirmation(closes, breach_idx=0, level=100.0, va_width=1.0, side="long", rule="R2_TWO_CONSECUTIVE_CLOSES")
    assert idx == 4  # second consecutive inside close is bar index 4 (bars 3,4 both inside)


def test_r3_two_of_three_closes_long():
    closes = np.array([99.5, 100.1, 99.9, 100.1, 100.2])
    idx = ev._find_confirmation(closes, breach_idx=0, level=100.0, va_width=1.0, side="long", rule="R3_TWO_OF_THREE_CLOSES")
    # inside-strict(long) = close>100.0; window[1:4]=[100.1,99.9,100.1] has 2 inside -> confirm at last bar of window = idx 3
    assert idx == 3


def test_r4_depth_acceptance():
    closes = np.array([99.5, 99.6, 100.05, 100.11])
    # va_width=1.0 -> depth=0.10; need close>=100.10 -> idx3
    idx = ev._find_confirmation(closes, breach_idx=0, level=100.0, va_width=1.0, side="long", rule="R4_DEPTH_ACCEPTANCE")
    assert idx == 3


def test_scan_profile_side_side_ok_disqualifies_close_past_poc():
    # Long breach that reaccepts but confirmation close is ABOVE poc -> disqualified (side_ok fails)
    bars = make_bars([
        (99.5, 100.6, 100.5),   # breach (low<VAL=100.0)
        (100.6, 100.9, 100.8),  # confirmation close 100.8 > poc(100.3) -> side_ok fails for R1
    ])
    prow = profile_row(level_val=100.0, level_vah=101.0, poc=100.3, va_width=1.0,
                        completion_ts=bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
                        expiry_ts=bars["ts_event"].iloc[-1] + pd.Timedelta(minutes=5))
    result = ev.scan_profile_side(bars, prow, side="long")
    assert result["interaction_kind"] == "BREACH"
    assert result["rules"]["R1_ONE_CLOSE"] is None  # disqualified: close > poc


def test_scan_profile_side_successful_discovery_when_no_rule_confirms():
    bars = make_bars([
        (99.5, 99.6, 99.55),
        (99.4, 99.5, 99.45),
        (99.3, 99.4, 99.35),
    ])
    prow = profile_row(level_val=100.0, level_vah=101.0, poc=100.5, va_width=1.0,
                        completion_ts=bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
                        expiry_ts=bars["ts_event"].iloc[-1] + pd.Timedelta(minutes=5))
    result = ev.scan_profile_side(bars, prow, side="long")
    assert result["interaction_kind"] == "BREACH"
    assert result["successful_discovery"] is True
    assert all(v is None for v in result["rules"].values())


def test_scan_profile_side_long_short_symmetry():
    long_bars = make_bars([(99.5, 100.6, 100.5), (100.6, 100.9, 100.75)])
    short_bars = make_bars([(99.4, 100.5, 99.5), (99.1, 99.4, 99.25)])
    prow_long = profile_row(level_val=100.0, level_vah=101.0, poc=100.3, va_width=1.0,
                             completion_ts=long_bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
                             expiry_ts=long_bars["ts_event"].iloc[-1] + pd.Timedelta(minutes=5))
    prow_short = profile_row(level_val=99.0, level_vah=100.0, poc=99.7, va_width=1.0,
                              completion_ts=short_bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
                              expiry_ts=short_bars["ts_event"].iloc[-1] + pd.Timedelta(minutes=5))
    rl = ev.scan_profile_side(long_bars, prow_long, side="long")
    rs = ev.scan_profile_side(short_bars, prow_short, side="short")
    assert rl["interaction_kind"] == "BREACH" and rs["interaction_kind"] == "BREACH"
    assert (rl["rules"]["R1_ONE_CLOSE"] is None) == (rs["rules"]["R1_ONE_CLOSE"] is None)


def test_confirmation_after_expiry_disqualified():
    bars = make_bars([
        (99.5, 99.6, 99.55),
        (100.3, 100.4, 100.35),  # would confirm R1 here, but this is after expiry
    ])
    prow = profile_row(level_val=100.0, level_vah=101.0, poc=100.5, va_width=1.0,
                        completion_ts=bars["ts_event"].iloc[0] - pd.Timedelta(minutes=1),
                        expiry_ts=bars["ts_event"].iloc[1])  # expires exactly at bar1's ts -> bar1 excluded
    result = ev.scan_profile_side(bars, prow, side="long")
    assert result["rules"]["R1_ONE_CLOSE"] is None
