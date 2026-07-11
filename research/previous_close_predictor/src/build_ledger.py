"""Build the generation-4 session-level ledger: previous-session closing-
window features joined to next-session atlas targets (reused unmodified
from generation 3 via file-path import). Development partition only.
"""
import importlib.util
import os

import numpy as np
import pandas as pd

from .prev_close_features import WINDOWS, build_prev_close_features

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "previous_close_predictor", "outputs")
ATLAS_PATH = os.path.join(REPO, "research", "cash_open_atlas", "src", "atlas.py")
DEV_END = pd.Timestamp("2022-12-31")
TARGET_HORIZONS = (5, 10, 15, 30)


def _load_atlas_module():
    spec = importlib.util.spec_from_file_location("gen3_atlas", ATLAS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_dev(instrument: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    df = df[df["session_date"] <= DEV_END].copy()
    assert df["session_date"].max() <= DEV_END, "partition breach"
    return df


def build_full_ledger(instrument: str):
    df = load_dev(instrument)
    atlas = _load_atlas_module()

    bar_frames = atlas.build_dense_bars(df, tau_max=59)
    target_led, target_missing = atlas.build_session_ledger(bar_frames, instrument)
    target_cols = ["session_date"] + [f"{m}_{h}" for h in TARGET_HORIZONS for m in ("R", "Q")] + \
        [f"closing_direction_{h}" for h in TARGET_HORIZONS] + \
        [f"dominant_side_{h}" for h in TARGET_HORIZONS]
    target_led = target_led[target_cols].copy()
    target_led["year"] = pd.to_datetime(target_led["session_date"]).dt.year

    feat = build_prev_close_features(df, instrument)

    all_sessions = sorted(df["session_date"].unique())
    sess_pos = {sd: i for i, sd in enumerate(all_sessions)}
    prev_of = {}
    for i, sd in enumerate(all_sessions):
        prev_of[sd] = all_sessions[i - 1] if i > 0 else None

    early_map = feat.set_index("session_date")["is_early_close"].to_dict()
    exclusions = []
    rows_link = []
    for sd in target_led["session_date"]:
        p = prev_of.get(sd)
        if p is None:
            exclusions.append({"instrument": instrument, "session_date": sd, "reason": "no_predecessor_session"})
            continue
        if early_map.get(p, True):
            exclusions.append({"instrument": instrument, "session_date": sd, "reason": "predecessor_early_close"})
            continue
        rows_link.append({"session_date": sd, "prev_session_date": p})

    link = pd.DataFrame(rows_link, columns=["session_date", "prev_session_date"])
    led = target_led.merge(link, on="session_date", how="inner")
    feat_cols = [c for c in feat.columns if c != "session_date" and c != "instrument"]
    feat_renamed = feat[["session_date"] + feat_cols].rename(
        columns={c: f"prev_{c}" for c in feat_cols}).rename(columns={"session_date": "prev_session_date"})
    led = led.merge(feat_renamed, on="prev_session_date", how="left")
    led["instrument"] = instrument
    led["data_partition"] = "development"

    return led, pd.DataFrame(exclusions), target_missing


def main(instrument: str):
    os.makedirs(OUT, exist_ok=True)
    led, excl, target_missing = build_full_ledger(instrument)
    led.to_parquet(os.path.join(OUT, f"{instrument.lower()}_predictor_ledger.parquet"), index=False)
    excl.to_csv(os.path.join(OUT, f"{instrument.lower()}_exclusions.csv"), index=False)
    target_missing.to_csv(os.path.join(OUT, f"{instrument.lower()}_target_missing.csv"), index=False)
    n_early_close_predecessors = int((excl["reason"] == "predecessor_early_close").sum()) if len(excl) else 0
    print(f"{instrument}: {len(led)} primary rows; "
          f"{n_early_close_predecessors} excluded (predecessor early close); "
          f"{len(excl) - n_early_close_predecessors} excluded (no predecessor)", flush=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
