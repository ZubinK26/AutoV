"""reset_domain_bundle: clean Phase 0 + optional out_dir."""

from __future__ import annotations

from pathlib import Path

from cpmpy_wfm_policy.pipeline.reset_domain_bundle import (
    reset_domain_for_rerun,
    reset_phase0_artifacts,
)


def test_reset_phase0_removes_known_files(tmp_path: Path) -> None:
    d = tmp_path / "dom"
    d.mkdir()
    (d / "signature.py").write_text("x", encoding="utf-8")
    (d / "rules.txt").write_text("y", encoding="utf-8")
    (d / "workflow_state.json").write_text("{}", encoding="utf-8")
    removed = reset_phase0_artifacts(d)
    assert (d / "rules.txt").is_file()
    assert not (d / "signature.py").is_file()
    assert not (d / "workflow_state.json").is_file()
    assert any("signature.py" in r for r in removed)


def test_reset_domain_wipes_out_dir(tmp_path: Path) -> None:
    dom = tmp_path / "dom"
    dom.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "policy.py").write_text("# x", encoding="utf-8")
    rep = reset_domain_for_rerun(dom, out_dir=out)
    assert rep["out_dir_reset"] == str(out.resolve())
    assert rep["out_dir_had_content"] is True
    assert out.is_dir()
    assert not (out / "policy.py").exists()
