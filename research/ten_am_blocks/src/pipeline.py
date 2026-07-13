"""End-to-end pipeline: 1m parquet -> session ledger -> Module A / Module B
events -> summary cells -> primary BH -> year stability -> classification.

Usage: python -m src.pipeline   (run from research/ten_am_blocks/)
"""
import json
import os

import pandas as pd

from . import data as dta
from . import session_ledger as sl
from . import module_a as ma
from . import module_b as mb
from . import summary as sm
from . import classification as cl

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "outputs")
REPORTS = os.path.join(HERE, "..", "reports")
TABLES = os.path.join(REPORTS, "tables")

INSTRUMENTS = ("ES", "NQ")


def run_instrument(root: str):
    df1m = dta.filter_development(dta.load_1m(root))
    records = sl.build_ledger(df1m, root)

    a_rows, b_rows = [], []
    for rec in records:
        if not rec["valid"]:
            continue
        a_ev = ma.compute_module_a(rec)
        if a_ev is not None:
            a_rows.append(a_ev)
        for side in ("upper", "lower"):
            b_ev = mb.compute_block_event(rec, side)
            if b_ev is not None:
                b_rows.append(b_ev)

    session_ledger_rows = []
    for rec in records:
        row = {k: v for k, v in rec.items() if k not in ("_rth", "upper", "lower")}
        if rec.get("valid"):
            for side in ("upper", "lower"):
                for k, v in rec[side].items():
                    row[f"{side}_{k}"] = v
        session_ledger_rows.append(row)

    audit = {
        "instrument": root,
        "n_1m_rows_dev": int(len(df1m)),
        "n_sessions_total": len(records),
        "n_sessions_valid": int(sum(r["valid"] for r in records)),
        "n_sessions_upper_block_valid": int(sum(r.get("valid") and r["upper"]["valid"] for r in records)),
        "n_sessions_lower_block_valid": int(sum(r.get("valid") and r["lower"]["valid"] for r in records)),
        "n_module_a_events": len(a_rows),
        "n_module_b_events": len(b_rows),
    }
    return pd.DataFrame(session_ledger_rows), pd.DataFrame(a_rows), pd.DataFrame(b_rows), audit


def run_all():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    audits = []
    all_a, all_b = [], []
    for root in INSTRUMENTS:
        ledger, a_ev, b_ev, audit = run_instrument(root)
        audits.append(audit)
        ledger.to_csv(os.path.join(OUT, f"{root.lower()}_session_ledger.csv"), index=False)
        if not a_ev.empty:
            all_a.append(a_ev)
        if not b_ev.empty:
            all_b.append(b_ev)

    events_a = pd.concat(all_a, ignore_index=True) if all_a else pd.DataFrame()
    events_b = pd.concat(all_b, ignore_index=True) if all_b else pd.DataFrame()
    events_a.to_csv(os.path.join(OUT, "module_a_outcomes.csv"), index=False)
    events_b.to_csv(os.path.join(OUT, "module_b_outcomes.csv"), index=False)

    with open(os.path.join(OUT, "bar_audit.json"), "w") as fh:
        json.dump(audits, fh, indent=2, default=str)

    cells_a = sm.build_module_a_cells(events_a)
    cells_a.to_csv(os.path.join(TABLES, "module_a_result_table.csv"), index=False)
    cells_b = sm.build_module_b_cells(events_b)
    cells_b.to_csv(os.path.join(TABLES, "module_b_result_table.csv"), index=False)

    pc_a = cl.apply_bh_module_a(cl.module_a_all_horizon_cells(events_a))
    yr_a = cl.module_a_year_stability(events_a)
    yr_a.to_csv(os.path.join(TABLES, "module_a_year_stability.csv"), index=False)
    classified_a = cl.classify_module_a(pc_a, yr_a)
    classified_a.to_csv(os.path.join(TABLES, "module_a_classification.csv"), index=False)
    mech_a = cl.coherent_mechanism_a(classified_a)
    mech_a.to_csv(os.path.join(TABLES, "module_a_mechanism.csv"), index=False)

    pc_b = cl.apply_bh_module_b(cl.module_b_primary_style_cells(events_b))
    yr_b = cl.module_b_year_stability(events_b)
    yr_b.to_csv(os.path.join(TABLES, "module_b_year_stability.csv"), index=False)
    classified_b = cl.classify_module_b(pc_b, yr_b)
    classified_b.to_csv(os.path.join(TABLES, "module_b_classification.csv"), index=False)
    mech_b = cl.coherent_mechanism_b(classified_b)
    mech_b.to_csv(os.path.join(TABLES, "module_b_mechanism.csv"), index=False)

    same_bar_b = cells_b.loc[
        (cells_b["horizon_min"] == cl.PRIMARY_HORIZON) & (cells_b["barrier"] == cl.PRIMARY_BARRIER)
    ]
    same_bar_b.to_csv(os.path.join(TABLES, "same_bar_morphology_table.csv"), index=False)

    context_a = cells_a.loc[cells_a["context_dim"] != "ALL"]
    context_a.to_csv(os.path.join(TABLES, "module_a_context_strata_table.csv"), index=False)
    context_b = cells_b.loc[cells_b["context_dim"] != "ALL"]
    context_b.to_csv(os.path.join(TABLES, "module_b_context_strata_table.csv"), index=False)

    null_a = classified_a.loc[classified_a["classification"] == "TEN_AM_MIXED_OR_NULL"]
    null_a.to_csv(os.path.join(TABLES, "null_inventory_module_a.csv"), index=False)
    under_a = classified_a.loc[classified_a["classification"] == "UNDERPOWERED"]
    under_a.to_csv(os.path.join(TABLES, "underpowered_inventory_module_a.csv"), index=False)
    null_b = classified_b.loc[classified_b["classification"] == "MIXED_OR_NULL"]
    null_b.to_csv(os.path.join(TABLES, "null_inventory_module_b.csv"), index=False)
    under_b = classified_b.loc[classified_b["classification"] == "UNDERPOWERED"]
    under_b.to_csv(os.path.join(TABLES, "underpowered_inventory_module_b.csv"), index=False)

    return {
        "audits": audits, "events_a": events_a, "events_b": events_b,
        "classified_a": classified_a, "classified_b": classified_b,
        "mech_a": mech_a, "mech_b": mech_b,
    }


if __name__ == "__main__":
    result = run_all()
    print(json.dumps(result["audits"], indent=2, default=str))
    print("module A events:", len(result["events_a"]), "module B events:", len(result["events_b"]))
    print(result["classified_a"]["classification"].value_counts())
    print(result["classified_b"]["classification"].value_counts())
    print(result["mech_a"]["mechanism"].value_counts())
    print(result["mech_b"]["mechanism"].value_counts())
