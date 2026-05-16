"""Tests for WFM chunk scope rewrite helpers (no live LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pivot_wfm.handoff_coverage import ChunkCoverageReport
from pivot_wfm.wfm_chunk_scope_rewrite import (
    merge_pinned_chunk_lines,
    parse_operator_notes_by_local_index,
    parse_rule_numbers_to_local_indices,
    run_wfm_chunk_scope_rewrite,
)


def test_parse_rule_numbers_full_regen_empty() -> None:
    assert parse_rule_numbers_to_local_indices(chunk_start_0=10, chunk_len=3, spec="") is None
    assert parse_rule_numbers_to_local_indices(chunk_start_0=10, chunk_len=3, spec="   ") is None


def test_parse_rule_numbers_single_and_range() -> None:
    # Chunk covers global 0-based 10,11,12 → human numbers 11,12,13
    s = parse_rule_numbers_to_local_indices(chunk_start_0=10, chunk_len=3, spec="12, 13")
    assert s == frozenset({1, 2})
    s2 = parse_rule_numbers_to_local_indices(chunk_start_0=10, chunk_len=3, spec="11-13")
    assert s2 == frozenset({0, 1, 2})


def test_parse_rule_numbers_out_of_chunk() -> None:
    with pytest.raises(ValueError, match="not in this chunk"):
        parse_rule_numbers_to_local_indices(chunk_start_0=10, chunk_len=3, spec="99")


def test_parse_operator_notes() -> None:
    text = "12: fix iff\nother noise\n13: second"
    d = parse_operator_notes_by_local_index(text, chunk_start_0=10, chunk_len=5)
    assert d[1] == "fix iff"
    assert d[2] == "second"


def test_merge_pinned_chunk_lines() -> None:
    model = ["A'", "B'", "C'"]
    base = ["A", "B", "C"]
    out = merge_pinned_chunk_lines(model, baseline=base, revise_local=frozenset({1}))
    assert out == ["A", "B'", "C"]


def test_run_wfm_chunk_scope_rewrite_pins_after_model() -> None:
    def fake_llm(_: str) -> str:
        return '{"rewritten_rules": ["wrong", "B2", "wrong"]}'

    cov = ChunkCoverageReport(
        rule_index_start=0,
        rule_index_end_exclusive=3,
        ok=False,
        forward_count=0,
        missing_indices=(0,),
        duplicate_indices=(),
        extra_indices=(),
        blocking_rows=(),
    )
    source = ["A", "B", "C"]
    baseline = ["A1", "B1", "C1"]
    out = run_wfm_chunk_scope_rewrite(
        source,
        rule_index_start=0,
        rule_index_end_exclusive=3,
        file_label="t.md",
        coverage_report=cov,
        handoff_path=None,
        llm=fake_llm,
        working_baseline=baseline,
        revise_local_indices=frozenset({1}),
    )
    assert out == ["A1", "B2", "C1"]

