"""OOS evaluation, 2019/2021/2023/2025 only, evaluated exactly once.
See SPEC_AUCTION_VALUE.md section 11, DECISIONS.md #9.

This module refuses to execute unless CANDIDATE_MANIFEST.md is present
in the git-committed HEAD tree (not merely present on disk -- a runtime
guard against ever opening OOS before the candidate freeze is pushed),
and refuses to re-run if an OOS output already exists on disk (a second
guard against accidentally evaluating OOS more than once).
"""
import itertools
import json
import os
import subprocess

import numpy as np
import pandas as pd

from . import classification as cls
from . import controls as ctl
from . import data as dat
from . import events as ev
from . import grid
from . import mapping as mp
from . import outcomes as out
from . import pipeline_dev as pdv
from . import profiles as prof

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MANIFEST_REL_PATH = "research/auction_value_rotation/CANDIDATE_MANIFEST.md"
OOS_OUTPUT_REL_PATH = "research/auction_value_rotation/outputs/oos_results.json"

# The exact 6 development-frozen parameter definitions from CANDIDATE_MANIFEST.md.
CANDIDATE_ROWS = [
    {"row": 1, "mapping_id": "M2_LONDON_TO_NY", "side": "short", "A": "A_GE_1_TICK", "B": 5,
     "C": "R1_ONE_CLOSE", "D": 0.20, "E": None, "role": "PRIMARY", "dev_diff_h60": 0.1738},
    {"row": 2, "mapping_id": "M2_LONDON_TO_NY", "side": "short", "A": "A_GE_1_TICK", "B": 5,
     "C": "R1_ONE_CLOSE", "D": 0.20, "E": 4.0, "role": "support", "dev_diff_h60": 0.1871},
    {"row": 3, "mapping_id": "M2_LONDON_TO_NY", "side": "short", "A": "A_GE_1_TICK", "B": 5,
     "C": "R1_ONE_CLOSE", "D": 0.20, "E": 6.0, "role": "support", "dev_diff_h60": 0.1789},
    {"row": 4, "mapping_id": "M2_LONDON_TO_NY", "side": "short", "A": "A_GE_1_TICK", "B": 3,
     "C": "R1_ONE_CLOSE", "D": 0.20, "E": 6.0, "role": "support", "dev_diff_h60": 0.2039},
    {"row": 5, "mapping_id": "M2_LONDON_TO_NY", "side": "short", "A": "A_GE_1_TICK", "B": 3,
     "C": "R1_ONE_CLOSE", "D": 0.20, "E": None, "role": "support", "dev_diff_h60": 0.1854},
    {"row": 6, "mapping_id": "M2_LONDON_TO_NY", "side": "short", "A": "A_GE_5PCT_VA", "B": 5,
     "C": "R1_ONE_CLOSE", "D": 0.10, "E": None, "role": "support", "dev_diff_h60": 0.0820},
]

OOS_MIN_TREAT = cls.CANDIDATE_MIN_TREAT
OOS_MIN_CONTROL = cls.CANDIDATE_MIN_CONTROL
OOS_BH_Q = cls.CANDIDATE_BH_Q
OOS_MAX_YEAR_SHARE = cls.CANDIDATE_MAX_YEAR_SHARE


class ManifestNotCommittedError(RuntimeError):
    pass


class OOSAlreadyEvaluatedError(RuntimeError):
    pass


def assert_manifest_committed():
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{MANIFEST_REL_PATH}"],
        cwd=REPO_ROOT, capture_output=True,
    )
    if result.returncode != 0:
        raise ManifestNotCommittedError(
            f"{MANIFEST_REL_PATH} is not present in the committed HEAD tree. "
            "OOS evaluation is disabled until the candidate manifest is committed and pushed."
        )


def assert_oos_not_already_run():
    path = os.path.join(REPO_ROOT, OOS_OUTPUT_REL_PATH)
    if os.path.exists(path):
        raise OOSAlreadyEvaluatedError(
            f"{OOS_OUTPUT_REL_PATH} already exists. OOS is evaluated exactly once; "
            "delete this guard file manually only if you are certain no prior OOS result exists."
        )


def build_oos_state(root: str, bands: dict) -> dict:
    """Mirrors pipeline_dev.build_dev_state but on data.OOS_YEARS. Reuses
    the frozen dev-only `bands` (never recomputed on OOS data)."""
    df1m = dat.load_1m(root)
    df1m = dat.add_causal_atr(df1m)
    df1m_oos = dat.filter_partition(df1m, dat.OOS_YEARS)
    dat.log_timestamp_boundary(f"{root}_oos_1m_raw", df1m_oos)

    leg_df = dat.add_leg_instances(df1m_oos)
    series = out.GlobalSeries(df1m_oos)

    target_bars_by_leg = {lid: g for lid, g in leg_df.groupby("session_leg_id", sort=False)}
    return {"root": root, "leg_df": leg_df, "series": series, "target_bars_by_leg": target_bars_by_leg, "bands": bands}


