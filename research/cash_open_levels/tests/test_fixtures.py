import importlib.util
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import levels as lv
from src import diagnostics as dg

TAXONOMY_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "research",
    "cash_open_taxonomy", "src", "taxonomy.py"))


def _load_taxonomy():
    spec = importlib.util.spec_from_file_location("gen6_taxonomy_test", TAXONOMY_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tx = _load_taxonomy()


def make_session_df(n_sessions=65, rth_bars_per_session=390, overnight_bars=40,
                    early_close_sessions=None, open_val=100.0, high_val=100.3,
                    low_val=99.8):
    """Builds a minimal df with an overnight leg (et_minute 0..569, one per
    minute of the prior evening, folded onto the SAME session_date per the
    processed-data convention) and an RTH leg (et_minute 570..959)."""
    early_close_sessions = early_close_sessions or set()
    rows = []
    base = pd.Timestamp("2021-01-01")
    for i in range(n_sessions):
        sd = base + pd.Timedelta(days=i)
        ts0 = sd - pd.Timedelta(hours=6)
        for k in range(overnight_bars):
            rows.append({"session_date": sd, "et_minute": 100 + k,
                        "ts_event": ts0 + pd.Timedelta(minutes=k),
                        "open": 99.0, "high": 99.2, "low": 98.8, "close": 99.1, "volume": 50})
        rth_end = rth_bars_per_session - 1
        if i in early_close_sessions:
            rth_end = max(0, rth_end - 5)
        for tau in range(rth_bars_per_session):
            minute = 570 + tau
            if tau > rth_end:
                continue
            row = {"session_date": sd, "et_minute": minute,
                  "ts_event": sd + pd.Timedelta(minutes=tau),
                  "open": open_val, "high": high_val, "low": low_val,
                  "close": (open_val + high_val) / 2, "volume": 100}
            if tau == 0:
                row["high"] = high_val
                row["low"] = low_val
            rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------- family 1 --
def test_family1_causal_60_session_window():
    df = make_session_df(n_sessions=65)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)
    for i in range(60):
        sd = pd.Timestamp("2021-01-01") + pd.Timedelta(days=i)
        assert np.isnan(fam1.loc[sd, "mult_U_1.0"])
    sd60 = pd.Timestamp("2021-01-01") + pd.Timedelta(days=60)
    assert np.isfinite(fam1.loc[sd60, "mult_U_1.0"])


def test_family1_no_lookahead():
    # varying U_0930 per session (not a tied constant) so a mutation is
    # guaranteed to move both the median and the MAD, not just the raw value
    n = 65
    rows = []
    for i in range(n):
        sd = pd.Timestamp("2021-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "ts_event": sd,
                    "open": 100.0, "high": 100.0 + (i + 1) * 0.1, "low": 99.95, "volume": 10})
    df = pd.DataFrame(rows)
    scales_a = tx.build_scale_tables(df)
    fam1_a = lv.build_family1(df, scales_a)
    sd60 = pd.Timestamp("2021-01-01") + pd.Timedelta(days=60)

    # mutating session 60's OWN 09:30 bar must not change session 60's scale
    df2 = df.copy()
    mask = (df2["session_date"] == sd60) & (df2["et_minute"] == 570)
    df2.loc[mask, "high"] = 999.0
    scales_b = tx.build_scale_tables(df2)
    fam1_b = lv.build_family1(df2, scales_b)
    assert fam1_a.loc[sd60, "scale_U"] == fam1_b.loc[sd60, "scale_U"]

    # mutating a MID-window session (index 30, well inside session 60's
    # 60-session trailing window of indices 0..59, and not the window's
    # extreme value) must change session 60's causal scale
    sd30 = pd.Timestamp("2021-01-01") + pd.Timedelta(days=30)
    df3 = df.copy()
    mask3 = (df3["session_date"] == sd30) & (df3["et_minute"] == 570)
    df3.loc[mask3, "high"] = 999.0
    scales_c = tx.build_scale_tables(df3)
    fam1_c = lv.build_family1(df3, scales_c)
    assert fam1_a.loc[sd60, "scale_U"] != fam1_c.loc[sd60, "scale_U"]


# ------------------------------------------------------------- family 2 --
def test_family2_vwap_formula_and_threshold():
    df = make_session_df(n_sessions=2, overnight_bars=40)
    fam2 = lv.build_family2(df)
    sd0 = pd.Timestamp("2021-01-01")
    sub = df[(df["session_date"] == sd0) & (df["et_minute"] < 570)]
    p = (sub["high"] + sub["low"] + sub["close"]) / 3.0
    expected_vwap = (sub["volume"] * p).sum() / sub["volume"].sum()
    assert abs(fam2.loc[sd0, "vwap_on"] - expected_vwap) < 1e-9
    assert fam2.loc[sd0, "vwap_on_j+0"] == fam2.loc[sd0, "vwap_on"]


