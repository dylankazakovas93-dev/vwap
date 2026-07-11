"""Descriptive analysis over the atlas ledgers. Development partition only.
Purely descriptive: no predictor, rule, or selection of any kind.
"""
import os

import numpy as np
import pandas as pd

from .analysis_utils import OUT, TAB, Registry, session_boot_ci, spearman
from .atlas import PRIMARY_HORIZONS, SECONDARY_HORIZON

ALL_H = list(PRIMARY_HORIZONS) + [SECONDARY_HORIZON]
QUANTS = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)
MIN_YEAR_CELL = 20  # reporting floor for year-by-year cells


def load(inst):
    return pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_atlas_ledger.parquet"))


def main():
    reg = Registry()
    rows_summary, rows_dirfreq, rows_agree, rows_year = [], [], [], []
    rows_symmetry, rows_concentration, rows_corr, rows_anomaly = [], [], [], []
    rows_crossinst = []

    ledgers = {inst: load(inst) for inst in ("ES", "NQ")}

    for inst, led in ledgers.items():
        for h in ALL_H:
            valid_col = "R" if h in PRIMARY_HORIZONS else "R"
            sub = led if h in PRIMARY_HORIZONS else led[led["secondary_valid"]]
            n = len(sub)
            for metric in ("R", "U", "D", "Q", "E"):
                col = f"{metric}_{h}"
                vals = sub[col].dropna()
                n_undef = int(sub[col].isna().sum()) if metric in ("Q", "E") else 0
                rec = {"instrument": inst, "horizon": h, "metric": metric,
                      "n_valid": n, "n_defined": len(vals), "n_undefined": n_undef,
                      "mean": float(vals.mean()) if len(vals) else np.nan,
                      "median": float(vals.median()) if len(vals) else np.nan}
                for q in QUANTS:
                    rec[f"q{int(q*100)}"] = float(vals.quantile(q)) if len(vals) else np.nan
                if len(vals) >= 5:
                    lo, hi = session_boot_ci(vals.to_numpy())
                    rec["mean_ci_lo"], rec["mean_ci_hi"] = lo, hi
                rows_summary.append(rec)
            reg.log("summary_stats", {"instrument": inst, "horizon": h})

            # direction / dominant-side frequencies
            for label_col, name in ((f"closing_direction_{h}", "closing_direction"),
                                    (f"dominant_side_{h}", "dominant_side")):
                vc = sub[label_col].value_counts(normalize=True)
                rec = {"instrument": inst, "horizon": h, "label": name, "n": n}
                for cat in vc.index:
                    rec[cat] = float(vc[cat])
                rows_dirfreq.append(rec)

            # initial/final agreement (h != 1)
            if h != 1:
                vc = sub[f"initial_final_agree_{h}"].value_counts(normalize=True)
                rec = {"instrument": inst, "horizon": h, "n": n}
                for cat in vc.index:
                    rec[cat] = float(vc[cat])
                rows_agree.append(rec)

            # upper-vs-lower symmetry: mean(U) vs mean(D), paired diff CI
            u, d = sub[f"U_{h}"].dropna(), sub[f"D_{h}"].dropna()
            common = sub.dropna(subset=[f"U_{h}", f"D_{h}"])
            diff = (common[f"U_{h}"] - common[f"D_{h}"]).to_numpy()
            lo, hi = session_boot_ci(diff) if len(diff) >= 5 else (np.nan, np.nan)
            rows_symmetry.append({"instrument": inst, "horizon": h, "n": len(diff),
                                  "mean_U": float(u.mean()) if len(u) else np.nan,
                                  "mean_D": float(d.mean()) if len(d) else np.nan,
                                  "mean_U_minus_D": float(diff.mean()) if len(diff) else np.nan,
                                  "ci_lo": lo, "ci_hi": hi})

            # concentration: top-decile share of |R| and of (U+D)
            for metric, series in ((f"R_{h}", sub[f"R_{h}"].abs()),
                                   (f"UplusD_{h}", (sub[f"U_{h}"] + sub[f"D_{h}"]))):
                s = series.dropna()
                if len(s) >= 10 and s.sum() > 0:
                    top_n = max(1, len(s) // 10)
                    share = float(s.nlargest(top_n).sum() / s.sum())
                else:
                    share = np.nan
                rows_concentration.append({"instrument": inst, "horizon": h,
                                           "metric": metric, "n": len(s),
                                           "top10pct_share": share})
            reg.log("symmetry_concentration", {"instrument": inst, "horizon": h})

        # year-by-year (R, Q) mean+count for each horizon
        for h in ALL_H:
            sub = led if h in PRIMARY_HORIZONS else led[led["secondary_valid"]]
            for metric in ("R", "Q"):
                col = f"{metric}_{h}"
                for yr, g in sub.groupby("year"):
                    vals = g[col].dropna()
                    if len(vals) < MIN_YEAR_CELL:
                        rows_year.append({"instrument": inst, "horizon": h, "metric": metric,
                                          "year": int(yr), "n": len(vals), "mean": np.nan,
                                          "note": "below_min_cell"})
                        continue
                    rows_year.append({"instrument": inst, "horizon": h, "metric": metric,
                                      "year": int(yr), "n": len(vals), "mean": float(vals.mean()),
                                      "note": ""})
        reg.log("year_by_year", {"instrument": inst})

        # correlation matrix across {R,U,D,Q,E} x horizons within instrument
        cols = [f"{m}_{h}" for h in ALL_H for m in ("R", "U", "D", "Q", "E")]
        cols = [c for c in cols if c in led.columns]
        corr_data = led[cols]
        for i, c1 in enumerate(cols):
            for c2 in cols[i:]:
                rho = spearman(corr_data[c1], corr_data[c2])
                rows_corr.append({"instrument": inst, "var1": c1, "var2": c2, "spearman": rho})
        reg.log("correlation_matrix", {"instrument": inst, "n_pairs": len(cols) * (len(cols) + 1) // 2})

        # anomaly inventory: coded-invariant checks
        for h in ALL_H:
            sub = led if h in PRIMARY_HORIZONS else led[led["secondary_valid"]]
            neg_u = int((sub[f"U_{h}"] < 0).sum())
            neg_d = int((sub[f"D_{h}"] < 0).sum())
            q = sub[f"Q_{h}"].dropna()
            q_oob = int(((q < -1.0000001) | (q > 1.0000001)).sum())
            rows_anomaly.append({"instrument": inst, "horizon": h, "check": "U>=0_violations", "n": neg_u})
            rows_anomaly.append({"instrument": inst, "horizon": h, "check": "D>=0_violations", "n": neg_d})
            rows_anomaly.append({"instrument": inst, "horizon": h, "check": "Q_out_of_bounds", "n": q_oob})
        # monotonicity of U,D across nested horizons (U_h non-decreasing in h)
        for base in ("U", "D"):
            prev = None
            for h in PRIMARY_HORIZONS:
                col = led[f"{base}_{h}"]
                if prev is not None:
                    viol = int((col < prev - 1e-9).sum())
                    rows_anomaly.append({"instrument": inst, "horizon": h,
                                         "check": f"{base}_monotone_violations_vs_prev_h", "n": viol})
                prev = col
        missing_path = os.path.join(OUT, f"{inst.lower()}_missing_sessions.csv")
        if os.path.exists(missing_path):
            miss = pd.read_csv(missing_path)
            for reason, cnt in miss["reason"].value_counts().items():
                rows_anomaly.append({"instrument": inst, "horizon": np.nan,
                                     "check": f"missing_session:{reason}", "n": int(cnt)})
        reg.log("anomaly_inventory", {"instrument": inst})

    # ES vs NQ correlation at matching horizons (on the intersection of session dates)
    es, nq = ledgers["ES"], ledgers["NQ"]
    merged = es[["session_date"] + [f"R_{h}" for h in ALL_H] + [f"Q_{h}" for h in ALL_H]].merge(
        nq[["session_date"] + [f"R_{h}" for h in ALL_H] + [f"Q_{h}" for h in ALL_H]],
        on="session_date", suffixes=("_ES", "_NQ"))
    for h in ALL_H:
        for metric in ("R", "Q"):
            rho = spearman(merged[f"{metric}_{h}_ES"], merged[f"{metric}_{h}_NQ"])
            rows_crossinst.append({"horizon": h, "metric": metric, "spearman_ES_NQ": rho, "n": len(merged)})
    reg.log("cross_instrument_correlation", {"n_sessions": len(merged)})

    pd.DataFrame(rows_summary).to_csv(os.path.join(TAB, "summary_stats.csv"), index=False)
    pd.DataFrame(rows_dirfreq).to_csv(os.path.join(TAB, "direction_frequencies.csv"), index=False)
    pd.DataFrame(rows_agree).to_csv(os.path.join(TAB, "initial_final_agreement.csv"), index=False)
    pd.DataFrame(rows_year).to_csv(os.path.join(TAB, "year_by_year.csv"), index=False)
    pd.DataFrame(rows_symmetry).to_csv(os.path.join(TAB, "upper_lower_symmetry.csv"), index=False)
    pd.DataFrame(rows_concentration).to_csv(os.path.join(TAB, "concentration.csv"), index=False)
    pd.DataFrame(rows_corr).to_csv(os.path.join(TAB, "correlation_matrix.csv"), index=False)
    pd.DataFrame(rows_crossinst).to_csv(os.path.join(TAB, "cross_instrument_correlation.csv"), index=False)
    pd.DataFrame(rows_anomaly).to_csv(os.path.join(TAB, "anomaly_inventory.csv"), index=False)
    print("registry rows:", reg.n)


if __name__ == "__main__":
    main()
