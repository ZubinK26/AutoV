"""Medium-tier verification: cumulative SAT + Hypothesis smoke (slice 6)."""

from __future__ import annotations

from typing import Any

import cpmpy as cp

from cpmpy_wfm_policy.runtime.pattern_a import PatternAEvaluationError, evaluate_boolean_expr


class MediumCheckError(RuntimeError):
    """Medium-tier verification failed."""


def run_cumulative_model_sat(
    rule_exprs: list[Any],
    global_constraints: list[Any] | None = None,
) -> None:
    """
    §5.2.3 — joint satisfiability of all formalized rules (+ optional globals).
    """
    g = list(global_constraints or [])
    m = cp.Model(g + list(rule_exprs))
    if not m.solve():
        raise MediumCheckError("cumulative model UNSAT (rules contradict each other or globals)")


def run_hypothesis_smoke_pattern_a(
    rules_by_id: dict[str, Any],
    *,
    state_strategy: Any,
    num_examples: int,
) -> None:
    """
    Draw *num_examples* states and evaluate Pattern-A rules (no SAT globals).
    Skips draws that under-specify variables (``PatternAEvaluationError``).
    """
    for _ in range(num_examples):
        state: dict[str, Any] = state_strategy.example()
        for _rid, expr in rules_by_id.items():
            try:
                evaluate_boolean_expr(expr, state)
            except PatternAEvaluationError:
                continue


def run_mutation_flip_dependency_smoke(
    expr: Any,
    *,
    state_when_true: dict[str, int | bool],
    critical_field: str,
    alternative_value: int | bool,
    pattern: str = "A",
) -> None:
    """
    Minimal mutation sanity: with *state_when_true*, rule is True; flip *critical_field*
    to *alternative_value* and expect rule False (Pattern A only).
    """
    if pattern != "A":
        return
    if not evaluate_boolean_expr(expr, state_when_true):
        raise MediumCheckError("mutation smoke requires state_when_true to satisfy the rule")
    st2 = dict(state_when_true)
    st2[critical_field] = alternative_value
    if evaluate_boolean_expr(expr, st2):
        raise MediumCheckError(
            f"expected mutation of {critical_field!r} to falsify rule; still True"
        )
