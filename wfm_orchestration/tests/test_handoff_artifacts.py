"""Tests for manifest + handoff path helpers."""

from __future__ import annotations

import json
from pathlib import Path

from wfm_orchestration.handoff_artifacts import (
    handoff_write_path,
    list_existing_handoffs_for_batch_example,
    record_handoff_artifact,
)


def test_handoff_write_path_default_dir(tmp_path: Path) -> None:
    p = handoff_write_path(tmp_path, "demo_20260101_120000Z_abcd1234")
    assert p.parent.name == "wfm_artifacts"
    assert p.name.endswith(".json")


def test_list_existing_handoffs_for_batch_example(tmp_path: Path) -> None:
    d = tmp_path / "bundles" / "wfm_artifacts"
    d.mkdir(parents=True)
    (d / "hard_F_8_20260420_154309Z_a3db088d.json").write_text("{}", encoding="utf-8")
    assert len(list_existing_handoffs_for_batch_example(tmp_path, "F-8")) == 1
    assert len(list_existing_handoffs_for_batch_example(tmp_path, "F-9")) == 0


def test_record_handoff_artifact_appends_line(tmp_path: Path) -> None:
    hp = tmp_path / "bundles" / "wfm_artifacts" / "x.json"
    hp.parent.mkdir(parents=True)
    hp.write_text("{}", encoding="utf-8")
    record_handoff_artifact(
        tmp_path,
        bundle_id="b1",
        example_id="F-8",
        handoff_path=hp,
        skip_registry=True,
    )
    mp = tmp_path / "bundles" / "wfm_artifacts" / "manifest.jsonl"
    assert mp.is_file()
    line = mp.read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["bundle_id"] == "b1"
    assert rec["example_id"] == "F-8"
    assert rec["skip_registry"] is True
    assert "smt_pipeline" in rec["smt_pipeline_hint"]
