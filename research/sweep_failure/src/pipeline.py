"""End-to-end pipeline: 1m parquet -> causal levels/ATR -> per-level
arming/interaction/classification -> volume percentile -> ES-NQ
confirmation -> outcomes -> barriers -> summary tables -> primary
matched comparison (permutation test) -> BH -> year stability ->
classification.

Usage: python -m src.pipeline   (run from research/sweep_failure/)
"""
import json
import os

import numpy as np
import pandas as pd

from . import data as dta
from . import levels as lv
from . import volume as vol
from . import events as ev
from . import outcomes as oc
from . import confirmation as cf
from . import summary as sm
from . import classification as cl

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "outputs")
REPORTS = os.path.join(HERE, "..", "reports")
TABLES = os.path.join(REPORTS, "tables")

INSTRUMENTS = ("ES", "NQ")
LEVEL_SIDE = {
    "prev_rth_high": "upper", "prev_rth_low": "lower",
    "overnight_high": "upper", "overnight_low": "lower",
}


def build_instrument(root: str):
    df1m = dta.filter_development(dta.load_1m(root))
    df1m = dta.add_causal_atr(df1m)
    level_records = lv.build_level_ledger(df1m, root)
    volume_pct = vol.build_volume_percentile_table(level_records)

    all_episodes, all_events = [], []
    for rec in level_records:
        if not rec["rth_valid"]:
            continue
        bars = rec["_rth_bars"]
        for level_type, side in LEVEL_SIDE.items():
            if level_type in ("prev_rth_high", "prev_rth_low"):
                if not rec["prev_rth_level_valid"]:
                    continue
                level = rec["prev_rth_high"] if level_type == "prev_rth_high" else rec["prev_rth_low"]
            else:
                if not rec["overnight_valid"]:
                    continue
                level = rec["overnight_high"] if level_type == "overnight_high" else rec["overnight_low"]

            episodes, events = ev.process_level_session(bars, level, side, level_type, root, rec["session_date"])
            all_episodes.extend(episodes)
            for e in events:
                if "breach_idx" in e:
                    et_m = int(bars.iloc[e["breach_idx"]]["et_minute"])
                    pct = volume_pct.get((rec["session_date"], et_m), np.nan)
                    e["volume_percentile"] = pct
                    e["volume_stratum"] = vol.volume_stratum(pct)
                else:
                    e["volume_percentile"] = np.nan
                    e["volume_stratum"] = None
            events = oc.add_outcomes(bars, events)
            events = oc.add_barrier_outcomes(bars, events)
            all_events.extend(events)

    audit = {
        "instrument": root,
        "n_1m_rows_dev": int(len(df1m)),
        "n_sessions_total": len(level_records),
        "n_sessions_rth_valid": int(sum(r["rth_valid"] for r in level_records)),
        "n_sessions_prev_rth_level_valid": int(sum(r.get("prev_rth_level_valid", False) for r in level_records)),
        "n_sessions_overnight_valid": int(sum(r.get("overnight_valid", False) for r in level_records)),
        "n_armed_episodes": len(all_episodes),
        "n_events": len(all_events),
    }
    return all_episodes, all_events, audit


def run_all():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TABLES, exist_ok=True)

    episodes_by_root, events_by_root, audits = {}, {}, []
    for root in INSTRUMENTS:
        episodes, events, audit = build_instrument(root)
        episodes_by_root[root] = episodes
        events_by_root[root] = events
        audits.append(audit)

    # ES-NQ confirmation (secondary diagnostic; symmetric)
    other = {"ES": "NQ", "NQ": "ES"}
    confirmed = {}
    for root in INSTRUMENTS:
        confirmed[root] = cf.add_confirmation(events_by_root[root], events_by_root[other[root]])

    all_events = confirmed["ES"] + confirmed["NQ"]
    events_df = pd.DataFrame(all_events)
    all_episodes = episodes_by_root["ES"] + episodes_by_root["NQ"]
    episodes_df = pd.DataFrame(all_episodes)

    events_df.to_csv(os.path.join(OUT, "all_events.csv"), index=False)
    episodes_df.to_csv(os.path.join(OUT, "all_episodes.csv"), index=False)

    with open(os.path.join(OUT, "bar_audit.json"), "w") as fh:
        json.dump(audits, fh, indent=2, default=str)

    pc = cl.primary_comparison(events_df)
    pc = cl.apply_bh_primary(pc)
    pc.to_csv(os.path.join(TABLES, "primary_matched_comparison.csv"), index=False)

    yr = cl.year_stability(events_df)
    yr.to_csv(os.path.join(TABLES, "year_stability.csv"), index=False)

    classified = cl.classify_primary(pc, yr)
    classified.to_csv(os.path.join(TABLES, "classification_table.csv"), index=False)

    sm.build_touch_control_table(events_df).to_csv(os.path.join(TABLES, "touch_control_table.csv"), index=False)
    sm.build_delayed_failure_table(events_df).to_csv(os.path.join(TABLES, "delayed_failure_table.csv"), index=False)
    sm.build_volume_table(events_df).to_csv(os.path.join(TABLES, "volume_table.csv"), index=False)
    sm.build_previous_test_table(events_df).to_csv(os.path.join(TABLES, "previous_test_table.csv"), index=False)
    sm.build_cross_market_table(events_df).to_csv(os.path.join(TABLES, "cross_market_confirmation_table.csv"), index=False)
    sm.build_failure_delay_table(events_df).to_csv(os.path.join(TABLES, "failure_delay_table.csv"), index=False)
    sm.build_breach_magnitude_table(events_df).to_csv(os.path.join(TABLES, "breach_magnitude_table.csv"), index=False)
    sm.build_same_bar_table(events_df).to_csv(os.path.join(TABLES, "same_bar_table.csv"), index=False)

    null_inv = classified.loc[classified["classification"] == "MIXED_OR_NULL"]
    null_inv.to_csv(os.path.join(TABLES, "null_inventory.csv"), index=False)
    under_inv = classified.loc[classified["classification"] == "UNDERPOWERED"]
    under_inv.to_csv(os.path.join(TABLES, "underpowered_inventory.csv"), index=False)

    return {
        "audits": audits, "events_df": events_df, "episodes_df": episodes_df,
        "primary_comparison": pc, "classified": classified, "year_stability": yr,
    }


if __name__ == "__main__":
    result = run_all()
    print(json.dumps(result["audits"], indent=2, default=str))
    print("events:", len(result["events_df"]), "episodes:", len(result["episodes_df"]))
    print(result["events_df"]["event_class"].value_counts())
    print(result["classified"]["classification"].value_counts())