def test_family2_missing_below_30_bars():
    df = make_session_df(n_sessions=2, overnight_bars=10)
    fam2 = lv.build_family2(df)
    sd0 = pd.Timestamp("2021-01-01")
    assert np.isnan(fam2.loc[sd0, "vwap_on"])


def test_family2_no_lookahead():
    df = make_session_df(n_sessions=2, overnight_bars=40)
    fam2_a = lv.build_family2(df)
    sd0 = pd.Timestamp("2021-01-01")
    df2 = df.copy()
    mask = (df2["session_date"] == sd0) & (df2["et_minute"] == 570)  # RTH bar, not overnight
    df2.loc[mask, "high"] = 999.0
    fam2_b = lv.build_family2(df2)
    assert fam2_a.loc[sd0, "vwap_on"] == fam2_b.loc[sd0, "vwap_on"]


# ------------------------------------------------------------- family 3 --
def test_family3_uses_prior_session_and_excludes_early_close():
    df = make_session_df(n_sessions=3, early_close_sessions={1})
    fam3 = lv.build_family3(df)
    sd0, sd1, sd2 = [pd.Timestamp("2021-01-01") + pd.Timedelta(days=i) for i in range(3)]
    # session 1 uses session 0 (not early close) -> valid
    assert np.isfinite(fam3.loc[sd1, "prior_high"])
    # session 2's predecessor (session 1) IS an early close -> missing
    assert np.isnan(fam3.loc[sd2, "prior_high"])
    assert fam3.loc[sd2, "prior_is_early_close"]


def test_family3_no_lookahead():
    df = make_session_df(n_sessions=3)
    fam3_a = lv.build_family3(df)
    sd1 = pd.Timestamp("2021-01-01") + pd.Timedelta(days=1)
    df2 = df.copy()
    mask = (df2["session_date"] == sd1) & (df2["et_minute"] == 570)
    df2.loc[mask, "high"] = 999.0
    fam3_b = lv.build_family3(df2)
    sd2 = pd.Timestamp("2021-01-01") + pd.Timedelta(days=2)
    # mutating session 1's own bar changes session 2's prior_high (session 1 IS session 2's predecessor)
    assert fam3_a.loc[sd2, "prior_high"] != fam3_b.loc[sd2, "prior_high"]
    # but must not change session 1's OWN prior_high (predecessor is session 0, untouched)
    assert fam3_a.loc[sd1, "prior_high"] == fam3_b.loc[sd1, "prior_high"]


# ------------------------------------------------------------- family 4 --
def test_family4_cross_reference_requires_family2_valid():
    df = make_session_df(n_sessions=2, overnight_bars=10)  # below 30-bar floor
    fam2 = lv.build_family2(df)
    fam4 = lv.build_family4(df, fam2)
    sd0 = pd.Timestamp("2021-01-01")
    assert np.isfinite(fam4.loc[sd0, "overnight_high"])  # raw level still valid
    assert np.isnan(fam4.loc[sd0, "overnight_high_dev_vwap"])  # cross-ref requires fam2


# --------------------------------------------------------- structural dup --
def test_structural_duplicate_mult_1_equals_median_quantile():
    df = make_session_df(n_sessions=65)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)
    dup = dg.structural_duplicates(fam1)
    row = dup[dup["level_id"] == "mult_U_1.0"].iloc[0]
    assert row["is_structural_duplicate"]
    assert row["max_abs_diff"] < 1e-9


# ------------------------------------------------------------ clustering --
def test_empirical_clustering_flags_close_levels():
    df = make_session_df(n_sessions=65)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)
    fam2 = lv.build_family2(df)
    fam3 = lv.build_family3(df)
    fam4 = lv.build_family4(df, fam2)
    long_df = lv.build_long_levels("ES", fam1, fam2, fam3, fam4)
    pairs = dg.empirical_clustering_flagged(long_df, fam1)
    if len(pairs):
        assert pairs["clustered"].dtype == bool
        assert (pairs["diff"] >= 0).all()


