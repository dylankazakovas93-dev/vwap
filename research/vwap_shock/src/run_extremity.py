"""Family-G analysis: extremity, VWAP-distance, acceptance-strength,
retracement. Continuous/binned response maps only; no optimization.

Writes reports/tables/ext_*.csv and appends configs to RUN_REGISTRY.csv.
"""
import os

import numpy as np
import pandas as pd

from .analysis import Registry, TAB, session_boot_ci, spearman
from .extremity import OUT, RETR_LEVELS, MIN_M_TICKS

MIN_CELL = 300  # preregistered minimum event count per reported cell

# extremity bands by |z_mod1| quantile of the top-10% event population,
# reported as ascending-magnitude ordered bins (monotonicity axis)
Z_BANDS = [("p90_95", 0.0, 0.5), ("p95_98", 0.5, 0.8),
           ("p98_99", 0.8, 0.9), ("p99_100", 0.9, 1.0)]
DEV_BINS = [("1.5-2.0", 1.5, 2.0), ("2.0-2.5", 2.0, 2.5),
            ("2.5-3.0", 2.5, 3.0), ("3.0-4.0", 3.0, 4.0), ("4.0+", 4.0, np.inf)]


def _retr_summary(g):
    """Retracement bucket + failure + break stats for an event group."""
    n = len(g)
    gm = g[g["M_ticks"] >= MIN_M_TICKS]  # fraction cells need a real impulse
    nm = len(gm)
    out = {"n": n, "n_M>=2t": nm, "med_M_ticks": float(g["M_ticks"].median()),
           "break_extreme_rate": float(g["break_extreme"].mean()),
           "full_failure_rate": float(gm["full_failure"].mean()) if nm else np.nan,
           "med_t_break": float(g.loc[g["break_extreme"], "t_break"].median()) if g["break_extreme"].any() else np.nan,
           "fret_30_ticks": float(g["fret_30_ticks"].mean())}
    if nm:
        mr = gm["max_retr_frac"].clip(upper=2.0)
        for lo, hi, lab in [(0.1, 0.2, "10_20"), (0.2, 0.3, "20_30"),
                            (0.3, 0.4, "30_40"), (0.4, 0.5, "40_50"),
                            (0.5, 1.0, "50_100"), (1.0, np.inf, "ge100")]:
            out[f"p_retr_{lab}"] = float(((mr >= lo) & (mr < hi)).mean())
        for R in RETR_LEVELS:
            out[f"p_reach_{int(R*100)}"] = float(gm[f"reach_{int(R*100)}"].mean())
        # post-50% dynamics
        p50 = gm[gm["reach_50"]]
        out["post50_break_rate"] = float(p50["post50_break"].mean()) if len(p50) else np.nan
        out["post50_mfe_ticks"] = float(p50["post50_mfe_ticks"].mean()) if len(p50) else np.nan
        out["post50_mae_ticks"] = float(p50["post50_mae_ticks"].mean()) if len(p50) else np.nan
        out["med_t_from50_to_break"] = float(
            (p50["t_post50_break"]).median()) if len(p50) and p50["post50_break"].any() else np.nan
    return out


