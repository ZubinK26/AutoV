from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pivot_pipeline.external_tester.completeness import check_completeness
from pivot_pipeline.external_tester.lower import (
    build_executable_world,
    to_template_instance,
    world_coverage,
    world_from_assignments,
)
from pivot_pipeline.external_tester.review_aggregate import aggregate_review
from pivot_pipeline.external_tester.review_pack import build_blind_review_user_message
from pivot_pipeline.external_tester.review_agent import run_review_agent
from pivot_pipeline.external_tester.policy_query import (
    build_query_addendum,
    run_lenient_policy_query,
    run_policy_query,
)
from pivot_pipeline.external_tester.run import (
    _world_to_link_fill,
    check_prior_critics,
    execute_after_review,
    run_external_tester_pipeline,
    run_policy_case_pipeline,
)
from pivot_pipeline.external_tester.schemas import (
    DerivedAssignment,
    PolicyCaseWorldV1,
    StatedAssignment,
)
from pivot_pipeline.external_tester.world_to_z3 import build_query_world
from pivot_pipeline.external_tester.schemas import (
    ExternalSourceEnvelope,
    ExternalWorldFillV1,
    FieldProvenanceReview,
    ProvenanceRef,
    VariableAssignment,
)
from pivot_pipeline.external_tester.source_numbering import raw_text_to_envelope
from pivot_pipeline.external_tester.variable_catalog import harvest_variable_sorts
from pivot_pipeline.external_tester.fill_batches import plan_grounded_batches
from pivot_pipeline.external_tester.fill_orchestration import (
    _parse_batch_assignments,
    merge_assignments,
)
from pivot_pipeline.external_tester.link_consistency import check_link_consistency
from pivot_pipeline.external_tester.variable_tiers import classify_variable_tiers
from pivot_pipeline.external_tester.world_defaults import (
    WORLD_SEMANTICS_GROUNDED_ONLY,
    DerivedIncompleteError,
    apply_not_found_defaults,
    not_found_defaults,
)
from pivot_pipeline.ir import (
    ConditionAtom,
    ConstantRelational,
    LogicalImplication,
    RelationalOperator,
)
from pivot_pipeline.pathway_compiler import build_meta_scheme
from pivot_pipeline.template_suite.diff import diff_instance
from pivot_pipeline.template_suite.execute_z3 import execute_instance
from pivot_pipeline.template_suite.validate import validate_instance


def _tiny_meta():
    rules = [
        ConstantRelational(
            rule_id="R0001",
            applies_to="GLOBAL",
            overrides=None,
            variable="score",
            relational_operator=RelationalOperator.GTE,
            constant_value=1,
            yields="SATISFIED",
        ),
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    return meta.model_copy(update={"variable_sorts": {"score": "int"}})


def _score_flag_implication_meta():
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


def _two_var_meta():
    rules = [
        ConstantRelational(
            rule_id="R0001",
            applies_to="GLOBAL",
            overrides=None,
            variable="score",
            relational_operator=RelationalOperator.GTE,
            constant_value=1,
            yields="SATISFIED",
        ),
    ]
    meta = build_meta_scheme(policy_id="p", rules=rules)
    return meta.model_copy(update={"variable_sorts": {"score": "int", "flag": "bool"}})


def _assignment(
    variable: str,
    sort: str,
    *,
    status: str = "present",
    value: int | bool | None = 2,
    line: int = 1,
) -> VariableAssignment:
    if status == "not_found":
        return VariableAssignment(variable=variable, sort=sort, status="not_found", rationale="absent")
    return VariableAssignment(
        variable=variable,
        sort=sort,
        status=status,
        value=value,
        provenance=ProvenanceRef(line_numbers=[line], quotes=[str(value)]),
        rationale="r",
    )


def test_harvest_variable_sorts() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "n",
            "constant_value": 1,
            "relational_operator": "EQ",
            "yields": "SATISFIED",
        },
        {
            "rule_id": "R2",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "b", "operator": "EQ", "value": True},
            "required_condition": {"kind": "atom", "variable": "x", "operator": "EQ", "value": True},
        },
    ]
    sorts = harvest_variable_sorts(rules)
    assert sorts["n"] == "int"
    assert sorts["b"] == "bool"