# ------------------------------------------------------- synthetic control --
def test_synthetic_control_matches_bucket_and_is_independent_of_real_value():
    df = make_session_df(n_sessions=65)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)
    fam2 = lv.build_family2(df)
    fam3 = lv.build_family3(df)
    fam4 = lv.build_family4(df, fam2)
    long_df = lv.build_long_levels("ES", fam1, fam2, fam3, fam4)
    synth = lv.build_synthetic_controls(long_df, fam1)

    merged = long_df.merge(synth, on=["instrument", "session_date", "level_id", "family", "side"],
                           suffixes=("", "_s"))
    valid = merged.dropna(subset=["normalized_distance_synth"])
    # every synthetic draw falls within the SAME bucket interval as the real level's own bucket
    bounds = {f"[{lo},{hi})": (lo, hi) for lo, hi in lv.DIST_BUCKETS}
    for _, r in valid.iterrows():
        lo, hi = bounds[r["distance_bucket"]]
        hi_check = hi if np.isfinite(hi) else lo + 1.0
        assert lo <= r["normalized_distance_synth"] < hi_check

    # reproducibility: same seed -> identical draws
    synth2 = lv.build_synthetic_controls(long_df, fam1)
    pd.testing.assert_series_equal(synth["value_synth"], synth2["value_synth"])

    # independence: value_synth must not equal the real level's own value in general
    # (spot check: not a pure copy of `value`)
    real_vals = long_df.set_index(["session_date", "level_id"])["value"]
    synth_vals = synth.set_index(["session_date", "level_id"])["value_synth"]
    common = real_vals.index.intersection(synth_vals.index)
    both_finite = real_vals.loc[common].notna() & synth_vals.loc[common].notna()
    if both_finite.sum() > 5:
        assert not np.allclose(real_vals.loc[common][both_finite], synth_vals.loc[common][both_finite])


# --------------------------------------------------------- ES/NQ separate --
def test_long_levels_one_row_per_session_level_and_instrument_tagged():
    df = make_session_df(n_sessions=65)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)
    fam2 = lv.build_family2(df)
    fam3 = lv.build_family3(df)
    fam4 = lv.build_family4(df, fam2)
    long_es = lv.build_long_levels("ES", fam1, fam2, fam3, fam4)
    long_nq = lv.build_long_levels("NQ", fam1, fam2, fam3, fam4)
    assert (long_es["instrument"] == "ES").all()
    assert (long_nq["instrument"] == "NQ").all()
    dup_check = long_es.groupby(["session_date", "level_id"]).size()
    assert (dup_check == 1).all()


# ------------------------------------------------- correction: family 1 --
def test_family1_quantile_levels_causal_window_and_p50_exclusion():
    n = 65
    rows = []
    for i in range(n):
        sd = pd.Timestamp("2021-01-01") + pd.Timedelta(days=i)
        rows.append({"session_date": sd, "et_minute": 570, "ts_event": sd,
                    "open": 100.0, "high": 100.0 + (i + 1) * 0.1, "low": 99.95, "volume": 10})
    df = pd.DataFrame(rows)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)

    # p50 must NOT exist as its own level_id anywhere in family1's columns
    assert "q_U_p50" not in fam1.columns
    assert "q_D_p50" not in fam1.columns
    for q in lv.QUANTILE_LADDER:
        label = lv._quantile_label(q)
        assert f"q_U_{label}" in fam1.columns
        assert f"q_D_{label}" in fam1.columns

    sd60 = pd.Timestamp("2021-01-01") + pd.Timedelta(days=60)
    for i in range(60):
        sd = pd.Timestamp("2021-01-01") + pd.Timedelta(days=i)
        assert np.isnan(fam1.loc[sd, "q_U_p75"])
    # session 60: exactly 60 predecessors (U_0930 = (i+1)*0.1 for i in 0..59)
    expected_p75 = np.quantile([(i + 1) * 0.1 for i in range(60)], 0.75)
    assert abs((fam1.loc[sd60, "q_U_p75"] - fam1.loc[sd60, "open"]) - expected_p75) < 1e-9


def test_family1_p50_alias_equals_median_multiplier():
    df = make_session_df(n_sessions=65)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)
    dup = dg.structural_duplicates(fam1)
    assert set(dup["level_id"]) == {"mult_U_1.0", "mult_D_1.0"}
    assert dup["is_structural_duplicate"].all()


# ------------------------------------------------- correction: family 2 --
def test_family2_three_sigma_bands_added():
    df = make_session_df(n_sessions=2, overnight_bars=40)
    fam2 = lv.build_family2(df)
    sd0 = pd.Timestamp("2021-01-01")
    assert abs((fam2.loc[sd0, "vwap_on_j+3"] - fam2.loc[sd0, "vwap_on"]) - 3 * fam2.loc[sd0, "sigma_on"]) < 1e-9
    assert abs((fam2.loc[sd0, "vwap_on"] - fam2.loc[sd0, "vwap_on_j-3"]) - 3 * fam2.loc[sd0, "sigma_on"]) < 1e-9


