from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.template_diagnostician_agent import (
    TemplateDiagnosticFinding,
    TemplateDiagnosticReport,
    finding_repair_eligible,
    format_template_diagnostic_terminal,
    template_repair_handoff_dict,
)
from pivot_pipeline.template_failure_bundle import report_needs_diagnostic
from pivot_pipeline.template_interactive_loop import (
    run_finding_triage,
    run_template_interactive_loop,
    template_report_ok,
)


def test_template_repair_handoff_filters_findings(tmp_path: Path) -> None:
    report = TemplateDiagnosticReport(
        verdict="ISSUES",
        findings=[
            TemplateDiagnosticFinding(
                id="TS001",
                severity="critical",
                category="policy_vs_nl",
                blame="policy_ir",
                repair_target="rules",
                explanation="vacuous k-of-n",
            ),
            TemplateDiagnosticFinding(
                id="TS002",
                severity="warn",
                category="template_golden",
                blame="template_golden",
                repair_target="suite",
                explanation="wrong golden",
            ),
        ],
    )
    h = template_repair_handoff_dict(
        report,
        approved_ids=["TS001"],
        ignored_ids=["TS002"],
        processed_nl_path=tmp_path / "rules_source.txt",
        template_run_report_path=tmp_path / "template_run_report.json",
        suite_path=tmp_path / "suite.json",
        failure_bundles=[],
    )
    assert h["approved_finding_ids"] == ["TS001"]
    assert h["ignored_finding_ids"] == ["TS002"]
    assert len(h["findings"]) == 1
    assert h["findings"][0]["id"] == "TS001"


def test_finding_repair_eligible() -> None:
    assert finding_repair_eligible(
        TemplateDiagnosticFinding(id="A", blame="policy_ir", repair_target="rules")
    )
    assert not finding_repair_eligible(
        TemplateDiagnosticFinding(id="B", blame="template_golden", repair_target="suite")
    )


def test_report_needs_diagnostic() -> None:
    assert report_needs_diagnostic({"summary": {"failed": 1, "inconclusive": 0, "passed": 5}})
    assert not report_needs_diagnostic({"summary": {"failed": 0, "inconclusive": 0, "passed": 5}})


def test_format_template_diagnostic_terminal() -> None:
    report = TemplateDiagnosticReport(
        verdict="ISSUES",
        suite_summary={"passed": 3, "failed": 1, "inconclusive": 0},
        findings=[
            TemplateDiagnosticFinding(
                id="TS001",
                instance_ids=["gen_008"],
                rule_ids=["R0002"],
                explanation="languages vacuous",
            )
        ],
    )
    text = format_template_diagnostic_terminal(report)
    assert "gen_008" in text
    assert "R0002" in text


def test_run_template_repairer_mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    from pivot_pipeline.template_repairer_agent import run_template_repairer

    captured: dict = {}

    def fake_complete(*, base_prompt: str, llm=None):
        captured["prompt"] = base_prompt
        out = MagicMock()
        out.rules = [{"rule_id": "R0002"}]
        out.change_summary = [MagicMock(finding_id="TS001", rule_id="R0002", change="fix")]
        out.change_summary[0].model_dump = lambda: {
            "finding_id": "TS001",
            "rule_id": "R0002",
            "change": "fix",
        }
        return out, False

    monkeypatch.setattr(
        "pivot_pipeline.template_repairer_agent.complete_repairer_prompt",
        fake_complete,
    )
    handoff = {
        "findings": [{"id": "TS001", "rule_ids": ["R0002"]}],
        "ignored_finding_ids": ["TS002"],
    }
    out, _ = run_template_repairer(
        policy_id="p",
        rules=[{"rule_id": "R0002"}],
        handoff=handoff,
        processed_nl_excerpt="nl",
        linearized_excerpt="lin",
    )
    assert out.rules == [{"rule_id": "R0002"}]
    assert "template_repairer" in captured["prompt"] or "Template" in captured["prompt"]