def main():
    reg = Registry()
    ext_rows, dev_rows, acc_rows, mono_rows = [], [], [], []
    for inst in ("ES", "NQ"):
        led = pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_extremity_dev.parquet"))
        z = led["zmod1_abs"]
        # ascending extremity bands by within-population quantile
        # (0-50-80-90-100 pct of the top-10% pop = whole-sample top 10/5/2/1%)
        led["zband"] = pd.qcut(z, [0.0, 0.5, 0.8, 0.9, 1.0], labels=False, duplicates="drop")
        band_names = {0: "p90_95", 1: "p95_98", 2: "p98_99", 3: "p99_100"}

        # 1) EXTREMITY response (retracement/continuation vs shock magnitude)
        for b, g in led.groupby("zband"):
            if len(g) < MIN_CELL:
                continue
            r = _retr_summary(g)
            r.update({"instrument": inst, "band": band_names.get(int(b), str(b)),
                      "z_lo": float(g["zmod1_abs"].min()), "z_hi": float(g["zmod1_abs"].max())})
            ext_rows.append(r)
        reg.log("2G", "extremity", {"instrument": inst, "family": "extremity_bands"}, "ok", "")

        # monotonicity of break/failure vs continuous z (Spearman)
        gm = led[led["M_ticks"] >= MIN_M_TICKS]
        for outcome in ("break_extreme", "full_failure"):
            rho = spearman(gm["zmod1_abs"].to_numpy(), gm[outcome].astype(float).to_numpy())
            lo, hi = session_boot_ci(gm.assign(_o=gm[outcome].astype(float)),
                                     lambda d: spearman(d["zmod1_abs"].to_numpy(), d["_o"].to_numpy()),
                                     nboot=200)
            mono_rows.append({"instrument": inst, "axis": "zmod1_abs", "outcome": outcome,
                              "spearman": rho, "ci_lo": lo, "ci_hi": hi, "n": len(gm)})

        # 2) VWAP DISTANCE (both anchors), binned by signed deviation level
        for anchor, col, vcol in (("globex", "dev_g_signed", "vwap_g_valid"),
                                   ("rth", "dev_r_signed", "vwap_r_valid")):
            sub = led[led[vcol] & led[col].notna()]
            for lab, lo, hi in DEV_BINS:
                g = sub[(sub[col] >= lo) & (sub[col] < hi)]
                rec = {"instrument": inst, "anchor": anchor, "dev_bin": lab, "n": len(g),
                       "adequate": len(g) >= MIN_CELL}
                if len(g):
                    rec.update({"break_extreme_rate": float(g["break_extreme"].mean()),
                                "full_failure_rate": float(g[g["M_ticks"] >= MIN_M_TICKS]["full_failure"].mean())
                                if (g["M_ticks"] >= MIN_M_TICKS).any() else np.nan,
                                "post50_break_rate": float(g[g["reach_50"]]["post50_break"].mean())
                                if g["reach_50"].any() else np.nan,
                                "fret_30_ticks": float(g["fret_30_ticks"].mean()),
                                "med_M_ticks": float(g["M_ticks"].median())})
                dev_rows.append(rec)
        reg.log("2G", "vwap_distance", {"instrument": inst, "family": "vwap_dist"}, "ok", "")

        # 3) ACCEPTANCE STRENGTH (post-decision break of impulse extreme)
        base_break = float(led["break_extreme"].mean())
        for rule in ("m2of3", "m3of4", "m4of5"):
            for veto in (1, 0):
                key = f"{rule}_veto{veto}"
                st = led[f"{key}_status"]
                for status in ("ACCEPT", "REJECT"):
                    g = led[st == status]
                    pb = g[f"{key}_postbreak"].dropna()
                    acc_rows.append({"instrument": inst, "rule": rule, "veto": veto,
                                     "status": status, "n": len(g), "n_postbreak": len(pb),
                                     "post_break_rate": float(pb.mean()) if len(pb) else np.nan,
                                     "baseline_break_rate": base_break})
        reg.log("2G", "acceptance_strength", {"instrument": inst, "family": "acc_strength"}, "ok", "")

    pd.DataFrame(ext_rows).to_csv(os.path.join(TAB, "ext_extremity.csv"), index=False)
    pd.DataFrame(mono_rows).to_csv(os.path.join(TAB, "ext_monotonicity.csv"), index=False)
    pd.DataFrame(dev_rows).to_csv(os.path.join(TAB, "ext_vwap_distance.csv"), index=False)
    pd.DataFrame(acc_rows).to_csv(os.path.join(TAB, "ext_acceptance_strength.csv"), index=False)
    print("family-G tables written; registry rows:", reg.n)


if __name__ == "__main__":
    main()