def evaluate_row_on_oos(oos_state: dict, row: dict, config: dict = prof.PRIMARY) -> dict:
    leg_df, series = oos_state["leg_df"], oos_state["series"]
    target_bars_by_leg, bands = oos_state["target_bars_by_leg"], oos_state["bands"]
    mapping_id, side = row["mapping_id"], row["side"]

    flat, mic = pdv.build_ledger_for_config(leg_df, target_bars_by_leg, config, mapping_id)
    if flat is None:
        return {"row": row["row"], "n_treat_all": 0, "n_control_all": 0, "pooled_diff_h60": np.nan}

    flat = out.add_primary_outcomes(flat, series)
    mic = out.add_primary_outcomes(mic, series)
    t_rows = cls.add_strata([r for r in flat if r["side"] == side], bands)
    c_rows = cls.add_strata([r for r in mic if r["side"] == side], bands)
    cell_rows = grid.apply_cell(t_rows, row["A"], row["B"], row["C"], row["D"], row["E"])
    result = cls.evaluate_cell(cell_rows, c_rows, dev_years=dat.OOS_YEARS)
    result["row"] = row["row"]
    result["mapping_id"], result["side"] = mapping_id, side
    result["A"], result["B"], result["C"], result["D"], result["E"] = row["A"], row["B"], row["C"], row["D"], row["E"]
    result["dev_diff_h60"] = row["dev_diff_h60"]
    return result


def evaluate_alt_profile_support(oos_state: dict, row: dict) -> bool:
    """OOS criterion 8: directional consistency under >=1 alternate
    profile construction, checked only for rows already passing 1-7."""
    for model in ("TYPICAL_PRICE_ROW", "CLOSE_PRICE_ROW"):
        cfg = {"model": model, "bin_width": 0.25, "va_pct": 0.70}
        r = evaluate_row_on_oos(oos_state, row, config=cfg)
        if r and not np.isnan(r["pooled_diff_h60"]) and r["pooled_diff_h60"] > 0:
            return True
    return False


def oos_pass_criteria(result: dict, opposite_edge_note: str = None) -> dict:
    q = result.get("bh_q")
    c1 = (not np.isnan(result["pooled_diff_h60"])) and result["pooled_diff_h60"] > 0
    c2 = c1 and result["pooled_diff_h60"] >= 0.5 * result["dev_diff_h60"]
    c3 = result["positive_years"] >= 3
    c4 = (q is not None) and (not np.isnan(q)) and q <= OOS_BH_Q
    c5 = result["n_treat_all"] >= OOS_MIN_TREAT and result["n_control_matched"] >= OOS_MIN_CONTROL
    c6 = ((not np.isnan(result["pooled_diff_h30"])) and (not np.isnan(result["pooled_diff_h60"]))
          and np.sign(result["pooled_diff_h30"]) == np.sign(result["pooled_diff_h60"]) and result["pooled_diff_h60"] > 0)
    c7 = (not np.isnan(result["max_year_share"])) and result["max_year_share"] <= OOS_MAX_YEAR_SHARE
    c8 = result.get("alt_profile_support", False)
    c9_reported = True  # informational only, never a pass/fail requirement

    criteria = {
        "oos01_positive_pooled_effect": bool(c1), "oos02_effect_ge_half_dev": bool(c2),
        "oos03_positive_ge3_of_4_years": bool(c3), "oos04_bh_q_le_0_10": bool(c4),
        "oos05_adequate_samples": bool(c5), "oos06_same_sign_30_60": bool(c6),
        "oos07_no_year_over_50pct_effect_mass": bool(c7), "oos08_alt_profile_support": bool(c8),
        "oos09_opposite_edge_reported": c9_reported,
    }
    criteria["PASS"] = all(v for k, v in criteria.items() if k != "oos09_opposite_edge_reported")
    return criteria


def run_oos_evaluation(root: str = "NQ") -> dict:
    assert_manifest_committed()
    assert_oos_not_already_run()

    bands_path = os.path.join(REPO_ROOT, "research", "auction_value_rotation", "outputs", f"{root}_frozen_bands.json")
    with open(bands_path) as fh:
        bands = json.load(fh)

    oos_state = build_oos_state(root, bands)

    results = [evaluate_row_on_oos(oos_state, row) for row in CANDIDATE_ROWS]

    p_values = [r["permutation"]["p_value"] if r.get("permutation") else np.nan for r in results]
    from . import permutation as perm
    q_values = perm.benjamini_hochberg(p_values)
    for r, q in zip(results, q_values):
        r["bh_q"] = q

    verdicts = []
    for r in results:
        base_pass_1_7 = (
            (not np.isnan(r["pooled_diff_h60"]) and r["pooled_diff_h60"] > 0)
            and r["positive_years"] >= 3
            and r["n_treat_all"] >= OOS_MIN_TREAT and r["n_control_matched"] >= OOS_MIN_CONTROL
        )
        if base_pass_1_7:
            row_def = next(x for x in CANDIDATE_ROWS if x["row"] == r["row"])
            r["alt_profile_support"] = evaluate_alt_profile_support(oos_state, row_def)
        else:
            r["alt_profile_support"] = False
        criteria = oos_pass_criteria(r)
        verdicts.append({"row": r["row"], "criteria": criteria, "result": r})

    output = {
        "root": root, "oos_years": list(dat.OOS_YEARS), "evaluated_at": pd.Timestamp.utcnow().isoformat(),
        "verdicts": verdicts,
        "family_pass": any(v["criteria"]["PASS"] for v in verdicts),
        "primary_row_pass": next(v["criteria"]["PASS"] for v in verdicts if v["row"] == 1),
    }

    out_path = os.path.join(REPO_ROOT, OOS_OUTPUT_REL_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items() if k != "permutation" or v is not None}
        if isinstance(o, list):
            return [clean(x) for x in o]
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, float) and np.isnan(o):
            return None
        return o

    with open(out_path, "w") as fh:
        json.dump(clean(output), fh, indent=2, default=str)

    return output