def test_template_finding_triage() -> None:
    report = TemplateDiagnosticReport(
        verdict="ISSUES",
        findings=[
            TemplateDiagnosticFinding(id="TS001", explanation="a"),
            TemplateDiagnosticFinding(id="TS002", explanation="b"),
        ],
    )
    inputs = iter(["a", "i"])
    approved, ignored = run_finding_triage(
        report,
        input_fn=lambda _p: next(inputs),
        print_fn=lambda *_a, **_k: None,
    )
    assert approved == {"TS001"}
    assert ignored == {"TS002"}


def test_template_loop_proceed_incomplete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from pivot_pipeline.rules_document import write_rules_document_file
    from pivot_pipeline.template_suite.run import rules_json_sha256

    rules = [{"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL", "variable": "x", "relational_operator": "EQ", "constant_value": 1, "yields": "SATISFIED"}]
    write_rules_document_file(tmp_path / "rules_extracted.json", policy_id="p", rules=rules)
    trep = {
        "policy_binding": {"rules_sha256": rules_json_sha256(rules)},
        "summary": {"passed": 1, "failed": 1, "inconclusive": 0, "errors": 0},
        "results": [
            {
                "instance_id": "toy_scenario_1",
                "verdict": "fail",
                "template_kind": "scenario",
                "actual": {},
                "golden": {},
                "diff": {"detail": "x"},
            }
        ],
    }
    (tmp_path / "template_run_report.json").write_text(json.dumps(trep), encoding="utf-8")
    suite_path = Path(__file__).resolve().parent / "fixtures" / "template_suite_toy_suite.json"
    (tmp_path / "rules_source.txt").write_text("Rule one.\n", encoding="utf-8")
    (tmp_path / "meta_scheme.json").write_text('{"policy_id":"p","rules":[]}', encoding="utf-8")

    diag = TemplateDiagnosticReport(
        verdict="ISSUES",
        findings=[
            TemplateDiagnosticFinding(
                id="TS001",
                blame="policy_ir",
                repair_target="rules",
                rule_ids=["R0001"],
                explanation="fix",
            )
        ],
    )

    monkeypatch.setattr(
        "pivot_pipeline.template_interactive_loop.run_template_diagnostician_with_repairs",
        lambda **_k: ("{}", diag, 0),
    )
    monkeypatch.setattr(
        "pivot_pipeline.template_interactive_loop.build_failure_bundles",
        lambda *_a, **_k: [{"instance_id": "gen_001", "verdict": "fail"}],
    )

    meta = MagicMock()
    summary: dict = {}
    gate_inputs = iter(["a", PROCEED_INCOMPLETE_TOKEN])

    rules, _meta, _s, _z, _ok, _iss, _lin, early = run_template_interactive_loop(
        work_dir=tmp_path,
        nl_text_for_artifacts="Rule one.\n",
        nl_for_precheck=tmp_path / "rules_source.txt",
        nl_lines_reg=["Rule one."],
        policy_id="p",
        rules=rules,
        meta_path=tmp_path / "meta_scheme.json",
        skip_registry=True,
        no_llm=False,
        skip_vnext_lowering=False,
        interactive_any=True,
        with_template_repair=True,
        suite_path=suite_path,
        reverify_tester=False,
        reverify_critic=False,
        reverify_cross=False,
        skip_critic=True,
        with_cross_critic=False,
        print_fn=lambda *_a, **_k: None,
        input_fn=lambda _p: next(gate_inputs),
        summary=summary,
        synth="",
        meta=meta,
        z3_result={},
        ok=True,
        issues=[],
        linearized="lin",
    )
    assert early is None
    assert summary.get("user_consented_template_issues")
    assert (tmp_path / "template_repair_handoff.json").is_file()
    assert rules[0]["rule_id"] == "R0001"


def test_template_report_ok() -> None:
    assert template_report_ok({"summary": {"failed": 0, "inconclusive": 0}})
    assert not template_report_ok({"summary": {"failed": 1, "inconclusive": 0}})


def test_coerce_string_change_summary() -> None:
    from pivot_pipeline.repairer_piv_agent import RepairerPivOutput, _coerce_repairer_payload

    data = {
        "rules": [{"rule_id": "R0001"}],
        "change_summary": ["TS002: fixed R0008 encoding"],
    }
    out = RepairerPivOutput.model_validate(_coerce_repairer_payload(data))
    assert len(out.change_summary) == 1
    assert "R0008" in out.change_summary[0].change
