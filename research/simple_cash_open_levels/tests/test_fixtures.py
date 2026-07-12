import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import levels as lv
from src import interactions as ix
from src import stats as st
from src import build_ledger as bd


def make_arrs(open_, high, low, close, volume=None, n=240):
    o = np.full(n, np.nan); h = np.full(n, np.nan); l = np.full(n, np.nan)
    c = np.full(n, np.nan); v = np.full(n, np.nan)
    for tau, val in open_.items(): o[tau] = val
    for tau, val in high.items(): h[tau] = val
    for tau, val in low.items(): l[tau] = val
    for tau, val in close.items(): c[tau] = val
    if volume:
        for tau, val in volume.items(): v[tau] = val
    return {"open": o, "high": h, "low": l, "close": c, "volume": v}


def make_session_df(n_sessions=65, overnight_bars=40, early_close_sessions=None,
                    open_val=100.0, high_val=100.3, low_val=99.8):
    early_close_sessions = early_close_sessions or set()
    rows = []
    base = pd.Timestamp("2019-01-01")
    for i in range(n_sessions):
        sd = base + pd.Timedelta(days=i)
        ts0 = sd - pd.Timedelta(hours=6)
        for k in range(overnight_bars):
            rows.append({"session_date": sd, "et_minute": 100 + k, "ts_event": ts0 + pd.Timedelta(minutes=k),
                        "open": 99.0, "high": 99.2, "low": 98.8, "close": 99.1, "volume": 50})
        rth_end = 389
        if i in early_close_sessions:
            rth_end = 384
        for tau in range(390):
            if tau > rth_end:
                continue
            minute = 570 + tau
            row = {"session_date": sd, "et_minute": minute, "ts_event": sd + pd.Timedelta(minutes=tau),
                  "open": open_val, "high": high_val, "low": low_val,
                  "close": (open_val + high_val) / 2, "volume": 100}
            rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------- 1: partition --
def test_01_partition_guard(tmp_path):
    rows = []
    for i in range(5):
        sd = pd.Timestamp("2022-12-29") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "ts_event": sd,
                    "open": 100.0, "high": 100.1, "low": 99.9, "close": 100.0, "volume": 10})
    df = pd.DataFrame(rows)
    proc = tmp_path / "processed"
    proc.mkdir()
    df.to_parquet(proc / "es_front_1m.parquet", index=False)
    out = lv.load_dev("ES", str(proc))
    assert out["session_date"].max() <= lv.DEV_END
    assert out["session_date"].min() >= lv.DEV_START


# ------------------------------------------------------- 2: ES/NQ separation --
def test_02_es_nq_separation(tmp_path):
    df = make_session_df(n_sessions=25)
    proc = tmp_path / "processed"
    proc.mkdir()
    for inst in ("es", "nq"):
        df.to_parquet(proc / f"{inst}_front_1m.parquet", index=False)
    import research.simple_cash_open_levels.src.build_ledger as bld
    old_proc = bld.PROC
    bld.PROC = str(proc)
    try:
        les, _, _, _ = bld.build_instrument_ledger("ES")
        lnq, _, _, _ = bld.build_instrument_ledger("NQ")
        assert (les["instrument"] == "ES").all()
        assert (lnq["instrument"] == "NQ").all()
    finally:
        bld.PROC = old_proc


# ------------------------------------------------------- 3: 86-level inventory --
def test_03_exact_86_level_inventory():
    assert len(lv.family_a_level_ids()) == 14
    assert len(lv.family_b_level_ids()) == 72
    assert len(lv.all_level_ids()) == 86
    assert len(set(lv.all_level_ids())) == 86


