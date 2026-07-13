"""Primary-family BH correction, year stability, cell classification, and
session-level mechanism classification.

See SPEC_SESSION_HORIZONS.md sections 12-14.
"""
import numpy as np
import pandas as pd

from .events import HORIZONS
from .summary import benjamini_hochberg

PRIMARY_BARRIER = 1.0
DISJOINT_BUCKETS = ("SESSION_0_TO_30", "SESSION_30_TO_60", "SESSION_60_TO_120", "SESSION_120_PLUS")
BUCKET_ORDER = {b: i for i, b in enumerate(DISJOINT_BUCKETS)}
HORIZON_ORDER = {h: i for i, h in enumerate(HORIZONS)}
MIN_TOUCH = 50
MIN_NONTIED = 20
MIN_EFFECT_PP = 5.0
YEARS = (2018, 2019, 2020, 2021, 2022)


def primary_cells(cells_df: pd.DataFrame) -> pd.DataFrame:
    return cells_df.loc[
        (cells_df["barrier_atr"] == PRIMARY_BARRIER) & (cells_df["touch_time_bucket"].isin(DISJOINT_BUCKETS))
    ].copy()


def apply_bh_primary(cells_df: pd.DataFrame) -> pd.DataFrame:
    pc = primary_cells(cells_df).reset_index(drop=True)
    pc["bh_family"] = pc["instrument"] + "|" + pc["session"]
    pc["q_value_primary"] = np.nan
    for fam, idx in pc.groupby("bh_family").groups.items():
        sub = pc.loc[idx]
        adj, _ = benjamini_hochberg(sub["barrier_binom_p"].to_numpy())
        pc.loc[idx, "q_value_primary"] = adj
    return pc


