"""Pathway sufficiency: grounded evidence required to evaluate must_satisfy_all."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.external_tester.schemas import PolicyCaseWorldV1, StatedAssignment
from pivot_pipeline.external_tester.variable_tiers import _walk_atom_vars
from pivot_pipeline.ir import MetaScheme

ClauseGroupKind = Literal["all", "at_least_k"]


class RuleGroundedRequirementV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    template_class: str
    clause_groups: list[dict[str, Any]] = Field(default_factory=list)
    """Each group: {kind: 'all'|'at_least_k', variables: [...], k: int optional}."""


class PathwayRequirementsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    pathway_id: str
    must_satisfy_all: list[str]
    rules: list[RuleGroundedRequirementV1] = Field(default_factory=list)
    all_required_variables: list[str] = Field(default_factory=list)


class MissingVariableV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    rule_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class PathwaySufficiencyReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    pathway_id: str
    tier1_complete: bool
    missing: list[MissingVariableV1] = Field(default_factory=list)
    resolved_variables: list[str] = Field(default_factory=list)
    by_rule: list[dict[str, Any]] = Field(default_factory=list)


def _pathway_must_satisfy(meta: MetaScheme, *, pathway_id: str) -> list[str]:
    for pw in meta.evaluation_pathways:
        if pw.pathway_id == pathway_id:
            return list(pw.must_satisfy_all)
    if meta.evaluation_pathways:
        return list(meta.evaluation_pathways[0].must_satisfy_all)
    return []


def _atoms_from_condition(expr: dict[str, Any] | None) -> set[str]:
    out: set[str] = set()
    if expr and isinstance(expr, dict):
        _walk_atom_vars(expr, out=out, sort_filter="any")
    return out


def _rule_grounded_requirement(rule: dict[str, Any]) -> RuleGroundedRequirementV1:
    rid = str(rule.get("rule_id", ""))
    tc = str(rule.get("template_class", ""))
    groups: list[dict[str, Any]] = []

    if tc == "LOGICAL_IMPLICATION":
        trig = _atoms_from_condition(rule.get("trigger_condition"))
        req = _atoms_from_condition(rule.get("required_condition"))
        if trig:
            groups.append({"kind": "all", "variables": sorted(trig), "k": len(trig)})
        if req:
            groups.append({"kind": "all", "variables": sorted(req), "k": len(req)})
    elif tc == "CONSTANT_RELATIONAL":
        v = rule.get("variable")
        if isinstance(v, str):
            groups.append({"kind": "all", "variables": [v], "k": 1})
    elif tc == "K_OF_N":
        clause_vars: set[str] = set()
        for c in rule.get("clauses") or []:
            if isinstance(c, dict):
                _walk_atom_vars(c, out=clause_vars, sort_filter="any")
        k = int(rule.get("k", 0))
        if clause_vars:
            groups.append(
                {
                    "kind": "at_least_k",
                    "variables": sorted(clause_vars),
                    "k": max(1, k),
                }
            )
        rv = rule.get("result_variable")
        if isinstance(rv, str) and rv.strip():
            groups.append({"kind": "all", "variables": [rv.strip()], "k": 1})
    else:
        atoms: set[str] = set()
        for key in ("trigger_condition", "required_condition", "left", "right"):
            if key in rule:
                atoms |= _atoms_from_condition(rule[key])
        for c in rule.get("clauses") or []:
            if isinstance(c, dict):
                _walk_atom_vars(c, out=atoms, sort_filter="any")
        if atoms:
            groups.append({"kind": "all", "variables": sorted(atoms), "k": len(atoms)})

    return RuleGroundedRequirementV1(
        rule_id=rid,
        template_class=tc,
        clause_groups=groups,
    )


def compute_pathway_requirements(
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    *,
    pathway_id: str = "compiled_default",
) -> PathwayRequirementsV1:
    must = _pathway_must_satisfy(meta, pathway_id=pathway_id)
    by_id = {str(r.get("rule_id", "")): r for r in rules if r.get("rule_id")}
    rule_reqs: list[RuleGroundedRequirementV1] = []
    all_vars: set[str] = set()

    for rid in must:
        r = by_id.get(rid)
        if not r:
            continue
        req = _rule_grounded_requirement(r)
        rule_reqs.append(req)
        for g in req.clause_groups:
            for v in g.get("variables") or []:
                all_vars.add(str(v))

    return PathwayRequirementsV1(
        pathway_id=pathway_id,
        must_satisfy_all=must,
        rules=rule_reqs,
        all_required_variables=sorted(all_vars),
    )


def _stated_map(world: PolicyCaseWorldV1) -> dict[str, StatedAssignment]:
    return {s.variable: s for s in world.stated}


def _variable_resolved(
    var: str,
    stated: dict[str, StatedAssignment],
    *,
    provenance_ok: set[str] | None,
) -> bool:
    s = stated.get(var)
    if not s:
        return False
    if provenance_ok is not None and var not in provenance_ok:
        return False
    return True


def _group_satisfied(
    group: dict[str, Any],
    stated: dict[str, StatedAssignment],
    *,
    provenance_ok: set[str] | None,
) -> tuple[bool, list[str]]:
    vars_list = [str(v) for v in group.get("variables") or []]
    if not vars_list:
        return True, []
    missing = [v for v in vars_list if not _variable_resolved(v, stated, provenance_ok=provenance_ok)]
    kind = str(group.get("kind", "all"))
    if kind == "at_least_k":
        k = int(group.get("k", 1))
        resolved_count = len(vars_list) - len(missing)
        if resolved_count >= k:
            return True, []
        need = k - resolved_count
        return False, missing[: max(need, len(missing))]
    if missing:
        return False, missing
    return True, []


def assess_pathway_sufficiency(
    world: PolicyCaseWorldV1,
    requirements: PathwayRequirementsV1,
    *,
    provenance_ok_vars: set[str] | None = None,
) -> PathwaySufficiencyReportV1:
    stated = _stated_map(world)
    unknown_set = set(world.unknown)
    missing_by_var: dict[str, MissingVariableV1] = {}
    resolved: set[str] = set()
    by_rule: list[dict[str, Any]] = []

    for rr in requirements.rules:
        rule_missing: list[str] = []
        for g in rr.clause_groups:
            ok, miss = _group_satisfied(g, stated, provenance_ok=provenance_ok_vars)
            for v in miss:
                rule_missing.append(v)
                if v not in missing_by_var:
                    missing_by_var[v] = MissingVariableV1(
                        variable=v,
                        rule_ids=[rr.rule_id],
                        reason="not stated or provenance not accepted",
                    )
                elif rr.rule_id not in missing_by_var[v].rule_ids:
                    missing_by_var[v].rule_ids.append(rr.rule_id)
            if not ok:
                continue
        for v in rr.clause_groups:
            for name in v.get("variables") or []:
                if _variable_resolved(str(name), stated, provenance_ok=provenance_ok_vars):
                    resolved.add(str(name))

        for name in sorted({v for g in rr.clause_groups for v in g.get("variables") or []}):
            if name in unknown_set and name not in missing_by_var:
                missing_by_var[name] = MissingVariableV1(
                    variable=name,
                    rule_ids=[rr.rule_id],
                    reason="grounded unknown (not_found in extract)",
                )
                rule_missing.append(name)

        by_rule.append(
            {
                "rule_id": rr.rule_id,
                "satisfied": len(rule_missing) == 0,
                "missing_variables": sorted(set(rule_missing)),
            }
        )

    for u in unknown_set:
        if u not in missing_by_var and u in requirements.all_required_variables:
            missing_by_var[u] = MissingVariableV1(
                variable=u,
                rule_ids=[],
                reason="grounded unknown (not_found in extract)",
            )

    missing_list = sorted(missing_by_var.values(), key=lambda m: m.variable)
    tier1_complete = len(missing_list) == 0

    return PathwaySufficiencyReportV1(
        pathway_id=requirements.pathway_id,
        tier1_complete=tier1_complete,
        missing=missing_list,
        resolved_variables=sorted(resolved),
        by_rule=by_rule,
    )


__all__ = [
    "MissingVariableV1",
    "PathwayRequirementsV1",
    "PathwaySufficiencyReportV1",
    "RuleGroundedRequirementV1",
    "assess_pathway_sufficiency",
    "compute_pathway_requirements",
]