def test_completeness_extra_variable() -> None:
    meta = _tiny_meta()
    fill = ExternalWorldFillV1(
        instance_id="ext_001",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[
            _assignment("score", "int", value=2),
            VariableAssignment(variable="bogus", sort="int", status="not_found", rationale="x"),
        ],
    )
    errs = check_completeness(fill, meta)
    assert any("unexpected" in e for e in errs)


def test_scenario_rejects_query() -> None:
    meta = _tiny_meta()
    with pytest.raises(ValueError, match="must not include query"):
        ExternalWorldFillV1(
            instance_id="e",
            template_kind="scenario",
            query={"decision_metric": "rule", "rule_id": "R0001"},
            golden={"sat": True},
            assignments=[_assignment("score", "int", value=2)],
        )


def test_world_defaults_not_found() -> None:
    meta = _two_var_meta()
    assignments = [
        _assignment("score", "int", value=2),
        VariableAssignment(variable="flag", sort="bool", status="not_found", rationale="n/a"),
    ]
    world = apply_not_found_defaults(assignments, meta.variable_sorts)
    assert world == {"score": 2, "flag": False}
    assert len(world) == len(meta.variable_sorts)


def test_build_executable_world_complete() -> None:
    meta = _two_var_meta()
    fill = ExternalWorldFillV1(
        instance_id="e",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[
            _assignment("score", "int", value=2),
            VariableAssignment(variable="flag", sort="bool", status="not_found", rationale="n/a"),
        ],
    )
    world = build_executable_world(fill, meta)
    assert set(world.keys()) == set(meta.variable_sorts.keys())


def test_world_coverage_closed_world() -> None:
    meta = _two_var_meta()
    fill = ExternalWorldFillV1(
        instance_id="e",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[
            _assignment("score", "int", value=2),
            VariableAssignment(variable="flag", sort="bool", status="not_found", rationale="n/a"),
        ],
    )
    cov = world_coverage(fill, 2, closed_world=True)
    assert cov == {"from_document": 1, "defaulted_not_found": 1, "total": 2}


def test_blind_review_excludes_full_document() -> None:
    source = raw_text_to_envelope("secret line\nscore is 2\nother", source_id="t")
    meta = _tiny_meta()
    fill = ExternalWorldFillV1(
        instance_id="ext_001",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[_assignment("score", "int", value=2, line=2)],
    )
    msg = build_blind_review_user_message(source, fill)
    assert "secret line" not in msg
    assert "L2:" in msg
    assert "golden" not in msg.lower()


def test_aggregate_review_fail() -> None:
    meta = _tiny_meta()
    fill = ExternalWorldFillV1(
        instance_id="e",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[_assignment("score", "int", value=9)],
    )
    out = aggregate_review(
        fill,
        [FieldProvenanceReview(variable="score", verdict="unsupported", notes="no match")],
    )
    assert out.verdict == "FAIL"
    assert "score" in out.blocking_variables


def test_scenario_lower_and_z3_execute() -> None:
    meta = _tiny_meta()
    fill = ExternalWorldFillV1(
        instance_id="ext_001",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[_assignment("score", "int", value=2)],
    )
    inst = to_template_instance(fill, meta)
    assert inst.world == {"score": 2}
    validate_instance(meta, inst)
    actual = execute_instance(meta, inst)
    assert actual.get("sat") is True
    verdict, _ = diff_instance(inst, actual)
    assert verdict == "pass"


def test_scenario_unsat_mismatch_golden() -> None:
    meta = _tiny_meta()
    fill = ExternalWorldFillV1(
        instance_id="ext_001",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[_assignment("score", "int", value=0)],
    )
    inst = to_template_instance(fill, meta)
    actual = execute_instance(meta, inst)
    assert actual.get("sat") is False
    verdict, _ = diff_instance(inst, actual)
    assert verdict == "fail"


def test_decision_query_legacy_omits_not_found() -> None:
    meta = _two_var_meta()
    fill = ExternalWorldFillV1(
        instance_id="ext_001",
        template_kind="decision_query",
        query={"decision_metric": "rule", "rule_id": "R0001"},
        golden={"decision": "satisfied"},
        assignments=[
            _assignment("score", "int", value=2),
            VariableAssignment(variable="flag", sort="bool", status="not_found", rationale="n/a"),
        ],
    )
    assert world_from_assignments(fill) == {"score": 2}
    inst = to_template_instance(fill, meta)
    assert "flag" not in inst.world


