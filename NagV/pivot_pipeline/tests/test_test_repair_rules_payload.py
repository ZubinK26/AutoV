from __future__ import annotations

import pytest

from pivot_pipeline.test_repair_rules_payload import (
    MergeRepairerOutputError,
    build_rules_payload_stubs,
    focus_rule_ids_from_handoff,
    merge_repairer_output,
    payload_rules_json_size,
)


def test_focus_rule_ids_from_formal_pointer() -> None:
    handoff = {
        "findings": [
            {"id": "T001", "formal_pointer": "R0006"},
            {"id": "T002", "formal_pointer": "R0013"},
        ]
    }
    assert focus_rule_ids_from_handoff(handoff) == ["R0006", "R0013"]


def test_build_rules_payload_stubs_smaller_than_full() -> None:
    full = [
        {
            "rule_id": "R0001",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "x", "operator": "EQ", "value": True},
            "required_condition": {"kind": "atom", "variable": "y", "operator": "EQ", "value": True},
        },
        {
            "rule_id": "R0002",
            "template_class": "SET_INCLUSION",
            "variable": "z",
            "inclusion_operator": "IN",
            "constant_array": ["a", "b"],
            "yields": "SATISFIED",
        },
    ]
    stubbed = build_rules_payload_stubs(full, ["R0001"])
    full_b, stub_b = payload_rules_json_size(full, stubbed)
    assert stub_b < full_b
    assert stubbed[0]["trigger_condition"] is not None
    assert stubbed[1].get("_payload_stub") is True


def test_merge_keeps_non_focus_unchanged() -> None:
    full = [
        {"rule_id": "R0001", "template_class": "LOGICAL_IMPLICATION", "applies_to": "GLOBAL", "x": 1},
        {"rule_id": "R0002", "template_class": "SET_INCLUSION", "applies_to": "GLOBAL", "y": 2},
    ]
    repairer = [
        {
            "rule_id": "R0001",
            "template_class": "LOGICAL_IMPLICATION",
            "applies_to": "GLOBAL",
            "x": 99,
        },
        {"rule_id": "R0002", "template_class": "SET_INCLUSION", "applies_to": "GLOBAL", "_payload_stub": True},
    ]
    merged = merge_repairer_output(
        full_rules=full,
        repairer_rules=repairer,
        focus_rule_ids=["R0001"],
    )
    assert merged[0]["x"] == 99
    assert merged[1] == full[1]


def test_merge_missing_rule_raises() -> None:
    full = [{"rule_id": "R0001", "template_class": "LOGICAL_IMPLICATION"}]
    with pytest.raises(MergeRepairerOutputError, match="missing"):
        merge_repairer_output(full_rules=full, repairer_rules=[], focus_rule_ids=["R0001"])