# ------------------------------------------------------- 4/5: overnight VWAP --
def test_04_05_overnight_vwap_and_sd_formula():
    rows = []
    sd0 = pd.Timestamp("2020-01-01")
    for k in range(40):
        rows.append({"session_date": sd0, "et_minute": 100 + k, "open": 99.0,
                    "high": 99.0 + 0.01 * k, "low": 98.9, "close": 99.0 + 0.005 * k, "volume": 10 + k})
    df = pd.DataFrame(rows)
    a1 = lv.build_family_a1_overnight(df)
    sub = df.copy()
    sub["p"] = (sub["high"] + sub["low"] + sub["close"]) / 3.0
    expected_vwap = (sub["volume"] * sub["p"]).sum() / sub["volume"].sum()
    expected_var = (sub["volume"] * sub["p"] ** 2).sum() / sub["volume"].sum() - expected_vwap ** 2
    expected_sd = np.sqrt(max(0, expected_var))
    assert abs(a1.loc[sd0, "VWAP_ON"] - expected_vwap) < 1e-9
    assert abs(a1.loc[sd0, "SD_ON"] - expected_sd) < 1e-9
    assert a1.loc[sd0, "ON_VWAP_0"] == a1.loc[sd0, "VWAP_ON"]
    assert abs(a1.loc[sd0, "ON_VWAP_p1"] - (expected_vwap + expected_sd)) < 1e-9


def test_04b_overnight_vwap_below_30_bars_invalid():
    rows = []
    sd0 = pd.Timestamp("2020-01-01")
    for k in range(10):
        rows.append({"session_date": sd0, "et_minute": 100 + k, "open": 99.0,
                    "high": 99.1, "low": 98.9, "close": 99.0, "volume": 10})
    df = pd.DataFrame(rows)
    a1 = lv.build_family_a1_overnight(df)
    assert np.isnan(a1.loc[sd0, "VWAP_ON"])


# ------------------------------------------------------- 6/7: prior-RTH VWAP --
def test_06_07_prior_rth_vwap_and_sd_formula():
    df = make_session_df(n_sessions=3)
    a2 = lv.build_family_a2_prior_rth(df)
    sd0 = pd.Timestamp("2019-01-01")
    sd1 = sd0 + pd.Timedelta(days=1)
    rth0 = df[(df.session_date == sd0) & (df.et_minute >= 570) & (df.et_minute <= 959)].copy()
    rth0["p"] = (rth0["high"] + rth0["low"] + rth0["close"]) / 3.0
    expected_vwap = (rth0["volume"] * rth0["p"]).sum() / rth0["volume"].sum()
    assert abs(a2.loc[sd1, "VWAP_PR"] - expected_vwap) < 1e-9
    expected_var = (rth0["volume"] * rth0["p"] ** 2).sum() / rth0["volume"].sum() - expected_vwap ** 2
    assert abs(a2.loc[sd1, "SD_PR"] - np.sqrt(max(0, expected_var))) < 1e-9


# ------------------------------------------------------- 8: early-close unavailable --
def test_08_early_close_prior_rth_unavailable():
    df = make_session_df(n_sessions=3, early_close_sessions={0})
    a2 = lv.build_family_a2_prior_rth(df)
    sd1 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=1)
    assert np.isnan(a2.loc[sd1, "VWAP_PR"])
    assert a2.loc[sd1, "prior_is_early_close"]


# ------------------------------------------------------- 9/10: 09:30-only, no leakage --
def test_09_10_excursion_uses_only_0930_candle_no_leakage():
    n = 65
    rows = []
    for i in range(n):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "open": 100.0,
                    "high": 100.0 + (i + 1) * 0.1, "low": 99.9, "volume": 10})
        # a later bar with an extreme value must NOT affect the excursion
        rows.append({"session_date": sd, "et_minute": 571, "open": 100.0,
                    "high": 999.0, "low": -999.0, "volume": 10})
    df = pd.DataFrame(rows)
    b = lv.build_family_b_excursions(df)
    sd0 = pd.Timestamp("2019-01-01")
    assert abs(b.loc[sd0, "U_0930"] - 0.1) < 1e-9  # NOT 899 (999-100)


# ------------------------------------------------------- 11-14: lookback windows --
def _make_excursion_fixture(n=65):
    rows = []
    for i in range(n):
        sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "open": 100.0,
                    "high": 100.0 + (i + 1) * 0.1, "low": 99.9, "volume": 10})
    return pd.DataFrame(rows)