def test_check_prior_critics_blocks(tmp_path: Path) -> None:
    (tmp_path / "cross_critic_report.json").write_text(
        json.dumps({"verdict": "ISSUES"}),
        encoding="utf-8",
    )
    assert check_prior_critics(tmp_path)


def test_policy_query_compatible() -> None:
    meta = _tiny_meta()
    world = PolicyCaseWorldV1(
        instance_id="ext_001",
        stated=[
            StatedAssignment(
                variable="score",
                sort="int",
                status="present",
                value=2,
                provenance=ProvenanceRef(line_numbers=[1], quotes=["2"]),
            )
        ],
        unknown=[],
        derived=[],
        coverage={"stated_count": 1, "unknown_grounded_count": 0, "derived_count": 0, "total": 1},
    )
    query, _complete = run_policy_query(meta, world)
    assert query.compatibility == "compatible"
    assert query.z3_status == "sat"


def test_policy_query_incompatible() -> None:
    meta = _tiny_meta()
    world = PolicyCaseWorldV1(
        instance_id="ext_001",
        stated=[
            StatedAssignment(
                variable="score",
                sort="int",
                status="present",
                value=0,
                provenance=ProvenanceRef(line_numbers=[1], quotes=["0"]),
            )
        ],
        unknown=[],
        derived=[],
        coverage={"stated_count": 1, "unknown_grounded_count": 0, "derived_count": 0, "total": 1},
    )
    query, _complete = run_policy_query(meta, world)
    assert query.compatibility == "incompatible"
    assert query.z3_status == "unsat"


def test_world_to_link_fill_omits_derived() -> None:
    meta = _two_var_meta()
    meta3 = meta.model_copy(
        update={"variable_sorts": {"score": "int", "flag": "bool", "ok": "bool"}}
    )
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
        derived=[
            DerivedAssignment(
                variable="ok",
                sort="bool",
                value=True,
                rationale="witness after pinning stated grounded",
            )
        ],
    )
    fill = _world_to_link_fill(world, meta3)
    names = {a.variable for a in fill.assignments}
    assert "ok" not in names
    assert "score" in names
    assert "flag" in names


def test_lenient_sat_witness_unknown() -> None:
    meta = _score_flag_implication_meta()
    rules = [
        {
            "rule_id": "R0001",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "score", "operator": "GTE", "value": 1},
            "required_condition": {"kind": "atom", "variable": "flag", "operator": "EQ", "value": True},
        },
    ]
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
        derived=[],
        coverage={},
    )
    lenient = run_lenient_policy_query(meta, world, rules)
    assert lenient.compatibility == "compatible"
    assert lenient.query_mode == "lenient"
    assert lenient.witness_unknown.get("flag") is True


def test_strict_lenient_diverge() -> None:
    meta = _score_flag_implication_meta()
    rules = [
        {
            "rule_id": "R0001",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "score", "operator": "GTE", "value": 1},
            "required_condition": {"kind": "atom", "variable": "flag", "operator": "EQ", "value": True},
        },
    ]
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
        derived=[],
        coverage={},
    )
    strict, _ = run_policy_query(meta, world)
    lenient = run_lenient_policy_query(meta, world, rules)
    assert strict.compatibility == "incompatible"
    assert lenient.compatibility == "compatible"
    addendum = build_query_addendum(strict, lenient)
    assert "strict=incompatible" in addendum.summary
    assert "lenient=compatible" in addendum.summary


def test_build_query_world_cwa_unknown() -> None:
    meta = _two_var_meta()
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
        derived=[],
        coverage={},
    )
    complete, defaulted, _ = build_query_world(world, meta)
    assert complete["score"] == 2
    assert complete["flag"] is False
    assert "flag" in defaulted


