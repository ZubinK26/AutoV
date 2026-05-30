from __future__ import annotations

from pivot_pipeline.external_tester.schemas import ExternalSourceEnvelope
from pivot_pipeline.external_tester.tier_speculative import _numbered_source
from pivot_pipeline.external_tester.pathway_sufficiency import (
    assess_pathway_sufficiency,
    compute_pathway_requirements,
)
from pivot_pipeline.external_tester.schemas import PolicyCaseWorldV1, ProvenanceRef, StatedAssignment
from pivot_pipeline.external_tester.variable_tiers import classify_variable_tiers
from pivot_pipeline.ir import ConditionAtom, ConstantRelational, LogicalImplication, RelationalOperator
from pivot_pipeline.pathway_compiler import build_meta_scheme


def _implication_meta():
    rules = [
        LogicalImplication(
            rule_id="R0001",
            applies_to="GLOBAL",
            overrides=None,
            trigger_condition=ConditionAtom(
                variable="score", operator=RelationalOperator.GTE, value=1
            ),
            required_condition=ConditionAtom(
                variable="flag", operator=RelationalOperator.EQ, value=True
            ),
        ),
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    return meta.model_copy(update={"variable_sorts": {"score": "int", "flag": "bool"}})


def test_numbered_source_from_string_lines() -> None:
    env = ExternalSourceEnvelope(source_id="cv", line_count=2, lines=["alpha", "beta"])
    text = _numbered_source(env)
    assert "L1: alpha" in text
    assert "L2: beta" in text


def test_bool_consequent_is_grounded() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "n", "operator": "GTE", "value": 1},
            "required_condition": {"kind": "atom", "variable": "ok", "operator": "EQ", "value": True},
        },
    ]
    tiers = classify_variable_tiers(rules, {"n": "int", "ok": "bool"})
    assert tiers["n"] == "grounded"
    assert tiers["ok"] == "grounded"


def test_sufficiency_missing_flag() -> None:
    meta = _implication_meta()
    rules = [r.model_dump(mode="json") for r in meta.rules]
    req = compute_pathway_requirements(meta, rules)
    world = PolicyCaseWorldV1(
        instance_id="e",
        stated=[
            StatedAssignment(
                variable="score",
                sort="int",
                status="present",
                value=2,
                provenance=ProvenanceRef(line_numbers=[1], quotes=["2"]),
            )
        ],
        unknown=["flag"],
    )
    report = assess_pathway_sufficiency(world, req)
    assert not report.tier1_complete
    assert any(m.variable == "flag" for m in report.missing)


def test_sufficiency_complete_when_stated() -> None:
    meta = _implication_meta()
    rules = [r.model_dump(mode="json") for r in meta.rules]
    req = compute_pathway_requirements(meta, rules)
    world = PolicyCaseWorldV1(
        instance_id="e",
        stated=[
            StatedAssignment(
                variable="score",
                sort="int",
                status="present",
                value=2,
                provenance=ProvenanceRef(line_numbers=[1], quotes=["2"]),
            ),
            StatedAssignment(
                variable="flag",
                sort="bool",
                status="present",
                value=True,
                provenance=ProvenanceRef(line_numbers=[2], quotes=["yes"]),
            ),
        ],
        unknown=[],
    )
    report = assess_pathway_sufficiency(world, req)
    assert report.tier1_complete
    assert report.missing == []