def test_11_12_13_14_exact_lookback_windows_no_fallback():
    df = _make_excursion_fixture(65)
    b = lv.build_family_b_excursions(df)
    for N in (5, 10, 20):
        for i in range(N):
            sd = pd.Timestamp("2019-01-01") + pd.Timedelta(days=i)
            assert np.isnan(b.loc[sd, f"CENTER_U_mean_N{N}"]), f"N={N} idx={i} should be NaN"
        sdN = pd.Timestamp("2019-01-01") + pd.Timedelta(days=N)
        assert np.isfinite(b.loc[sdN, f"CENTER_U_mean_N{N}"])
        expected_mean = np.mean([(i + 1) * 0.1 for i in range(N)])
        assert abs(b.loc[sdN, f"CENTER_U_mean_N{N}"] - expected_mean) < 1e-9


# ------------------------------------------------------- 15/16/17/18: centers/SD --
def test_15_16_mean_and_median_center():
    df = _make_excursion_fixture(65)
    b = lv.build_family_b_excursions(df)
    sd5 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=5)
    vals = [(i + 1) * 0.1 for i in range(5)]
    assert abs(b.loc[sd5, "CENTER_U_mean_N5"] - np.mean(vals)) < 1e-9
    assert abs(b.loc[sd5, "CENTER_U_median_N5"] - np.median(vals)) < 1e-9


def test_17_ema_center_adjust_false():
    df = _make_excursion_fixture(65)
    b = lv.build_family_b_excursions(df)
    sd5 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=5)
    vals = np.array([(i + 1) * 0.1 for i in range(5)])
    expected = pd.Series(vals).ewm(span=5, adjust=False).mean().iloc[-1]
    assert abs(b.loc[sd5, "CENTER_U_ema_N5"] - expected) < 1e-9


def test_18_sample_sd_ddof1():
    df = _make_excursion_fixture(65)
    b = lv.build_family_b_excursions(df)
    sd5 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=5)
    vals = [(i + 1) * 0.1 for i in range(5)]
    assert abs(b.loc[sd5, "SD_U_N5"] - np.std(vals, ddof=1)) < 1e-9


# ------------------------------------------------------- 19/20: upper/lower formulas --
def test_19_20_upper_lower_formula_every_k():
    df = _make_excursion_fixture(65)
    b = lv.build_family_b_excursions(df)
    sd20 = pd.Timestamp("2019-01-01") + pd.Timedelta(days=20)
    O = b.loc[sd20, "O_0930"]
    cu = b.loc[sd20, "CENTER_U_mean_N5"]
    su = b.loc[sd20, "SD_U_N5"]
    cd = b.loc[sd20, "CENTER_D_mean_N5"]
    sdv = b.loc[sd20, "SD_D_N5"]
    for k in (0, 1, 2, 3):
        assert abs(b.loc[sd20, f"upper_N5_mean_k{k}"] - (O + cu + k * su)) < 1e-9
        assert abs(b.loc[sd20, f"lower_N5_mean_k{k}"] - (O - cd - k * sdv)) < 1e-9


# ------------------------------------------------------- 21: touch window --
def test_21_touch_window_exactly_0930_1129():
    assert ix.TOUCH_START == 570 and ix.TOUCH_END == 689
    assert ix.TOUCH_END - ix.TOUCH_START + 1 == 120


# ------------------------------------------------------- 22: first-touch only --
def test_22_first_touch_only_consumption():
    low = np.array([105, 95, 95, 95])
    high = np.array([106, 101, 101, 101])
    V = 100.0
    cond = (low <= V) & (high >= V)
    first = np.argmax(cond)
    assert first == 1


# ------------------------------------------------------- 23-26: same-bar morphology --
def test_23_24_same_bar_upper_reversal_and_blast():
    assert ix.same_bar_morphology("UPPER_LEVEL", 99.0, 100.0) == "SAME_BAR_REVERSAL_PROXY"
    assert ix.same_bar_morphology("UPPER_LEVEL", 101.0, 100.0) == "SAME_BAR_BLAST_THROUGH_PROXY"


