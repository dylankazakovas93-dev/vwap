import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.episodes import _find_outer, _find_reclaim, build_episode_ledger
from src.outcomes import fixed_horizon_returns, symmetric_first_passage
from src.opening_scale import build_opening_tables, build_bar_frames


def make_dense_bars(closes, opens=None, highs=None, lows=None, n=None):
    n = n or len(closes)
    closes = np.array(closes + [np.nan] * (n - len(closes)), dtype=float)
    opens = np.array((opens or closes[:len(closes)].tolist()) + [np.nan] * (n - len(opens or closes)), dtype=float) if opens else closes.copy()
    highs = np.array(highs + [np.nan] * (n - len(highs)), dtype=float) if highs else closes + 0.1
    lows = np.array(lows + [np.nan] * (n - len(lows)), dtype=float) if lows else closes - 0.1
    return {"open": opens, "high": highs, "low": lows, "close": closes,
            "ts_event": np.arange(n)}


def test_find_outer_lower_and_upper():
    # O=100. lower excursion: low breaches 100 - 2*S at tau=3 (S=1 => thr=98)
    n = 10
    bars = make_dense_bars(closes=[100, 99.5, 99, 98.5, 98.2] + [98] * (n - 5))
    bars["low"] = bars["close"] - 0.5
    bars["low"][3] = 97.9  # breach at tau=3 (thr 98)
    S_row = np.full(n, 1.0)
    out = _find_outer(bars, S_row, A=2.0)
    assert out["direction"] == "lower"
    assert out["tau"] == 3

    bars2 = make_dense_bars(closes=[100, 100.5, 101, 101.5, 102.2] + [102] * (n - 5))
    bars2["high"] = bars2["close"] + 0.5
    bars2["high"][3] = 102.1  # breach at tau=3 (thr 100+2=102)
    out2 = _find_outer(bars2, S_row, A=2.0)
    assert out2["direction"] == "upper"
    assert out2["tau"] == 3


def test_find_outer_ambiguous_same_bar():
    n = 6
    bars = make_dense_bars(closes=[100] * n)
    bars["high"][2] = 105.0
    bars["low"][2] = 95.0
    S_row = np.full(n, 1.0)
    out = _find_outer(bars, S_row, A=2.0)
    assert out["direction"] == "AMBIGUOUS_DIRECTION"


def test_find_reclaim_excludes_same_bar_as_outer():
    # lower excursion at tau=2 (O=100,S=1,A=2 -> outer thr=98); reclaim B=0.5A=1 -> level=99
    n = 8
    bars = make_dense_bars(closes=[100, 99, 97.5, 97.5, 99.2, 99.5, 99.5, 99.5])
    t = _find_reclaim(bars, tau_outer=2, direction="lower", O=100.0, S=1.0, B=1.0)
    # bar 2 itself closes at 97.5 (< 99) -> must NOT count; bar 4 closes 99.2 >= 99 -> reclaim
    assert t == 4


def test_fixed_horizon_returns_direction_alignment():
    n = 20
    bars = make_dense_bars(closes=list(range(100, 100 + n)))  # rising 1pt/bar
    bars["open"] = bars["close"] - 1  # open = prior close roughly
    res = fixed_horizon_returns(bars, origin_tau=5, direction=1)
    entry = bars["open"][5]
    assert res["fret_1"] == pytest.approx((bars["close"][6] - entry) * 1)
    res_short = fixed_horizon_returns(bars, origin_tau=5, direction=-1)
    assert res_short["fret_1"] == pytest.approx((bars["close"][6] - entry) * -1)
    assert res_short["fret_1"] == -res["fret_1"]


def test_symmetric_first_passage_fair_barriers():
    n = 30
    bars = make_dense_bars(closes=[100.0] * n)
    bars["open"] = bars["close"].copy()
    bars["high"] = bars["close"] + 0.1
    bars["low"] = bars["close"] - 0.1
    # push price up by 5 points at tau=10 (favourable for direction=+1, M=5, f=0.5 -> barrier=2.5)
    bars["high"][10] = 103.0  # hits +2.5 barrier from entry=100
    res = symmetric_first_passage(bars, origin_tau=5, direction=1, M=5.0, S=5.0)
    assert res["fp_0.5"][0] == "CONT"
    # mirror: direction=-1 with same absolute move should read as REV (adverse)
    res2 = symmetric_first_passage(bars, origin_tau=5, direction=-1, M=5.0, S=5.0)
    assert res2["fp_0.5"][0] == "REV"


def test_opening_scale_causal_no_lookahead():
    # 25 sessions; session index 0..24; the scale for session 24 must not
    # depend on session 24's own displacement.
    rows = []
    for i in range(25):
        sd = pd.Timestamp("2020-01-01") + pd.Timedelta(days=i)
        base_ts = sd - pd.Timedelta(hours=1)  # arbitrary
        for tau in range(3):
            rows.append({"session_date": sd, "et_minute": 570 + tau,
                        "open": 100.0, "close": 100.0 + (tau * (i + 1)),
                        "ts_event": base_ts + pd.Timedelta(minutes=tau)})
    df = pd.DataFrame(rows)
    O, S = build_opening_tables(df)
    # tau=1 displacement grows with i (i+1); S for session 24 uses sessions 0..23 (i=0..23)
    med_expected = 1.4826 * np.median([1 * (i + 1) for i in range(24)])
    assert S.loc[pd.Timestamp("2020-01-01") + pd.Timedelta(days=24), 1] == pytest.approx(med_expected)
    # first 20 sessions (index<20, i.e. <20 prior obs) have no valid scale
    assert np.isnan(S.loc[pd.Timestamp("2020-01-01") + pd.Timedelta(days=10), 1])
