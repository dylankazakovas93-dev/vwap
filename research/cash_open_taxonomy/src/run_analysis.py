"""Class-frequency, ambiguity, and ladder diagnostics — SPEC_TAXONOMY.md
Sec. 9. Purely descriptive; no level-reaction or profitability content.
"""
import ast
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import taxonomy as tx

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
GEN_DIR = os.path.join(REPO, "research", "cash_open_taxonomy")
TAB = os.path.join(GEN_DIR, "reports", "tables")
OUT = os.path.join(GEN_DIR, "outputs")
MIN_CELL = 20

ALL_HORIZONS = list(tx.HORIZONS_PRIMARY) + [tx.HORIZON_SECONDARY]
SAMEBAR_LABELS = ("SAME_BAR_BULLISH_REVERSAL_PROXY", "SAME_BAR_BEARISH_REVERSAL_PROXY",
                  "SAME_BAR_DUAL_SIDED_AMBIGUOUS")
SUBSEQUENT_LABELS = ("CONTINUATION_EXPANSION_PROXY_DIRECTION", "BALANCE_FAILURE_TO_EXPAND",
                     "LATER_OPPOSITE_SIDE_TAKEOVER", "LATER_ORDERED_REVERSAL_AFTER_PROXY")
ORDINARY_LABELS = ("DIRECT_BULLISH_EXPANSION", "DIRECT_BEARISH_EXPANSION",
                   "INITIAL_DOWNSIDE_BULLISH_REVERSAL", "INITIAL_UPSIDE_BEARISH_REVERSAL",
                   "TWO_SIDED_BALANCED", "DELAYED_EXPANSION_AFTER_INITIAL_BALANCE")


def git_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()


class Registry:
    def __init__(self):
        self.path = os.path.join(GEN_DIR, "RUN_REGISTRY.csv")
        self.sha = git_sha()
        self.n = 0

    def log(self, hyp, config, metric=""):
        self.n += 1
        ch = hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()[:12]
        row = pd.DataFrame([{
            "run_id": f"g6_{self.n:03d}", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": self.sha, "dataset_hash": "see DATA_CONTRACT.md", "stage": "taxonomy_diagnostics",
            "hypothesis_id": hyp, "config_hash": ch, "parent_run_id": "", "change_reason": "",
            "train_period": "2018-2022", "validation_period": "", "test_period": "", "seed": "",
            "command": json.dumps(config, default=str), "status": "ok", "primary_metric": metric,
            "selected": "", "notes": "",
        }])
        row.to_csv(self.path, mode="a", header=False, index=False)


def load(inst):
    return pd.read_parquet(os.path.join(OUT, f"{inst.lower()}_taxonomy_ledger.parquet"))


