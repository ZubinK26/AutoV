from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.cross_repairer_agent import cross_repairer_system_prompt, run_cross_repairer
from pivot_pipeline.test_repair_rules_payload import (
    build_rules_payload_stubs,
    focus_rule_ids_from_handoff,
    merge_repairer_output,
    payload_rules_json_size,
)


def test_focus_rule_ids_from_cross_handoff() -> None:
    handoff = {
        "findings": [
            {
                "id": "X001",
                "rule_ids": ["R0030", "R0037"],
                "explanation": "align R0031",
            },
        ]
    }
    ids = focus_rule_ids_from_handoff(handoff)
    assert ids == ["R0030", "R0031", "R0037"]


def test_cross_repair_stub_payload_smaller() -> None:
    full = [
        {
            "rule_id": f"R{i:04d}",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "operator": "EQ", "value": True, "variable": "x"},
            "required_condition": {"kind": "atom", "operator": "EQ", "value": True, "variable": "y"},
        }
        for i in range(1, 21)
    ]
    stubbed = build_rules_payload_stubs(full, ["R0001", "R0002"])
    full_b, stub_b = payload_rules_json_size(full, stubbed)
    assert stub_b < full_b


def test_cross_repairer_prompt_includes_normative_and_focus() -> None:
    text = cross_repairer_system_prompt()
    assert "repairer_ir_normative" in text.lower() or "denylist" in text.lower()
    assert "focus_rule_ids" in text
    assert "do not invent" in text.lower() or "Do not invent" in text


def test_run_cross_repairer_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    full = [
        {"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL", "variable": "a", "relational_operator": "EQ", "constant_value": True, "yields": "SATISFIED"},
        {"rule_id": "R0002", "template_class": "CONSTANT_RELATIONAL", "variable": "b", "relational_operator": "EQ", "constant_value": True, "yields": "SATISFIED"},
    ]
    handoff = {
        "findings": [{"id": "X001", "rule_ids": ["R0001"], "explanation": "fix R0001"}],
        "approved_finding_ids": ["X001"],
    }

    def fake_complete(*, base_prompt: str, llm=None):
        assert "focus_rule_ids" in base_prompt
        assert "_payload_stub" in base_prompt
        out = MagicMock()
        out.rules = [
            full[0],
            {"rule_id": "R0002", "template_class": "CONSTANT_RELATIONAL", "variable": "b", "relational_operator": "EQ", "constant_value": True, "yields": "SATISFIED", "_payload_stub": True},
        ]
        out.change_summary = [MagicMock(finding_id="X001", rule_id="R0001", change="x")]
        out.change_summary[0].model_dump = lambda: {"finding_id": "X001", "rule_id": "R0001", "change": "x"}
        return out, False

    monkeypatch.setattr(
        "pivot_pipeline.cross_repairer_agent.complete_repairer_prompt",
        fake_complete,
    )
    out, _ = run_cross_repairer(
        policy_id="t",
        rules=full,
        handoff=handoff,
        processed_nl_excerpt="line",
        linearized_excerpt="R0001 | ...",
        llm=lambda _p: "{}",
    )
    merged = merge_repairer_output(full_rules=full, repairer_rules=out.rules, focus_rule_ids=["R0001"])
    assert merged[0] == full[0]
    assert merged[1] == full[1]
