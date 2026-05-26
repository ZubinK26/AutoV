from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.post_model_workflow import TesterFinding, TesterReport
from pivot_pipeline.tester_interactive_loop import (
    BLOCKED_TEST_REPAIR_COMPILE,
    run_finding_triage,
    run_tester_interactive_loop,
)


def test_tester_repair_handoff_filters_findings(tmp_path: Path) -> None:
    from pivot_pipeline.tester_repairer_agent import tester_repair_handoff_dict

    report = TesterReport(
        verdict="issues",
        findings=[
            TesterFinding(id="T001", severity="warn", category="misalignment", explanation="a"),
            TesterFinding(id="T002", severity="critical", category="omission", explanation="b"),
        ],
    )
    h = tester_repair_handoff_dict(
        report,
        approved_ids=["T001"],
        ignored_ids=["T002"],
        full_report_path=tmp_path / "tester_report.json",
    )
    assert h["approved_finding_ids"] == ["T001"]
    assert h["ignored_finding_ids"] == ["T002"]
    assert len(h["findings"]) == 1
    assert h["findings"][0]["id"] == "T001"


def test_finding_triage_approve_ignore() -> None:
    report = TesterReport(
        verdict="issues",
        findings=[
            TesterFinding(id="T001", severity="warn", category="misalignment", explanation="x"),
            TesterFinding(id="T002", severity="critical", category="omission", explanation="y"),
        ],
    )
    inputs = iter(["a", "i"])
    approved, ignored = run_finding_triage(
        report,
        input_fn=lambda _p: next(inputs),
        print_fn=lambda *_a, **_k: None,
    )
    assert approved == {"T001"}
    assert ignored == {"T002"}


def test_run_test_repairer_mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    from pivot_pipeline.tester_repairer_agent import run_test_repairer

    captured: dict = {}

    def fake_complete(*, base_prompt: str, llm=None):
        captured["prompt"] = base_prompt
        out = MagicMock()
        out.rules = [{"rule_id": "R0001"}]
        out.change_summary = [MagicMock(finding_id="T001", rule_id="R0001", change="fix")]
        out.change_summary[0].model_dump = lambda: {
            "finding_id": "T001",
            "rule_id": "R0001",
            "change": "fix",
        }
        return out, False

    monkeypatch.setattr(
        "pivot_pipeline.tester_repairer_agent.complete_repairer_prompt",
        fake_complete,
    )
    handoff = {
        "findings": [{"id": "T001"}],
        "ignored_finding_ids": ["T002"],
    }
    out, _ = run_test_repairer(
        policy_id="p",
        rules=[{"rule_id": "R0001"}],
        handoff=handoff,
        processed_nl_excerpt="nl",
        linearized_excerpt="lin",
    )
    assert out.rules == [{"rule_id": "R0001"}]
    assert "tester_nl_alignment" in captured["prompt"]
    assert "T002" in captured["prompt"]


def test_tester_loop_rerun_after_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIVOT_TESTER_REPAIR_MAX_ROUNDS", "3")
    monkeypatch.setenv("PIVOT_TESTER_REPAIR_COMPILE_ATTEMPTS", "1")

    calls = {"tester": 0}

    def fake_tester(*_a, **_k):
        calls["tester"] += 1
        if calls["tester"] == 1:
            return "{}", TesterReport(
                verdict="issues",
                findings=[
                    TesterFinding(id="T001", severity="warn", category="threshold", explanation="fix me"),
                ],
            )
        return "{}", TesterReport(verdict="ok", findings=[])

    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.run_pivot_tester",
        fake_tester,
    )

    fake_out = MagicMock()
    fake_out.change_summary = []
    fake_out.rules = [{"rule_id": "R0001"}]

    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.run_test_repairer",
        lambda **_k: (fake_out, False),
    )

    meta = MagicMock()
    meta.model_dump_json = lambda indent=2: "{}"

    monkeypatch.setattr(
        "pivot_pipeline.repair_apply.load_rules_and_compile",
        lambda _p, _r: meta,
    )
    monkeypatch.setattr(
        "pivot_pipeline.repair_apply.run_z3_check",
        lambda _m: {"ok": True},
    )
    monkeypatch.setattr(
        "pivot_pipeline.repair_apply.meta_scheme_to_markdown",
        lambda _m: "synth",
    )
    monkeypatch.setattr(
        "pivot_pipeline.repair_apply.run_precheck",
        lambda **_k: (True, []),
    )
    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.build_and_write_assessment_artifacts",
        lambda **_k: "linearized",
    )

    inputs = iter(["a", REPAIR_CRITIC_DRIFT_TOKEN])

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
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: next(inputs),
        summary={},
        synth="s",
        meta=meta,
        z3_result={},
        ok=True,
        issues=[],
        linearized="lin",
        refresh_varprod_trigger_check=lambda: True,
    )

    assert calls["tester"] == 2
    assert early is None
    assert (tmp_path / "rules_after_test_repair.json").is_file()
    assert (tmp_path / "tester_repair_handoff.json").is_file()


