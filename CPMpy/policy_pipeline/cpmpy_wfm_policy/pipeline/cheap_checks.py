"""Cheap verification: direct eval (scalar) vs solver (global / vector routing)."""

from __future__ import annotations

from typing import Any

import cpmpy as cp
from cpmpy.transformations.get_variables import get_variables

from cpmpy_wfm_policy.runtime.pattern_a import PatternAEvaluationError, evaluate_boolean_expr


class CheapCheckError(RuntimeError):
    """Per-rule cheap checks failed."""


def _state_equalities(
    expressions: list[Any],
    state: dict[str, int | bool],
) -> list[Any]:
    """Equality constraints for every variable occurring in *expressions* with a *state* key."""
    vs = get_variables(expressions)
    cons: list[Any] = []
    for v in vs:
        if v.name in state:
            cons.append(v == state[v.name])
    missing = [v.name for v in vs if v.name not in state]
    if missing:
        raise CheapCheckError(f"missing state keys: {sorted(missing)}")
    return cons


def rule_non_trivial_scalar(expr: Any) -> None:
    """
    §5.1.3: both rule and ~rule should be satisfiable (non-tautology, non-contradiction).
    """
    m1 = cp.Model([expr])
    if not m1.solve():
        raise CheapCheckError("rule is unsatisfiable (equivalent to false everywhere)")
    m2 = cp.Model([~expr])
    if not m2.solve():
        raise CheapCheckError("rule is a tautology (equivalent to true everywhere)")


def rule_non_trivial_global(expr: Any, global_constraints: list[Any]) -> None:
    """Non-triviality with optional signature-level globals."""
    g = list(global_constraints)
    m1 = cp.Model(g + [expr])
    if not m1.solve():
        raise CheapCheckError("rule is unsatisfiable (equivalent to false everywhere)")
    m2 = cp.Model(g + [~expr])
    if not m2.solve():
        raise CheapCheckError("rule is a tautology (equivalent to true everywhere)")


def run_direct_eval_fixtures(
    expr: Any,
    fixtures: list[tuple[dict[str, int | bool], bool]],
) -> None:
    """§5.1.1 direct substitution path for scalar non-global rules."""
    for i, (state, expected) in enumerate(fixtures):
        try:
            got = evaluate_boolean_expr(expr, state)
        except PatternAEvaluationError as e:
            raise CheapCheckError(f"fixture {i}: evaluation error: {e}") from e
        if got != expected:
            raise CheapCheckError(
                f"fixture {i}: expected boolean {expected!r}, got {got!r}; state keys={sorted(state)}"
            )


def run_global_solver_fixtures(
    expr: Any,
    *,
    global_constraints: list[Any] | None,
    fixtures: list[tuple[dict[str, int | bool], bool]],
) -> None:
    """
    §5.1.1 CONFLICT path: ground state, check SAT of (globals ∧ state ∧ expr) matches *expected*.
    """
    g = list(global_constraints or [])
    for i, (state, expected) in enumerate(fixtures):
        ground = _state_equalities(g + [expr], state)
        sat_rule = cp.Model(g + ground + [expr]).solve()
        if expected and not sat_rule:
            raise CheapCheckError(
                f"fixture {i}: expected rule satisfiable under state, got UNSAT; keys={sorted(state)}"
            )
        if (not expected) and sat_rule:
            raise CheapCheckError(
                f"fixture {i}: expected rule unsatisfiable under state, got SAT; keys={sorted(state)}"
            )


def run_scalar_cheap_checks(
    expr: Any,
    *,
    fixtures: list[tuple[dict[str, int | bool], bool]] | None = None,
    run_nontrivial: bool = True,
) -> None:
    """Pattern A / scalar path: direct eval + optional non-triviality."""
    if run_nontrivial:
        rule_non_trivial_scalar(expr)
    if fixtures:
        run_direct_eval_fixtures(expr, fixtures)


def run_global_cheap_checks(
    expr: Any,
    *,
    global_constraints: list[Any] | None = None,
    fixtures: list[tuple[dict[str, int | bool], bool]] | None = None,
    run_nontrivial: bool = True,
) -> None:
    """Pattern B path: solver-based fixtures + non-triviality with optional globals."""
    if run_nontrivial:
        rule_non_trivial_global(expr, list(global_constraints or []))
    if fixtures:
        run_global_solver_fixtures(
            expr, global_constraints=global_constraints, fixtures=fixtures
        )


def run_routed_cheap_checks(
    expr: Any,
    *,
    pattern: str,
    global_constraints: list[Any] | None = None,
    fixtures: list[tuple[dict[str, int | bool], bool]] | None = None,
    run_nontrivial: bool = True,
) -> None:
    """Dispatch by manifest routing flag (A = scalar, B = solver)."""
    if pattern == "A":
        run_scalar_cheap_checks(expr, fixtures=fixtures, run_nontrivial=run_nontrivial)
    elif pattern == "B":
        run_global_cheap_checks(
            expr,
            global_constraints=global_constraints,
            fixtures=fixtures,
            run_nontrivial=run_nontrivial,
        )
    else:
        raise CheapCheckError(f"unknown pattern {pattern!r}")
