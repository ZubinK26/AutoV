from __future__ import annotations

from pathlib import Path

from agentsim.runtime.simulation_batch import run_write_tool_matrix
from agentsim.runtime.snapshot import policy_v0_text
from agentsim.runtime.write_registry import WRITE_TOOL_IDS


def test_matrix_always_allow_all_execute() -> None:
    recs = run_write_tool_matrix(use_builtin_z3_policy=False)
    assert len(recs) == len(WRITE_TOOL_IDS)
    assert all(r.verdict == "ALLOW" and r.executed for r in recs)
    assert all(r.error_message is None for r in recs)


def test_matrix_z3_bundle_no_runtime_errors() -> None:
    recs = run_write_tool_matrix(use_builtin_z3_policy=True)
    assert len(recs) == len(WRITE_TOOL_IDS)
    assert all(r.error_message is None for r in recs)
    assert all(r.verdict != "ERROR" for r in recs)


def test_matrix_policy_file_same_verdicts_as_bundled(tmp_path: Path) -> None:
    path = tmp_path / "policy_probe.smt2"
    path.write_text(policy_v0_text(), encoding="utf-8")
    from_file = run_write_tool_matrix(policy_smt2_path=path)
    inline = run_write_tool_matrix(policy_smt2_text=policy_v0_text())
    assert [r.verdict for r in from_file] == [r.verdict for r in inline]
