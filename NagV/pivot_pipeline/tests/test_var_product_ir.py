from __future__ import annotations

import pytest

from pivot_pipeline.ir import (
    ConditionAtom,
    ConditionVarProductCmp,
    LogicalImplication,
    RelationalOperator,
    VarProdRhsConst,
    load_rules_and_compile,
)
from pivot_pipeline.var_product_validate import validate_var_product_rules
from pivot_pipeline.z3_compile import run_z3_check


def test_varprod_z3_sat() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "t", "operator": "EQ", "value": True},
            "required_condition": {
                "kind": "varprod_cmp",
                "left_variable": "a",
                "right_variable": "b",
                "operator": "LTE",
                "rhs": {"kind": "const", "value": 1_000_000},
            },
        },
    ]
    meta = load_rules_and_compile("t", rules)
    out = run_z3_check(meta)
    assert out["status"] == "sat"
    assert out.get("model_verified") is True


def test_varprod_rhs_var() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "t", "operator": "EQ", "value": True},
            "required_condition": {
                "kind": "varprod_cmp",
                "left_variable": "a",
                "right_variable": "b",
                "operator": "LTE",
                "rhs": {"kind": "var", "variable": "cap"},
            },
        },
    ]
    meta = load_rules_and_compile("t", rules)
    out = run_z3_check(meta)
    assert out["status"] == "sat"


def test_two_varprod_same_rule_rejected() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "t", "operator": "EQ", "value": True},
            "required_condition": {
                "kind": "and",
                "children": [
                    {
                        "kind": "varprod_cmp",
                        "left_variable": "a",
                        "right_variable": "b",
                        "operator": "LTE",
                        "rhs": {"kind": "const", "value": 10},
                    },
                    {
                        "kind": "varprod_cmp",
                        "left_variable": "x",
                        "right_variable": "y",
                        "operator": "LTE",
                        "rhs": {"kind": "const", "value": 10},
                    },
                ],
            },
        },
    ]
    with pytest.raises(ValueError, match="at most one varprod_cmp"):
        load_rules_and_compile("t", rules)


def test_varprod_bool_choice_var_rejected() -> None:
    rules_list = [
        {
            "rule_id": "R0",
            "template_class": "EXCLUSIVE_CHOICE",
            "mode": "exactly_one",
            "variables": ["flag_a", "flag_b"],
        },
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "t", "operator": "EQ", "value": True},
            "required_condition": {
                "kind": "varprod_cmp",
                "left_variable": "flag_a",
                "right_variable": "b",
                "operator": "LTE",
                "rhs": {"kind": "const", "value": 1},
            },
        },
    ]
    with pytest.raises(ValueError, match="EXCLUSIVE_CHOICE"):
        load_rules_and_compile("t", rules_list)


def test_varprod_nested_under_not_and_depth() -> None:
    inner = ConditionVarProductCmp(
        left_variable="a",
        right_variable="b",
        operator=RelationalOperator.LTE,
        rhs=VarProdRhsConst(kind="const", value=500),
    )
    trig = ConditionAtom(variable="t", operator=RelationalOperator.EQ, value=True)
    req = LogicalImplication.model_validate(
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": trig.model_dump(),
            "required_condition": {"kind": "not", "child": inner.model_dump()},
        }
    )
    validate_var_product_rules([req])


def test_registry_collect_varprod_slugs() -> None:
    from pivot_pipeline.registry_pass import apply_registry_to_rules, collect_used_slugs

    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "t", "operator": "EQ", "value": True},
            "required_condition": {
                "kind": "varprod_cmp",
                "left_variable": "a",
                "right_variable": "b",
                "operator": "LTE",
                "rhs": {"kind": "var", "variable": "cap_rhs"},
            },
        },
    ]
    assert set(collect_used_slugs(rules)) == {"a", "b", "cap_rhs", "t"}
    m = {"a": "a2", "b": "b2", "cap_rhs": "cap2", "t": "t2"}
    # normalize keys like registry would — fake full alias map with slug keys
    alias = {k: v for k, v in m.items()}
    updated = apply_registry_to_rules(rules, alias)
    req = updated[0]["required_condition"]
    assert req["left_variable"] == "a2"
    assert req["right_variable"] == "b2"
    assert req["rhs"]["variable"] == "cap2"
