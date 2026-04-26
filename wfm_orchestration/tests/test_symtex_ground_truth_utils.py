"""SymTex handoff discovery and pending-formalize logic (no live LLM or solver)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wfm_orchestration.symtex_ground_truth_utils import (
    is_asp_pipeline_committed,
    looks_like_symtex_nl_bench_body,
    pending_formalize_symtex_handoffs,
)


def _minimal_symtex_style_handoff() -> dict:
    return {
        "schema_version": "registry_persistence_v1",
        "bundle_id": "symtex_batch_20260000_testabc",
        "user_original_input": (
            "The following facts and rules are quoted verbatim from the benchmark instance.\n\n"
            "Facts:\nfoo.\n\nRules:\n"
        ),
        "lines": [],
    }


def test_looks_like_symtex_banner() -> None:
    assert looks_like_symtex_nl_bench_body(
        "The following facts and rules are quoted verbatim from the benchmark instance.\n"
    )
    assert not looks_like_symtex_nl_bench_body("F-10 FOLIO stress example.")


def test_pending_baseline_filter_skips_unless_committed_in_baseline(tmp_path: Path) -> None:
    """Re-run set: only handoffs with a prior committed record in the baseline out dir."""
    h = tmp_path / "wfm_artifacts"
    h.mkdir()
    b_new = tmp_path / "asp_new"
    b_new.mkdir()
    baseline = tmp_path / "asp_baseline"
    baseline.mkdir()
    a = "symtex_batch_20260000_hasbaseline"
    b = "symtex_batch_20260000_nobaseline"
    d_a = {**_minimal_symtex_style_handoff(), "bundle_id": a}
    d_b = {**_minimal_symtex_style_handoff(), "bundle_id": b}
    (h / f"{a}.json").write_text(json.dumps(d_a, ensure_ascii=False), encoding="utf-8")
    (h / f"{b}.json").write_text(json.dumps(d_b, ensure_ascii=False), encoding="utf-8")
    (baseline / f"{a}.json").write_text(
        json.dumps({"bundle_id": a, "pipeline_status": "committed", "pipeline_kind": "asp_clincon"}),
        encoding="utf-8",
    )
    # b is not in baseline => excluded when only_if_baseline_committed_in=baseline
    pending = pending_formalize_symtex_handoffs(
        repo_root=tmp_path,
        handoff_dir=h,
        bundle_out_dir=b_new,
        glob="*.json",
        only_if_baseline_committed_in=baseline,
    )
    assert len(pending) == 1
    assert pending[0].name == f"{a}.json"


def test_pending_formalize_one_then_committed(tmp_path: Path) -> None:
    h = tmp_path / "wfm_artifacts"
    h.mkdir()
    bdir = tmp_path / "asp_from_wfm"
    bdir.mkdir()
    f = h / "symtex_batch_20260000_testabc.json"
    f.write_text(json.dumps(_minimal_symtex_style_handoff(), ensure_ascii=False), encoding="utf-8")

    pending = pending_formalize_symtex_handoffs(
        repo_root=tmp_path, handoff_dir=h, bundle_out_dir=bdir, glob="*.json"
    )
    assert len(pending) == 1
    (bdir / "symtex_batch_20260000_testabc.json").write_text(
        json.dumps(
            {"bundle_id": "x", "pipeline_status": "committed", "pipeline_kind": "asp_clincon"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    again = pending_formalize_symtex_handoffs(
        repo_root=tmp_path, handoff_dir=h, bundle_out_dir=bdir, glob="*.json"
    )
    assert not again


def test_is_asp_committed(tmp_path: Path) -> None:
    b = tmp_path / "b.json"
    b.write_text(
        json.dumps({"pipeline_status": "committed", "pipeline_kind": "asp_clincon"}), encoding="utf-8"
    )
    assert is_asp_pipeline_committed(bundle_out_dir=tmp_path, bundle_id="b")
    assert not is_asp_pipeline_committed(bundle_out_dir=tmp_path, bundle_id="missing")


def test_e2e_skip_formalize_when_nothing_pending() -> None:
    """If no SymTex handoff needs formalization, skip the expensive integration (placeholder)."""
    from pathlib import Path

    from wfm_orchestration.symtex_ground_truth_utils import pending_formalize_symtex_handoffs

    _repo = Path(__file__).resolve().parent.parent.parent
    handoff = _repo / "bundles" / "wfm_artifacts"
    bdir = _repo / "bundles" / "asp_from_wfm"
    if not handoff.is_dir():
        pytest.skip("no bundles/wfm_artifacts in workspace")
    pending = pending_formalize_symtex_handoffs(
        repo_root=_repo, handoff_dir=handoff, bundle_out_dir=bdir, glob="*.json"
    )
    if not pending:
        pytest.skip("all SymTex handoffs already have committed formalization, or no symtex_batch_ handoffs match")


def test_e2e_wfm_ground_truth_dry_run() -> None:
    """Optional: verify SymTex index exists (ground-truth pool). Unblocks CI without Gemini."""
    from pathlib import Path

    from wfm_orchestration.asp_demo_sources import load_symtex_paired_index

    _repo = Path(__file__).resolve().parent.parent.parent
    try:
        n = len(load_symtex_paired_index(_repo))
    except (FileNotFoundError, RuntimeError):
        pytest.skip("ASPBench SymTex not cloned")
    assert n > 0
