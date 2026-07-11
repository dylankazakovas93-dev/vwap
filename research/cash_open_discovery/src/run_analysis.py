"""Preregistered discovery analysis over the episode ledgers.
Development partition only. Writes reports/tables/*.csv and RUN_REGISTRY.csv.
"""
import os

import numpy as np
import pandas as pd

from .analysis_utils import OUT, TAB, Registry, session_boot_ci, spearman

MIN_CELL = 100  # SPEC_DISCOVERY Sec. 8
TICK = 0.25
TIMING_BINS = [(0, 5, "0-5"), (5, 10, "5-10"), (10, 15, "10-15"), (15, np.inf, ">15")]


def _bin_timing(x):
    for lo, hi, lab in TIMING_BINS:
        if lo <= x < hi:
            return lab
    return np.nan


def load(inst, label):
    return pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_{label}_ledger.parquet"))


def directional(led):
    return led[led["outer_direction"] != "AMBIGUOUS_DIRECTION"].copy()


def main():
    reg = Registry()
    rows_counts, rows_q1, rows_q2, rows_q3, rows_q4, rows_q5 = [], [], [], [], [], []
    rows_overnight, rows_concentration, rows_ambig = [], [], []

    for inst in ("ES", "NQ"):
        led = load(inst, "primary")

        # ambiguous-direction rate by A (reported explicitly, Sec. 4/8)
        for A, g in led.groupby("A"):
            rows_ambig.append({"instrument": inst, "A": A, "n_total": len(g),
                               "n_ambiguous": int((g["outer_direction"] == "AMBIGUOUS_DIRECTION").sum()),
                               "ambiguous_rate": float((g["outer_direction"] == "AMBIGUOUS_DIRECTION").mean())})
        reg.log("ambiguous_rate", {"instrument": inst, "family": "ambiguous_by_A"})

        d = directional(led)
        d["year"] = pd.to_datetime(d["session_date"]).dt.year
        d["month"] = pd.to_datetime(d["session_date"]).dt.to_period("M").astype(str)
        d["timing_outer_bin"] = d["minutes_to_outer"].apply(_bin_timing)

        # event counts by year/month/direction/A/timing
        c = d.groupby(["A", "outer_direction", "year"]).size().rename("n").reset_index()
        c["instrument"] = inst
        rows_counts.append(c)
        reg.log("counts", {"instrument": inst, "family": "counts"})

        # ===== Q1: held vs reclaimed matched comparison at checkpoints H=5/10/15 =====
        for H in (5, 10, 15):
            status_col = f"cp{H}_status"
            for A, g in d.groupby("A"):
                if len(g) < MIN_CELL:
                    continue
                for status, gg in g.groupby(status_col):
                    if len(gg) < 30:  # descriptive floor for sub-cells
                        continue
                    for h in (5, 15, 30):
                        col = f"cp{H}_fret_{h}"
                        vals = gg[col].dropna()
                        if len(vals) < 20:
                            continue
                        lo, hi = session_boot_ci(gg.dropna(subset=[col]).assign(y=gg[col]),
                                                 lambda b: b["y"].mean(), nboot=300)
                        rows_q1.append({"instrument": inst, "A": A, "checkpoint_H": H,
                                        "status": status, "n": len(gg), "horizon_min": h,
                                        "mean_fret_ticks": float(vals.mean() / TICK),
                                        "ci_lo_ticks": lo / TICK, "ci_hi_ticks": hi / TICK,
                                        "p_above_zero": float((vals > 0).mean())})
        reg.log("q1_held_vs_reclaimed", {"instrument": inst, "family": "q1"})

        # ===== Q2: reclaim speed (using the reclaim_50 decision path) =====
        r = d[d["reclaim_50_tau"].notna()].copy()
        r["speed_bin"] = r["minutes_to_reclaim_50"].apply(_bin_timing)
        for A, g in r.groupby("A"):
            if len(g) < MIN_CELL:
                continue
            for sb, gg in g.groupby("speed_bin"):
                if len(gg) < 30:
                    continue
                for h in (15, 30):
                    col = f"reclaim_50_fret_{h}"
                    vals = gg[col].dropna()
                    if len(vals) < 20:
                        continue
                    rows_q2.append({"instrument": inst, "A": A, "speed_bin": sb, "n": len(gg),
                                    "horizon_min": h, "mean_fret_ticks": float(vals.mean() / TICK)})
            rho = spearman(g["minutes_to_reclaim_50"], g["reclaim_50_fret_30"])
            reg.log("q2_reclaim_speed", {"instrument": inst, "A": A}, metric=rho)
        rows_q2_mono = spearman(r["minutes_to_reclaim_50"], r["reclaim_50_fret_30"])
        rows_q2.append({"instrument": inst, "A": "ALL", "speed_bin": "spearman_overall",
                        "n": len(r), "horizon_min": 30, "mean_fret_ticks": rows_q2_mono})

        # ===== Q3: outer-excursion speed =====
        r2 = d[d["reclaim_50_tau"].notna()].copy()
        r2["outer_speed_bin"] = r2["minutes_to_outer"].apply(_bin_timing)
        for A, g in r2.groupby("A"):
            if len(g) < MIN_CELL:
                continue
            for sb, gg in g.groupby("outer_speed_bin"):
                if len(gg) < 30:
                    continue
                vals = gg["reclaim_50_fret_30"].dropna()
                if len(vals) < 20:
                    continue
                rows_q3.append({"instrument": inst, "A": A, "outer_speed_bin": sb,
                                "n": len(gg), "mean_fret_30_ticks": float(vals.mean() / TICK)})
        rho3 = spearman(r2["minutes_to_outer"], r2["reclaim_50_fret_30"])
        rows_q3.append({"instrument": inst, "A": "ALL", "outer_speed_bin": "spearman_overall",
                        "n": len(r2), "mean_fret_30_ticks": rho3})
        reg.log("q3_outer_speed", {"instrument": inst, "family": "q3"})

        # ===== Q4: magnitude (A domain) effect =====
        for A, g in d.groupby("A"):
            reclaimed = g[g["reclaim_50_tau"].notna()]
            vals = reclaimed["reclaim_50_fret_30"].dropna()
            rows_q4.append({"instrument": inst, "A": A, "n_episodes": len(g),
                            "reclaim_rate": float(g["reclaim_type"].isin(["HALF", "FULL"]).mean()),
                            "n_reclaimed": len(reclaimed),
                            "mean_fret_30_ticks": float(vals.mean() / TICK) if len(vals) >= 20 else np.nan})
        reg.log("q4_magnitude", {"instrument": inst, "family": "q4"})

        # ===== Q5: full vs partial reclaim =====
        for A, g in d.groupby("A"):
            half_only = g[g["reclaim_type"] == "HALF"]
            full = g[g["reclaim_type"] == "FULL"]
            for label_, gg, col in (("HALF_only", half_only, "reclaim_50_fret_30"),
                                    ("FULL", full, "reclaim_full_fret_30")):
                vals = gg[col].dropna()
                rec = {"instrument": inst, "A": A, "group": label_, "n": len(gg)}
                if len(vals) >= 20:
                    lo, hi = session_boot_ci(gg.dropna(subset=[col]).assign(y=gg[col]),
                                             lambda b: b["y"].mean(), nboot=300)
                    rec.update({"mean_fret_30_ticks": float(vals.mean() / TICK),
                               "ci_lo_ticks": lo / TICK, "ci_hi_ticks": hi / TICK})
                else:
                    rec.update({"mean_fret_30_ticks": np.nan, "ci_lo_ticks": np.nan, "ci_hi_ticks": np.nan})
                rows_q5.append(rec)
        reg.log("q5_full_vs_partial", {"instrument": inst, "family": "q5"})

        # ===== overnight/prior-session explanatory value =====
        expl_vars = ["globex_open_to_0929_return", "prior_close_to_0929_gap",
                    "position_in_overnight_range", "overnight_path_efficiency",
                    "overnight_pct_bars_up", "final10min_return", "final30min_return",
                    "final60min_return", "final10min_path_efficiency",
                    "final10min_priorclose_return", "final10min_priorclose_path_eff",
                    "final10min_sessionend_return", "dist_from_vwap_0929_at_open"]
        dirn = d[d["A"] == 1.0].copy()
        dirn["is_upper"] = (dirn["outer_direction"] == "upper").astype(float)
        dirn["reclaimed_any"] = dirn["reclaim_type"].isin(["HALF", "FULL"]).astype(float)
        d1 = dirn[dirn["reclaim_50_tau"].notna()]
        for v in expl_vars:
            if v not in dirn.columns:
                continue
            rows_overnight.append({"instrument": inst, "variable": v, "target": "which_side_first(upper=1)",
                                   "spearman": spearman(dirn[v], dirn["is_upper"]), "n": dirn[v].notna().sum()})
            rows_overnight.append({"instrument": inst, "variable": v, "target": "reclaimed_any",
                                   "spearman": spearman(dirn[v], dirn["reclaimed_any"]), "n": dirn[v].notna().sum()})
            rows_overnight.append({"instrument": inst, "variable": v, "target": "fwd_return_30_if_reclaimed",
                                   "spearman": spearman(d1[v], d1["reclaim_50_fret_30"]), "n": d1[v].notna().sum()})
        reg.log("overnight_explanatory", {"instrument": inst, "family": "overnight", "vars": expl_vars})

        # ===== concentration diagnostics =====
        for A, g in d.groupby("A"):
            reclaimed = g[g["reclaim_50_tau"].notna()].dropna(subset=["reclaim_50_fret_30"])
            if len(reclaimed) < MIN_CELL:
                continue
            by_year = reclaimed.groupby("year")["reclaim_50_fret_30"].agg(["mean", "count"])
            tot = reclaimed["reclaim_50_fret_30"].sum()
            top10_share = reclaimed["reclaim_50_fret_30"].abs().nlargest(max(1, len(reclaimed) // 10)).sum() / reclaimed["reclaim_50_fret_30"].abs().sum() if reclaimed["reclaim_50_fret_30"].abs().sum() > 0 else np.nan
            rows_concentration.append({"instrument": inst, "A": A, "n": len(reclaimed),
                                       "year_mean_min": float(by_year["mean"].min()),
                                       "year_mean_max": float(by_year["mean"].max()),
                                       "n_years": len(by_year), "top10pct_abs_share": float(top10_share)})
        reg.log("concentration", {"instrument": inst, "family": "concentration"})

    pd.DataFrame(rows_ambig).to_csv(os.path.join(TAB, "ambiguous_rate_by_A.csv"), index=False)
    pd.concat(rows_counts).to_csv(os.path.join(TAB, "event_counts.csv"), index=False)
    pd.DataFrame(rows_q1).to_csv(os.path.join(TAB, "q1_held_vs_reclaimed.csv"), index=False)
    pd.DataFrame(rows_q2).to_csv(os.path.join(TAB, "q2_reclaim_speed.csv"), index=False)
    pd.DataFrame(rows_q3).to_csv(os.path.join(TAB, "q3_outer_speed.csv"), index=False)
    pd.DataFrame(rows_q4).to_csv(os.path.join(TAB, "q4_magnitude.csv"), index=False)
    pd.DataFrame(rows_q5).to_csv(os.path.join(TAB, "q5_full_vs_partial.csv"), index=False)
    pd.DataFrame(rows_overnight).to_csv(os.path.join(TAB, "overnight_explanatory.csv"), index=False)
    pd.DataFrame(rows_concentration).to_csv(os.path.join(TAB, "concentration.csv"), index=False)
    print("registry rows:", reg.n)


if __name__ == "__main__":
    main()
