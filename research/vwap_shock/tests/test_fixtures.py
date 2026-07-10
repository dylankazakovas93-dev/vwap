"""Hand-calculated deterministic fixtures for the Stage 2 engine."""
import numpy as np
import pandas as pd
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.features import compute_features
from src.events import _first_passage, _acceptance, _forward_block


def make_session(closes, session="2020-01-06", start_min=1080, vol=None,
                 opens=None, highs=None, lows=None):
    n = len(closes)
    closes = np.asarray(closes, float)
    opens = np.asarray(opens, float) if opens is not None else np.r_[closes[0], closes[:-1]]
    highs = np.asarray(highs, float) if highs is not None else np.maximum(opens, closes) + 0.25
    lows = np.asarray(lows, float) if lows is not None else np.minimum(opens, closes) - 0.25
    vol = np.asarray(vol, float) if vol is not None else np.full(n, 100.0)
    base = pd.Timestamp(session, tz="UTC") - pd.Timedelta(hours=1)
    ts = pd.date_range(base, periods=n, freq="1min")
    return pd.DataFrame({
        "ts_event": ts, "session_date": pd.Timestamp(session),
        "et_minute": [(start_min + i) % 1440 for i in range(n)],
        "symbol": "ESH0", "roll": False,
        "open": opens, "high": highs, "low": lows, "close": closes, "volume": vol,
    })


def test_path_efficiency_and_persistence():
    # closes: +1,+1,-1,+1,+1 then shock bar. L=5 window ends at t-1.
    closes = [100, 101, 102, 101, 102, 103, 110]
    df = compute_features(make_session(closes))
    t = 6  # shock bar
    # window r_i for i in t-5..t-1: +1,+1,-1,+1,+1 ; D5 = 103-100 = 3
    assert df["D5"].iloc[t] == pytest.approx(3.0)
    assert df["E5"].iloc[t] == pytest.approx(3.0 / 5.0)
    assert df["P5"].iloc[t] == pytest.approx(4.0 / 5.0)


def test_terminal_run_length():
    closes = [100, 99, 100, 101, 102, 103, 110]
    df = compute_features(make_session(closes))
    t = 6
    # r ending at t-1: +1,+1,+1,+1 after a -1 => run 4, sign +1
    assert df["runlen_prev"].iloc[t] == 4
    assert df["runsign_prev"].iloc[t] == 1


def test_vwap_and_sigma_causal():
    closes = [100, 102, 104]
    highs = [101, 103, 105]
    lows = [99, 101, 103]
    opens = [100, 100, 102]
    vol = [10, 20, 30]
    df = compute_features(make_session(closes, opens=opens, highs=highs, lows=lows, vol=vol))
    pbar = np.array([(101 + 99 + 100) / 3, (103 + 101 + 102) / 3, (105 + 103 + 104) / 3])
    w = np.array([10, 20, 30.0])
    vwap2 = (pbar[:2] * w[:2]).sum() / w[:2].sum()
    assert df["vwap_g"].iloc[1] == pytest.approx(vwap2)
    var2 = (w[:2] * (pbar[:2] - vwap2) ** 2).sum() / w[:2].sum()
    assert df["sig_g"].iloc[1] == pytest.approx(np.sqrt(var2))
    # validity requires >= 30 completed bars
    assert not df["vwap_g_valid"].iloc[1]


def test_first_passage_conservative_ambig():
    op = np.array([100.0, 100.0, 100.0])
    hi = np.array([100.0, 103.0, 100.0])
    lo = np.array([100.0, 97.0, 100.0])
    out, t = _first_passage(op, hi, lo, 0, 1, 2.0)
    assert out == "AMBIG" and t == 1
    hi2 = np.array([100.0, 101.0, 103.0])
    lo2 = np.array([100.0, 99.5, 99.0])
    out2, t2 = _first_passage(op, hi2, lo2, 0, 1, 2.0)
    assert out2 == "CONT" and t2 == 2
    out3, _ = _first_passage(op, hi2, lo2, 0, -1, 2.0)
    assert out3 == "REV"


