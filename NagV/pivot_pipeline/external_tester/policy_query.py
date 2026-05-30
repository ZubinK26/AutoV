"""Policy compatibility query (Z3 only — strict CWA + lenient existential)."""

from __future__ import annotations

import os
from typing import Any, Literal

from pivot_pipeline.external_tester.schemas import (
    PolicyCaseWorldV1,
    PolicyQueryAddendumV1,
    PolicyQueryResultV1,
)
from pivot_pipeline.external_tester.variable_tiers import Tier, tiers_for_meta
from pivot_pipeline.external_tester.world_to_z3 import (
    UnknownPolicy,
    build_query_world,
    build_stated_pin_dict,
    build_tier1_query_world,
    resolve_unknown_policy,
)
from pivot_pipeline.external_tester.z3_model import model_value
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.template_suite.execute_z3 import _run_sat_with_model

Compatibility = Literal["compatible", "incompatible", "unknown"]
QueryMode = Literal["strict", "lenient"]

_LENIENT_WITNESS_NOTE = (
    "One satisfying completion for unknown and derived variables; "
    "not unique and not extracted from the document."
)


def lenient_query_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    raw = os.getenv("PIVOT_CASE_LENIENT_QUERY", "off").strip().lower()
    return raw in ("on", "true", "1", "yes")


def _compatibility_from_z3(z3_status: str) -> Compatibility:
    if z3_status == "sat":
        return "compatible"
    if z3_status == "unsat":
        return "incompatible"
    return "unknown"


def _strict_policy_name() -> str:
    return os.getenv("PIVOT_CASE_DEFAULT_POLICY", "cwa_pessimistic_v1").strip() or "cwa_pessimistic_v1"


def extract_witness_slices(
    model: Any,
    aux: dict[str, Any],
    world: PolicyCaseWorldV1,
    tiers: dict[str, Tier],
    *,
    include_full: bool = False,
) -> tuple[dict[str, int | bool], dict[str, int | bool], dict[str, int | bool] | None]:
    """Return (witness_unknown, witness_derived, witness_full or None)."""
    sym = aux["symbols"]
    sorts: dict[str, str] = aux["sorts"]
    witness_unknown: dict[str, int | bool] = {}
    for name in sorted(world.unknown):
        if name in sorts:
            witness_unknown[name] = model_value(model, sym, sorts, name)

    witness_derived: dict[str, int | bool] = {}
    for name in sorted(sorts.keys()):
        if tiers.get(name) == "derived":
            witness_derived[name] = model_value(model, sym, sorts, name)

    witness_full: dict[str, int | bool] | None = None
    if include_full:
        witness_full = {}
        for name in sorted(sorts.keys()):
            witness_full[name] = model_value(model, sym, sorts, name)
    return witness_unknown, witness_derived, witness_full


def run_tier1_policy_query(
    meta: MetaScheme,
    world: PolicyCaseWorldV1,
    rules: list[dict[str, Any]],
    tiers: dict[str, Tier],
) -> tuple[PolicyQueryResultV1, dict[str, int | bool]]:
    """Tier-1 document strict: stated + rule-derived eval; no CWA on grounded unknowns."""
    complete, defaulted, _unknown = build_tier1_query_world(world, meta, rules, tiers)
    z3_status, _model, _aux = _run_sat_with_model(meta, complete)
    result = PolicyQueryResultV1(
        query_mode="strict",
        z3_status=z3_status,  # type: ignore[arg-type]
        compatibility=_compatibility_from_z3(z3_status),
        defaulted_variables=defaulted,
        default_policy="tier1_stated_plus_derived_eval_v1",
    )
    return result, complete


def run_policy_query(
    meta: MetaScheme,
    world: PolicyCaseWorldV1,
    *,
    unknown_policy: UnknownPolicy | None = None,
) -> tuple[PolicyQueryResultV1, dict[str, int | bool]]:
    """
    Strict: stated + derived + query-time CWA on unknown grounded.
    """
    policy = unknown_policy or resolve_unknown_policy()
    complete, defaulted, _unknown = build_query_world(world, meta, unknown_policy=policy)
    z3_status, _model, _aux = _run_sat_with_model(meta, complete)
    result = PolicyQueryResultV1(
        query_mode="strict",
        z3_status=z3_status,  # type: ignore[arg-type]
        compatibility=_compatibility_from_z3(z3_status),
        defaulted_variables=defaulted,
        default_policy=_strict_policy_name(),
    )
    return result, complete


def run_lenient_policy_query(
    meta: MetaScheme,
    world: PolicyCaseWorldV1,
    rules: list[dict[str, Any]],
) -> PolicyQueryResultV1:
    """Existential: pin stated only; Z3 assigns unknown grounded + derived."""
    stated_pin = build_stated_pin_dict(world)
    z3_status, model, aux = _run_sat_with_model(meta, stated_pin)
    compat = _compatibility_from_z3(z3_status)

    witness_unknown: dict[str, int | bool] = {}
    witness_derived: dict[str, int | bool] = {}
    witness_note = ""

    if z3_status == "sat" and model is not None:
        tiers = tiers_for_meta(meta, rules)
        full = os.getenv("PIVOT_CASE_LENIENT_WITNESS_FULL", "off").strip().lower() in (
            "on",
            "true",
            "1",
            "yes",
        )
        wu, wd, wf = extract_witness_slices(
            model, aux, world, tiers, include_full=full
        )
        witness_unknown = wu
        witness_derived = wd
        witness_note = _LENIENT_WITNESS_NOTE
        if full and wf:
            witness_note += " witness_full included in addendum."
    elif z3_status == "unsat":
        witness_note = "No satisfying completion exists while fixing stated facts."

    return PolicyQueryResultV1(
        query_mode="lenient",
        z3_status=z3_status,  # type: ignore[arg-type]
        compatibility=compat,
        defaulted_variables=[],
        default_policy="existential_completion_v1",
        witness_unknown=witness_unknown,
        witness_derived=witness_derived,
        witness_note=witness_note,
    )


def dual_query_summary(strict: PolicyQueryResultV1, lenient: PolicyQueryResultV1 | None) -> str:
    parts = [f"strict={strict.compatibility}"]
    if lenient is not None:
        parts.append(f"lenient={lenient.compatibility}")
    return "; ".join(parts)


def build_query_addendum(
    strict: PolicyQueryResultV1,
    lenient: PolicyQueryResultV1 | None,
) -> PolicyQueryAddendumV1:
    strict_copy = strict.model_copy(update={"query_mode": "strict"})
    diverges = None
    if lenient is not None:
        diverges = (
            strict_copy.compatibility == "incompatible"
            and lenient.compatibility == "compatible"
        )
    return PolicyQueryAddendumV1(
        strict=strict_copy,
        lenient=lenient,
        summary=dual_query_summary(strict_copy, lenient),
        strict_incompatible_lenient_compatible=diverges,
    )


__all__ = [
    "build_query_addendum",
    "dual_query_summary",
    "extract_witness_slices",
    "lenient_query_enabled",
    "run_lenient_policy_query",
    "run_policy_query",
    "run_tier1_policy_query",
]
