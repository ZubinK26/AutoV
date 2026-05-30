"""Tier-2 programmatic completion: strict_eval fills + strict Z3 re-query."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pivot_pipeline.external_tester.derive_eval import evaluate_derived_strict
from pivot_pipeline.external_tester.pathway_sufficiency import PathwaySufficiencyReportV1
from pivot_pipeline.external_tester.policy_query import run_policy_query
from pivot_pipeline.external_tester.schemas import (
    PolicyCaseWorldV1,
    PolicyQueryResultV1,
    ProvenanceRef,
    StatedAssignment,
)
from pivot_pipeline.external_tester.variable_tiers import Tier
from pivot_pipeline.ir import MetaScheme

InferenceSource = Literal["strict_eval", "k_of_n", "derived_default"]


class ProgrammaticInferenceV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable: str
    sort: Literal["int", "bool"]
    value: int | bool
    source: InferenceSource = "strict_eval"
    rationale: str = ""
    rule_ids: list[str] = Field(default_factory=list)


class ProgrammaticFillReportV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    inferences: list[ProgrammaticInferenceV1] = Field(default_factory=list)
    filled_variables: list[str] = Field(default_factory=list)
    tier2_query: PolicyQueryResultV1 | None = None


def _missing_var_names(sufficiency: PathwaySufficiencyReportV1) -> list[str]:
    return [m.variable for m in sufficiency.missing]


def run_tier2_programmatic(
    *,
    world: PolicyCaseWorldV1,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    tiers: dict[str, Tier],
    sufficiency: PathwaySufficiencyReportV1,
) -> tuple[ProgrammaticFillReportV1, PolicyCaseWorldV1]:
    """Fill pathway-missing vars via strict_eval; run strict query on completed world."""
    missing = _missing_var_names(sufficiency)
    sorts = dict(meta.variable_sorts)
    prior_stated = {s.variable: s for s in world.stated}
    inferences: list[ProgrammaticInferenceV1] = []

    derived = evaluate_derived_strict(
        rules,
        stated=list(world.stated),
        unknown=missing,
        sorts=sorts,
        tiers=tiers,
    )
    derived_map = {d.variable: d for d in derived}

    for var in missing:
        d = derived_map.get(var)
        if d is None:
            continue
        src: InferenceSource = "strict_eval"
        if "K_OF_N" in d.rationale:
            src = "k_of_n"
        elif "default" in d.rationale.lower():
            src = "derived_default"
        inferences.append(
            ProgrammaticInferenceV1(
                variable=var,
                sort=d.sort,  # type: ignore[arg-type]
                value=d.value,
                source=src,
                rationale=d.rationale,
            )
        )

    completed_stated = list(world.stated)
    stated_names = {s.variable for s in completed_stated}
    unknown = list(world.unknown)
    for inf in inferences:
        if inf.variable in stated_names:
            continue
        completed_stated.append(
            StatedAssignment(
                variable=inf.variable,
                sort=inf.sort,
                status="inferred",
                value=inf.value,
                provenance=ProvenanceRef(
                    line_numbers=[0],
                    quotes=[f"tier2:{inf.source}"],
                ),
                rationale=inf.rationale or "tier-2 programmatic fill",
            )
        )
        stated_names.add(inf.variable)
        if inf.variable in unknown:
            unknown.remove(inf.variable)

    completed_world = world.model_copy(
        update={
            "stated": completed_stated,
            "unknown": unknown,
            "derived": list(world.derived),
        }
    )

    tier2_query: PolicyQueryResultV1 | None = None
    try:
        tier2_query, _complete = run_policy_query(
            meta,
            completed_world,
            unknown_policy="block",
        )
    except ValueError:
        tier2_query = PolicyQueryResultV1(
            query_mode="strict",
            z3_status="unknown",
            compatibility="unknown",
            defaulted_variables=[],
            default_policy="tier2_blocked_incomplete",
        )

    report = ProgrammaticFillReportV1(
        inferences=inferences,
        filled_variables=[i.variable for i in inferences],
        tier2_query=tier2_query,
    )
    return report, completed_world


__all__ = [
    "ProgrammaticFillReportV1",
    "ProgrammaticInferenceV1",
    "run_tier2_programmatic",
]