def test_run_pipeline_blocked_insufficient(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    meta = _score_flag_implication_meta()
    rules_path = tmp_path / "rules_extracted.json"
    rules_path.write_text(
        json.dumps(
            {
                "policy_id": "p",
                "rules": [r.model_dump(mode="json") for r in meta.rules],
            }
        ),
        encoding="utf-8",
    )
    src = tmp_path / "doc.txt"
    src.write_text("score is 2\n", encoding="utf-8")

    def fake_world(**_k):
        return PolicyCaseWorldV1(
            instance_id="ext_001",
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
            derived=[],
            coverage={"stated_count": 1, "unknown_grounded_count": 1, "derived_count": 0, "total": 2},
        )

    def fake_review(**_k):
        from pivot_pipeline.external_tester.schemas import ExternalProvenanceReviewV1

        return ExternalProvenanceReviewV1(verdict="PASS", field_reviews=[], blocking_variables=[])

    monkeypatch.setattr("pivot_pipeline.external_tester.run.load_meta_from_rules_path", lambda _p: meta)
    monkeypatch.setattr("pivot_pipeline.external_tester.run.build_policy_case_world", fake_world)
    monkeypatch.setattr("pivot_pipeline.external_tester.run.run_trust_review", fake_review)
    monkeypatch.setattr("pivot_pipeline.external_tester.policy_case_eval.tier3_enabled", lambda **_k: False)

    summary = run_policy_case_pipeline(
        work_dir=tmp_path,
        source_path=src,
        rules_extracted_path=rules_path,
        skip_tier2=True,
        skip_tier3=True,
        skip_narrative=True,
        print_fn=MagicMock(),
    )
    assert summary.get("tier1_complete") is False
    assert "insufficient_evidence" in summary.get("outcome", "")
    report = json.loads((tmp_path / "policy_case_report.json").read_text(encoding="utf-8"))
    assert report.get("outcome") == "blocked_insufficient_evidence"
    assert report.get("compatibility") is None


def test_run_pipeline_mocked_v4(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    meta = _tiny_meta()
    rules_path = tmp_path / "rules_extracted.json"
    rules_path.write_text(
        json.dumps(
            {
                "policy_id": "p",
                "rules": [r.model_dump(mode="json") for r in meta.rules],
            }
        ),
        encoding="utf-8",
    )
    src = tmp_path / "doc.txt"
    src.write_text("score is 2\n", encoding="utf-8")

    def fake_world(**_k):
        return PolicyCaseWorldV1(
            instance_id="ext_001",
            stated=[
                StatedAssignment(
                    variable="score",
                    sort="int",
                    status="present",
                    value=2,
                    provenance=ProvenanceRef(line_numbers=[1], quotes=["2"]),
                )
            ],
            unknown=[],
            derived=[],
            coverage={"stated_count": 1, "unknown_grounded_count": 0, "derived_count": 0, "total": 1},
        )

    def fake_review(**_k):
        from pivot_pipeline.external_tester.schemas import ExternalProvenanceReviewV1

        return ExternalProvenanceReviewV1(verdict="PASS", field_reviews=[], blocking_variables=[])

    monkeypatch.setattr("pivot_pipeline.external_tester.run.load_meta_from_rules_path", lambda _p: meta)
    monkeypatch.setattr("pivot_pipeline.external_tester.run.build_policy_case_world", fake_world)
    monkeypatch.setattr("pivot_pipeline.external_tester.run.run_trust_review", fake_review)

    summary = run_policy_case_pipeline(
        work_dir=tmp_path,
        source_path=src,
        rules_extracted_path=rules_path,
        print_fn=MagicMock(),
    )
    assert summary.get("provenance_verdict") == "PASS"
    assert summary.get("compatibility") == "compatible"
    report = json.loads((tmp_path / "policy_case_report.json").read_text(encoding="utf-8"))
    assert report.get("outcome") == "complete"
    assert report.get("compatibility") == "compatible"
    assert (tmp_path / "policy_case_explanation.json").is_file()
    assert (tmp_path / "policy_case_tier_addendum.json").is_file()
    assert (tmp_path / "policy_case_sufficiency.json").is_file()
    addendum = json.loads(
        (tmp_path / "policy_case_tier_addendum.json").read_text(encoding="utf-8")
    )
    assert addendum["tier1"]["compatibility"] == "compatible"


def test_classify_variable_tiers() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "n", "operator": "GTE", "value": 1},
            "required_condition": {"kind": "atom", "variable": "ok", "operator": "EQ", "value": True},
        },
        {
            "rule_id": "R2",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "n",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        },
    ]
    tiers = classify_variable_tiers(rules, {"n": "int", "ok": "bool"})
    assert tiers["n"] == "grounded"
    assert tiers["ok"] == "grounded"


