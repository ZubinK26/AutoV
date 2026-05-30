"""Strict derive: rule outputs from stated facts + CWA on grounded unknowns (no SAT witness)."""

from __future__ import annotations

from typing import Any, Literal

from pivot_pipeline.external_tester.schemas import DerivedAssignment, StatedAssignment
from pivot_pipeline.external_tester.variable_tiers import Tier
from pivot_pipeline.external_tester.world_defaults import default_for_sort, not_found_defaults

Op = Literal["EQ", "NEQ", "GT", "LT", "GTE", "LTE"]


def _compare(op: str, left: int | bool, right: int | bool) -> bool:
    if op == "EQ":
        return left == right
    if op == "NEQ":
        return left != right
    if op == "GT":
        return int(left) > int(right)
    if op == "LT":
        return int(left) < int(right)
    if op == "GTE":
        return int(left) >= int(right)
    if op == "LTE":
        return int(left) <= int(right)
    raise ValueError(f"unsupported operator {op!r}")


def _eval_atom(atom: dict[str, Any], world: dict[str, int | bool]) -> bool:
    var = atom["variable"]
    op = str(atom.get("operator", "EQ"))
    rhs = atom.get("value")
    left = world.get(var)
    if left is None:
        return False
    if isinstance(rhs, bool) and isinstance(left, int):
        rhs = 1 if rhs else 0
    if isinstance(rhs, bool):
        return _compare(op, left, rhs)
    if isinstance(rhs, (int, float)):
        return _compare(op, int(left), int(rhs))
    if isinstance(rhs, str):
        return _compare(op, int(left), int(rhs))
    return False


def _eval_condition(expr: dict[str, Any] | None, world: dict[str, int | bool]) -> bool:
    if not expr or not isinstance(expr, dict):
        return True
    kind = expr.get("kind")
    if kind == "atom":
        return _eval_atom(expr, world)
    if kind == "and":
        children = expr.get("children") or []
        return all(_eval_condition(c, world) for c in children)
    if kind == "or":
        children = expr.get("children") or []
        return any(_eval_condition(c, world) for c in children)
    if kind == "not":
        return not _eval_condition(expr.get("child"), world)
    return True


def build_partial_world(
    stated: list[StatedAssignment],
    unknown: list[str],
    sorts: dict[str, str],
) -> dict[str, int | bool]:
    """Stated grounded facts + pessimistic defaults for grounded unknowns."""
    defaults = not_found_defaults()
    world: dict[str, int | bool] = {s.variable: s.value for s in stated}
    for name in unknown:
        world[name] = default_for_sort(sorts.get(name, "int"), defaults=defaults)
    return world


def evaluate_k_of_n_result(
    rule: dict[str, Any],
    world: dict[str, int | bool],
) -> bool | None:
    rv = rule.get("result_variable")
    if not isinstance(rv, str) or not rv.strip():
        return None
    k = int(rule.get("k", 0))
    satisfied = 0
    for clause in rule.get("clauses") or []:
        if isinstance(clause, dict) and _eval_atom(clause, world):
            satisfied += 1
    return satisfied >= k


def evaluate_derived_strict(
    rules: list[dict[str, Any]],
    *,
    stated: list[StatedAssignment],
    unknown: list[str],
    sorts: dict[str, str],
    tiers: dict[str, Tier],
) -> list[DerivedAssignment]:
    """Compute derived-tier variables from policy structure + partial world."""
    partial = build_partial_world(stated, unknown, sorts)
    out: list[DerivedAssignment] = []

    for r in rules:
        if not isinstance(r, dict):
            continue
        if str(r.get("template_class", "")) == "K_OF_N":
            rv = r.get("result_variable")
            if isinstance(rv, str) and rv.strip() and tiers.get(rv.strip()) == "derived":
                val = evaluate_k_of_n_result(r, partial)
                if val is not None:
                    out.append(
                        DerivedAssignment(
                            variable=rv.strip(),
                            sort=sorts.get(rv.strip(), "bool"),  # type: ignore[arg-type]
                            value=val,
                            source="strict_eval",
                            rationale="K_OF_N clause count vs k on partial world",
                        )
                    )

    for r in rules:
        if not isinstance(r, dict):
            continue
        if str(r.get("template_class", "")) != "LOGICAL_IMPLICATION":
            continue
        trig = r.get("trigger_condition")
        req = r.get("required_condition")
        if not isinstance(req, dict) or req.get("kind") != "atom":
            continue
        var = req.get("variable")
        if not isinstance(var, str) or tiers.get(var) != "derived":
            continue
        if req.get("value") is not True:
            continue
        trigger_holds = _eval_condition(trig, partial)
        required_holds = _eval_atom(req, partial)
        val = (not trigger_holds) or required_holds
        if any(d.variable == var for d in out):
            continue
        out.append(
            DerivedAssignment(
                variable=var,
                sort=sorts.get(var, "bool"),  # type: ignore[arg-type]
                value=val,
                source="strict_eval",
                rationale="material implication on partial world",
            )
        )

    for name in sorted(sorts.keys()):
        if tiers.get(name) != "derived":
            continue
        if any(d.variable == name for d in out):
            continue
        out.append(
            DerivedAssignment(
                variable=name,
                sort=sorts[name],  # type: ignore[arg-type]
                value=default_for_sort(sorts[name]),
                source="strict_eval",
                rationale="derived tier default (no rule output computed)",
            )
        )

    return sorted(out, key=lambda d: d.variable)


__all__ = [
    "build_partial_world",
    "evaluate_derived_strict",
    "evaluate_k_of_n_result",
]
