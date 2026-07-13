import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import profiles as prof


def make_bars(rows):
    # rows: list of (low, high, close, volume)
    return pd.DataFrame({
        "low": [r[0] for r in rows], "high": [r[1] for r in rows],
        "close": [r[2] for r in rows], "volume": [r[3] for r in rows],
    })


def test_uniform_range_hand_calculated():
    # Bar highs/lows are kept strictly inside bin interiors (never exactly
    # on a bin edge) so the floor-based bin assignment is unambiguous by
    # hand: [100.00,100.25) is bin0, [100.25,100.50) is bin1.
    bars = make_bars([
        (100.01, 100.24, 100.10, 100.0),   # bin0 only -> +100
        (100.01, 100.24, 100.20, 50.0),    # bin0 only -> +50 (bin0 total 150)
        (100.26, 100.49, 100.30, 40.0),    # bin1 only -> +40
        (100.01, 100.49, 100.25, 20.0),    # spans bin0..bin1 -> 10 each
    ])
    p = prof.build_profile(bars, model="UNIFORM_RANGE", bin_width=0.25, va_pct=0.70)
    # bin0: 100+50+10=160 ; bin1: 40+10=50
    assert p["total_volume"] == pytest.approx(210.0)
    assert p["poc"] == pytest.approx(100.125)  # midpoint of bin0, the max-volume bin
    assert p["val"] == pytest.approx(100.00)


def test_typical_price_row_hand_calculated():
    bars = make_bars([
        (100.00, 100.50, 100.00, 100.0),  # HLC3 = (100.5+100.0+100.0)/3=100.1667 -> bin0
        (100.00, 100.50, 100.50, 60.0),   # HLC3 = (100.5+100.0+100.5)/3=100.333 -> bin1
    ])
    p = prof.build_profile(bars, model="TYPICAL_PRICE_ROW", bin_width=0.25, va_pct=0.70)
    assert p["total_volume"] == pytest.approx(160.0)
    # bin0=[100.00,100.25) gets 100, bin1=[100.25,100.50) gets 60 -> poc = bin0
    assert p["poc"] == pytest.approx(100.125)


def test_close_price_row_hand_calculated():
    bars = make_bars([
        (100.00, 100.50, 100.05, 30.0),  # close bin0
        (100.00, 100.50, 100.40, 90.0),  # close bin1
    ])
    p = prof.build_profile(bars, model="CLOSE_PRICE_ROW", bin_width=0.25, va_pct=0.70)
    assert p["total_volume"] == pytest.approx(120.0)
    assert p["poc"] == pytest.approx(100.375)  # bin1 midpoint, the max-volume bin


def test_poc_tie_break_lowest_price_bin():
    bars = make_bars([
        (100.00, 100.25, 100.10, 50.0),
        (100.75, 101.00, 100.90, 50.0),
    ])
    p = prof.build_profile(bars, model="CLOSE_PRICE_ROW", bin_width=0.25, va_pct=0.70)
    assert p["poc"] == pytest.approx(100.125)  # lower of the two equal-volume bins


def test_va_expansion_tie_break_prefers_upper_bin():
    # Three equal-volume bins in a row; POC = middle (max, first found).
    # Expanding from POC with equal vol_below/vol_above should prefer upper.
    bars = make_bars([
        (100.00, 100.25, 100.10, 10.0),
        (100.25, 100.50, 100.40, 30.0),  # POC (unique max)
        (100.50, 100.75, 100.60, 10.0),
        (100.75, 101.00, 100.90, 10.0),
    ])
    p = prof.build_profile(bars, model="CLOSE_PRICE_ROW", bin_width=0.25, va_pct=0.68)
    # total=60, target=40.8; poc bin=30 included; below(10) vs above(10) tie -> prefer upper
    # included becomes 40 (still < 40.8) -> continue: below(10) vs above(10) tie again -> upper
    # included becomes 50 >= 40.8 -> stop. va spans bins [100.25,100.50)..[100.75,101.00)
    assert p["val"] == pytest.approx(100.25)
    assert p["vah"] == pytest.approx(101.00)


def test_va_width_and_bin_count_scale_with_bin_width():
    rows = [(100.00 + 0.25 * i, 100.25 + 0.25 * i, 100.10 + 0.25 * i, 10.0) for i in range(8)]
    bars = make_bars(rows)
    p_fine = prof.build_profile(bars, model="CLOSE_PRICE_ROW", bin_width=0.25, va_pct=0.70)
    p_coarse = prof.build_profile(bars, model="CLOSE_PRICE_ROW", bin_width=1.00, va_pct=0.70)
    assert p_coarse["n_bins"] < p_fine["n_bins"]


@pytest.mark.parametrize("va_pct", prof.VA_PCTS)
def test_va_pct_included_at_least_target(va_pct):
    rng = np.random.default_rng(0)
    n = 50
    lows = 100 + rng.random(n) * 5
    highs = lows + rng.random(n) * 0.5 + 0.01
    closes = lows + (highs - lows) / 2
    vols = rng.random(n) * 100 + 1
    bars = pd.DataFrame({"low": lows, "high": highs, "close": closes, "volume": vols})
    p = prof.build_profile(bars, model="UNIFORM_RANGE", bin_width=0.25, va_pct=va_pct)
    assert p["val"] < p["poc"] < p["vah"] or p["val"] <= p["poc"] <= p["vah"]