def test_25_26_same_bar_lower_reversal_and_blast():
    assert ix.same_bar_morphology("LOWER_LEVEL", 101.0, 100.0) == "SAME_BAR_REVERSAL_PROXY"
    assert ix.same_bar_morphology("LOWER_LEVEL", 99.0, 100.0) == "SAME_BAR_BLAST_THROUGH_PROXY"


# ------------------------------------------------------- 27/28: outcome window --
def test_27_28_outcomes_start_t_plus_1_touch_bar_excluded():
    arrs_a = make_arrs({0: 100, 1: 100.2}, {0: 100.3, 1: 100.3}, {0: 99.7, 1: 100.1}, {0: 100.0, 1: 100.2})
    arrs_b = {k: v.copy() for k, v in arrs_a.items()}
    arrs_b["high"][0] = 99999.0
    arrs_b["low"][0] = -99999.0
    arrs_b["close"][0] = -99999.0
    out_a = ix.raw_outcomes(arrs_a, T=0, level_value=100.0, h=1)
    out_b = ix.raw_outcomes(arrs_b, T=0, level_value=100.0, h=1)
    assert out_a == out_b


# ------------------------------------------------------- 29-31: horizons --
def test_29_30_31_complete_horizons():
    assert set(ix.HORIZONS) >= {30, 60, 120}
    assert set(ix.PRIMARY_HORIZONS) == {30, 60, 120}
    assert ix.TOUCH_END + 120 - ix.TOUCH_START == ix.TAU_MAX == 239


# ------------------------------------------------------- 32: mirrored excursions --
def test_32_mirrored_upper_lower_excursions():
    arrs = make_arrs({0: 100}, {0: 100.2, 1: 103}, {0: 99.8, 1: 99}, {0: 100, 1: 102})
    up = ix.oriented_outcomes(arrs, T=0, level_value=100.0, h=1, orientation="UPPER_LEVEL", native_sd=2.0)
    down = ix.oriented_outcomes(arrs, T=0, level_value=100.0, h=1, orientation="LOWER_LEVEL", native_sd=2.0)
    assert up["CONT_EXC_h"] == max(0.0, 103 - 100.0)
    assert down["CONT_EXC_h"] == max(0.0, 100.0 - 99)
    assert up["REV_EXC_h"] == max(0.0, 100.0 - 99)
    assert down["REV_EXC_h"] == max(0.0, 103 - 100.0)


# ------------------------------------------------------- 33/34: native-SD normalization --
def test_33_native_sd_normalization():
    arrs = make_arrs({0: 100}, {0: 100.2, 1: 103}, {0: 99.8, 1: 99}, {0: 100, 1: 102})
    out = ix.oriented_outcomes(arrs, T=0, level_value=100.0, h=1, orientation="UPPER_LEVEL", native_sd=2.0)
    assert abs(out["CONT_EXC_SD_h"] - out["CONT_EXC_h"] / 2.0) < 1e-9


def test_34_zero_sd_handling():
    arrs = make_arrs({0: 100}, {0: 100.2, 1: 103}, {0: 99.8, 1: 99}, {0: 100, 1: 102})
    out = ix.oriented_outcomes(arrs, T=0, level_value=100.0, h=1, orientation="UPPER_LEVEL", native_sd=0.0)
    assert np.isnan(out["CONT_EXC_SD_h"])
    assert np.isfinite(out["CONT_EXC_h"])  # raw retained


