"""Build PolicyCaseWorldV1: extract stated facts, explicit unknown, Z3 witness derive."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from z3 import sat

from pivot_pipeline.external_tester.fill_orchestration import (
    _assignments_by_var,
    _load_assignments_file,
    run_phase1_chunked,
    run_phase2_derive,
)
from pivot_pipeline.external_tester.schemas import (
    DerivedAssignment,
    ExternalSourceEnvelope,
    PolicyCaseWorldV1,
    ProvenanceRef,
    StatedAssignment,
    VariableAssignment,
)
from pivot_pipeline.external_tester.trace import append_trace
from pivot_pipeline.external_tester.derive_eval import build_partial_world, evaluate_derived_strict
from pivot_pipeline.external_tester.variable_tiers import Tier, tiers_for_meta
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.external_tester.z3_model import model_value
from pivot_pipeline.template_suite.execute_z3 import _world_to_z3
from pivot_pipeline.z3_compile import build_solver


def resolve_derive_mode(explicit: str | None = None) -> str:
    raw = (explicit or os.getenv("PIVOT_CASE_DERIVE_MODE", "strict_eval")).strip().lower()
    if raw in ("llm_glossary", "llm"):
        return "llm_glossary"
    if raw in ("z3_witness", "witness"):
        return "z3_witness"
    return "strict_eval"


def merge_case_scope_into_stated(
    stated: list[StatedAssignment],
    unknown: list[str],
    *,
    source: ExternalSourceEnvelope,
    tiers: dict[str, Tier],
    sorts: dict[str, str],
) -> tuple[list[StatedAssignment], list[str]]:
    """Apply optional ``case_scope`` from source envelope (grounded vars only)."""
    scope = source.case_scope or {}
    if not scope:
        return stated, unknown
    by_var = {s.variable: s for s in stated}
    unknown_set = set(unknown)
    for var, val in sorted(scope.items()):
        if tiers.get(var) != "grounded":
            continue
        if var not in sorts:
            continue
        sort = sorts[var]
        if sort == "bool" and not isinstance(val, bool):
            raise ValueError(f"case_scope {var}: expected bool, got {val!r}")
        if sort == "int" and not isinstance(val, int):
            raise ValueError(f"case_scope {var}: expected int, got {val!r}")
        by_var[var] = StatedAssignment(
            variable=var,
            sort=sort,  # type: ignore[arg-type]
            status="inferred",
            value=val,
            provenance=ProvenanceRef(),
            rationale="case_scope from source envelope",
        )
        unknown_set.discard(var)
    return sorted(by_var.values(), key=lambda s: s.variable), sorted(unknown_set)


def stated_pin_contradicts_policy(
    meta: MetaScheme,
    stated: list[StatedAssignment],
) -> bool:
    """True when policy ∧ stated grounded facts alone is UNSAT."""
    from z3 import sat

    pin = {s.variable: s.value for s in stated}
    if not pin:
        return False
    solver, aux = build_solver(meta)
    sym = aux["symbols"]
    sorts: dict[str, str] = aux["sorts"]
    solver.add(_world_to_z3(sym, sorts, pin))
    return solver.check() != sat


def _phase1_to_stated_unknown(
    phase1: list[VariableAssignment],
    tiers: dict[str, Tier],
) -> tuple[list[StatedAssignment], list[str]]:
    stated: list[StatedAssignment] = []
    unknown: list[str] = []
    for a in phase1:
        if tiers.get(a.variable) != "grounded":
            continue
        if a.status == "not_found":
            unknown.append(a.variable)
        elif a.status in ("present", "inferred"):
            stated.append(
                StatedAssignment(
                    variable=a.variable,
                    sort=a.sort,  # type: ignore[arg-type]
                    status=a.status,  # type: ignore[arg-type]
                    value=a.value,  # type: ignore[arg-type]
                    provenance=a.provenance,
                    rationale=a.rationale,
                )
            )
        else:
            raise ValueError(f"phase1 {a.variable}: unexpected status {a.status!r}")
    return stated, sorted(unknown)


def derive_z3_witness(
    meta: MetaScheme,
    stated: list[StatedAssignment],
    tiers: dict[str, Tier],
    *,
    work_dir: Path | None = None,
) -> list[DerivedAssignment]:
    """After pinning stated grounded facts, read derived-tier values from one SAT witness."""
    pin = {s.variable: s.value for s in stated}
    if not pin:
        return []

    solver, aux = build_solver(meta)
    sym = aux["symbols"]
    sorts: dict[str, str] = aux["sorts"]
    solver.add(_world_to_z3(sym, sorts, pin))
    if solver.check() != sat:
        if work_dir is not None:
            append_trace(
                work_dir,
                {"kind": "derive_witness_unsat", "pinned": sorted(pin.keys())},
            )
        return []

    model = solver.model()
    derived: list[DerivedAssignment] = []
    for name in sorted(sorts.keys()):
        if tiers.get(name) != "derived":
            continue
        val = model_value(model, sym, sorts, name)
        derived.append(
            DerivedAssignment(
                variable=name,
                sort=sorts[name],  # type: ignore[arg-type]
                value=val,
                source="z3_witness",
                rationale="witness after pinning stated grounded",
            )
        )
    return derived


def _llm_derive_to_policy(
    assignments: list[VariableAssignment],
    tiers: dict[str, Tier],
) -> list[DerivedAssignment]:
    out: list[DerivedAssignment] = []
    for a in assignments:
        if a.value is None:
            raise ValueError(f"derive {a.variable}: missing value")
        out.append(
            DerivedAssignment(
                variable=a.variable,
                sort=a.sort,  # type: ignore[arg-type]
                value=a.value,
                source="llm_glossary",
                rationale=a.rationale or "llm glossary derive",
            )
        )
    missing = sorted(
        n for n, t in tiers.items() if t == "derived" and n not in {d.variable for d in out}
    )
    if missing:
        raise ValueError(f"llm derive missing variables: {', '.join(missing)}")
    return out


def _coverage(world: PolicyCaseWorldV1, total: int) -> dict[str, int]:
    return {
        "stated_count": len(world.stated),
        "unknown_grounded_count": len(world.unknown),
        "derived_count": len(world.derived),
        "total": total,
    }


def build_policy_case_world(
    *,
    work_dir: Path,
    source: ExternalSourceEnvelope,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    instance_id: str,
    derive_mode: str | None = None,
    refill_variables: list[str] | None = None,
    feedback: str = "",
) -> PolicyCaseWorldV1:
    """Phase 1 extract → stated/unknown → derive (default Z3 witness)."""
    work_dir = work_dir.resolve()
    tiers = tiers_for_meta(meta, rules)
    sorts = dict(meta.variable_sorts)
    mode = resolve_derive_mode(derive_mode)

    p1_path = work_dir / "policy_case_world_phase1.json"
    legacy_p1 = work_dir / "external_world_fill_phase1.json"

    if refill_variables:
        p1_by = _load_assignments_file(p1_path) or _load_assignments_file(legacy_p1)
        new_p1 = run_phase1_chunked(
            work_dir=work_dir,
            source=source,
            meta=meta,
            tiers=tiers,
            only_variables=refill_variables,
            feedback=feedback,
        )
        p1_by.update(_assignments_by_var(new_p1))
        grounded_count = sum(1 for t in tiers.values() if t == "grounded")
        if len(p1_by) < grounded_count:
            raise ValueError(
                "provenance refill: prior phase1 snapshot missing; run full extract first "
                f"(have {len(p1_by)} grounded, need {grounded_count})"
            )
        phase1 = [p1_by[k] for k in sorted(p1_by) if tiers.get(k) == "grounded" and k in p1_by]
        append_trace(
            work_dir,
            {"kind": "world_refill", "variables": refill_variables, "n": len(new_p1)},
        )
    else:
        phase1 = run_phase1_chunked(
            work_dir=work_dir,
            source=source,
            meta=meta,
            tiers=tiers,
            only_variables=None,
            feedback=feedback,
        )

    if refill_variables is None:
        p1_path.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "assignments": [a.model_dump(mode="json") for a in phase1],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        append_trace(work_dir, {"kind": "world_phase1", "n": len(phase1)})

    stated, unknown = _phase1_to_stated_unknown(phase1, tiers)
    stated, unknown = merge_case_scope_into_stated(
        stated, unknown, source=source, tiers=tiers, sorts=sorts
    )

    if stated_pin_contradicts_policy(meta, stated):
        append_trace(work_dir, {"kind": "stated_pin_unsat", "pinned": [s.variable for s in stated]})

    derived: list[DerivedAssignment] = []

    if mode == "llm_glossary":
        p1_assignments = [a for a in phase1 if tiers.get(a.variable) == "grounded"]
        p2 = run_phase2_derive(
            work_dir=work_dir,
            meta=meta,
            rules=rules,
            phase1=p1_assignments,
            tiers=tiers,
            only_variables=None,
            feedback=feedback,
        )
        derived = _llm_derive_to_policy(p2, tiers)
        append_trace(work_dir, {"kind": "world_derive", "mode": "llm_glossary", "n": len(derived)})
    elif mode == "strict_eval":
        derived = evaluate_derived_strict(
            rules, stated=stated, unknown=unknown, sorts=sorts, tiers=tiers
        )
        append_trace(work_dir, {"kind": "world_derive", "mode": "strict_eval", "n": len(derived)})
    else:
        derived = derive_z3_witness(meta, stated, tiers, work_dir=work_dir)
        append_trace(work_dir, {"kind": "world_derive", "mode": "z3_witness", "n": len(derived)})

    world = PolicyCaseWorldV1(
        instance_id=instance_id,
        stated=stated,
        unknown=unknown,
        derived=derived,
        coverage={},
    )
    world = world.model_copy(update={"coverage": _coverage(world, len(sorts))})

    path = work_dir / "policy_case_world.json"
    path.write_text(
        json.dumps(world.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return world


__all__ = [
    "build_policy_case_world",
    "derive_z3_witness",
    "merge_case_scope_into_stated",
    "resolve_derive_mode",
    "stated_pin_contradicts_policy",
]
