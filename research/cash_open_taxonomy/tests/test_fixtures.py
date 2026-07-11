import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import taxonomy as tx


def make_dense(closes, opens=None, highs=None, lows=None):
    n = len(closes)
    closes = np.array(closes, float)
    opens = np.array(opens, float) if opens else np.r_[closes[0], closes[:-1]]
    highs = np.array(highs, float) if highs else np.maximum(opens, closes) + 0.1
    lows = np.array(lows, float) if lows else np.minimum(opens, closes) - 0.1
    return {"open": opens, "high": highs, "low": lows, "close": closes}


# --------------------------------------------------------------- scales --
def test_causal_scale_prior_sessions_only():
    rows = []
    for i in range(25):
        sd = pd.Timestamp("2021-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "open": 100.0,
                    "high": 100.0 + (i + 1) * 0.1, "low": 100.0 - 0.05})
    df = pd.DataFrame(rows)
    scales = tx.build_scale_tables(df)
    med_expected = np.median([(i + 1) * 0.1 for i in range(24)])
    assert scales.loc[pd.Timestamp("2021-01-01") + pd.Timedelta(days=24), "scale_U"] == pytest.approx(med_expected)
    assert np.isnan(scales.loc[pd.Timestamp("2021-01-01") + pd.Timedelta(days=10), "scale_U"])


# ----------------------------------------------------------- primitives --
def test_no_lookahead_in_path_arrays():
    closes1 = [100.0, 101.0, 102.0, 103.0]
    closes2 = [100.0, 101.0, 9999.0, -500.0]  # bars after t=1 differ wildly
    arrs1 = make_dense(closes1)
    arrs2 = make_dense(closes2)
    u1, d1, Q1, cd1 = tx.path_arrays(arrs1, 100.0, 1.0, 1.0)
    u2, d2, Q2, cd2 = tx.path_arrays(arrs2, 100.0, 1.0, 1.0)
    assert u1[1] == pytest.approx(u2[1])
    assert d1[1] == pytest.approx(d2[1])
    assert cd1[1] == pytest.approx(cd2[1])


def test_incomplete_bar_invalidates_from_that_point():
    closes = [100.0, 101.0, np.nan, 103.0]
    arrs = make_dense(closes)
    arrs["high"][2] = np.nan
    arrs["low"][2] = np.nan
    u, d, Q, cd = tx.path_arrays(arrs, 100.0, 1.0, 1.0)
    assert np.isfinite(u[1])
    assert np.isnan(u[2]) and np.isnan(u[3])


def test_bar0_morphology_invariant():
    arrs = make_dense([100.5], opens=[100.0], highs=[101.0], lows=[99.5])
    row = tx.bar0_morphology(arrs, 100.0, 1.0, 1.0)
    total = row["body_ratio_0"] + row["upper_wick_ratio_0"] + row["lower_wick_ratio_0"]
    assert total == pytest.approx(1.0)


# ---------------------------------------------------------- same-bar h1 --
def test_samebar_h1_ambiguity_band():
    # u0=1.2, d0=1.3 (dual-sided); norm_close_disp within band -> ambiguous
    assert tx.classify_samebar_h1(1.2, 1.3, 0.05) == "SAME_BAR_DUAL_SIDED_AMBIGUOUS"
    assert tx.classify_samebar_h1(1.2, 1.3, 0.20) == "SAME_BAR_BULLISH_REVERSAL_PROXY"
    assert tx.classify_samebar_h1(1.2, 1.3, -0.20) == "SAME_BAR_BEARISH_REVERSAL_PROXY"
    assert tx.classify_samebar_h1(0.5, 1.3, 0.5) is None  # not dual-sided


# ------------------------------------------------------ same-bar subseq --
def test_samebar_continuation_expansion():
    # bullish proxy; price keeps making new highs, Q stays positive
    u = np.array([1.2, 1.3, 1.5, 1.8, 2.0])
    d = np.array([1.3, 1.2, 1.0, 0.9, 0.8])
    Q = (u - d) / (u + d)
    lbl, t = tx.classify_samebar_subsequent(Q, u, d, proxy_sign=1, t_h=4)
    assert lbl == "CONTINUATION_EXPANSION_PROXY_DIRECTION"


def test_samebar_balance_failure_to_expand():
    u = np.array([1.2, 1.2, 1.2, 1.2, 1.2])  # never exceeds bar-0 high
    d = np.array([1.3, 1.1, 1.0, 1.1, 1.0])
    Q = (u - d) / (u + d)  # stays positive (bullish side ahead), never opposite-dominant
    lbl, t = tx.classify_samebar_subsequent(Q, u, d, proxy_sign=1, t_h=4)
    assert lbl == "BALANCE_FAILURE_TO_EXPAND"