# ------------------------------------------------- correction: family 3 --
def test_family3_prior_rth_mid_and_vwap():
    df = make_session_df(n_sessions=3, early_close_sessions={1})
    fam3 = lv.build_family3(df)
    sd0, sd1, sd2 = [pd.Timestamp("2021-01-01") + pd.Timedelta(days=i) for i in range(3)]
    assert np.isfinite(fam3.loc[sd1, "prior_rth_mid"])
    assert np.isfinite(fam3.loc[sd1, "prior_rth_vwap"])
    # session 1's predecessor (session 0) is not early close -> mid = (high+low)/2
    rth0 = df[(df["session_date"] == sd0) & (df["et_minute"] >= lv.OPEN_MINUTE) & (df["et_minute"] <= lv.RTH_END_MINUTE)]
    expected_mid = (rth0["high"].max() + rth0["low"].min()) / 2.0
    assert abs(fam3.loc[sd1, "prior_rth_mid"] - expected_mid) < 1e-9
    # session 2's predecessor (session 1) IS early close -> both missing
    assert np.isnan(fam3.loc[sd2, "prior_rth_mid"])
    assert np.isnan(fam3.loc[sd2, "prior_rth_vwap"])


def test_family3_prior_settlement_open_not_implemented():
    df = make_session_df(n_sessions=3)
    fam3 = lv.build_family3(df)
    assert "prior_settlement_open" not in fam3.columns
    assert "prior_settlement_open" not in lv.LEVEL_COLUMNS


# ------------------------------------------------- correction: family 4 --
def test_family4_mid_and_open_and_vwap_crossref_not_recomputed():
    df = make_session_df(n_sessions=2, overnight_bars=40)
    fam2 = lv.build_family2(df)
    fam4 = lv.build_family4(df, fam2)
    sd0 = pd.Timestamp("2021-01-01")
    assert abs(fam4.loc[sd0, "overnight_mid"] - (fam4.loc[sd0, "overnight_high"] + fam4.loc[sd0, "overnight_low"]) / 2.0) < 1e-9
    sub = df[(df["session_date"] == sd0) & (df["et_minute"] < lv.OPEN_MINUTE)].sort_values("ts_event")
    assert fam4.loc[sd0, "overnight_open"] == sub.iloc[0]["open"]
    # cross-referenced deviation fields must use family 2's own vwap_on value directly
    assert abs(fam4.loc[sd0, "overnight_high_dev_vwap"] - (fam4.loc[sd0, "overnight_high"] - fam2.loc[sd0, "vwap_on"])) < 1e-9


def test_family4_dev_vwap_fields_excluded_from_level_inventory():
    assert "overnight_high_dev_vwap" not in lv.LEVEL_COLUMNS
    assert "overnight_low_dev_vwap" not in lv.LEVEL_COLUMNS
    assert "overnight_mid" in lv.LEVEL_COLUMNS
    assert "overnight_open" in lv.LEVEL_COLUMNS


# --------------------------------------------------- exact inventory count --
def test_level_columns_exact_inventory_count_by_family():
    # Locks the exact per-family and total level_id count so a future
    # ladder change (or a documentation transcription error, as previously
    # found) is caught immediately by the test suite rather than only by
    # manual audit. family1: 4 mult x2 sides + 3 mad x2 sides + 4 quantile
    # x2 sides = 22. family2: 7 sigma steps (j=-3..+3). family3: prior
    # high/low/close/mid/vwap = 5. family4: high/low/mid/open = 4.
    from collections import Counter
    counts = Counter(family for family, side, _ in lv.LEVEL_COLUMNS.values())
    assert counts["family1"] == 2 * (len(lv.MULT_LADDER) + len(lv.MAD_LADDER) + len(lv.QUANTILE_LADDER)) == 22
    assert counts["family2"] == len(lv.VWAP_J) == 7
    assert counts["family3"] == 5
    assert counts["family4"] == 4
    assert len(lv.LEVEL_COLUMNS) == 38
    assert "q_U_p50" not in lv.LEVEL_COLUMNS and "q_D_p50" not in lv.LEVEL_COLUMNS
    assert "prior_settlement_open" not in lv.LEVEL_COLUMNS


def test_level_counts_table_matches_level_columns_inventory():
    df = make_session_df(n_sessions=65)
    scales = tx.build_scale_tables(df)
    fam1 = lv.build_family1(df, scales)
    fam2 = lv.build_family2(df)
    fam3 = lv.build_family3(df)
    fam4 = lv.build_family4(df, fam2)
    long_df = lv.build_long_levels("ES", fam1, fam2, fam3, fam4)
    counts = dg.level_counts(long_df)
    assert len(counts) == len(lv.LEVEL_COLUMNS)
    assert set(counts["level_id"]) == set(lv.LEVEL_COLUMNS.keys())
    fam_sizes = counts.groupby("family").size().to_dict()
    assert fam_sizes == {"family1": 22, "family2": 7, "family3": 5, "family4": 4}
