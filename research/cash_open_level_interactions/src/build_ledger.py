"""Build the generation-8 real/synthetic event ledgers. Development
partition only. Reuses generation 7's level-construction engine
unmodified (imported by exact file path) -- no new control-generation
method, no re-derivation of level values or synthetic controls.
"""
import os

import numpy as np
import pandas as pd

from . import interactions as ix

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROC = os.path.join(REPO, "data", "processed")
OUT = os.path.join(REPO, "research", "cash_open_level_interactions", "outputs")


def _load_gen7():
    """Reuses generation 7's level-construction engine unmodified.
    build_levels.py contains an internal `from . import levels`, so it is
    imported as a real package (research.cash_open_levels.src), not via
    importlib file-path loading (which would break that relative import) --
    unlike taxonomy.py/atlas.py in earlier generations, which are
    self-contained and have no internal relative imports."""
    from research.cash_open_levels.src import levels as lv
    from research.cash_open_levels.src import build_levels as bl
    return lv, bl


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def build_instrument_ledger(instrument: str, lv, bl, tx):
    df = bl.load_dev(instrument)
    built = bl.build_instrument(instrument, tx)
    fam1 = built["fam1"]
    long_df = built["long"]
    synth_df = built["synth"]

    real_wide = long_df.pivot(index="session_date", columns="level_id", values="value")
    synth_wide = synth_df.pivot(index="session_date", columns="level_id", values="value_synth")
    dense = ix.build_dense_bars_with_volume(df, ix.TAU_MAX)

    level_ids = sorted(lv.LEVEL_COLUMNS.keys())
    level_family = {k: v[0] for k, v in lv.LEVEL_COLUMNS.items()}
    n_levels = len(level_ids)

    levels_rows = []
    events_rows = []
    outcomes_rows = []
    barriers_rows = []

    sessions = sorted(real_wide.index)
    for s in sessions:
        arrs = dense.get(s)
        touch_window_complete = arrs is not None and ix._window_complete(arrs, 0, 29, ("open", "high", "low", "close", "volume"))
        outcome_window_complete = arrs is not None and ix._window_complete(arrs, 0, 44, ("open", "high", "low", "close"))

        if s in fam1.index:
            O = fam1.loc[s, "open"]
            scale_U = fam1.loc[s, "scale_U"]
            scale_D = fam1.loc[s, "scale_D"]
        else:
            O = arrs["open"][0] if arrs is not None else np.nan
            scale_U = np.nan
            scale_D = np.nan

        V_real_arr = np.array([real_wide.loc[s, lid] if lid in real_wide.columns else np.nan for lid in level_ids])
        V_synth_arr = np.array([synth_wide.loc[s, lid] if lid in synth_wide.columns else np.nan for lid in level_ids])

        real_valid = np.isfinite(V_real_arr)
        synth_valid = np.isfinite(V_synth_arr)

        # ------------------------------------------------ touch search --
        touched = {"REAL": np.zeros(n_levels, dtype=bool), "SYNTHETIC": np.zeros(n_levels, dtype=bool)}
        first_tau = {"REAL": np.full(n_levels, -1, dtype=int), "SYNTHETIC": np.full(n_levels, -1, dtype=int)}
        if touch_window_complete:
            low30 = arrs["low"][0:30]
            high30 = arrs["high"][0:30]
            for arm, V_arr, valid in (("REAL", V_real_arr, real_valid), ("SYNTHETIC", V_synth_arr, synth_valid)):
                Vm = np.where(valid, V_arr, np.nan)
                cond = (low30[:, None] <= Vm[None, :]) & (high30[:, None] >= Vm[None, :])
                any_touch = cond.any(axis=0)
                idx = cond.argmax(axis=0)
                touched[arm] = any_touch
                first_tau[arm] = np.where(any_touch, idx, -1)

        real_touch_eligible = real_valid & touch_window_complete
        synth_touch_eligible = synth_valid & touch_window_complete
        mutually_touch_eligible = real_touch_eligible & synth_touch_eligible

        # per-level per-arm computed fields, needed for isolation pass
        orientation_arr = {"REAL": [None] * n_levels, "SYNTHETIC": [None] * n_levels}
        dir_arr = {"REAL": [None] * n_levels, "SYNTHETIC": [None] * n_levels}
        side_scale_arr = {"REAL": [np.nan] * n_levels, "SYNTHETIC": [np.nan] * n_levels}
        norm_elig_arr = {"REAL": np.zeros(n_levels, dtype=bool), "SYNTHETIC": np.zeros(n_levels, dtype=bool)}

        for arm, V_arr, elig in (("REAL", V_real_arr, real_touch_eligible), ("SYNTHETIC", V_synth_arr, synth_touch_eligible)):
            for i, lid in enumerate(level_ids):
                V = V_arr[i]
                row = {"instrument": instrument, "session_date": s, "level_id": lid,
                      "level_family": level_family[lid], "arm": arm, "V": V,
                      "level_valid": bool(real_valid[i] if arm == "REAL" else synth_valid[i]),
                      "touch_eligible": bool(elig[i])}
                is_touched = bool(elig[i] and touched[arm][i])
                row["touched"] = is_touched
                if is_touched:
                    T = int(first_tau[arm][i])
                    et_minute = ix.TOUCH_START + T
                    row["first_touch_et_minute"] = et_minute
                    row["first_touch_tau"] = T
                    row["touch_bucket"] = ix.bucket_for_et_minute(et_minute)
                    O_t, H_t, L_t, C_t = arrs["open"][T], arrs["high"][T], arrs["low"][T], arrs["close"][T]
                    row["touch_bar_open"], row["touch_bar_high"] = O_t, H_t
                    row["touch_bar_low"], row["touch_bar_close"] = L_t, C_t
                    row["touch_bar_volume"] = arrs["volume"][T]
                    orientation, dir_, side_scale = ix.orientation_for(V, O, scale_U, scale_D)
                    orientation_arr[arm][i] = orientation
                    dir_arr[arm][i] = dir_
                    side_scale_arr[arm][i] = side_scale if side_scale is not None else np.nan
                    row["orientation"] = orientation
                    row["dir"] = dir_
                    row["side_scale"] = side_scale
                    row["distance_from_open_points"] = V - O if np.isfinite(O) else np.nan
                    row["distance_from_open_scale_units"] = ((V - O) / side_scale) if (side_scale and np.isfinite(O)) else np.nan
                    row["touch_bar_dual_sided"] = ix.touch_bar_dual_sided(O_t, H_t, L_t, scale_U, scale_D)
                    row.update(ix.touch_bar_diagnostics(O_t, H_t, L_t, C_t, V))
                    ne = bool(elig[i] and outcome_window_complete and orientation in ("ABOVE_OPEN", "BELOW_OPEN")
                             and np.isfinite(scale_U) and np.isfinite(scale_D) and scale_U > 0 and scale_D > 0)
                    norm_elig_arr[arm][i] = ne
                    row["normalized_outcome_eligible"] = ne

                    if outcome_window_complete:
                        for h in ix.HORIZONS:
                            orow = {"instrument": instrument, "session_date": s, "level_id": lid,
                                   "arm": arm, "horizon": h}
                            orow.update(ix.raw_outcomes(arrs, T, V, h))
                            if ne:
                                orow.update(ix.normalized_outcomes(arrs, T, V, h, dir_, orientation, scale_U, scale_D))
                                orow.update(ix.directional_close_recross(arrs, T, h, orientation, V))
                                labels = ix.continuation_rejection_labels(orow["D_h"])
                                for tau, lab in labels.items():
                                    orow[f"label_tau{tau}"] = lab
                            outcomes_rows.append(orow)

                            if ne:
                                for k in ix.BARRIER_K:
                                    brow = {"instrument": instrument, "session_date": s, "level_id": lid,
                                           "arm": arm, "horizon": h, "k": k}
                                    brow.update(ix.barrier_outcomes(arrs, T, h, k, orientation, V, scale_U, scale_D))
                                    barriers_rows.append(brow)
                else:
                    row["normalized_outcome_eligible"] = False
                events_rows.append(row)

        # ------------------------------------------------ isolation pass --
        cluster_thresh = np.array([0.10 * side_scale_arr["REAL"][i] if np.isfinite(side_scale_arr["REAL"][i]) else np.nan
                                   for i in range(n_levels)])
        uf = UnionFind(n_levels)
        cluster_members = [set() for _ in range(n_levels)]
        for i in range(n_levels):
            if not real_valid[i] or not np.isfinite(cluster_thresh[i]):
                continue
            for j in range(i + 1, n_levels):
                if not real_valid[j] or not np.isfinite(cluster_thresh[j]):
                    continue
                dist = abs(V_real_arr[i] - V_real_arr[j])
                if dist <= cluster_thresh[i] or dist <= cluster_thresh[j]:
                    uf.union(i, j)
                    cluster_members[i].add(j)
                    cluster_members[j].add(i)

        comp_map = {}
        for i in range(n_levels):
            if real_valid[i]:
                comp_map.setdefault(uf.find(i), []).append(i)

        co_touch_real = [set() for _ in range(n_levels)]
        co_touch_synth = [set() for _ in range(n_levels)]
        for i in range(n_levels):
            if touched["REAL"][i] and real_touch_eligible[i]:
                T = int(first_tau["REAL"][i])
                lo_t, hi_t = arrs["low"][T], arrs["high"][T]
                for j in range(n_levels):
                    if j == i or not real_valid[j]:
                        continue
                    if lo_t <= V_real_arr[j] <= hi_t:
                        co_touch_real[i].add(j)
            if touched["SYNTHETIC"][i] and synth_touch_eligible[i]:
                T = int(first_tau["SYNTHETIC"][i])
                lo_t, hi_t = arrs["low"][T], arrs["high"][T]
                for j in range(n_levels):
                    if not real_valid[j]:
                        continue
                    if lo_t <= V_real_arr[j] <= hi_t:
                        co_touch_synth[i].add(j)

        for i, lid in enumerate(level_ids):
            real_isolated = np.nan
            if touched["REAL"][i] and real_touch_eligible[i]:
                comp_size = len(comp_map.get(uf.find(i), [i]))
                real_isolated = int(comp_size == 1 and len(co_touch_real[i]) == 0)

            synthetic_isolated = np.nan
            if touched["SYNTHETIC"][i] and synth_touch_eligible[i] and np.isfinite(side_scale_arr["SYNTHETIC"][i]):
                synth_thresh = 0.10 * side_scale_arr["SYNTHETIC"][i]
                far_from_all = True
                for j in range(n_levels):
                    if not real_valid[j]:
                        continue
                    if abs(V_synth_arr[i] - V_real_arr[j]) <= synth_thresh:
                        far_from_all = False
                        break
                synthetic_isolated = int(far_from_all and len(co_touch_synth[i]) == 0)

            pair_separated = np.nan
            side_scale_real_i = side_scale_arr["REAL"][i]
            if real_valid[i] and synth_valid[i] and np.isfinite(side_scale_real_i):
                pair_separated = int(abs(V_real_arr[i] - V_synth_arr[i]) > 0.10 * side_scale_real_i)

            reason = []
            if not real_valid[i]:
                reason.append("real_level_invalid")
            if not synth_valid[i]:
                reason.append("synthetic_level_invalid")
            if not touch_window_complete:
                reason.append("touch_window_incomplete")
            if not outcome_window_complete:
                reason.append("outcome_window_incomplete")

            levels_rows.append({
                "instrument": instrument, "session_date": s, "level_id": lid,
                "level_family": level_family[lid],
                "V_real": V_real_arr[i], "V_synth": V_synth_arr[i], "O_0930": O,
                "scale_U": scale_U, "scale_D": scale_D,
                "real_level_valid": bool(real_valid[i]), "synthetic_level_valid": bool(synth_valid[i]),
                "touch_window_complete": bool(touch_window_complete),
                "outcome_window_complete": bool(outcome_window_complete),
                "mutually_touch_eligible": bool(mutually_touch_eligible[i]),
                "real_touch_eligible": bool(real_touch_eligible[i]),
                "synthetic_touch_eligible": bool(synth_touch_eligible[i]),
                "real_touched": bool(real_touch_eligible[i] and touched["REAL"][i]),
                "synthetic_touched": bool(synth_touch_eligible[i] and touched["SYNTHETIC"][i]),
                "real_normalized_outcome_eligible": bool(norm_elig_arr["REAL"][i]),
                "synthetic_normalized_outcome_eligible": bool(norm_elig_arr["SYNTHETIC"][i]),
                "reason_code": ";".join(reason) if reason else "",
                "cluster_flag": int(len(comp_map.get(uf.find(i), [i])) > 1) if real_valid[i] else np.nan,
                "cluster_id": int(uf.find(i)) if real_valid[i] else np.nan,
                "cluster_member_level_ids": ",".join(level_ids[j] for j in sorted(cluster_members[i])) if real_valid[i] else "",
                "co_touch_level_ids_real": ",".join(level_ids[j] for j in sorted(co_touch_real[i])),
                "co_touch_level_ids_synthetic": ",".join(level_ids[j] for j in sorted(co_touch_synth[i])),
                "real_isolated": real_isolated,
                "synthetic_isolated": synthetic_isolated,
                "pair_separated": pair_separated,
            })

    levels_tbl = pd.DataFrame(levels_rows)
    events_tbl = pd.DataFrame(events_rows)
    outcomes_tbl = pd.DataFrame(outcomes_rows)
    barriers_tbl = pd.DataFrame(barriers_rows)
    if "arm" in events_tbl.columns:
        is_synth = events_tbl["arm"] == "SYNTHETIC"
        events_tbl.loc[is_synth, "synthetic_seed"] = lv.SYNTHETIC_SEED
        events_tbl.loc[is_synth, "control_provenance"] = "gen7_build_synthetic_controls"
    return levels_tbl, events_tbl, outcomes_tbl, barriers_tbl


def main():
    os.makedirs(OUT, exist_ok=True)
    lv, bl = _load_gen7()
    tx = bl._load_taxonomy_module()
    for instrument in ("ES", "NQ"):
        levels_tbl, events_tbl, outcomes_tbl, barriers_tbl = build_instrument_ledger(instrument, lv, bl, tx)
        levels_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_levels.parquet"), index=False)
        events_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_events.parquet"), index=False)
        outcomes_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_outcomes.parquet"), index=False)
        barriers_tbl.to_parquet(os.path.join(OUT, f"{instrument.lower()}_barriers.parquet"), index=False)
        print(f"{instrument}: {len(levels_tbl)} unit rows, {len(events_tbl)} event rows, "
             f"{len(outcomes_tbl)} outcome rows, {len(barriers_tbl)} barrier rows", flush=True)


if __name__ == "__main__":
    main()