def test_samebar_immediate_takeover():
    # bullish proxy (u0=1.2,d0=1.3), but bar 1 already opposite-dominant
    u = np.array([1.2, 1.2, 1.2, 1.2])
    d = np.array([1.3, 2.0, 2.5, 3.0])
    Q = (u - d) / (u + d)
    lbl, t = tx.classify_samebar_subsequent(Q, u, d, proxy_sign=1, t_h=3)
    assert lbl == "LATER_OPPOSITE_SIDE_TAKEOVER"


def test_samebar_ordered_reversal_after_hold():
    # bullish proxy; bar1 still proxy-dominant (clean hold), bar2 opposite takes over
    u = np.array([1.2, 1.3, 1.3, 1.3])
    d = np.array([1.3, 1.2, 2.0, 2.5])
    Q = (u - d) / (u + d)
    lbl, t_take = tx.classify_samebar_subsequent(Q, u, d, proxy_sign=1, t_h=3)
    assert lbl == "LATER_ORDERED_REVERSAL_AFTER_PROXY"
    assert t_take == 2


# --------------------------------------------------------------- ordinary
def test_ordinary_direct_bullish_expansion():
    n = 10
    u = np.linspace(0.3, 2.0, n)
    d = np.full(n, 0.2)
    Q = (u - d) / (u + d)
    close_disp = np.linspace(0.1, 3.0, n)
    label, extra = tx.classify_ordinary(u, d, Q, close_disp, t_h=9)
    assert label == "DIRECT_BULLISH_EXPANSION"


def test_ordinary_reversal_with_timing():
    n = 12
    u = np.array([0.2] * 12)
    d = np.array([0.3, 0.6, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1])  # commits DOWN at t=2
    close_disp = np.array([-0.3, -0.6, -1.0, 0.2, 0.5, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0])
    u2 = np.array([0.2, 0.2, 0.2, 0.3, 0.6, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4])  # upside commits at t=5
    Q = (u2 - d) / (u2 + d)
    label, extra = tx.classify_ordinary(u2, d, Q, close_disp, t_h=11)
    assert label == "INITIAL_DOWNSIDE_BULLISH_REVERSAL"
    assert extra["timing_bin"] is not None


def test_ordinary_two_sided_balanced():
    n = 8
    u = np.full(n, 0.3)
    d = np.full(n, 0.3)
    Q = np.zeros(n)
    close_disp = np.zeros(n)
    label, extra = tx.classify_ordinary(u, d, Q, close_disp, t_h=7)
    assert label == "TWO_SIDED_BALANCED"


# ----------------------------------------------------------------- ladder
def test_ladder_order_and_ties():
    u = np.array([0.3, 0.6, 1.1, 1.6, 2.1])
    d = np.array([0.3, 0.6, 0.6, 0.6, 0.6])
    res = tx.excursion_ladder(u, d)
    assert res["reached_UP_0.5"] and res["first_bar_UP_0.5"] == 1
    assert res["reached_UP_2.0"] and res["first_bar_UP_2.0"] == 4
    assert not res["reached_DOWN_1.0"]
    # bar 1: UP reaches 0.5 AND DOWN reaches 0.5 simultaneously -> tie
    assert 1 in res["same_bar_ties"]


def test_ladder_monotonic_reach_rate_invariant():
    u = np.array([0.6, 1.1, 1.6, 2.1])
    d = np.full(4, 0.1)
    res = tx.excursion_ladder(u, d)
    # reaching 2.0 implies having passed 0.5/1.0/1.5 at or before that bar
    bars = [res[f"first_bar_UP_{t}"] for t in tx.LADDER]
    assert bars == sorted(bars)


# ------------------------------------------------------ end-to-end ledger
def test_one_row_per_session_and_es_nq_separate(tmp_path, monkeypatch):
    import src.build_ledger as bl
    rows = []
    for i in range(25):
        sd = pd.Timestamp("2021-01-01") + pd.Timedelta(days=i)
        for tau in range(60):
            rows.append({"session_date": sd, "et_minute": 570 + tau, "ts_event": sd,
                        "open": 100.0, "high": 100.3, "low": 99.8, "close": 100.1, "volume": 100})
    df = pd.DataFrame(rows)
    proc = tmp_path / "processed"
    proc.mkdir()
    for inst in ("es", "nq"):
        df.to_parquet(proc / f"{inst}_front_1m.parquet", index=False)
    monkeypatch.setattr(bl, "PROC", str(proc))
    monkeypatch.setattr(bl, "DEV_END", pd.Timestamp("2099-01-01"))
    led_es = bl.build_taxonomy_ledger("ES")
    led_nq = bl.build_taxonomy_ledger("NQ")
    if len(led_es):
        assert led_es["session_date"].is_unique
        assert (led_es["instrument"] == "ES").all()
    if len(led_nq):
        assert (led_nq["instrument"] == "NQ").all()
