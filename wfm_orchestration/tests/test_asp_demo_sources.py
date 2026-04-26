"""ASP demo loaders: require ASPBench clone for full index test."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent.parent


def test_symtex_index_if_clone_present() -> None:
    symtex = _REPO / "test_sets" / "datasets" / "aspbench" / "repo" / "datasets" / "SymTex"
    if not symtex.is_dir():
        pytest.skip("ASPBench repo not cloned")
    from wfm_orchestration.asp_demo_sources import load_symtex_paired_index

    idx = load_symtex_paired_index(_REPO)
    assert len(idx) >= 1000
    ex = idx[0]
    assert ex.source_id
    assert ex.nl_document
    assert ex.reference_asp_program
    assert "Facts:" in ex.nl_document


def test_symtex_record_assessment_dict() -> None:
    from wfm_orchestration.asp_demo_sources import SymTexPairedExample, symtex_record_to_assessment_dict

    ex = SymTexPairedExample(
        task="answerset_generation",
        source_id="test_id",
        nl_document="Facts:\na.\n\nRules:\nb.",
        reference_asp_program="a.\nb.",
        textual_jsonl_relpath="t.jsonl",
        symbolic_jsonl_relpath="s.jsonl",
        extra={},
    )
    d = symtex_record_to_assessment_dict(ex)
    assert d["reference_asp_program"] == "a.\nb."
    assert d["source_id"] == "test_id"
    assert d["truth_assessment"]["assessable_against_stored_reference_asp"] is True
