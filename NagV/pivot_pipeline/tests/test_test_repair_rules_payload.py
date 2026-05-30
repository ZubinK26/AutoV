from __future__ import annotations

import pytest

from pivot_pipeline.repair_ir_validation import (
    RepairIrValidationError,
    precompile_repaired_rules_validated,
)
from pivot_pipeline.test_repair_rules_payload import (
    MergeRepairerOutputError,
    build_rules_payload_stubs,
    focus_rule_ids_from_handoff,
    merge_repairer_output,
    payload_rules_json_size,
    suggest_next_rule_ids,
)


def test_focus_rule_ids_from_formal_pointer() -> None:
    handoff = {
        "findings": [
            {"id": "T001", "formal_pointer": "R0006"},
            {"id": "T002", "formal_pointer": "R0013"},
        ]
    }
    assert focus_rule_ids_from_handoff(handoff) == ["R0006", "R0013"]


def test_suggest_next_rule_ids() -> None:
    full = [{"rule_id": "R0009"}, {"rule_id": "R0007"}]
    assert suggest_next_rule_ids(full, count=2) == ["R0010", "R0011"]


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


def test_merge_appends_companion_constant_relational() -> None:
    full = [
        {
            "rule_id": "R0007",
            "template_class": "K_OF_N",
            "applies_to": "GLOBAL",
            "k": 1,
            "clauses": [
                {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
            ],
        },
        {"rule_id": "R0009", "template_class": "CONSTANT_RELATIONAL", "applies_to": "GLOBAL"},
    ]
    repairer = [
        {
            "rule_id": "R0007",
            "template_class": "K_OF_N",
            "applies_to": "GLOBAL",
            "k": 1,
            "clauses": [
                {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
            ],
            "result_variable": "meets_skill",
        },
        {"rule_id": "R0009", "template_class": "CONSTANT_RELATIONAL", "applies_to": "GLOBAL", "_payload_stub": True},
        {
            "rule_id": "R0010",
            "template_class": "CONSTANT_RELATIONAL",
            "applies_to": "GLOBAL",
            "variable": "meets_skill",
            "constant_value": True,
            "yields": "SATISFIED",
            "relational_operator": "EQ",
        },
    ]
    merged = merge_repairer_output(
        full_rules=full,
        repairer_rules=repairer,
        focus_rule_ids=["R0007"],
        allow_append_rules=True,
    )
    assert len(merged) == 3
    assert merged[0]["result_variable"] == "meets_skill"
    assert merged[2]["rule_id"] == "R0010"
    assert merged[2]["yields"] == "SATISFIED"


def test_merge_append_stub_for_new_rule_raises() -> None:
    full = [{"rule_id": "R0007", "template_class": "K_OF_N", "k": 1, "clauses": []}]
    repairer = [
        {"rule_id": "R0007", "template_class": "K_OF_N", "k": 1, "clauses": []},
        {"rule_id": "R0010", "template_class": "CONSTANT_RELATIONAL", "_payload_stub": True},
    ]
    with pytest.raises(MergeRepairerOutputError, match="full rule object"):
        merge_repairer_output(
            full_rules=full, repairer_rules=repairer, allow_append_rules=True
        )


def test_merge_missing_rule_raises() -> None:
    full = [{"rule_id": "R0001", "template_class": "LOGICAL_IMPLICATION"}]
    with pytest.raises(MergeRepairerOutputError, match="missing"):
        merge_repairer_output(full_rules=full, repairer_rules=[], focus_rule_ids=["R0001"])


def test_repairer_rules_with_missing_stubs() -> None:
    from pivot_pipeline.test_repair_rules_payload import (
        merge_repairer_output,
        repairer_rules_with_missing_stubs,
    )

    full = [
        {"rule_id": "R0001", "template_class": "K_OF_N", "k": 1, "clauses": []},
        {"rule_id": "R0008", "template_class": "LOGICAL_IMPLICATION"},
    ]
    partial = [{"rule_id": "R0008", "template_class": "K_OF_N", "k": 1, "clauses": []}]
    extended, filled = repairer_rules_with_missing_stubs(full, partial)
    assert filled == ["R0001"]
    merged = merge_repairer_output(
        full_rules=full, repairer_rules=extended, focus_rule_ids=["R0008"]
    )
    assert merged[0]["rule_id"] == "R0001"
    assert merged[1]["template_class"] == "K_OF_N"


def test_precompile_accepts_k_of_n_result_variable_only() -> None:
    before = [
        {
            "rule_id": "R0007",
            "template_class": "K_OF_N",
            "applies_to": "GLOBAL",
            "k": 1,
            "clauses": [
                {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
            ],
        }
    ]
    after_rules = [
        {
            "rule_id": "R0007",
            "template_class": "K_OF_N",
            "applies_to": "GLOBAL",
            "k": 1,
            "clauses": before[0]["clauses"],
            "result_variable": "meets_skill",
        },
    ]
    out, _ = precompile_repaired_rules_validated(
        "policy",
        after_rules,
        rules_before=before,
        focus_rule_ids=["R0007"],
        change_summary=[
            {"finding_id": "T002", "rule_id": "R0007", "change": "Set result_variable"},
        ],
        skip_vnext_lowering=False,
    )
    assert len(out) == 1
