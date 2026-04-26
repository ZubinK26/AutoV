from __future__ import annotations

from pathlib import Path

from wfm_orchestration.ground_truth_asp import (
    curated_id_has_ground_truth_lp,
    truth_assessment_curated_wfm,
)


def test_empty_manifest_map_has_no_ground_truth(tmp_path: Path) -> None:
    t = truth_assessment_curated_wfm("F-8", repo_root=tmp_path, m={})
    assert t["assessable_against_stored_reference_asp"] is False


def test_manifest_path_resolved_relative_to_repo(tmp_path: Path) -> None:
    (tmp_path / "ref.lp").write_text("a.\n", encoding="utf-8")
    m = {"F-8": "ref.lp"}
    assert curated_id_has_ground_truth_lp(tmp_path, "F-8", m) is True
    t = truth_assessment_curated_wfm("F-8", repo_root=tmp_path, m=m)
    assert t["assessable_against_stored_reference_asp"] is True
