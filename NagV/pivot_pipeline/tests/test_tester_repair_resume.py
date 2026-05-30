from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.post_model_workflow import TesterFinding, TesterReport
from pivot_pipeline.tester_repair_resume import (
    TesterRepairResumeError,
    load_last_test_repair_compile_error,
    validate_tester_repair_resume,
)


def test_validate_resume_after_proceed_incomplete_message(tmp_path: Path) -> None:
    (tmp_path / "tester_report.json").write_text(
        TesterReport(verdict="issues", findings=[TesterFinding(id="T001")]).model_dump_json(),
        encoding="utf-8",
    )
    (tmp_path / "tester_repair_handoff.json").write_text(
        json.dumps(
            {
                "approved_finding_ids": [],
                "source_note": "user chose PROCEED_INCOMPLETE after tester issues",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(TesterRepairResumeError, match="PROCEED_INCOMPLETE"):
        validate_tester_repair_resume(tmp_path)


def test_validate_resume_requires_approvals(tmp_path: Path) -> None:
    (tmp_path / "tester_report.json").write_text(
        TesterReport(verdict="issues", findings=[TesterFinding(id="T001")]).model_dump_json(),
        encoding="utf-8",
    )
    (tmp_path / "tester_repair_handoff.json").write_text(
        json.dumps({"approved_finding_ids": [], "ignored_finding_ids": []}),
        encoding="utf-8",
    )
    with pytest.raises(TesterRepairResumeError, match="approved_finding_ids"):
        validate_tester_repair_resume(tmp_path)


def test_load_last_compile_error_from_handoff(tmp_path: Path) -> None:
    (tmp_path / "tester_repair_handoff.json").write_text(
        json.dumps({"last_compile_validation_error": "atom.operator IN not allowed"}),
        encoding="utf-8",
    )
    assert load_last_test_repair_compile_error(tmp_path) == "atom.operator IN not allowed"


def test_load_compile_error_skips_registry_stage(tmp_path: Path) -> None:
    (tmp_path / "tester_repair_handoff.json").write_text(
        json.dumps(
            {
                "last_repair_error_stage": "registry_json",
                "last_compile_validation_error": "should not load",
                "last_registry_error": "Unterminated string",
            }
        ),
        encoding="utf-8",
    )
    assert load_last_test_repair_compile_error(tmp_path) is None


def test_load_last_compile_error_from_trace(tmp_path: Path) -> None:
    trace = tmp_path / "test_repairer_trace.jsonl"
    trace.write_text(
        json.dumps({"error": "503 UNAVAILABLE"}) + "\n"
        + json.dumps({"compile_validation_error": "schema fail"}) + "\n",
        encoding="utf-8",
    )
    assert load_last_test_repair_compile_error(tmp_path) == "schema fail"


def test_resume_skips_tester_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from pivot_pipeline.tester_interactive_loop import run_tester_interactive_loop

    report = TesterReport(
        verdict="issues",
        findings=[TesterFinding(id="T001", severity="warn", category="other", explanation="x")],
    )
    (tmp_path / "tester_report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    handoff = {
        "handoff_schema_version": "1.1",
        "approved_finding_ids": ["T001"],
        "ignored_finding_ids": [],
        "findings": [report.findings[0].model_dump(mode="json")],
    }
    (tmp_path / "tester_repair_handoff.json").write_text(
        json.dumps(handoff, indent=2), encoding="utf-8"
    )

    tester_calls = {"n": 0}

    def fake_tester(**_k):
        tester_calls["n"] += 1
        return "{}", TesterReport(verdict="ok", findings=[]), 0

    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.run_pivot_tester_with_repairs",
        fake_tester,
    )

    from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN

    inputs = iter([PROCEED_INCOMPLETE_TOKEN])

    _, _, _, _, _, _, _, early = run_tester_interactive_loop(
        work_dir=tmp_path,
        nl_text_for_artifacts="nl",
        nl_for_precheck=tmp_path / "n.md",
        nl_lines_reg=[],
        policy_id="p",
        rules=[{"rule_id": "R0001"}],
        meta_path=tmp_path / "meta_scheme.json",
        skip_registry=True,
        no_llm=False,
        interactive_any=True,
        with_test_repair=True,
        fail_on_tester_findings=False,
        resume_tester_repair=True,
        retriage_tester=False,
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: next(inputs),
        summary={},
        synth="s",
        meta=None,
        z3_result={},
        ok=True,
        issues=[],
        linearized="lin",
        refresh_varprod_trigger_check=lambda: True,
    )
    assert tester_calls["n"] == 0
    assert early is None
