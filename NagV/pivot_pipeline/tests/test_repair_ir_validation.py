from __future__ import annotations

import copy

import pytest

from pivot_pipeline.repair_ir_validation import (
    RepairIrValidationError,
    k_of_n_binding_note,
    precompile_repaired_rules_validated,
    sanitize_rule_dict_audited,
    validate_repair_ir_application,
)


def test_sanitize_drops_invalid_k_of_n_variable() -> None:
    raw = {
        "rule_id": "R0019",
        "template_class": "K_OF_N",
        "k": 2,
        "clauses": [
            {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
            {"kind": "atom", "variable": "b", "operator": "EQ", "value": True},
        ],
        "variable": "meets_support_ops_competency_requirement",
        "yields": "SATISFIED",
    }
    clean, dropped = sanitize_rule_dict_audited(raw)
    assert "variable" in dropped
    assert "yields" in dropped
    assert "result_variable" not in clean


def test_validate_rejects_dropped_k_of_n_variable_on_focus() -> None:
    before = [
        {
            "rule_id": "R0019",
            "template_class": "K_OF_N",
            "k": 2,
            "clauses": [
                {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
                {"kind": "atom", "variable": "b", "operator": "EQ", "value": True},
            ],
        }
    ]
    merged = [copy.deepcopy(before[0]) | {"variable": "meets_x"}]
    sanitized, dropped = sanitize_rule_dict_audited(merged[0])
    with pytest.raises(RepairIrValidationError, match="cannot use top-level"):
        validate_repair_ir_application(
            rules_before=before,
            merged_rules=merged,
            sanitized_rules=[sanitized],
            focus_rule_ids=["R0019"],
            change_summary=[
                {
                    "finding_id": "X001",
                    "rule_id": "R0019",
                    "change": "Added variable to K_OF_N",
                }
            ],
            dropped_by_rule_id={"R0019": dropped},
        )


def test_validate_rejects_unchanged_focus_rule() -> None:
    rule = {
        "rule_id": "R0019",
        "template_class": "K_OF_N",
        "k": 2,
        "clauses": [
            {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
            {"kind": "atom", "variable": "b", "operator": "EQ", "value": True},
        ],
    }
    with pytest.raises(RepairIrValidationError, match="unchanged"):
        validate_repair_ir_application(
            rules_before=[rule],
            merged_rules=[copy.deepcopy(rule)],
            sanitized_rules=[copy.deepcopy(rule)],
            focus_rule_ids=["R0019"],
            change_summary=[
                {"finding_id": "X001", "rule_id": "R0019", "change": "Assigned variable"}
            ],
            dropped_by_rule_id={},
        )


def test_k_of_n_binding_note_with_result_variable() -> None:
    note = k_of_n_binding_note(
        {
            "template_class": "K_OF_N",
            "result_variable": "meets_support_ops_competency_requirement",
        },
        all_rules=[],
    )
    assert "assigns result" in note
    assert "meets_support_ops_competency_requirement" in note
    assert "via compile lowering" in note


def test_validate_global_k_of_n_accepts_result_variable_only() -> None:
    before = {
        "rule_id": "R0007",
        "template_class": "K_OF_N",
        "applies_to": "GLOBAL",
        "k": 1,
        "clauses": [
            {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
        ],
    }
    after = {**before, "result_variable": "has_required_backend_skills"}
    validate_repair_ir_application(
        rules_before=[before],
        merged_rules=[after],
        sanitized_rules=[after],
        focus_rule_ids=["R0007"],
        change_summary=[
            {"finding_id": "T002", "rule_id": "R0007", "change": "Set result_variable"}
        ],
        dropped_by_rule_id={},
    )


def test_precompile_validated_accepts_result_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rule = {
        "rule_id": "R0019",
        "template_class": "K_OF_N",
        "k": 2,
        "clauses": [
            {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
            {"kind": "atom", "variable": "b", "operator": "EQ", "value": True},
        ],
        "result_variable": "meets_support_ops_competency_requirement",
    }
    before = [
        {
            "rule_id": "R0019",
            "template_class": "K_OF_N",
            "k": 2,
            "clauses": rule["clauses"],
        }
    ]
    out, _ = precompile_repaired_rules_validated(
        "t",
        [rule],
        rules_before=before,
        focus_rule_ids=["R0019"],
        change_summary=[
            {
                "finding_id": "X001",
                "rule_id": "R0019",
                "change": "Set result_variable",
            },
        ],
        skip_vnext_lowering=False,
    )
    assert out
