"""Standalone feature-vs-target screen — SPEC_PREDICTOR.md Sec. 8-10.
480 elementary tests (2 instruments x 5 features x 6 windows x 4 horizons x
2 targets), each logged as one RUN_REGISTRY.csv row. No interactions.
"""
import os

import numpy as np
import pandas as pd

from .analysis_utils import (OUT, TAB, Registry, boot_ci_corr, n_valid_pairs,
                             pearson, spearman, z_from_spearman)
from .prev_close_features import WINDOWS

FEATURES = ("norm_ret", "range_ratio", "close_location", "signed_efficiency", "volume_ratio")
HORIZONS = (5, 10, 15, 30)
TARGETS = ("R", "Q")
COVERAGE_LEVELS = (1.00, 0.50, 0.30, 0.15)
N_TESTS = 2 * len(FEATURES) * len(WINDOWS) * len(HORIZONS) * len(TARGETS)
ALPHA = 0.05
BONF_ALPHA = ALPHA / N_TESTS


def load(inst):
    return pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_predictor_ledger.parquet"))


def _rank_corr_small_n(a, b):
    """Spearman rank correlation with no minimum-n gate (for the 5-point
    quintile-mean monotonicity check, where n=5 is expected, not an error)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return np.nan
    ar = pd.Series(a).rank().to_numpy()
    br = pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ar, br)[0, 1])


def quintile_table(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 50:
        return None, np.nan
    try:
        d["q"] = pd.qcut(d["x"], 5, labels=False, duplicates="drop")
    except ValueError:
        return None, np.nan
    means = d.groupby("q")["y"].mean()
    mono = _rank_corr_small_n(means.index.to_numpy(), means.to_numpy())
    return means.to_dict(), mono


def coverage_stats(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    n_total = len(d)
    out = {}
    if n_total < 20:
        for c in COVERAGE_LEVELS:
            out[c] = {"n": 0, "accuracy": np.nan, "mean_y": np.nan}
        return out
    d["absx"] = d["x"].abs()
    d = d.sort_values("absx", ascending=False)
    for c in COVERAGE_LEVELS:
        k = max(1, int(round(n_total * c)))
        sub = d.iloc[:k]
        signed = sub[(sub["x"] != 0) & (sub["y"] != 0)]
        acc = float((np.sign(signed["x"]) == np.sign(signed["y"])).mean()) if len(signed) else np.nan
        out[c] = {"n": k, "accuracy": acc, "mean_y": float(sub["y"].mean())}
    return out


def symmetry_stats(x, y, seed):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    pos, neg = d[d["x"] > 0]["y"], d[d["x"] < 0]["y"]
    if len(pos) < 10 or len(neg) < 10:
        return np.nan, np.nan, np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    diffs = []
    pv, nv = pos.to_numpy(), neg.to_numpy()
    for _ in range(300):
        dp = rng.choice(pv, len(pv), replace=True).mean()
        dn = rng.choice(nv, len(nv), replace=True).mean()
        diffs.append(dp - dn)
    diffs = np.asarray(diffs)
    return (float(pos.mean()), float(neg.mean()), float(pos.mean() - neg.mean()),
           float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)))


def outlier_influence(x, y, method="spearman"):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 30:
        return np.nan
    idx_drop = d["x"].abs().idxmax()
    d2 = d.drop(index=idx_drop)
    fn = spearman if method == "spearman" else pearson
    return fn(d2["x"].to_numpy(), d2["y"].to_numpy())


def main():
    reg = Registry()
    rows = []
    ledgers = {inst: load(inst) for inst in ("ES", "NQ")}

    for inst, led in ledgers.items():
        for feature in FEATURES:
            for W in WINDOWS:
                xcol = f"prev_{feature}_{W}"
                if xcol not in led.columns:
                    continue
                x_full = led[xcol]
                for h in HORIZONS:
                    for tgt in TARGETS:
                        ycol = f"{tgt}_{h}"
                        y_full = led[ycol]
                        n = n_valid_pairs(x_full, y_full)
                        r_p = pearson(x_full, y_full)
                        r_s = spearman(x_full, y_full)
                        ci_s_lo, ci_s_hi = boot_ci_corr(x_full, y_full, "spearman")
                        ci_p_lo, ci_p_hi = boot_ci_corr(x_full, y_full, "pearson")
                        p_raw = z_from_spearman(r_s, n)
                        sig_bonf = bool(np.isfinite(p_raw) and p_raw < BONF_ALPHA)

                        qmeans, mono = quintile_table(x_full, y_full)
                        cov = coverage_stats(x_full, y_full)
                        pos_m, neg_m, diff_m, diff_lo, diff_hi = symmetry_stats(x_full, y_full, seed=20260711)
                        outl_s = outlier_influence(x_full, y_full, "spearman")

                        d = pd.DataFrame({"x": x_full, "y": y_full,
                                         "year": led["year"]}).dropna()
                        year_rows = {}
                        for yr, g in d.groupby("year"):
                            year_rows[yr] = {"mean": g["y"].mean(), "count": len(g),
                                             "spearman": spearman(g["x"], g["y"])}

                        row = {
                            "instrument": inst, "feature": feature, "window": W, "horizon": h, "target": tgt,
                            "n_valid": n, "pearson_r": r_p, "pearson_ci_lo": ci_p_lo, "pearson_ci_hi": ci_p_hi,
                            "spearman_rho": r_s, "spearman_ci_lo": ci_s_lo, "spearman_ci_hi": ci_s_hi,
                            "p_raw_approx": p_raw, "bonferroni_alpha": BONF_ALPHA, "significant_bonf": sig_bonf,
                            "quintile_monotonicity_spearman": mono,
                            "q0_mean": qmeans.get(0) if qmeans else np.nan,
                            "q4_mean": qmeans.get(4) if qmeans else np.nan,
                            "cov100_n": cov[1.00]["n"], "cov100_acc": cov[1.00]["accuracy"],
                            "cov50_n": cov[0.50]["n"], "cov50_acc": cov[0.50]["accuracy"],
                            "cov30_n": cov[0.30]["n"], "cov30_acc": cov[0.30]["accuracy"],
                            "cov15_n": cov[0.15]["n"], "cov15_acc": cov[0.15]["accuracy"],
                            "mean_y_given_x_pos": pos_m, "mean_y_given_x_neg": neg_m,
                            "bull_bear_diff": diff_m, "bull_bear_diff_ci_lo": diff_lo, "bull_bear_diff_ci_hi": diff_hi,
                            "spearman_drop_top_outlier": outl_s,
                            "n_years": len(year_rows),
                        }
                        for yr, v in year_rows.items():
                            row[f"year_{yr}_mean"] = v["mean"]
                            row[f"year_{yr}_n"] = v["count"]
                            row[f"year_{yr}_spearman"] = v["spearman"]
                        rows.append(row)
                reg.log("feature_window_screen", {"instrument": inst, "feature": feature, "window": W},
                       metric=r_s if np.isfinite(r_s) else "")

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(TAB, "feature_screen_full.csv"), index=False)

    # compact top-line table (no year columns) for quick reading
    core_cols = ["instrument", "feature", "window", "horizon", "target", "n_valid",
                "pearson_r", "pearson_ci_lo", "pearson_ci_hi", "spearman_rho",
                "spearman_ci_lo", "spearman_ci_hi", "p_raw_approx", "significant_bonf",
                "quintile_monotonicity_spearman", "cov100_acc", "cov50_acc", "cov30_acc",
                "cov15_acc", "bull_bear_diff", "bull_bear_diff_ci_lo", "bull_bear_diff_ci_hi",
                "spearman_drop_top_outlier"]
    out[core_cols].to_csv(os.path.join(TAB, "feature_screen_core.csv"), index=False)

    # effective-N sensitivity: average pairwise |Spearman| among the 30 features, per instrument
    eff_rows = []
    for inst, led in ledgers.items():
        cols = [f"prev_{f}_{W}" for f in FEATURES for W in WINDOWS if f"prev_{f}_{W}" in led.columns]
        corrs = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                rho = spearman(led[cols[i]], led[cols[j]])
                if np.isfinite(rho):
                    corrs.append(abs(rho))
        avg_abs_rho = float(np.mean(corrs)) if corrs else np.nan
        m = len(cols)
        eff_n = m / (1 + (m - 1) * avg_abs_rho) if np.isfinite(avg_abs_rho) else np.nan
        eff_rows.append({"instrument": inst, "n_features": m, "avg_abs_pairwise_spearman": avg_abs_rho,
                         "effective_n_features": eff_n})
        reg.log("effective_n_sensitivity", {"instrument": inst})
    pd.DataFrame(eff_rows).to_csv(os.path.join(TAB, "effective_n_sensitivity.csv"), index=False)

    # sample-size / exclusion summary
    excl_rows = []
    for inst in ("ES", "NQ"):
        excl = pd.read_csv(os.path.join(OUT, f"{inst.lower()}_exclusions.csv"))
        for reason, cnt in excl["reason"].value_counts().items():
            excl_rows.append({"instrument": inst, "reason": reason, "n": int(cnt)})
        excl_rows.append({"instrument": inst, "reason": "primary_valid_rows", "n": len(ledgers[inst])})
    pd.DataFrame(excl_rows).to_csv(os.path.join(TAB, "sample_summary.csv"), index=False)

    print(f"registered tests logged: {reg.n}; total elementary tests: {N_TESTS}")


if __name__ == "__main__":
    main()