def year_stability(events_full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if events_full.empty:
        return pd.DataFrame(rows)
    keys = ["instrument", "session", "approach_side"]
    for gvals, g in events_full.groupby(keys):
        instrument, session, side = gvals
        for bucket in DISJOINT_BUCKETS:
            gb = g.loc[g["touch_time_bucket"] == bucket]
            for H in HORIZONS:
                for year in YEARS:
                    gy = gb.loc[gb["year"] == year]
                    n = len(gy)
                    n_rej_sb = int((gy["same_bar_morphology"] == "SAME_BAR_REJECTION_PROXY").sum())
                    n_brk_sb = int((gy["same_bar_morphology"] == "SAME_BAR_BREAKTHROUGH_PROXY").sum())
                    col = f"b{PRIMARY_BARRIER}_h{H}_outcome"
                    n_rej_first = n_brk_first = 0
                    if col in gy.columns and n:
                        vc = gy[col].value_counts()
                        n_rej_first = int(vc.get("REJECTION_FIRST", 0))
                        n_brk_first = int(vc.get("BREAKTHROUGH_FIRST", 0))
                    valid_h = gy.loc[gy[f"horizon_{H}_complete"] & gy["atr_valid"]] if n else gy
                    med_signed = (
                        float(valid_h[f"signed_close_atr_h{H}"].median()) if len(valid_h) else np.nan
                    )
                    rows.append(
                        {
                            "instrument": instrument,
                            "session": session,
                            "approach_side": side,
                            "touch_time_bucket": bucket,
                            "horizon_bars": H,
                            "year": year,
                            "n_events": n,
                            "rejection_first_rate": (n_rej_first / n) if n else np.nan,
                            "breakthrough_first_rate": (n_brk_first / n) if n else np.nan,
                            "rej_minus_brk_first_rate": ((n_rej_first - n_brk_first) / n) if n else np.nan,
                            "median_signed_close_atr": med_signed,
                            "same_bar_rejection_rate": (n_rej_sb / n) if n else np.nan,
                            "same_bar_breakthrough_rate": (n_brk_sb / n) if n else np.nan,
                            "sign": np.sign(med_signed) if pd.notna(med_signed) else np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def _year_flags(yr_sub: pd.DataFrame) -> dict:
    signs = yr_sub["sign"].dropna()
    n_years_with_10 = int((yr_sub["n_events"] >= 10).sum())
    agree_count = 0
    if len(signs) > 0:
        mode_sign = signs.mode()
        if len(mode_sign):
            agree_count = int((signs == mode_sign.iloc[0]).sum())
    return {"n_years_with_ge10_events": n_years_with_10, "max_year_sign_agreement": agree_count}


def classify_primary(pc: pd.DataFrame, yr: pd.DataFrame) -> pd.DataFrame:
    out_rows = []
    for _, row in pc.iterrows():
        n_touch = row["touch_events"]
        n_nontied = row["barrier_nontied_n"]
        yr_sub = yr.loc[
            (yr["instrument"] == row["instrument"])
            & (yr["session"] == row["session"])
            & (yr["approach_side"] == row["approach_side"])
            & (yr["touch_time_bucket"] == row["touch_time_bucket"])
            & (yr["horizon_bars"] == row["horizon_bars"])
        ]
        flags = _year_flags(yr_sub) if len(yr_sub) else {"n_years_with_ge10_events": 0, "max_year_sign_agreement": 0}
        min_sample_met = n_touch >= MIN_TOUCH and n_nontied >= MIN_NONTIED
        effect_pp = row["barrier_rej_minus_brk_first_rate"] * 100 if pd.notna(row["barrier_rej_minus_brk_first_rate"]) else np.nan
        effect_ok = pd.notna(effect_pp) and abs(effect_pp) >= MIN_EFFECT_PP
        q = row.get("q_value_primary", np.nan)
        q_ok = pd.notna(q) and q < 0.05
        med_signed = row["median_signed_close_atr"]
        sign_matches = (
            pd.notna(med_signed) and pd.notna(effect_pp) and effect_pp != 0
            and np.sign(med_signed) == np.sign(effect_pp)
        )
        year_ok = flags["max_year_sign_agreement"] >= 4

        if not min_sample_met:
            label = "UNDERPOWERED"
        elif effect_ok and q_ok and sign_matches and year_ok:
            label = "REJECTION_DOMINANT" if effect_pp > 0 else "BREAKTHROUGH_DOMINANT"
        else:
            label = "MIXED_OR_NULL"

        d = row.to_dict()
        d.update(flags)
        d["effect_pp"] = effect_pp
        d["min_sample_met"] = min_sample_met
        d["classification"] = label
        out_rows.append(d)
    return pd.DataFrame(out_rows)


def classify_sessions(classified: pd.DataFrame) -> pd.DataFrame:
    """Session-level mechanism classification, SPEC_SESSION_HORIZONS.md sec 14."""
    rows = []
    keys = ["instrument", "session", "approach_side"]
    directional = {"REJECTION_DOMINANT", "BREAKTHROUGH_DOMINANT"}
    for gvals, g in classified.groupby(keys):
        instrument, session, side = gvals
        dirs = g.loc[g["classification"].isin(directional)]
        label = "NO_COHERENT_SESSION_MECHANISM"
        support_notes = ""
        for direction, cls_name in (
            ("REJECTION_DOMINANT", f"{session}_REJECTION_MECHANISM"),
            ("BREAKTHROUGH_DOMINANT", f"{session}_BREAKTHROUGH_MECHANISM"),
        ):
            dd = dirs.loc[dirs["classification"] == direction]
            if dd.empty:
                continue
            found = False
            for bucket in dd["touch_time_bucket"].unique():
                db = dd.loc[dd["touch_time_bucket"] == bucket]
                horizons_here = sorted(db["horizon_bars"].unique(), key=lambda h: HORIZON_ORDER[h])
                adj_horizon = any(
                    HORIZON_ORDER[horizons_here[k + 1]] - HORIZON_ORDER[horizons_here[k]] == 1
                    for k in range(len(horizons_here) - 1)
                )
                if not adj_horizon:
                    continue
                if bucket == "SESSION_0_TO_30":
                    # single-bucket exception: adjacent-horizon support alone suffices
                    combined_years = g.loc[
                        (g["classification"] == direction) & (g["touch_time_bucket"] == bucket)
                    ]
                    if _pooled_year_support(combined_years):
                        found = True
                        support_notes = f"{bucket} (first-30-min exception), horizons {horizons_here}"
                        break
                    continue
                buckets_here = sorted(dd["touch_time_bucket"].unique(), key=lambda b: BUCKET_ORDER[b])
                adj_bucket = any(
                    BUCKET_ORDER[buckets_here[k + 1]] - BUCKET_ORDER[buckets_here[k]] == 1
                    for k in range(len(buckets_here) - 1)
                )
                if adj_bucket:
                    combined = dd
                    if _pooled_year_support(combined):
                        found = True
                        support_notes = f"buckets {buckets_here}, horizons {horizons_here}"
                        break
            if found:
                label = cls_name
                break
        rows.append(
            {
                "instrument": instrument,
                "session": session,
                "approach_side": side,
                "n_directional_cells": len(dirs),
                "session_mechanism": label,
                "support": support_notes,
            }
        )
    return pd.DataFrame(rows)


def _pooled_year_support(cells: pd.DataFrame) -> bool:
    """>=4-of-5-year sign agreement, using max_year_sign_agreement already
    computed per cell; require it in at least one corroborating cell."""
    if cells.empty:
        return False
    return bool((cells["max_year_sign_agreement"] >= 4).any())
