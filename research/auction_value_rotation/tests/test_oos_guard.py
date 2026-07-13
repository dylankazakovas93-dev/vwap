import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from research.auction_value_rotation.src import oos_pipeline as oosp


def test_manifest_is_committed_in_head():
    """The manifest this file's guard checks for must actually be present
    in the committed HEAD tree at test time (it is committed before the
    OOS pipeline is ever written/run, per the pre-OOS freeze procedure)."""
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{oosp.MANIFEST_REL_PATH}"],
        cwd=oosp.REPO_ROOT, capture_output=True,
    )
    assert result.returncode == 0


def test_assert_manifest_committed_raises_for_missing_path(monkeypatch):
    monkeypatch.setattr(oosp, "MANIFEST_REL_PATH", "this/path/does/not/exist/CANDIDATE_MANIFEST.md")
    with pytest.raises(oosp.ManifestNotCommittedError):
        oosp.assert_manifest_committed()


def test_assert_manifest_committed_passes_for_real_manifest():
    oosp.assert_manifest_committed()  # must not raise


def test_assert_oos_not_already_run_raises_if_output_exists(tmp_path, monkeypatch):
    fake_output = tmp_path / "fake_oos_results.json"
    fake_output.write_text("{}")
    monkeypatch.setattr(oosp, "OOS_OUTPUT_REL_PATH", os.path.relpath(str(fake_output), oosp.REPO_ROOT))
    with pytest.raises(oosp.OOSAlreadyEvaluatedError):
        oosp.assert_oos_not_already_run()


def test_oos_pass_criteria_all_pass():
    result = {
        "pooled_diff_h60": 0.15, "dev_diff_h60": 0.20, "positive_years": 3, "bh_q": 0.05,
        "n_treat_all": 350, "n_control_matched": 200, "pooled_diff_h30": 0.14,
        "max_year_share": 0.4, "alt_profile_support": True,
    }
    criteria = oosp.oos_pass_criteria(result)
    assert criteria["PASS"] is True


def test_oos_pass_criteria_fails_when_effect_shrinks_too_much():
    result = {
        "pooled_diff_h60": 0.05, "dev_diff_h60": 0.20, "positive_years": 3, "bh_q": 0.05,
        "n_treat_all": 350, "n_control_matched": 200, "pooled_diff_h30": 0.05,
        "max_year_share": 0.4, "alt_profile_support": True,
    }
    criteria = oosp.oos_pass_criteria(result)
    assert criteria["oos02_effect_ge_half_dev"] is False
    assert criteria["PASS"] is False


def test_oos_pass_criteria_criterion_9_never_blocks_pass():
    result = {
        "pooled_diff_h60": 0.15, "dev_diff_h60": 0.20, "positive_years": 4, "bh_q": 0.01,
        "n_treat_all": 400, "n_control_matched": 300, "pooled_diff_h30": 0.14,
        "max_year_share": 0.3, "alt_profile_support": True,
    }
    criteria = oosp.oos_pass_criteria(result)
    assert criteria["oos09_opposite_edge_reported"] is True
    assert criteria["PASS"] is True  # criterion 9 is informational, never required


def test_candidate_rows_match_manifest_count():
    assert len(oosp.CANDIDATE_ROWS) == 6
    assert sum(1 for r in oosp.CANDIDATE_ROWS if r["role"] == "PRIMARY") == 1
