"""Tests for ``prompts_wfm.load_wfm_prompts``."""

from __future__ import annotations

from wfm_orchestration.prompts_wfm import load_wfm_prompts


def test_pivot_profile_appends_chunk_cardinality_to_agent2() -> None:
    _, p2_default, _, _, _ = load_wfm_prompts(wfm_profile=None)
    _, p2_pivot, _, _, _ = load_wfm_prompts(wfm_profile="pivot")
    assert "Agent 2 chunk line budget" in p2_pivot
    assert p2_pivot != p2_default
    assert len(p2_pivot) > len(p2_default)
