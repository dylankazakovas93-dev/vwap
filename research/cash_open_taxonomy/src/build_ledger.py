"""Build the generation-6 taxonomy ledger. Development partition only."""
import importlib.util
import os

import numpy as np
import pandas as pd

from . import taxonomy as tx

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "cash_open_taxonomy", "outputs")
ATLAS_PATH = os.path.join(REPO, "research", "cash_open_atlas", "src", "atlas.py")
DEV_END = pd.Timestamp("2022-12-31")

ALL_HORIZONS = list(tx.HORIZONS_PRIMARY) + [tx.HORIZON_SECONDARY]


def _load_atlas_module():
    spec = importlib.util.spec_from_file_location("gen3_atlas_g6", ATLAS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_dev(instrument: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    df = df[df["session_date"] <= DEV_END].copy()
    assert df["session_date"].max() <= DEV_END, "partition breach"
    return df


def build_taxonomy_ledger(instrument: str) -> pd.DataFrame:
    df = load_dev(instrument)
    atlas = _load_atlas_module()
    bar_frames = atlas.build_dense_bars(df, tau_max=tx.TAU_MAX)
    scales = tx.build_scale_tables(df)

    rows = []
    for sd, arrs in bar_frames.items():
        if sd not in scales.index:
            continue
        sU, sD = scales.loc[sd, "scale_U"], scales.loc[sd, "scale_D"]
        O = arrs["open"][0]
        if not np.isfinite(O) or not (np.isfinite(sU) and np.isfinite(sD)):
            continue
        u, d, Q, close_disp = tx.path_arrays(arrs, O, sU, sD)
        if not (np.isfinite(u[0]) and np.isfinite(d[0])):
            continue

        row = {"instrument": instrument, "session_date": sd, "year": pd.Timestamp(sd).year,
              "scale_U": sU, "scale_D": sD,
              "scale_U_mad": scales.loc[sd, "scale_U_mad"], "scale_D_mad": scales.loc[sd, "scale_D_mad"]}
        row.update(tx.bar0_morphology(arrs, O, sU, sD))
        row["u_0"], row["d_0"] = u[0], d[0]

        samebar_label = tx.classify_samebar_h1(u[0], d[0], row["norm_close_disp_0"])
        row["samebar_h1_label"] = samebar_label if samebar_label else "NOT_DUAL_SIDED"
        row["caveat"] = tx.CAVEAT if samebar_label else ""

        proxy_sign = None
        if samebar_label == "SAME_BAR_BULLISH_REVERSAL_PROXY":
            proxy_sign = 1
        elif samebar_label == "SAME_BAR_BEARISH_REVERSAL_PROXY":
            proxy_sign = -1

        for h in ALL_HORIZONS:
            t_h = h - 1
            if t_h >= len(u) or not np.isfinite(u[t_h]):
                row[f"class_h{h}"] = None
                continue
            if samebar_label in ("SAME_BAR_BULLISH_REVERSAL_PROXY", "SAME_BAR_BEARISH_REVERSAL_PROXY"):
                if h == 1:
                    row[f"class_h{h}"] = samebar_label
                else:
                    lbl, t_take = tx.classify_samebar_subsequent(Q, u, d, proxy_sign, t_h)
                    row[f"class_h{h}"] = lbl
                    if lbl == "LATER_ORDERED_REVERSAL_AFTER_PROXY":
                        row[f"timing_h{h}"] = tx.timing_bin(t_take + 1)
            elif samebar_label == "SAME_BAR_DUAL_SIDED_AMBIGUOUS":
                row[f"class_h{h}"] = samebar_label if h == 1 else "NOT_APPLICABLE_AMBIGUOUS_PROXY"
            else:
                label, extra = tx.classify_ordinary(u, d, Q, close_disp, t_h)
                row[f"class_h{h}"] = label
                if "timing_bin" in extra:
                    row[f"timing_h{h}"] = extra["timing_bin"]
                if extra.get("ambiguous_bars"):
                    row[f"ambig_bars_h{h}"] = extra["ambiguous_bars"]

        ladder = tx.excursion_ladder(u, d)
        for k, v in ladder.items():
            row[k] = v if not isinstance(v, (list, dict)) else str(v)
        row["n_ties"] = len(ladder["same_bar_ties"])

        # sensitivity grid: same-bar family label under each (tau_c, tau_b)
        for tc in tx.TAU_C_GRID:
            for tb in tx.TAU_B_GRID:
                lbl = tx.classify_samebar_h1(u[0], d[0], row["norm_close_disp_0"], tau_c=tc, tau_b=tb)
                row[f"grid_tc{tc}_tb{tb}"] = lbl if lbl else "NOT_DUAL_SIDED"

        rows.append(row)

    return pd.DataFrame(rows)


def main(instrument: str):
    os.makedirs(OUT, exist_ok=True)
    led = build_taxonomy_ledger(instrument)
    led["data_partition"] = "development"
    led.to_parquet(os.path.join(OUT, f"{instrument.lower()}_taxonomy_ledger.parquet"), index=False)
    n_samebar = int(led["samebar_h1_label"].isin(
        ["SAME_BAR_BULLISH_REVERSAL_PROXY", "SAME_BAR_BEARISH_REVERSAL_PROXY",
         "SAME_BAR_DUAL_SIDED_AMBIGUOUS"]).sum())
    print(f"{instrument}: {len(led)} sessions; {n_samebar} same-bar dual-sided at h=1", flush=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