def main():
    reg = Registry()
    class_freq_rows, samebar_freq_rows, subsequent_freq_rows = [], [], []
    ambig_rows, grid_rows, ladder_rows, tie_rows, morph_rows = [], [], [], [], []

    ledgers = {inst: load(inst) for inst in ("ES", "NQ")}

    for inst, led in ledgers.items():
        # h=1 same-bar family + ordinary(bar-0-only) frequency, per year
        for h in ALL_HORIZONS:
            col = f"class_h{h}"
            if col not in led.columns:
                continue
            sub = led.dropna(subset=[col])
            vc = sub[col].value_counts()
            for label, n in vc.items():
                class_freq_rows.append({"instrument": inst, "horizon": h, "class": label,
                                        "n": int(n), "frac": float(n / len(sub)),
                                        "below_floor": bool(n < MIN_CELL)})
            for yr, g in sub.groupby("year"):
                vcy = g[col].value_counts()
                for label, n in vcy.items():
                    class_freq_rows.append({"instrument": inst, "horizon": h, "year": yr,
                                            "class": label, "n": int(n), "frac": float(n / len(g)),
                                            "below_floor": bool(n < MIN_CELL)})
        reg.log("class_frequency", {"instrument": inst})

        # same-bar h1 frequency (redundant w/ class_h1 but reported explicitly per spec)
        vc1 = led["samebar_h1_label"].value_counts()
        for label, n in vc1.items():
            samebar_freq_rows.append({"instrument": inst, "label": label, "n": int(n),
                                      "frac": float(n / len(led))})
        reg.log("samebar_h1_frequency", {"instrument": inst})

        # subsequent-path frequency for the proxy cohort, per horizon>1, per year
        proxy_mask = led["samebar_h1_label"].isin(
            ["SAME_BAR_BULLISH_REVERSAL_PROXY", "SAME_BAR_BEARISH_REVERSAL_PROXY"])
        for h in ALL_HORIZONS:
            if h == 1:
                continue
            col = f"class_h{h}"
            if col not in led.columns:
                continue
            sub = led[proxy_mask].dropna(subset=[col])
            vc = sub[col].value_counts()
            for label, n in vc.items():
                subsequent_freq_rows.append({"instrument": inst, "horizon": h, "label": label,
                                             "n": int(n), "frac": float(n / len(sub)) if len(sub) else np.nan,
                                             "below_floor": bool(n < MIN_CELL)})
        reg.log("subsequent_path_frequency", {"instrument": inst})

        # ambiguous-direction-at-bar-t (ordinary path) counts
        for h in ALL_HORIZONS:
            col = f"ambig_bars_h{h}"
            if col in led.columns:
                n_sessions_with_ambig = int(led[col].notna().sum())
                ambig_rows.append({"instrument": inst, "horizon": h,
                                   "n_sessions_with_ambiguous_bar": n_sessions_with_ambig})
        # bar-0 dual-sided ambiguous (primary tau_b) count already in samebar_freq_rows

        # 3x3 sensitivity grid: same-bar-family frequency
        for tc in tx.TAU_C_GRID:
            for tb in tx.TAU_B_GRID:
                col = f"grid_tc{tc}_tb{tb}"
                vc = led[col].value_counts()
                for label, n in vc.items():
                    grid_rows.append({"instrument": inst, "tau_c": tc, "tau_b": tb,
                                      "label": label, "n": int(n), "frac": float(n / len(led))})
        reg.log("sensitivity_grid", {"instrument": inst})

        # ladder reach rates + ties
        for side in ("UP", "DOWN"):
            for th in tx.LADDER:
                col = f"reached_{side}_{th}"
                if col in led.columns:
                    rate = float(led[col].mean())
                    ladder_rows.append({"instrument": inst, "side": side, "threshold": th,
                                        "reach_rate": rate, "n": len(led)})
        tie_rate = float((led["n_ties"] > 0).mean())
        tie_rows.append({"instrument": inst, "n_sessions": len(led),
                         "n_sessions_with_tie": int((led["n_ties"] > 0).sum()), "tie_rate": tie_rate})
        reg.log("ladder_diagnostics", {"instrument": inst})

        # morphology descriptive stats per same-bar class
        for label in SAMEBAR_LABELS:
            sub = led[led["samebar_h1_label"] == label]
            if len(sub) == 0:
                continue
            rec = {"instrument": inst, "label": label, "n": len(sub)}
            for f in ("close_location_0", "body_ratio_0", "upper_wick_ratio_0", "lower_wick_ratio_0"):
                rec[f"{f}_mean"] = float(sub[f].mean())
                rec[f"{f}_median"] = float(sub[f].median())
            morph_rows.append(rec)
        reg.log("morphology_stats", {"instrument": inst})

    pd.DataFrame(class_freq_rows).to_csv(os.path.join(TAB, "class_frequency.csv"), index=False)
    pd.DataFrame(samebar_freq_rows).to_csv(os.path.join(TAB, "samebar_h1_frequency.csv"), index=False)
    pd.DataFrame(subsequent_freq_rows).to_csv(os.path.join(TAB, "subsequent_path_frequency.csv"), index=False)
    pd.DataFrame(ambig_rows).to_csv(os.path.join(TAB, "ambiguous_bar_counts.csv"), index=False)
    pd.DataFrame(grid_rows).to_csv(os.path.join(TAB, "sensitivity_grid.csv"), index=False)
    pd.DataFrame(ladder_rows).to_csv(os.path.join(TAB, "ladder_reach_rates.csv"), index=False)
    pd.DataFrame(tie_rows).to_csv(os.path.join(TAB, "ladder_ties.csv"), index=False)
    pd.DataFrame(morph_rows).to_csv(os.path.join(TAB, "samebar_morphology_stats.csv"), index=False)
    print("registry rows:", reg.n)


if __name__ == "__main__":
    main()
