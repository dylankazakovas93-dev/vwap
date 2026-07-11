"""Placebo comparison: identical state machine re-based at 13:00 ET."""
import os

import numpy as np
import pandas as pd

from .analysis_utils import OUT, TAB, Registry
from .run_analysis import directional

TICK = 0.25


def main():
    reg = Registry()
    rows = []
    for inst in ("ES", "NQ"):
        for label in ("primary", "placebo"):
            led = pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_{label}_ledger.parquet"))
            d = directional(led)
            for A, g in d.groupby("A"):
                reclaimed = g[g["reclaim_50_tau"].notna()].dropna(subset=["reclaim_50_fret_30"])
                if len(reclaimed) < 50:
                    continue
                rows.append({"instrument": inst, "anchor": label, "A": A,
                            "n_episodes": len(g), "n_reclaimed": len(reclaimed),
                            "reclaim_rate": float(g["reclaim_type"].isin(["HALF", "FULL"]).mean()),
                            "mean_fret_30_ticks": float(reclaimed["reclaim_50_fret_30"].mean() / TICK)})
            reg.log("placebo", {"instrument": inst, "anchor": label})
    pd.DataFrame(rows).to_csv(os.path.join(TAB, "placebo_comparison.csv"), index=False)
    print("done")


if __name__ == "__main__":
    main()