def test_link_consistency_flags_dependent_not_found() -> None:
    meta = _tiny_meta()
    rules = [
        {
            "rule_id": "R2",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": "score", "operator": "GTE", "value": 1},
            "required_condition": {"kind": "atom", "variable": "ok", "operator": "EQ", "value": True},
        },
    ]
    meta2 = meta.model_copy(update={"variable_sorts": {"score": "int", "ok": "bool"}})
    fill = ExternalWorldFillV1(
        instance_id="e",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[
            _assignment("score", "int", value=2),
            VariableAssignment(variable="ok", sort="bool", status="not_found", rationale="x"),
        ],
    )
    res = check_link_consistency(fill, meta2, rules, warn_only=False)
    assert not res.ok
    assert any("inconsistent_link" in e for e in res.errors)


def test_derived_not_found_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_EXTERNAL_DERIVED_NOT_FOUND_POLICY", "block")
    meta = _tiny_meta()
    meta2 = meta.model_copy(update={"variable_sorts": {"score": "int", "ok": "bool"}})
    fill = ExternalWorldFillV1(
        instance_id="e",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[
            _assignment("score", "int", value=2),
            VariableAssignment(variable="ok", sort="bool", status="not_found", rationale="x"),
        ],
    )
    tiers = {"score": "grounded", "ok": "derived"}
    with pytest.raises(DerivedIncompleteError):
        apply_not_found_defaults(fill.assignments, dict(meta2.variable_sorts), tiers=tiers)


def test_batch_parser_drops_extra_variables(tmp_path: Path) -> None:
    raw = json.dumps(
        {
            "schema_version": "1",
            "batch_id": "p1_00",
            "variables_requested": ["score"],
            "assignments": [
                {
                    "variable": "score",
                    "sort": "int",
                    "status": "present",
                    "value": 2,
                    "provenance": {"line_numbers": [1], "quotes": ["2"]},
                    "rationale": "r",
                },
                {
                    "variable": "extra_derived",
                    "sort": "bool",
                    "status": "not_found",
                    "rationale": "x",
                },
            ],
        }
    )
    got = _parse_batch_assignments(
        raw, expected=["score"], batch_id="p1_00", work_dir=tmp_path
    )
    assert len(got) == 1
    assert got[0].variable == "score"


def test_plan_grounded_batches() -> None:
    tiers = {"a": "grounded", "b": "grounded", "c": "derived"}
    sorts = {"a": "int", "b": "bool", "c": "bool"}
    batches = plan_grounded_batches(tiers=tiers, sorts=sorts)
    flat = [x for batch in batches for x in batch]
    assert flat == ["a", "b"]


def test_execute_skipped_when_review_fail(tmp_path: Path) -> None:
    meta = _tiny_meta()
    fill = ExternalWorldFillV1(
        instance_id="e",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[_assignment("score", "int", value=1)],
    )
    row = execute_after_review(work_dir=tmp_path, meta=meta, fill=fill, review_verdict="FAIL")
    assert row.get("skipped") is True


