"""End-to-end pipeline: 1m parquet -> sync -> leg instances -> 5-min
returns -> causal normalization/regression -> leader/laggard ->
event scan -> outcomes -> attribution -> primary comparison -> BH ->
year stability -> classification.

Usage: python -m src.pipeline   (run from research/es_nq_unsupported_move/)
"""
import json
import os

import numpy as np
import pandas as pd

from . import data as dta
from . import returns as ret
from . import regression as reg
from . import leadership as lead
from . import events as ev
from . import outcomes as oc
from . import attribution as attr
from . import classification as cl
from . import summary as sm

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "outputs")
REPORTS = os.path.join(HERE, "..", "reports")
TABLES = os.path.join(REPORTS, "tables")


def run_all():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    es1m = dta.filter_development(dta.load_1m("ES"))
    nq1m = dta.filter_development(dta.load_1m("NQ"))
    sync_df, coverage = dta.synchronize(es1m, nq1m)
    with open(os.path.join(OUT, "sync_coverage.json"), "w") as fh:
        json.dump(coverage, fh, indent=2)

    leg_bars_full = dta.add_leg_instances(sync_df)
    leg_bars_full = ret.add_five_min_returns(leg_bars_full)

    endpoints = ret.window_endpoints(leg_bars_full)
    reg_df = reg.add_causal_normalization_and_regression(endpoints)
    reg_df = lead.add_leader_laggard(reg_df)
    reg_df = lead.add_typical_leader(reg_df)

    leg_lengths = leg_bars_full.groupby("session_leg_id")["local_rank"].max().to_dict()
    events_df = ev.scan_events(reg_df, leg_lengths)
    n_leader_ties = ev.count_leader_ties(reg_df)

    leg_bar_index = oc.build_leg_bar_index(leg_bars_full)
    events_out = oc.classify_outcome(events_df, leg_bar_index)
    events_out = attr.add_attribution(events_out, leg_bar_index)

    keep_cols = [c for c in events_out.columns if c != "residual_path"]
    events_out[keep_cols].to_csv(os.path.join(OUT, "events_outcomes_attribution.csv"), index=False)

    pc = cl.primary_comparison(events_out)
    pc = cl.apply_bh_primary(pc)
    pc.to_csv(os.path.join(TABLES, "primary_matched_comparison.csv"), index=False)

    yr = cl.year_stability(events_out)
    yr.to_csv(os.path.join(TABLES, "year_stability.csv"), index=False)

    classified = cl.classify_primary(pc, yr)
    classified.to_csv(os.path.join(TABLES, "classification_table.csv"), index=False)

    sm.attribution_table(events_out).to_csv(os.path.join(TABLES, "attribution_table.csv"), index=False)
    sm.leader_instrument_table(events_out).to_csv(os.path.join(TABLES, "leader_instrument_table.csv"), index=False)
    sm.typicality_table(events_out).to_csv(os.path.join(TABLES, "typicality_table.csv"), index=False)
    sm.adjacent_horizon_table(events_out).to_csv(os.path.join(TABLES, "adjacent_horizon_table.csv"), index=False)
    sm.direction_session_table(events_out).to_csv(os.path.join(TABLES, "direction_session_table.csv"), index=False)

    null_inv = classified.loc[classified["classification"] == "MIXED_OR_NULL"]
    null_inv.to_csv(os.path.join(TABLES, "null_inventory.csv"), index=False)
    under_inv = classified.loc[classified["classification"] == "UNDERPOWERED"]
    under_inv.to_csv(os.path.join(TABLES, "underpowered_inventory.csv"), index=False)

    audit = {
        "sync_coverage": coverage,
        "n_leg_instances": int(leg_bars_full["session_leg_id"].nunique()),
        "n_window_endpoints": int(len(endpoints)),
        "n_leader_ties": n_leader_ties,
        "n_events_total": int(len(events_df)),
        "n_extreme": int((events_df["event_class"] == "EXTREME_UNSUPPORTED_MOVE").sum()) if len(events_df) else 0,
        "n_moderate": int((events_df["event_class"] == "MODERATE_UNSUPPORTED_MOVE").sum()) if len(events_df) else 0,
    }
    with open(os.path.join(OUT, "run_audit.json"), "w") as fh:
        json.dump(audit, fh, indent=2, default=str)

    return {
        "audit": audit, "events_out": events_out, "primary_comparison": pc,
        "classified": classified, "year_stability": yr,
    }


if __name__ == "__main__":
    result = run_all()
    print(json.dumps(result["audit"], indent=2, default=str))
    print(result["events_out"]["event_class"].value_counts())
    print(result["classified"]["classification"].value_counts())
