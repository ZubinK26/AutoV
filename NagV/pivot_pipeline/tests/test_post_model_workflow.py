from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.linearize_rules import build_and_write_linearized, linearized_model_artifact_path

from pivot_pipeline.post_model_workflow import TesterOutputError
from pivot_pipeline.post_model_workflow import TesterReport as PivotTesterReport
from pivot_pipeline.post_model_workflow import run_pivot_tester, run_pivot_tester_with_repairs


def test_tester_report_parses_new_categories() -> None:
    payload = {
        "verdict": "issues",
        "compared_against": "processed_nl_and_linearized_model",
        "findings": [
            {
                "id": "T001",
                "severity": "critical",
                "category": "threshold",
                "nl_pointer": "line 3",
                "formal_pointer": "R0003",
                "explanation": "Limit mismatch",
                "recommendation": "Fix constant in IR",
            }
        ],
        "notes": "",
    }
    report = PivotTesterReport.model_validate(payload)
    assert report.verdict == "issues"
    assert report.findings[0].category == "threshold"


def test_tester_repair_second_llm_fixes_json() -> None:
    calls: list[str] = []
    good = json.dumps(
        {
            "verdict": "ok",
            "compared_against": "processed_nl_and_linearized_model",
            "findings": [],
            "notes": "",
        }
    )

    def fake_llm(prompt: str, **kwargs: object) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return '{"verdict": "ok", "findings": ['
        return good

    raw, report, attempts = run_pivot_tester_with_repairs(
        processed_nl="line one",
        linearized_model="R0001 | CONSTANT_RELATIONAL | x EQ 1",
        llm=fake_llm,
        max_repairs=2,
    )
    assert report.verdict == "ok"
    assert attempts == 1
    assert len(calls) == 2
    assert "JSON parse" in calls[1] or "Pivot Tester — JSON" in calls[1]
    assert raw == good


def test_tester_repair_exhausted_raises() -> None:
    def bad_llm(prompt: str, **kwargs: object) -> str:
        return '{"verdict": "issues", "findings": ['

    with pytest.raises(TesterOutputError, match="invalid tester JSON after 0 repair"):
        run_pivot_tester_with_repairs(
            processed_nl="x",
            linearized_model="R0001 | CONSTANT_RELATIONAL | x EQ 1",
            llm=bad_llm,
            max_repairs=0,
        )


def test_run_pivot_tester_prompt_includes_linearization() -> None:
    captured: list[str] = []

    def fake_llm(prompt: str, **kwargs: object) -> str:
        captured.append(prompt)
        return json.dumps(
            {
                "verdict": "ok",
                "compared_against": "processed_nl_and_linearized_model",
                "findings": [],
                "notes": "",
            }
        )

    raw, report = run_pivot_tester(
        processed_nl="Every score must be at most 10.",
        linearized_model="R0001 | CONSTANT_RELATIONAL | score LTE 10 | yields SATISFIED\n",
        llm=fake_llm,
    )
    assert report.verdict == "ok"
    assert len(captured) == 1
    assert "Every score must be at most 10." in captured[0]
    assert "R0001 | CONSTANT_RELATIONAL" in captured[0]
    assert "<<<PROCESSED_NL>>>" not in captured[0]
    assert "<<<LINEARIZED_MODEL>>>" not in captured[0]
    assert "Linearized model" in captured[0]
    assert raw


def test_build_and_write_linearized_creates_artifact(tmp_path: Path) -> None:
    rules = [
        {
            "rule_id": "R0001",
            "applies_to": "GLOBAL",
            "overrides": None,
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "n",
            "relational_operator": "LTE",
            "constant_value": 3,
            "yields": "SATISFIED",
        }
    ]
    text = build_and_write_linearized(work_dir=tmp_path, rules=rules)
    path = linearized_model_artifact_path(tmp_path)
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == text
    assert "R0001 | CONSTANT_RELATIONAL | n LTE 3 | yields SATISFIED" in text


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[2] / "exports" / "pivot_runs_test_input2" / "rules_extracted.json").is_file(),
    reason="pivot_runs_test_input2 export not in tree",
)
def test_skip_phase0_with_tester_only_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    export = Path(__file__).resolve().parents[2] / "exports" / "pivot_runs_test_input2"
    work = tmp_path / "replay"
    work.mkdir()
    for name in ("rules_extracted.json", "rules_source.txt", "meta_scheme.json"):
        (work / name).write_text((export / name).read_text(encoding="utf-8"), encoding="utf-8")

    def fake_tester(**kwargs: object) -> tuple[str, PivotTesterReport]:
        return (
            json.dumps(
                {
                    "verdict": "ok",
                    "compared_against": "processed_nl_and_linearized_model",
                    "findings": [],
                    "notes": "mock",
                }
            ),
            PivotTesterReport(
                verdict="ok",
                compared_against="processed_nl_and_linearized_model",
                findings=[],
                notes="mock",
            ),
        )

    monkeypatch.setattr(
        "pivot_pipeline.tester_interactive_loop.run_pivot_tester_with_repairs",
        lambda **kwargs: fake_tester(**kwargs) + (0,),
    )

    nl = export.parent.parent / "pivot_pipeline" / "golden_test_run" / "input" / "Test_input2.md"
    if not nl.is_file():
        pytest.skip("Test_input2.md not in tree")

    from pivot_pipeline.run import run_pivot_pipeline

    summary = run_pivot_pipeline(
        repo_root=Path(__file__).resolve().parents[3],
        work_dir=work,
        nl_source=nl,
        rules_json=work / "rules_extracted.json",
        skip_phase0=True,
        reset_progress=False,
        rules_per_chunk=5,
        skip_critic=True,
        with_tester=True,
        fail_on_tester_findings=False,
        repairer_max_rounds=0,
    )
    assert summary.get("tester_verdict") == "ok"
    assert (work / "tester_report.json").is_file()
    assert (work / "linearized_model_for_cross_critic.txt").is_file()
    assert summary.get("critic") == "skipped"
