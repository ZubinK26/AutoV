"""Tests for ``run_wfm_handoff_batch`` helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smt_pipeline.run_wfm_handoff_batch import (
    _find_handoff_for_example,
    _is_pipeline_committed,
)


def test_is_pipeline_committed(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "bundle_a.json").write_text(
        json.dumps({"pipeline_status": "committed"}),
        encoding="utf-8",
    )
    (out / "bundle_b.json").write_text(
        json.dumps({"pipeline_status": "failed"}),
        encoding="utf-8",
    )
    assert _is_pipeline_committed(out, "bundle_a")
    assert not _is_pipeline_committed(out, "bundle_b")
    assert not _is_pipeline_committed(out, "missing")


def test_find_handoff_for_example(tmp_path: Path) -> None:
    d = tmp_path / "wfm_artifacts"
    d.mkdir()
    (d / "hard_F_8_20260101Z_a.json").write_text("{}", encoding="utf-8")
    (d / "hard_F_8_20260202Z_b.json").write_text("{}", encoding="utf-8")
    got = _find_handoff_for_example(d, "F-8")
    assert got is not None
    assert got.name == "hard_F_8_20260202Z_b.json"
