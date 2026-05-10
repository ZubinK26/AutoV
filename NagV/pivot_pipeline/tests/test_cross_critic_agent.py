from __future__ import annotations

import json
from pathlib import Path

from pivot_pipeline.cross_critic_agent import (
    format_cross_critic_report_terminal,
    parse_cross_critic_response,
)
from pivot_pipeline.cross_repairer_agent import run_cross_repairer

_FIXTURE_RULES = (
    Path(__file__).resolve().parents[2] / "exports" / "pivot_runs_test_input2" / "rules_extracted.json"
)


def test_parse_cross_critic_json() -> None:
    payload = {
        "verdict": "ISSUES",
        "compared_against": "processed_nl_and_linearized_model",
        "findings": [
            {
                "id": "X001",
                "severity": "warn",
                "category": "outcome_split",
                "rule_ids": ["R0015", "R0020"],
                "explanation": "Denied encoded twice",
                "recommendation": "Normalize outcome variable",
            }
        ],
        "audit_trail_bullets": [],
        "notes": "",
    }
    r = parse_cross_critic_response(json.dumps(payload))
    assert r.verdict == "ISSUES"
    assert r.findings[0].category == "outcome_split"
    assert "X001" in format_cross_critic_report_terminal(r)


def test_cross_repairer_mock_llm() -> None:
    rules = [{"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL", "variable": "x", "relational_operator": "LTE", "constant_value": 1, "yields": "SATISFIED"}]
    handoff = {
        "handoff_schema_version": "1",
        "source": "cross_critic",
        "findings": [],
        "verdict": "ISSUES",
    }

    def fake_llm(_prompt: str) -> str:
        return json.dumps(
            {
                "rules": rules,
                "change_summary": [{"rule_id": "R0001", "finding_id": "X001", "change": "noop"}],
            }
        )

    out, retry = run_cross_repairer(
        policy_id="t",
        rules=rules,
        handoff=handoff,
        processed_nl_excerpt="01. Test.",
        linearized_excerpt="R0001 | ...",
        llm=fake_llm,
    )
    assert len(out.rules) == 1
    assert retry is False
