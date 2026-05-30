"""Lower ExternalWorldFillV1 to executable template instances."""

from __future__ import annotations

from pivot_pipeline.external_tester.schemas import ExternalWorldFillV1
from pivot_pipeline.external_tester.variable_tiers import tiers_for_meta
from pivot_pipeline.external_tester.world_defaults import (
    DerivedIncompleteError,
    apply_not_found_defaults,
    derived_not_found_policy,
)
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.template_suite.schemas import DecisionQueryInstance, ScenarioInstance, TemplateInstance


def world_from_assignments(fill: ExternalWorldFillV1) -> dict[str, int | bool]:
    """v1 decision_query: only present/inferred values (not_found omitted)."""
    world: dict[str, int | bool] = {}
    for a in fill.assignments:
        if a.status in ("present", "inferred") and a.value is not None:
            world[a.variable] = a.value
    return world


def build_executable_world(
    fill: ExternalWorldFillV1,
    meta: MetaScheme,
    *,
    rules: list | None = None,
    tiers: dict | None = None,
) -> dict[str, int | bool]:
    """Scenario: complete world; grounded not_found → CWA; derived not_found → block (default)."""
    sorts = dict(meta.variable_sorts)
    tier_map = tiers
    if tier_map is None and rules is not None:
        tier_map = tiers_for_meta(meta, rules)
    return apply_not_found_defaults(fill.assignments, sorts, tiers=tier_map)


def world_coverage(
    fill: ExternalWorldFillV1,
    total: int,
    *,
    closed_world: bool,
) -> dict[str, int]:
    from_document = sum(1 for a in fill.assignments if a.status in ("present", "inferred"))
    not_found = sum(1 for a in fill.assignments if a.status == "not_found")
    if closed_world:
        return {
            "from_document": from_document,
            "defaulted_not_found": not_found,
            "total": total,
        }
    asserted = from_document
    return {"asserted": asserted, "omitted": not_found, "total": total}


def to_template_instance(
    fill: ExternalWorldFillV1,
    meta: MetaScheme,
    *,
    rules: list | None = None,
    tiers: dict | None = None,
) -> TemplateInstance:
    if fill.template_kind == "scenario":
        world = build_executable_world(fill, meta, rules=rules, tiers=tiers)
        return ScenarioInstance(
            instance_id=fill.instance_id,
            world=world,
            golden=fill.golden,
        )
    if fill.query is None:
        raise ValueError("decision_query fill requires query")
    world = world_from_assignments(fill)
    return DecisionQueryInstance(
        instance_id=fill.instance_id,
        world=world,
        query=fill.query,
        golden=fill.golden,
    )


__all__ = [
    "build_executable_world",
    "to_template_instance",
    "world_coverage",
    "world_from_assignments",
]
