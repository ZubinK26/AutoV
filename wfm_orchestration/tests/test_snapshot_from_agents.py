"""Tests for ``wfm_acceptance_snapshot_from_agent_outputs`` (no Gemini)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from registry_stage.wfm_acceptance_handoff import build_handoff_bundle, validate_handoff_roundtrip
from wfm_orchestration.snapshot_from_agents import wfm_acceptance_snapshot_from_agent_outputs


def test_two_line_pass_and_oos() -> None:
    a2 = """1. "First line statement."
2. "Second line statement."
"""
    a3 = """PASS: 1. "First line statement."
OUT_OF_SCOPE: 2. "Second line statement." | transitive closure is out of scope for the formalizer.
"""
    snap = wfm_acceptance_snapshot_from_agent_outputs(
        bundle_id="t1",
        user_original_input="user raw",
        agent2_output=a2,
        agent3_output=a3,
    )
    assert len(snap.lines) == 2
    assert snap.lines[0].line_index == 0 and snap.lines[0].agent3_verdict == "PASS"
    assert snap.lines[1].line_index == 1 and snap.lines[1].agent3_verdict == "OUT_OF_SCOPE"
    bundle = validate_handoff_roundtrip(build_handoff_bundle(snap))
    assert bundle.bundle_id == "t1"


def test_global_rule_index_start_offsets_line_index() -> None:
    a2 = """1. "First."
2. "Second."
"""
    a3 = """PASS: 1. "First."
PASS: 2. "Second."
"""
    snap = wfm_acceptance_snapshot_from_agent_outputs(
        bundle_id="off",
        user_original_input="u",
        agent2_output=a2,
        agent3_output=a3,
        global_rule_index_start=5,
    )
    assert len(snap.lines) == 2
    assert snap.lines[0].line_index == 5
    assert snap.lines[1].line_index == 6


def test_rewrite_verdict() -> None:
    a2 = """1. "Original."
"""
    a3 = """REWRITE: 1. "Rewritten in scope."
"""
    snap = wfm_acceptance_snapshot_from_agent_outputs(
        bundle_id="t2",
        user_original_input="u",
        agent2_output=a2,
        agent3_output=a3,
    )
    assert snap.lines[0].agent3_verdict == "REWRITE"
    assert "Rewritten" in snap.lines[0].statement_nl


def test_effective_lines_required() -> None:
    with pytest.raises(ValueError, match="no lines"):
        wfm_acceptance_snapshot_from_agent_outputs(
            bundle_id="x",
            user_original_input="u",
            agent2_output="no numbered lines here",
            agent3_output="PASS: 1. \"x\"",
        )
