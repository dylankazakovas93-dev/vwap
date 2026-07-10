"""Stage 2 preregistered analysis runner. Development partition only.

Usage: python -m src.run_analysis
Writes committed summary tables to reports/tables/ and registers every
analysis configuration in RUN_REGISTRY.csv.
"""
import os

import numpy as np
import pandas as pd

from .analysis import (FEATURES, INCREMENT_MAP, NBOOT, OUT, SEED, TAB, TICK,
                       Registry, acceptance_table, cont_y, decided,
                       increment_stat, match_placebo, monotonicity,
                       response_map, session_boot_ci, spearman)
from .events import build_event_ledger

CONFIGS = [(inst, k, z) for inst in ("ES", "NQ") for k in (1, 3) for z in (3.0, 4.0)]
PRIMARY = {("ES", 1, 3.0), ("NQ", 1, 3.0)}


def load_events(inst, k):
    df = pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_events_k{k}_dev.parquet"))
    df["zabs"] = df[f"z_mod{k}"].abs()
    return df


def main():
    os.makedirs(TAB, exist_ok=True)
    reg = Registry()
    counts, base, rmaps, monos, incs, accs, placebos, segs = ([] for _ in range(8))

    for inst, k, z in CONFIGS:
        ev = load_events(inst, k)
        ev = ev[ev["zabs"] >= z].copy()
        primary = (inst, k, z) in PRIMARY
        cfg = {"instrument": inst, "k": k, "z_thr": z}

        # counts
        c = ev.assign(year=ev["session_date"].dt.year).groupby(
            ["year", "segment", "direction"]).size().rename("n").reset_index()
        c[["instrument", "k", "z_thr"]] = inst, k, z
        counts.append(c)
        reg.log("2", "counts", {**cfg, "family": "counts"}, "ok", len(ev))

        # baseline outcome distribution
        fp = ev["fp_outcome"].value_counts(normalize=True).to_dict()
        d = decided(ev)
        rec = {"instrument": inst, "k": k, "z_thr": z, "n_events": len(ev),
               "n_decided": len(d), "cont_rate": float(cont_y(d).mean()),
               "p_none": fp.get("NONE", 0.0), "p_ambig": fp.get("AMBIG", 0.0)}
        for h in (1, 5, 15, 30, 60):
            rec[f"fret_{h}_ticks"] = float(ev[f"fret_{h}"].mean() / TICK)
        rec["mae_ticks"] = float(ev["mae"].mean() / TICK)
        rec["mfe_ticks"] = float(ev["mfe"].mean() / TICK)
        rec["med_t_mfe"] = float(ev["t_mfe"].median())
        rec["med_t_mae"] = float(ev["t_mae"].median())
        rec["med_fp_bars"] = float(ev["fp_bars"].median())
        if primary:
            lo, hi = session_boot_ci(d.assign(y=cont_y(d)), lambda b: b["y"].mean())
            rec["cont_rate_ci_lo"], rec["cont_rate_ci_hi"] = lo, hi
            lo, hi = session_boot_ci(ev, lambda b: b["fret_30"].mean() / TICK)
            rec["fret_30_ci_lo"], rec["fret_30_ci_hi"] = lo, hi
        base.append(rec)
        reg.log("2", "baseline", {**cfg, "family": "baseline"}, "ok", rec["cont_rate"])

        # per-segment baseline
        for seg, g in decided(ev).groupby("segment"):
            segs.append({"instrument": inst, "k": k, "z_thr": z, "segment": seg,
                         "n": len(g), "cont_rate": float(cont_y(g).mean()),
                         "fret_30_ticks": float(g["fret_30"].mean() / TICK)})

        # response maps + monotonicity
        for f in FEATURES:
            for r in response_map(ev, f, k):
                rmaps.append({"instrument": inst, "k": k, "z_thr": z, **r})
            m = monotonicity(ev, f, with_ci=primary)
            if m:
                monos.append({"instrument": inst, "k": k, "z_thr": z, **m})
        reg.log("2", "response_maps", {**cfg, "family": "response+mono",
                                       "features": FEATURES}, "ok", "")

        # nested increments (displacement-controlled)
        d = decided(ev).assign(y=lambda x: cont_y(x))
        for name, f in INCREMENT_MAP.items():
            stat = increment_stat(d, f)
            rec = {"instrument": inst, "k": k, "z_thr": z, "increment": name,
                   "feature": f, "topbot_diff": stat}
            if primary and np.isfinite(stat):
                lo, hi = session_boot_ci(d, lambda b, f=f: increment_stat(b, f),
                                         nboot=200)
                rec["ci_lo"], rec["ci_hi"] = lo, hi
            incs.append(rec)
        reg.log("2", "increments", {**cfg, "family": "increments"}, "ok", "")

        # acceptance
        accs.extend(acceptance_table(ev, inst, k, z))
        reg.log("2", "acceptance", {**cfg, "family": "acceptance"}, "ok", "")

    # write main tables BEFORE placebo so a late failure cannot discard them
    pd.concat(counts).to_csv(os.path.join(TAB, "event_counts.csv"), index=False)
    pd.DataFrame(base).to_csv(os.path.join(TAB, "baseline_outcomes.csv"), index=False)
    pd.DataFrame(segs).to_csv(os.path.join(TAB, "segment_baseline.csv"), index=False)
    pd.DataFrame(rmaps).to_csv(os.path.join(TAB, "response_maps.csv"), index=False)
    pd.DataFrame(monos).to_csv(os.path.join(TAB, "monotonicity.csv"), index=False)
    pd.DataFrame(incs).to_csv(os.path.join(TAB, "increments.csv"), index=False)
    pd.DataFrame(accs).to_csv(os.path.join(TAB, "acceptance.csv"), index=False)

    # matched placebo, primary configs only
    for inst in ("ES", "NQ"):
        feat = pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_features_dev.parquet"))
        ev = load_events(inst, 1)
        ev = ev[ev["zabs"] >= 3.0]
        rng = np.random.default_rng(SEED)
        pl_bars = match_placebo(feat, ev, rng)
        mask = pd.Series(False, index=feat.index)
        mask.loc[pl_bars.index] = True
        pl = build_event_ledger(feat, k=1, z_thr=0.0, instrument=inst, mask=mask)
        pl.to_parquet(os.path.join(OUT, f"{inst.lower()}_placebo_k1_dev.parquet"), index=False)
        dpl = decided(pl)
        dev_ = decided(ev)
        rec = {"instrument": inst, "n_events": len(dev_), "n_placebo": len(dpl),
               "event_cont_rate": float(cont_y(dev_).mean()),
               "placebo_cont_rate": float(cont_y(dpl).mean()),
               "event_fret_30_ticks": float(ev["fret_30"].mean() / TICK),
               "placebo_fret_30_ticks": float(pl["fret_30"].mean() / TICK)}
        lo, hi = session_boot_ci(dpl.assign(y=cont_y(dpl)), lambda b: b["y"].mean())
        rec["placebo_ci_lo"], rec["placebo_ci_hi"] = lo, hi
        placebos.append(rec)
        reg.log("2", "placebo", {"instrument": inst, "family": "placebo"}, "ok",
                rec["placebo_cont_rate"])

    pd.concat(counts).to_csv(os.path.join(TAB, "event_counts.csv"), index=False)
    pd.DataFrame(base).to_csv(os.path.join(TAB, "baseline_outcomes.csv"), index=False)
    pd.DataFrame(segs).to_csv(os.path.join(TAB, "segment_baseline.csv"), index=False)
    pd.DataFrame(rmaps).to_csv(os.path.join(TAB, "response_maps.csv"), index=False)
    pd.DataFrame(monos).to_csv(os.path.join(TAB, "monotonicity.csv"), index=False)
    pd.DataFrame(incs).to_csv(os.path.join(TAB, "increments.csv"), index=False)
    pd.DataFrame(accs).to_csv(os.path.join(TAB, "acceptance.csv"), index=False)
    pd.DataFrame(placebos).to_csv(os.path.join(TAB, "placebo.csv"), index=False)
    print(f"registry rows appended: {reg.n}")


if __name__ == "__main__":
    main()