def test_review_agent_prompt_blind(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_llm(prompt: str, *, stage: str) -> str:
        captured.append(prompt)
        payload = {
            "schema_version": "1",
            "field_reviews": [
                {"variable": "score", "verdict": "supported", "notes": "ok"},
            ],
        }
        return json.dumps(payload)

    monkeypatch.setattr(
        "pivot_pipeline.external_tester.review_agent.external_llm_complete",
        fake_llm,
    )
    source = ExternalSourceEnvelope(source_id="s", line_count=2, lines=["hidden", "score 2"])
    meta = _tiny_meta()
    fill = ExternalWorldFillV1(
        instance_id="e",
        template_kind="scenario",
        golden={"sat": True},
        assignments=[_assignment("score", "int", value=2, line=2)],
    )
    out = run_review_agent(work_dir=tmp_path, source=source, fill=fill, meta=meta)
    assert out.verdict == "PASS"
    assert "hidden" not in captured[0]


def test_ensure_meta_merges_k_of_n_result_variables() -> None:
    from pivot_pipeline.external_tester.variable_catalog import ensure_meta_variable_sorts
    from pivot_pipeline.template_suite.run import load_meta_from_rules_path

    rules_path = (
        Path(__file__).resolve().parents[2]
        / "exports"
        / "pivot_runs"
        / "Backend_Engineer_v1_wfm"
        / "rules_extracted.json"
    )
    if not rules_path.is_file():
        pytest.skip("Backend_Engineer fixture not present")
    rules = json.loads(rules_path.read_text(encoding="utf-8"))["rules"]
    partial = _tiny_meta().model_copy(
        update={
            "variable_sorts": {
                "has_experience_issue_tracking": "int",
            }
        }
    )
    meta = ensure_meta_variable_sorts(partial, rules)
    assert "has_backend_skill_set" in meta.variable_sorts
    assert "has_workflow_skill_set" in meta.variable_sorts
    assert meta.variable_sorts["has_backend_skill_set"] == "bool"
    loaded = load_meta_from_rules_path(rules_path)
    merged = ensure_meta_variable_sorts(loaded, rules)
    assert "has_backend_skill_set" in merged.variable_sorts


def test_harvest_policy_literals_maps_strings() -> None:
    from pivot_pipeline.policy_literals import harvest_policy_literals

    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {
                "kind": "atom",
                "variable": "role",
                "operator": "EQ",
                "value": "backend_engineer",
            },
            "required_condition": {"kind": "atom", "variable": "ok", "operator": "EQ", "value": True},
        },
    ]
    lit = harvest_policy_literals(rules)
    assert lit["backend_engineer"] == 1
    assert "backend_engineer" not in lit or "role" not in lit


def test_z3_compile_uses_literal_int_not_shadow_var() -> None:
    from pivot_pipeline.z3_compile import build_solver
    from pivot_pipeline.template_suite.run import load_meta_from_rules_path

    rules_path = (
        Path(__file__).resolve().parents[2]
        / "exports"
        / "pivot_runs"
        / "Backend_Engineer_v1_wfm"
        / "rules_extracted.json"
    )
    if not rules_path.is_file():
        pytest.skip("Backend_Engineer fixture not present")
    meta = load_meta_from_rules_path(rules_path)
    _solver, aux = build_solver(meta)
    assert "backend_engineer" not in aux["symbols"]


def _cv2_weak_world(meta, rules) -> PolicyCaseWorldV1:
    from pivot_pipeline.external_tester.derive_eval import evaluate_derived_strict
    from pivot_pipeline.external_tester.variable_catalog import ensure_meta_variable_sorts
    from pivot_pipeline.external_tester.variable_tiers import tiers_for_meta

    meta = ensure_meta_variable_sorts(meta, rules)
    tiers = tiers_for_meta(meta, rules)
    stated = [
        StatedAssignment(
            variable="has_experience_issue_tracking",
            sort="int",
            status="present",
            value=1,
            provenance=ProvenanceRef(line_numbers=[26], quotes=["ticketing system"]),
            rationale="cv2 weak source",
        ),
    ]
    unknown = sorted(
        n for n, t in tiers.items() if t == "grounded" and n not in {s.variable for s in stated}
    )
    derived = evaluate_derived_strict(
        rules,
        stated=stated,
        unknown=unknown,
        sorts=dict(meta.variable_sorts),
        tiers=tiers,
    )
    return PolicyCaseWorldV1(
        instance_id="cv2",
        stated=stated,
        unknown=unknown,
        derived=derived,
        coverage={"grounded_unknown": len(unknown)},
    )


def test_backend_engineer_cv2_strict_incompatible() -> None:
    from pivot_pipeline.external_tester.variable_catalog import ensure_meta_variable_sorts
    from pivot_pipeline.template_suite.run import load_meta_from_rules_path

    rules_path = (
        Path(__file__).resolve().parents[2]
        / "exports"
        / "pivot_runs"
        / "Backend_Engineer_v1_wfm"
        / "rules_extracted.json"
    )
    if not rules_path.is_file():
        pytest.skip("Backend_Engineer fixture not present")
    meta = load_meta_from_rules_path(rules_path)
    rules = json.loads(rules_path.read_text(encoding="utf-8"))["rules"]
    world = _cv2_weak_world(meta, rules)
    meta = ensure_meta_variable_sorts(meta, rules)
    query, _complete = run_policy_query(meta, world)
    assert query.compatibility == "incompatible"
    lenient = run_lenient_policy_query(meta, world, rules)
    addendum = build_query_addendum(query, lenient)
    assert addendum.strict_incompatible_lenient_compatible is True
