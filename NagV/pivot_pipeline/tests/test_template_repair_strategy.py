from __future__ import annotations

import pytest

from pivot_pipeline.repair_ir_validation import RepairIrValidationError
from pivot_pipeline.template_repair_strategy import (
    infer_repair_strategy_from_bundle,
    repair_improved_subset,
    validate_template_repair_transition,
)


def test_infer_mutant_unsat_strategy() -> None:
    b = {
        "template_kind": "counterfactual_flip",
        "verdict": "inconclusive",
        "actual": {"z3_status_mutant": "unsat"},
        "diff": {"detail": "mutant unsat"},
    }
    assert infer_repair_strategy_from_bundle(b) == "counterfactual_avoid_implication_on_mutant_pins"


def test_infer_no_flip_strategy() -> None:
    b = {
        "template_kind": "counterfactual_flip",
        "verdict": "fail",
        "actual": {"base_decision": "satisfied", "mutant_decision": "satisfied"},
        "diff": {"detail": "expect_flip mismatch"},
    }
    assert infer_repair_strategy_from_bundle(b) == "counterfactual_require_enforced_obligation"


def test_validate_rejects_implication_for_counterfactual_strategy() -> None:
    before = [
        {
            "rule_id": "R0008",
            "template_class": "K_OF_N",
            "k": 1,
            "clauses": [{"kind": "atom", "variable": "x", "operator": "EQ", "value": True}],
            "result_variable": "meets_x",
        }
    ]
    after = [
        {
            "rule_id": "R0008",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {
                "kind": "atom",
                "variable": "is_candidate",
                "operator": "EQ",
                "value": True,
            },
            "required_condition": {
                "kind": "atom",
                "variable": "x",
                "operator": "EQ",
                "value": True,
            },
        }
    ]
    with pytest.raises(RepairIrValidationError, match="forbids LOGICAL_IMPLICATION"):
        validate_template_repair_transition(
            rules_before=before,
            rules_after=after,
            focus_rule_ids=["R0008"],
            strategies_by_rule={"R0008": "counterfactual_require_enforced_obligation"},
        )


def test_repair_improved_subset() -> None:
    before = {
        "results": [
            {"instance_id": "a", "verdict": "inconclusive"},
            {"instance_id": "b", "verdict": "pass"},
        ]
    }
    after = {
        "results": [
            {"instance_id": "a", "verdict": "pass"},
            {"instance_id": "b", "verdict": "pass"},
        ]
    }
    assert repair_improved_subset(
        before_report=before,
        after_report=after,
        instance_ids={"a"},
    )


def test_repair_improved_inconclusive_to_fail() -> None:
    """Same issue count but better verdict (mutant SAT) must be accepted."""
    before = {"results": [{"instance_id": "flip", "verdict": "inconclusive"}]}
    after = {"results": [{"instance_id": "flip", "verdict": "fail"}]}
    assert repair_improved_subset(
        before_report=before,
        after_report=after,
        instance_ids={"flip"},
    )


def test_repair_not_improved_fail_to_inconclusive() -> None:
    before = {"results": [{"instance_id": "flip", "verdict": "fail"}]}
    after = {"results": [{"instance_id": "flip", "verdict": "inconclusive"}]}
    assert not repair_improved_subset(
        before_report=before,
        after_report=after,
        instance_ids={"flip"},
    )
