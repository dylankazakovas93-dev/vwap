"""Build the generation-7 level library. Development partition only.
Level construction + diagnostics ONLY -- no touches/reactions/returns/
taxonomy-conditional outcomes/profitability anywhere in this module.
"""
import importlib.util
import os

import pandas as pd

from . import levels as lv
from . import diagnostics as dg

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "cash_open_levels", "outputs")
TABLES = os.path.join(REPO, "research", "cash_open_levels", "reports", "tables")
TAXONOMY_PATH = os.path.join(REPO, "research", "cash_open_taxonomy", "src", "taxonomy.py")
DEV_END = pd.Timestamp("2022-12-31")


def _load_taxonomy_module():
    spec = importlib.util.spec_from_file_location("gen6_taxonomy_g7", TAXONOMY_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_dev(instrument: str) -> pd.DataFrame:
    df = pd.read_parquet(os.path.join(PROC, f"{instrument.lower()}_front_1m.parquet"))
    df = df[df["session_date"] <= DEV_END].copy()
    assert df["session_date"].max() <= DEV_END, "partition breach"
    return df


def build_instrument(instrument: str, tx):
    df = load_dev(instrument)
    scales = tx.build_scale_tables(df)

    fam1 = lv.build_family1(df, scales)
    fam2 = lv.build_family2(df)
    fam3 = lv.build_family3(df)
    fam4 = lv.build_family4(df, fam2)

    long_df = lv.build_long_levels(instrument, fam1, fam2, fam3, fam4)
    synth = lv.build_synthetic_controls(long_df, fam1)

    return {"fam1": fam1, "fam2": fam2, "fam3": fam3, "fam4": fam4,
           "long": long_df, "synth": synth}


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)
    tx = _load_taxonomy_module()

    all_long = []
    fam1_by_instrument = {}
    for instrument in ("ES", "NQ"):
        built = build_instrument(instrument, tx)
        fam1_by_instrument[instrument] = built["fam1"]
        for name in ("fam1", "fam2", "fam3", "fam4"):
            built[name].reset_index().rename(columns={"index": "session_date"}).to_parquet(
                os.path.join(OUT, f"{instrument.lower()}_{name}.parquet"), index=False)
        built["long"].to_parquet(os.path.join(OUT, f"{instrument.lower()}_levels_long.parquet"), index=False)
        built["synth"].to_parquet(os.path.join(OUT, f"{instrument.lower()}_synthetic_controls.parquet"), index=False)
        all_long.append(built["long"])
        print(f"{instrument}: {built['long']['session_date'].nunique()} sessions, "
             f"{len(built['long'])} level rows, {len(built['synth'])} synthetic controls", flush=True)

    long_all = pd.concat(all_long, ignore_index=True)

    counts = dg.level_counts(long_all)
    missing = dg.missingness_table(long_all)
    counts.to_csv(os.path.join(TABLES, "level_counts.csv"), index=False)
    missing.to_csv(os.path.join(TABLES, "missingness.csv"), index=False)

    dup_frames = []
    cluster_pairs_frames = []
    for instrument in ("ES", "NQ"):
        fam1 = fam1_by_instrument[instrument]
        d = dg.structural_duplicates(fam1)
        d.insert(0, "instrument", instrument)
        dup_frames.append(d)

        long_instr = long_all[long_all["instrument"] == instrument]
        pairs = dg.empirical_clustering_flagged(long_instr, fam1)
        cluster_pairs_frames.append(pairs)

    dup_all = pd.concat(dup_frames, ignore_index=True)
    dup_all.to_csv(os.path.join(TABLES, "structural_duplicates.csv"), index=False)

    pairs_all = pd.concat(cluster_pairs_frames, ignore_index=True) if cluster_pairs_frames else pd.DataFrame()
    cluster_summary = dg.clustering_summary(pairs_all)
    cluster_summary.to_csv(os.path.join(TABLES, "clustering_summary.csv"), index=False)
    overlap = dg.overlap_per_session(pairs_all)
    overlap.to_csv(os.path.join(TABLES, "overlap_per_session.csv"), index=False)

    coverage = dg.coverage_table(long_all)
    coverage.to_csv(os.path.join(TABLES, "coverage.csv"), index=False)

    print("Diagnostics written to reports/tables/.", flush=True)


if __name__ == "__main__":
    main()
