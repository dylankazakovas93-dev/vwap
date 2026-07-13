"""Resolution attribution (convergent/divergent events, primary horizon).
See SPEC_UNSUPPORTED_MOVE.md section 8.
"""
import numpy as np
import pandas as pd

MATERIALITY_FRACTION = 0.25
PRIMARY_HORIZON = 15


def add_attribution(events_out: pd.DataFrame, leg_bar_index: dict) -> pd.DataFrame:
    rows = []
    for ev in events_out.to_dict("records"):
        row = dict(ev)
        outcome = row.get(f"outcome_h{PRIMARY_HORIZON}")
        row["attribution"] = None
        if outcome not in ("RESIDUAL_CLOSURE_FIRST", "RESIDUAL_EXPANSION_FIRST", "NEITHER_WITHIN_HORIZON"):
            rows.append(row)
            continue
        if outcome == "RESIDUAL_EXPANSION_FIRST":
            row["attribution"] = "DIVERGENCE_EXPANDS"
            rows.append(row)
            continue
        if outcome == "NEITHER_WITHIN_HORIZON":
            row["attribution"] = "DIVERGENCE_PERSISTS"
            rows.append(row)
            continue

        # RESIDUAL_CLOSURE_FIRST: compute leader/laggard post-event contributions
        leg_id = row["session_leg_id"]
        t = int(row["local_rank"])
        h_star = row.get(f"resolution_bar_h{PRIMARY_HORIZON}")
        bars = leg_bar_index.get(leg_id)
        r0 = row.get("r0")
        leader = row.get("leader")
        leader_dir = row.get("leader_direction")
        if bars is None or h_star is None or leader is None or pd.isna(r0) or r0 == 0:
            rows.append(row)
            continue
        idx_t, idx_res = t, t + int(h_star)
        if idx_t not in bars.index or idx_res not in bars.index:
            rows.append(row)
            continue
        es_move = bars.loc[idx_res, "close_es"] / bars.loc[idx_t, "close_es"] - 1
        nq_move = bars.loc[idx_res, "close_nq"] / bars.loc[idx_t, "close_nq"] - 1
        d_l = 1.0 if leader_dir == "UP" else -1.0
        leader_move = es_move if leader == "ES" else nq_move
        laggard_move = nq_move if leader == "ES" else es_move
        leader_reversal_amount = -d_l * leader_move
        laggard_catchup_amount = d_l * laggard_move
        thresh = MATERIALITY_FRACTION * abs(r0)
        rev_material = abs(leader_reversal_amount) >= thresh
        catch_material = abs(laggard_catchup_amount) >= thresh
        row["leader_reversal_amount"] = leader_reversal_amount
        row["laggard_catchup_amount"] = laggard_catchup_amount
        if rev_material and catch_material:
            row["attribution"] = "JOINT_CONVERGENCE"
        elif rev_material:
            row["attribution"] = "LEADER_REVERSAL"
        elif catch_material:
            row["attribution"] = "LAGGARD_CATCHUP"
        else:
            row["attribution"] = "PARTIAL_OR_MIXED"
        rows.append(row)
    return pd.DataFrame(rows)
