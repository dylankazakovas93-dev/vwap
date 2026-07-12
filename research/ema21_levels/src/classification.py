"""Primary-family BH correction, year stability, and classification.

See SPEC_EMA21_LEVELS.md sections 11-13.
"""
import numpy as np
import pandas as pd

from .summary import STRATA, binom_p, benjamini_hochberg

PRIMARY_HORIZON = 5
PRIMARY_BARRIER = 1.0
MIN_TOUCH = 50
MIN_NONTIED = 20
MIN_EFFECT_PP = 5.0
MIN_YEARS_WITH_10 = 4
YEARS = (2018, 2019, 2020, 2021, 2022)


def primary_cells(cells_df: pd.DataFrame) -> pd.DataFrame:
    return cells_df.loc[
        (cells_df["horizon_bars"] == PRIMARY_HORIZON) & (cells_df["barrier_atr"] == PRIMARY_BARRIER)
    ].copy()


def apply_bh_primary(cells_df: pd.DataFrame) -> pd.DataFrame:
    pc = primary_cells(cells_df).reset_index(drop=True)
    pc["bh_family"] = pc.apply(
        lambda r: f"{r['instrument']}|{r['ema_session_definition']}|{r['time_stratum']}", axis=1
    )
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
    keys = ["instrument", "ema_session_definition", "ema_span", "approach_side"]
    for gvals, g in events_full.groupby(keys):
        instrument, session_def, span, side = gvals
        for stratum in STRATA:
            gs = g if stratum == "ALL_RTH" else g.loc[g["time_stratum"] == stratum]
            for year in YEARS:
                gy = gs.loc[gs["year"] == year]
                n = len(gy)
                n_rej_sb = int((gy["same_bar_morphology"] == "SAME_BAR_REJECTION_PROXY").sum())
                n_brk_sb = int((gy["same_bar_morphology"] == "SAME_BAR_BREAKTHROUGH_PROXY").sum())
                sb_diff = ((n_rej_sb - n_brk_sb) / n) if n else np.nan

                row = {
                    "instrument": instrument,
                    "ema_session_definition": session_def,
                    "ema_span": span,
                    "approach_side": side,
                    "time_stratum": stratum,
                    "year": year,
                    "n_events": n,
                    "same_bar_rej_minus_brk": sb_diff,
                }
                for b in (0.5, 1.0):
                    col = f"b{b}_h{PRIMARY_HORIZON}_outcome"
                    if col in gy.columns and n:
                        vc = gy[col].value_counts()
                        rej = int(vc.get("REJECTION_FIRST", 0))
                        brk = int(vc.get("BREAKTHROUGH_FIRST", 0))
                        row[f"barrier{b}_rej_minus_brk_first_rate"] = (rej - brk) / n
                    else:
                        row[f"barrier{b}_rej_minus_brk_first_rate"] = np.nan
                valid_h = gy.loc[gy[f"horizon_{PRIMARY_HORIZON}_complete"] & gy["atr_valid"]] if n else gy
                row["median_signed_close_atr"] = (
                    float(valid_h[f"signed_close_atr_h{PRIMARY_HORIZON}"].median()) if len(valid_h) else np.nan
                )
                row["sign"] = (
                    np.sign(row["median_signed_close_atr"])
                    if pd.notna(row["median_signed_close_atr"])
                    else np.nan
                )
                rows.append(row)
    return pd.DataFrame(rows)


def _year_flags(yr_sub: pd.DataFrame) -> dict:
    signs = yr_sub["sign"].dropna()
    n_years_with_10 = int((yr_sub["n_events"] >= 10).sum())
    sign_reversal = False
    if len(signs) >= 2:
        sign_reversal = bool((signs.diff().dropna() != 0).any() and signs.nunique() > 1)
    year_events = yr_sub.set_index("year")["n_events"]
    total = year_events.sum()
    one_year_dominance = bool(total > 0 and (year_events.max() / total) >= 0.5)
    covid_conc = bool(total > 0 and year_events.get(2020, 0) / total >= 0.5)
    agree_count = 0
    if len(signs) > 0:
        mode_sign = signs.mode()
        if len(mode_sign):
            agree_count = int((signs == mode_sign.iloc[0]).sum())
    return {
        "n_years_with_ge10_events": n_years_with_10,
        "sign_reversal": sign_reversal,
        "one_year_dominance": one_year_dominance,
        "year_2020_concentration": covid_conc,
        "max_year_sign_agreement": agree_count,
    }


