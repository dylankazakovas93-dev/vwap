"""Leader/laggard assignment and causal session-leadership diagnostic.
See SPEC_UNSUPPORTED_MOVE.md sections 5, 9.
"""
import numpy as np
import pandas as pd


def add_leader_laggard(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    abs_es = out["es_ret_z"].abs()
    abs_nq = out["nq_ret_z"].abs()
    tie = np.isclose(abs_es, abs_nq, equal_nan=False) & abs_es.notna() & abs_nq.notna()
    out["leader_tie"] = tie
    leader = np.where(abs_es > abs_nq, "ES", np.where(abs_nq > abs_es, "NQ", None))
    out["leader"] = leader
    out.loc[tie, "leader"] = None
    out["laggard"] = np.where(out["leader"] == "ES", "NQ", np.where(out["leader"] == "NQ", "ES", None))
    out["leader_ret_z"] = np.where(out["leader"] == "ES", out["es_ret_z"], out["nq_ret_z"])
    out["laggard_ret_z"] = np.where(out["leader"] == "ES", out["nq_ret_z"], out["es_ret_z"])
    out["leader_direction"] = np.where(
        out["leader"].isna(), None,
        np.where(np.where(out["leader"] == "ES", out["es_ret"], out["nq_ret"]) > 0, "UP", "DOWN"),
    )
    out["same_direction"] = np.sign(out["es_ret"]) == np.sign(out["nq_ret"])
    return out


def add_typical_leader(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    frac = out["historical_es_lead_fraction"]
    typical = np.where(frac.isna(), "NO_STABLE_LEADER",
                        np.where(frac > 0.55, "ES", np.where(frac < 0.45, "NQ", "NO_STABLE_LEADER")))
    out["historically_typical_leader"] = typical
    match = []
    for lead, typ in zip(out["leader"], typical):
        if typ == "NO_STABLE_LEADER" or lead is None:
            match.append("NO_STABLE_HISTORICAL_LEADER")
        elif lead == typ:
            match.append("TYPICAL")
        else:
            match.append("ATYPICAL")
    out["leader_typicality"] = match
    return out
