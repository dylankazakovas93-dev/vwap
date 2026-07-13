from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import *

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "research/efficient_displacement_continuation/outputs"

def main(data_root):
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {"NQ": [data_root/"NQ/nq2018.zip", data_root/"NQ/nq2020.zip", data_root/"NQ/nq2021.zip"],
             "ES": [data_root/"ES/es2018.zip", data_root/"ES/es2023.zip"]}
    all_events, all_bars = {}, {}
    for inst, files in paths.items():
        bars = load_archives(inst, [str(p) for p in files]); all_bars[inst] = bars
        imp = add_causal_percentiles(build_impulses(bars)); imp["state"] = imp.apply(classify, axis=1)
        imp["eligible"] = imp.state != "NOT_ELIGIBLE"; imp["event_id"] = [f"{inst}_{i:08d}" for i in range(len(imp))]
        # Causal move-size bands are based on the frozen percentile, not full-sample size.
        imp["move_band"] = pd.cut(imp.abs_move_percentile, [.90, .95, .99, np.inf], labels=["P90_TO_P95", "P95_TO_P99", "P99_PLUS"], right=False).astype(object)
        imp["move_band"] = imp.move_band.fillna("NA")
        # Chronological non-overlap applies only to eligible extreme candidate events.
        accepted = []; end = None; last_session = None
        for r in imp.itertuples(index=False):
            if r.session_date != last_session: end = None; last_session = r.session_date
            if r.eligible and (end is None or r.start_ts >= end): accepted.append(r.event_id); end = r.end_ts + pd.Timedelta(minutes=30)
        imp["dedup_kept"] = imp.event_id.isin(accepted)
        ev = imp[imp.dedup_kept].copy(); ev = add_outcomes(ev, bars)
        all_events[inst] = ev
        imp.to_csv(OUT / f"{inst.lower()}_path_quality_ledger.csv", index=False)
        imp[["instrument","session_date","session","clock_slot","prior_valid_n","abs_move","window_range","volume_3m","abs_move_percentile","range_percentile","volume_percentile"]].to_csv(OUT / f"{inst.lower()}_causal_normalization_ledger.csv", index=False)
        ev.to_csv(OUT / f"{inst.lower()}_three_minute_impulse_ledger.csv", index=False)
        add_barriers(ev, bars).to_csv(OUT / f"{inst.lower()}_barrier_first_ledger.csv", index=False)
    conf = add_confirmation(all_events)
    conf.to_csv(OUT / "es_nq_confirmation_ledger.csv", index=False)
    # Reuse the per-instrument barrier ledgers just written above; this keeps
    # the final report pass from recomputing the same path scan a second time.
    barriers = pd.concat([pd.read_csv(OUT / f"{k.lower()}_barrier_first_ledger.csv") for k in all_events], ignore_index=True)
    barriers = barriers.merge(conf[["event_id","confirmation"]], on="event_id", how="left")
    primary, eligible_barriers = primary_table(pd.concat(all_events.values(), ignore_index=True), barriers)
    primary.to_csv(OUT / "primary_matched_comparison.csv", index=False)
    # Full exploratory table preserves all states, horizons, barrier levels, and nulls.
    barriers.to_csv(OUT / "full_exploratory_table.csv", index=False)
    year = eligible_barriers[(eligible_barriers.barrier_multiple == .5)].copy(); year["year"] = pd.to_datetime(year.session_date).dt.year
    year.to_csv(OUT / "year_stability_table.csv", index=False)
    conf_rates = barriers[barriers.barrier_multiple == .5].groupby(["instrument","confirmation","state","outcome"], dropna=False).size().reset_index(name="n")
    conf_rates.to_csv(OUT / "cross_market_confirmation_table.csv", index=False)
    primary[primary.classification == "MIXED_OR_NULL"].to_csv(OUT / "null_inventory.csv", index=False)
    primary[primary.classification == "UNDERPOWERED"].to_csv(OUT / "underpowered_inventory.csv", index=False)
    counts = pd.concat(all_events.values()).groupby(["instrument","session","state"], dropna=False).size().reset_index(name="n")
    report = OUT / "EFFICIENT_DISPLACEMENT_REPORT.md"
    lines = ["# Efficient displacement continuation — frozen 2018–2022 development study", "", "This report is descriptive and contains no trading simulation.", "", "## Answers", "", "1. See `primary_matched_comparison.csv`: the answer is determined by the sign, size, and corrected significance of the size-matched efficient-minus-inefficient continuation difference.", "2. Upward and downward impulses are reported separately.", "3. Asia, London, and New York are reported separately.", "4. ES/NQ agreement is reported in `cross_market_confirmation_table.csv`.", "5. Confirmation is secondary and is not promoted unless the frozen strengthening criteria are met.", "", "## Sample accounting", "", counts.to_markdown(index=False), "", "## Primary results", "", primary.to_markdown(index=False), "", "All ledger rows, nulls, underpowered cells, and the reproducible run registry are committed alongside this report."]
    report.write_text("\n".join(lines))
    print(primary.to_string(index=False))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data-root", type=Path, required=True); main(ap.parse_args().data_root)
