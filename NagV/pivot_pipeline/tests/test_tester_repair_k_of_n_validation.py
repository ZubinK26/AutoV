from __future__ import annotations

import copy

import pytest

from pivot_pipeline.repair_ir_validation import RepairIrValidationError, precompile_repaired_rules_validated


def test_test_repair_yields_on_k_of_n_fails_validation() -> None:
    """Mirrors silent no-op when repairer adds yields to K_OF_N (stripped on sanitize)."""
    before = [
        {
            "rule_id": "R0007",
            "template_class": "K_OF_N",
            "k": 1,
            "clauses": [
                {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
            ],
        }
    ]
    merged = [copy.deepcopy(before[0]) | {"yields": "SATISFIED"}]
    with pytest.raises(RepairIrValidationError, match="cannot use top-level|unchanged"):
        precompile_repaired_rules_validated(
            "policy",
            merged,
            rules_before=before,
            focus_rule_ids=["R0007"],
            change_summary=[
                {
                    "finding_id": "T002",
                    "rule_id": "R0007",
                    "change": "Added yields SATISFIED to K_OF_N",
                }
            ],
        )
