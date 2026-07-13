"""Secondary diagnostic tables (attribution, ES/NQ-led, typicality,
directions, sessions, adjacent horizons).
"""
import numpy as np
import pandas as pd


def attribution_table(events_out: pd.DataFrame) -> pd.DataFrame:
    df = events_out.loc[events_out["attribution"].notna()]
    rows = []
    for (leg, leader), g in df.groupby(["leg", "leader"]):
        vc = g["attribution"].value_counts()
        n = len(g)
        row = {"leg": leg, "leader": leader, "n": n}
        for cat in ("LEADER_REVERSAL", "LAGGARD_CATCHUP", "JOINT_CONVERGENCE",
                    "DIVERGENCE_EXPANDS", "DIVERGENCE_PERSISTS", "PARTIAL_OR_MIXED"):
            row[cat] = int(vc.get(cat, 0))
            row[f"{cat}_rate"] = vc.get(cat, 0) / n if n else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def leader_instrument_table(events_out: pd.DataFrame) -> pd.DataFrame:
    df = events_out.loc[events_out["event_class"].isin(("EXTREME_UNSUPPORTED_MOVE", "MODERATE_UNSUPPORTED_MOVE"))]
    rows = []
    for (leader, cls), g in df.groupby(["leader", "event_class"]):
        vc = g["outcome_h15"].value_counts()
        n = len(g)
        rows.append({
            "leader": leader, "event_class": cls, "n": n,
            "closure_rate": vc.get("RESIDUAL_CLOSURE_FIRST", 0) / n if n else np.nan,
            "expansion_rate": vc.get("RESIDUAL_EXPANSION_FIRST", 0) / n if n else np.nan,
        })
    return pd.DataFrame(rows)


def typicality_table(events_out: pd.DataFrame) -> pd.DataFrame:
    df = events_out.loc[events_out["event_class"].isin(("EXTREME_UNSUPPORTED_MOVE", "MODERATE_UNSUPPORTED_MOVE"))]
    rows = []
    for (typ, cls), g in df.groupby(["leader_typicality", "event_class"]):
        vc = g["outcome_h15"].value_counts()
        n = len(g)
        rows.append({
            "leader_typicality": typ, "event_class": cls, "n": n,
            "closure_rate": vc.get("RESIDUAL_CLOSURE_FIRST", 0) / n if n else np.nan,
            "expansion_rate": vc.get("RESIDUAL_EXPANSION_FIRST", 0) / n if n else np.nan,
        })
    return pd.DataFrame(rows)


def adjacent_horizon_table(events_out: pd.DataFrame) -> pd.DataFrame:
    df = events_out.loc[events_out["event_class"].isin(("EXTREME_UNSUPPORTED_MOVE", "MODERATE_UNSUPPORTED_MOVE"))]
    rows = []
    for H in (5, 10, 15, 30):
        col = f"outcome_h{H}"
        if col not in df.columns:
            continue
        for cls, g in df.groupby("event_class"):
            vc = g[col].value_counts()
            n_resolved = int(vc.get("RESIDUAL_CLOSURE_FIRST", 0) + vc.get("RESIDUAL_EXPANSION_FIRST", 0))
            rows.append({
                "horizon_min": H, "event_class": cls, "n_resolved": n_resolved,
                "closure_rate": vc.get("RESIDUAL_CLOSURE_FIRST", 0) / n_resolved if n_resolved else np.nan,
            })
    return pd.DataFrame(rows)


def direction_session_table(events_out: pd.DataFrame) -> pd.DataFrame:
    df = events_out.loc[events_out["event_class"].isin(("EXTREME_UNSUPPORTED_MOVE", "MODERATE_UNSUPPORTED_MOVE"))]
    rows = []
    for (leg, direction, same_dir, cls), g in df.groupby(["leg", "leader_direction", "same_direction", "event_class"]):
        vc = g["outcome_h15"].value_counts()
        n = len(g)
        rows.append({
            "leg": leg, "leader_direction": direction, "same_direction_es_nq": same_dir, "event_class": cls,
            "n": n, "closure_rate": vc.get("RESIDUAL_CLOSURE_FIRST", 0) / n if n else np.nan,
        })
    return pd.DataFrame(rows)