def test_proceed_incomplete_writes_handoff(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.run_pivot_tester",
        lambda **_k: (
            "{}",
            TesterReport(
                verdict="issues",
                findings=[TesterFinding(id="T001", severity="warn", category="other", explanation="x")],
            ),
        ),
    )
    inputs = iter(["i", PROCEED_INCOMPLETE_TOKEN])
    summary: dict = {}
    _, _, _, _, _, _, _, early = run_tester_interactive_loop(
        work_dir=tmp_path,
        nl_text_for_artifacts="nl",
        nl_for_precheck=tmp_path / "n.md",
        nl_lines_reg=[],
        policy_id="p",
        rules=[],
        meta_path=tmp_path / "meta_scheme.json",
        skip_registry=True,
        no_llm=False,
        interactive_any=True,
        with_test_repair=True,
        fail_on_tester_findings=False,
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: next(inputs),
        summary=summary,
        synth="s",
        meta=None,
        z3_result={},
        ok=True,
        issues=[],
        linearized="lin",
        refresh_varprod_trigger_check=lambda: True,
    )
    assert early is None
    assert summary.get("user_consented_tester_issues") is True
    handoff = json.loads((tmp_path / "tester_repair_handoff.json").read_text(encoding="utf-8"))
    assert handoff["ignored_finding_ids"] == ["T001"]
    assert handoff["approved_finding_ids"] == []


def test_with_test_repair_requires_with_tester_cli() -> None:
    from pivot_pipeline.cli import main

    rc = main(["--input", "x.nl", "--work-dir", ".", "--with-test-repair"])
    assert rc == 2


def test_exhaust_test_repair_sessions_returns_blocked(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PIVOT_TESTER_REPAIR_MAX_ROUNDS", "1")
    monkeypatch.setenv("PIVOT_TESTER_REPAIR_COMPILE_ATTEMPTS", "1")

    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.run_pivot_tester",
        lambda **_k: (
            "{}",
            TesterReport(
                verdict="issues",
                findings=[TesterFinding(id="T001", severity="warn", category="other", explanation="x")],
            ),
        ),
    )

    fake_out = MagicMock()
    fake_out.change_summary = []
    fake_out.rules = []

    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.run_test_repairer",
        lambda **_k: (fake_out, False),
    )

    def boom(_p: str, _r: object):
        msg = "did not compile"
        raise ValueError(msg)

    monkeypatch.setattr(
        "pivot_pipeline.repair_apply.load_rules_and_compile",
        boom,
    )

    inputs = iter(["a", REPAIR_CRITIC_DRIFT_TOKEN, ""])

    _, _, _, _, _, _, _, early = run_tester_interactive_loop(
        work_dir=tmp_path,
        nl_text_for_artifacts="nl",
        nl_for_precheck=tmp_path / "n.md",
        nl_lines_reg=[],
        policy_id="p",
        rules=[],
        meta_path=tmp_path / "meta_scheme.json",
        skip_registry=True,
        no_llm=False,
        interactive_any=True,
        with_test_repair=True,
        fail_on_tester_findings=False,
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

    assert early == BLOCKED_TEST_REPAIR_COMPILE
