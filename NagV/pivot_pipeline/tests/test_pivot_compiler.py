from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.pathway_compiler import assert_override_dag_acyclic, build_meta_scheme
from pivot_pipeline.ir import (
    ArithmeticEvaluation,
    ConditionAtom,
    ConstantRelational,
    LogicalImplication,
    MathOperator,
    Preemption,
    PreemptionAction,
    RelationalOperator,
)
from pivot_pipeline.z3_compile import run_z3_check


FIX = Path(__file__).resolve().parent / "fixtures" / "minimal_rules.json"


def test_load_compile_z3_sat() -> None:
    body = json.loads(FIX.read_text(encoding="utf-8"))
    meta = load_rules_and_compile(body["policy_id"], body["rules"])
    assert meta.evaluation_pathways[0].must_satisfy_all == ["R1"]
    r = run_z3_check(meta)
    assert r["status"] == "sat"
    assert "elapsed_ms" in r
    assert r.get("model_verified") is True


def test_override_tie_break() -> None:
    rules = [
        ConstantRelational(
            rule_id="R1",
            variable="x",
            relational_operator=RelationalOperator.EQ,
            constant_value=1,
            yields="SATISFIED",
        ),
        ConstantRelational(
            rule_id="R_z",
            overrides="R1",
            variable="x",
            relational_operator=RelationalOperator.EQ,
            constant_value=2,
            yields="SATISFIED",
        ),
        ConstantRelational(
            rule_id="R_a",
            overrides="R1",
            variable="x",
            relational_operator=RelationalOperator.EQ,
            constant_value=3,
            yields="SATISFIED",
        ),
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    assert meta.evaluation_pathways[0].must_satisfy_all == ["R_z"]


def test_override_cycle_errors() -> None:
    rules = [
        ConstantRelational(
            rule_id="R1",
            overrides="R2",
            variable="x",
            relational_operator=RelationalOperator.EQ,
            constant_value=1,
            yields="SATISFIED",
        ),
        ConstantRelational(
            rule_id="R2",
            overrides="R1",
            variable="x",
            relational_operator=RelationalOperator.EQ,
            constant_value=2,
            yields="SATISFIED",
        ),
    ]
    with pytest.raises(ValueError, match="cycle"):
        assert_override_dag_acyclic(rules)


def test_arithmetic_multiply_two_vars_rejected() -> None:
    with pytest.raises(ValueError, match="MULTIPLY"):
        ArithmeticEvaluation(
            rule_id="M",
            operand_1="a",
            math_operator=MathOperator.MULTIPLY,
            operand_2="b",
            relational_operator=RelationalOperator.LT,
            target_limit=100,
            yields="SATISFIED",
        )


def test_implication_encodes() -> None:
    trig = ConditionAtom(variable="x", operator=RelationalOperator.GT, value=0)
    req = ConditionAtom(variable="y", operator=RelationalOperator.GT, value=0)
    rules = [
        LogicalImplication(
            rule_id="I1",
            trigger_condition=trig,
            required_condition=req,
        )
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    r = run_z3_check(meta)
    assert r["status"] == "sat"


def test_preemption_bypass_waives_target_obligation() -> None:
    rules = [
        ConstantRelational(
            rule_id="R_storage",
            variable="requested_storage_volume",
            relational_operator=RelationalOperator.LT,
            constant_value=500,
            yields="SATISFIED",
        ),
        Preemption(
            rule_id="R_bypass",
            preempting_condition=ConditionAtom(
                variable="is_ml_engineer",
                operator=RelationalOperator.EQ,
                value=True,
            ),
            action=PreemptionAction.BYPASS_RULE,
            target_rule_id="R_storage",
        ),
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    r = run_z3_check(meta)
    assert r["status"] == "sat"


def test_preemption_resolves_storage_limit_500gb_alias() -> None:
    rules = [
        ConstantRelational(
            rule_id="R0003",
            variable="requested_storage_volume",
            relational_operator=RelationalOperator.LT,
            constant_value=500,
            yields="SATISFIED",
        ),
        Preemption(
            rule_id="R0007",
            preempting_condition=ConditionAtom(
                variable="requestor_role",
                operator=RelationalOperator.EQ,
                value="ML_ENGINEER",
            ),
            action=PreemptionAction.BYPASS_RULE,
            target_rule_id="storage_limit_500gb",
        ),
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    prem = next(r for r in meta.rules if isinstance(r, Preemption))
    assert prem.target_rule_id == "R0003"
    r = run_z3_check(meta)
    assert r["status"] == "sat"


def test_preemption_unknown_target_rule_id_errors() -> None:
    rules = [
        ConstantRelational(
            rule_id="R1",
            variable="x",
            relational_operator=RelationalOperator.LT,
            constant_value=10,
            yields="SATISFIED",
        ),
        Preemption(
            rule_id="Rp",
            preempting_condition=ConditionAtom(
                variable="y", operator=RelationalOperator.EQ, value=True
            ),
            action=PreemptionAction.BYPASS_RULE,
            target_rule_id="no_such_rule",
        ),
    ]
    with pytest.raises(ValueError, match="target_rule_id"):
        build_meta_scheme(policy_id="p", rules=rules)
