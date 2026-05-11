"""Policy refinement pipeline tests (no live Gemini — injected callables)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smt_pipeline.models import CriticContext

from policy_refinement.config import RefinementConfig
from policy_refinement.run import run_assess_and_refine


def test_assess_and_refine_happy_path_injected(tmp_path: Path) -> None:
    nl = tmp_path / "nl.md"
    nl.write_text("Every widget is blue.\n", encoding="utf-8")
    pol = tmp_path / "policy.smt2"
    pol.write_text(
        "\n".join(
            [
                "(set-logic ALL)",
                "; Rule: r_taut0000000001  |  Line: 0",
                "; NL: \"x\"",
                "(assert (= 0 0))",
                "",
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"

    def assessor_fn(_user: str) -> str:
        return json.dumps(
            {
                "schema_version": "policy_refinement_assessment_v1",
                "run_id": "test",
                "summary": "Trivial test vacuity",
                "no_changes_needed": False,
                "recommendations": [
                    {
                        "rec_id": "REC-001",
                        "severity": "high",
                        "issue_type": "vacuous_axiom",
                        "nl_evidence": {"line_numbers": [1], "quoted_snippet": "Every widget is blue."},
                        "policy_evidence": {"rule_id": "r_taut0000000001"},
                        "description": "Replace with meaningful assert",
                        "suggested_remediation": "Use (assert true) for smoke test",
                    }
                ],
            }
        )

    refined_body = "\n".join(
        [
            "(set-logic ALL)",
            "; Rule: r_taut0000000001  |  Line: 0",
            "; --- REFINE rec_id=REC-001 | test fix ---",
            "(assert true)",
            "",
        ]
    )

    def implementer_fn(_user: str) -> str:
        return json.dumps(
            {
                "schema_version": "policy_refinement_implementation_v1",
                "rec_ids_addressed": ["REC-001"],
                "rec_ids_skipped": [],
                "policy_smt2_full_text": refined_body,
                "edit_notes": [{"rec_id": "REC-001", "policy_line_start": 3, "policy_line_end": 5, "note": "x"}],
            }
        )

    def critic_fn(_ctx: CriticContext) -> dict:
        return {"approved": True, "objections": []}

    res = run_assess_and_refine(
        policy_path=pol,
        nl_path=nl,
        out_dir=out,
        run_id="test_run",
        cfg=RefinementConfig(),
        assessor_fn=assessor_fn,
        implementer_fn=implementer_fn,
        repair_fn=lambda **kw: kw["full_policy"],
        critic_fn=critic_fn,
    )
    assert res.status == "success"
    refined = (out / "policy_refined.smt2").read_text(encoding="utf-8")
    assert "REFINE rec_id=REC-001" in refined
    assert "assert true" in refined.lower()
    final_report = json.loads((out / "final_report.json").read_text(encoding="utf-8"))
    assert final_report["status"] == "success"


def test_validate_assessment_rejects_bad_schema() -> None:
    from policy_refinement.validate import validate_assessment

    errs = validate_assessment({"schema_version": "wrong", "recommendations": []}, max_recommendations=50)
    assert any("schema_version" in e for e in errs)