def test_forward_returns_from_next_open():
    op = np.array([100.0, 105.0, 106.0, 107.0])
    cl = np.array([104.0, 105.5, 106.5, 107.5])
    hi = cl + 1
    lo = op - 1
    fb = _forward_block(op, hi, lo, cl, 0, 1)
    assert fb["entry_price"] == 105.0  # open of t+1, not close of t
    assert fb["fret_1"] == pytest.approx(0.5)


def test_acceptance_band_touch_is_not_acceptance():
    # vwap flat 100, sigma 1. Event bar closes at 102.5 (beyond 2 sigma).
    n = 8
    cl = np.array([102.5, 102.4, 100.9, 102.6, 102.7, 102.8, 102.9, 103.0])
    vwap = np.full(n, 100.0)
    sig = np.full(n, 1.0)
    valid = np.full(n, True)
    res = _acceptance(cl, vwap, sig, valid, 0, 1, n)
    # bar 2 closes at 100.9 -> inside inner band -> rejection for A1
    assert res["A1_status"] == "REJECT"
    # A2: rejection too (reclaim within window)
    assert res["A2_status"] == "REJECT"
    cl2 = np.array([102.5, 102.4, 102.2, 102.6, 102.7, 102.8, 102.9, 103.0])
    res2 = _acceptance(cl2, vwap, sig, valid, 0, 1, n)
    assert res2["A1_status"] == "ACCEPT"  # 2 of 3 beyond, no reclaim
    assert res2["A2_status"] == "ACCEPT"


def test_minute_of_day_baseline_excludes_current_session():
    # 25 sessions, one bar per session at same minute; volume ramps.
    frames = []
    for i in range(25):
        f = make_session([100 + i, 100 + i + 1], session=str(pd.Timestamp("2020-01-06") + pd.Timedelta(days=i))[:10])
        f["volume"] = [100.0 + i, 200.0 + i]
        frames.append(f)
    df = compute_features(pd.concat(frames, ignore_index=True))
    # baseline for session j uses sessions < j only
    row = df[(df["et_minute"] == 1080)].iloc[24]
    med_expected = np.median([100.0 + i for i in range(24)])
    assert row["mod_vol_med"] == pytest.approx(med_expected)
    # first 20 sessions have no baseline
    assert np.isnan(df[df["et_minute"] == 1080].iloc[10]["mod_vol_med"])


def test_event_ledger_signed_persistence():
    from src.events import build_event_ledger
    # 40 up bars then a big up shock: P15_d should be ~1, E15_d positive
    closes = [100 + 0.25 * i for i in range(40)] + [120.0]
    df = make_session(closes)
    feat = compute_features(df)
    # force a valid minute-of-day sigma so z_mod1 triggers: bypass by mask
    mask = pd.Series(False, index=feat.index)
    mask.iloc[-1] = True
    led = build_event_ledger(feat, k=1, z_thr=0.0, instrument="ES", mask=mask)
    assert len(led) == 0  # last bar has no t+1 -> excluded

    closes = [100 + 0.25 * i for i in range(40)] + [120.0, 120.5, 121.0]
    feat = compute_features(make_session(closes))
    mask = pd.Series(False, index=feat.index)
    mask.iloc[40] = True
    led = build_event_ledger(feat, k=1, z_thr=0.0, instrument="ES", mask=mask)
    assert len(led) == 1
    row = led.iloc[0]
    assert row["direction"] == 1
    assert row["P15_d"] == pytest.approx(1.0)
    assert row["E15_d"] == pytest.approx(1.0)
    assert row["run_d"] > 0
    # opposite-direction shock: persistence folds to 0, efficiency negative
    closes2 = [100 + 0.25 * i for i in range(40)] + [90.0, 89.5, 89.0]
    feat2 = compute_features(make_session(closes2))
    mask2 = pd.Series(False, index=feat2.index)
    mask2.iloc[40] = True
    led2 = build_event_ledger(feat2, k=1, z_thr=0.0, instrument="ES", mask=mask2)
    row2 = led2.iloc[0]
    assert row2["direction"] == -1
    assert row2["P15_d"] == pytest.approx(0.0)
    assert row2["E15_d"] == pytest.approx(-1.0)