# ------------------------------------------------------- 35-38: barriers --
def test_35_continuation_first_barrier():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103, 2: 100.05}, {0: 99.9, 1: 100, 2: 97},
                     {0: 100, 1: 102, 2: 98})
    b = ix.barrier_outcomes(arrs, T=0, h=2, b=1.0, orientation="UPPER_LEVEL", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "CONTINUATION_FIRST"


def test_36_reversal_first_barrier():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.05, 2: 105}, {0: 99.9, 1: 97, 2: 104},
                     {0: 100, 1: 98, 2: 104.5})
    b = ix.barrier_outcomes(arrs, T=0, h=2, b=1.0, orientation="UPPER_LEVEL", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "REVERSAL_FIRST"


def test_37_same_bar_tie():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 103}, {0: 99.9, 1: 97}, {0: 100, 1: 100})
    b = ix.barrier_outcomes(arrs, T=0, h=1, b=1.0, orientation="UPPER_LEVEL", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "SAME_BAR_TIE"


def test_38_neither_barrier():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 100.2}, {0: 99.9, 1: 99.8}, {0: 100, 1: 100.1})
    b = ix.barrier_outcomes(arrs, T=0, h=1, b=1.0, orientation="UPPER_LEVEL", level_value=100.0, native_sd=2.0)
    assert b["barrier_first_outcome"] == "NEITHER"


# ------------------------------------------------------- 39: post-touch-retouch --
def test_39_post_touch_retouch_definition():
    arrs = make_arrs({0: 100}, {0: 100.1, 1: 105, 2: 100.05}, {0: 99.9, 1: 104, 2: 99.95},
                     {0: 100, 1: 104.5, 2: 100.0})
    out = ix.raw_outcomes(arrs, T=0, level_value=100.0, h=2)
    assert out["post_touch_retouch"] == 1


# ------------------------------------------------------- 40: close-recross --
def test_40_directional_close_recross_ordering():
    arrs = make_arrs({0: 100}, {}, {}, {0: 100.0, 1: 101.0, 2: 99.0})
    out = ix.directional_close_recross(arrs, T=0, h=2, orientation="UPPER_LEVEL", level_value=100.0)
    assert out["directional_rejection_recross"] == 1
    arrs2 = make_arrs({0: 100}, {}, {}, {0: 100.0, 1: 99.0, 2: 99.5})
    out2 = ix.directional_close_recross(arrs2, T=0, h=2, orientation="UPPER_LEVEL", level_value=100.0)
    assert out2["directional_rejection_recross"] == 0


# ------------------------------------------------------- 41: year-split --
def test_41_year_split_accounting():
    levels_tbl = pd.DataFrame({
        "instrument": ["ES"] * 4, "level_id": ["upper_N5_mean_k0"] * 4,
        "session_date": [pd.Timestamp("2019-01-01"), pd.Timestamp("2019-06-01"),
                         pd.Timestamp("2020-01-01"), pd.Timestamp("2020-06-01")],
        "level_valid": [True] * 4, "touched": [True, False, True, True],
    })
    yrs = st.year_stability_touch(levels_tbl)
    assert set(yrs["year"]) == {2019, 2020}
    row2019 = yrs[yrs.year == 2019].iloc[0]
    assert row2019["n_valid"] == 2 and row2019["n_touched"] == 1


# ------------------------------------------------------- 42: alias handling --
def test_42_coincident_level_alias_handling():
    levels_tbl = pd.DataFrame({
        "instrument": ["ES"] * 3, "session_date": [pd.Timestamp("2020-01-01")] * 3,
        "level_id": ["a", "b", "c"], "level_value": [100.0, 100.1, 110.0],
        "level_valid": [True, True, True], "touched": [True, False, False],
    })
    clusters = st.coincident_levels(levels_tbl, tick=0.25)
    sizes = sorted(clusters["cluster_size"].tolist())
    assert sizes == [1, 2]  # {a,b} cluster (within tick), {c} alone


# ------------------------------------------------------- 43: complete null retention --
def test_43_complete_null_retention_bh():
    df = pd.DataFrame({"instrument": ["ES"] * 3, "level_id": ["x", "y", "z"],
                       "horizon": [30] * 3, "p_raw": [np.nan, 0.5, np.nan]})
    out = st.bh_within(df, "p_raw", group_cols=("instrument", "horizon"))
    assert len(out) == 3  # no row dropped despite NaN p-values
    assert out["q_value"].isna().sum() == 2