def classify_primary(pc: pd.DataFrame, yr: pd.DataFrame) -> pd.DataFrame:
    pc = pc.copy()
    out_rows = []
    for _, row in pc.iterrows():
        n_touch = row["touch_events"]
        n_nontied = row["barrier_nontied_n"]
        yr_sub = yr.loc[
            (yr["instrument"] == row["instrument"])
            & (yr["ema_session_definition"] == row["ema_session_definition"])
            & (yr["ema_span"] == row["ema_span"])
            & (yr["approach_side"] == row["approach_side"])
            & (yr["time_stratum"] == row["time_stratum"])
        ]
        flags = _year_flags(yr_sub) if len(yr_sub) else {
            "n_years_with_ge10_events": 0, "sign_reversal": np.nan,
            "one_year_dominance": np.nan, "year_2020_concentration": np.nan,
            "max_year_sign_agreement": 0,
        }
        min_sample_met = (
            n_touch >= MIN_TOUCH
            and n_nontied >= MIN_NONTIED
            and flags["n_years_with_ge10_events"] >= MIN_YEARS_WITH_10
        )
        effect_pp = row["barrier_rej_minus_brk_first_rate"] * 100 if pd.notna(row["barrier_rej_minus_brk_first_rate"]) else np.nan
        effect_ok = pd.notna(effect_pp) and abs(effect_pp) >= MIN_EFFECT_PP
        q = row.get("q_value_primary", np.nan)
        q_ok = pd.notna(q) and q < 0.05
        med_signed = row["median_signed_close_atr"]
        sign_matches = False
        if pd.notna(med_signed) and pd.notna(effect_pp) and effect_pp != 0:
            sign_matches = np.sign(med_signed) == np.sign(effect_pp)
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


def classify_specificity(classified: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["instrument", "ema_session_definition", "approach_side", "time_stratum"]
    for gvals, g in classified.groupby(keys):
        instrument, session_def, side, stratum = gvals
        by_span = {int(r["ema_span"]): r for _, r in g.iterrows()}
        if not all(s in by_span for s in (20, 21, 22)):
            continue
        c20, c21, c22 = by_span[20]["classification"], by_span[21]["classification"], by_span[22]["classification"]
        e20, e21, e22 = (
            abs(by_span[20]["effect_pp"]) if pd.notna(by_span[20]["effect_pp"]) else 0,
            abs(by_span[21]["effect_pp"]) if pd.notna(by_span[21]["effect_pp"]) else 0,
            abs(by_span[22]["effect_pp"]) if pd.notna(by_span[22]["effect_pp"]) else 0,
        )
        directional = {"REJECTION_DOMINANT", "BREAKTHROUGH_DOMINANT"}
        if c21 in directional and c20 != c21 and c22 != c21 and (e21 - e20) >= 5.0 and (e21 - e22) >= 5.0:
            spec = "EMA21_SPECIFIC"
        elif (c20 == c21 == c22) and max(abs(e20 - e21), abs(e21 - e22), abs(e20 - e22)) < 5.0:
            spec = "GENERIC_EMA_ZONE"
        elif c20 == c22 == "MIXED_OR_NULL" and c21 == "MIXED_OR_NULL":
            spec = "GENERIC_EMA_ZONE"
        else:
            spec = "INCONCLUSIVE_SPECIFICITY"
        rows.append(
            {
                "instrument": instrument,
                "ema_session_definition": session_def,
                "approach_side": side,
                "time_stratum": stratum,
                "ema20_classification": c20,
                "ema21_classification": c21,
                "ema22_classification": c22,
                "ema20_effect_pp": e20,
                "ema21_effect_pp": e21,
                "ema22_effect_pp": e22,
                "specificity": spec,
            }
        )
    return pd.DataFrame(rows)
