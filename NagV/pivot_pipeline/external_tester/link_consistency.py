"""Pre-Z3 link consistency between filled variables and dependents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pivot_pipeline.external_tester.schemas import ExternalWorldFillV1, VariableAssignment
from pivot_pipeline.external_tester.variable_tiers import Tier, tiers_for_meta
from pivot_pipeline.ir import MetaScheme


@dataclass(frozen=True)
class LinkValidationResult:
    ok: bool
    errors: list[str]

    def to_report_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors}


def _walk_atom_vars(obj: Any, *, out: set[str]) -> None:
    if isinstance(obj, dict):
        if obj.get("kind") == "atom" and isinstance(obj.get("variable"), str):
            out.add(obj["variable"])
        elif obj.get("kind") in ("and", "or"):
            for c in obj.get("children") or []:
                _walk_atom_vars(c, out=out)
        elif obj.get("kind") == "not":
            _walk_atom_vars(obj.get("child"), out=out)
        else:
            for v in obj.values():
                _walk_atom_vars(v, out=out)
    elif isinstance(obj, list):
        for it in obj:
            _walk_atom_vars(it, out=out)


def build_link_edges(rules: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Directed edges: filled trigger/input A may require dependent B to be set."""
    edges: list[tuple[str, str]] = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        tc = str(r.get("template_class", ""))
        if tc == "LOGICAL_IMPLICATION":
            triggers: set[str] = set()
            heads: set[str] = set()
            if "trigger_condition" in r:
                _walk_atom_vars(r["trigger_condition"], out=triggers)
            _walk_atom_vars(r.get("required_condition"), out=heads)
            for t in triggers:
                for h in heads:
                    if t != h:
                        edges.append((t, h))
        elif tc == "CONSTANT_RELATIONAL":
            v = r.get("variable")
            if isinstance(v, str):
                edges.append((v, v))
        elif tc == "K_OF_N":
            rv = r.get("result_variable")
            clause_vars: set[str] = set()
            for c in r.get("clauses") or []:
                if isinstance(c, dict):
                    _walk_atom_vars(c, out=clause_vars)
            if isinstance(rv, str) and rv.strip():
                for cv in clause_vars:
                    if cv != rv:
                        edges.append((cv, rv))
    return edges


def _filled_vars(assignments: list[VariableAssignment]) -> set[str]:
    return {a.variable for a in assignments if a.status in ("present", "inferred")}


def _not_found_vars(assignments: list[VariableAssignment]) -> set[str]:
    return {a.variable for a in assignments if a.status == "not_found"}


def check_link_consistency(
    fill: ExternalWorldFillV1,
    meta: MetaScheme,
    rules: list[dict[str, Any]],
    *,
    tiers: dict[str, Tier] | None = None,
    warn_only: bool = True,
) -> LinkValidationResult:
    tiers = tiers or tiers_for_meta(meta, rules)
    filled = _filled_vars(fill.assignments)
    not_found = _not_found_vars(fill.assignments)
    errors: list[str] = []

    for a, b in build_link_edges(rules):
        if a in filled and b in not_found:
            errors.append(f"inconsistent_link: {b!r} is not_found but linked from filled {a!r}")

    for name, tier in tiers.items():
        if tier == "derived" and name in not_found:
            errors.append(f"derived_incomplete: {name!r} is not_found after phase 2")

    if warn_only and errors:
        return LinkValidationResult(ok=True, errors=errors)
    return LinkValidationResult(ok=not errors, errors=errors)


__all__ = [
    "LinkValidationResult",
    "build_link_edges",
    "check_link_consistency",
]
