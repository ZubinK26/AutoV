"""Build Z3 world constraints from PolicyCaseWorldV1."""

from __future__ import annotations

import os
from typing import Any, Literal

from z3 import And, Not

from pivot_pipeline.external_tester.derive_eval import evaluate_derived_strict
from pivot_pipeline.external_tester.schemas import PolicyCaseWorldV1
from pivot_pipeline.external_tester.variable_tiers import Tier
from pivot_pipeline.external_tester.world_defaults import default_for_sort, not_found_defaults
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.template_suite.execute_z3 import _fresh_bool, _int_var

UnknownPolicy = Literal["block", "cwa"]


def resolve_unknown_policy(explicit: str | None = None) -> UnknownPolicy:
    raw = (
        explicit
        or os.getenv("PIVOT_CASE_UNKNOWN_POLICY", os.getenv("PIVOT_EXTERNAL_UNKNOWN_POLICY", "cwa"))
    ).strip().lower()
    if raw == "block":
        return "block"
    return "cwa"


def build_query_world(
    world: PolicyCaseWorldV1,
    meta: MetaScheme,
    *,
    unknown_policy: UnknownPolicy | None = None,
) -> tuple[dict[str, int | bool], list[str], list[str]]:
    """
    Return (complete world dict, defaulted_variable names, unknown_grounded names).
    """
    policy = unknown_policy or resolve_unknown_policy()
    sorts = dict(meta.variable_sorts)
    stated_vals = {s.variable: s.value for s in world.stated}
    derived_vals = {d.variable: d.value for d in world.derived}
    unknown_set = set(world.unknown)
    defaults = not_found_defaults()

    complete: dict[str, int | bool] = {}
    defaulted: list[str] = []

    for var in sorted(sorts.keys()):
        if var in stated_vals:
            complete[var] = stated_vals[var]
        elif var in derived_vals:
            complete[var] = derived_vals[var]
        elif var in unknown_set:
            if policy == "block":
                raise ValueError(f"unknown grounded variable blocks query: {var!r}")
            complete[var] = default_for_sort(sorts[var], defaults=defaults)
            defaulted.append(var)
        else:
            if policy == "block":
                raise ValueError(f"variable missing from case world: {var!r}")
            complete[var] = default_for_sort(sorts[var], defaults=defaults)
            defaulted.append(var)

    return complete, defaulted, sorted(unknown_set)


def build_tier1_query_world(
    world: PolicyCaseWorldV1,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    tiers: dict[str, Tier],
) -> tuple[dict[str, int | bool], list[str], list[str]]:
    """
    Tier-1 strict: pin stated facts + derived from strict_eval on stated only (no CWA).
    """
    sorts = dict(meta.variable_sorts)
    stated_vals = {s.variable: s.value for s in world.stated}
    unknown_grounded = [u for u in world.unknown if tiers.get(u) == "grounded"]
    if unknown_grounded:
        raise ValueError(f"tier-1 query blocked: unknown grounded {unknown_grounded!r}")

    derived_list = evaluate_derived_strict(
        rules,
        stated=list(world.stated),
        unknown=[],
        sorts=sorts,
        tiers=tiers,
    )
    complete: dict[str, int | bool] = dict(stated_vals)
    for d in derived_list:
        complete[d.variable] = d.value

    missing = [v for v in sorted(sorts.keys()) if v not in complete]
    if missing:
        raise ValueError(f"tier-1 query missing catalog variables: {missing!r}")

    return complete, [], sorted(unknown_grounded)


def build_stated_pin_dict(world: PolicyCaseWorldV1) -> dict[str, int | bool]:
    """Values to pin for lenient / derive passes (stated grounded only)."""
    return {s.variable: s.value for s in world.stated}


def pin_stated_world(
    stated: dict[str, int | bool],
    meta: MetaScheme,
) -> Any:
    """Z3 conjunction pinning stated/derived values (for witness / partial check)."""
    sym: dict[str, Any] = {}
    sorts = dict(meta.variable_sorts)
    parts: list[Any] = []
    for name, val in sorted(stated.items()):
        st = sorts.get(name, "int")
        if st == "bool":
            b = _fresh_bool(sym, sorts, name)
            parts.append(b if val else Not(b))
        else:
            iv = _int_var(sym, sorts, name)
            parts.append(iv == int(val))
    return And(*parts) if parts else True


__all__ = [
    "UnknownPolicy",
    "build_query_world",
    "build_stated_pin_dict",
    "build_tier1_query_world",
    "pin_stated_world",
    "resolve_unknown_policy",
]
