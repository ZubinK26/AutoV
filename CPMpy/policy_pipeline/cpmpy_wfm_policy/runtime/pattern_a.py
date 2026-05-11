"""Runtime: Pattern A — fast scalar / non-global evaluation (see Project_Spec §7.1)."""

from __future__ import annotations

import time
from typing import Any

import cpmpy as cp
from cpmpy.transformations.get_variables import get_variables


class PatternAEvaluationError(RuntimeError):
    """State substitution or solve failed."""


def evaluate_boolean_expr(expr: Any, state: dict[str, int | bool]) -> bool:
    """
    Ground every decision variable occurring in *expr* from *state* (by ``var.name``)
    and return the truth value of *expr*.
    """
    m = cp.Model()
    for v in get_variables(expr):
        name = v.name
        if name not in state:
            raise PatternAEvaluationError(f"missing state key for variable {name!r}")
        m += v == state[name]
    ok = m.solve()
    if not ok:
        raise PatternAEvaluationError("state is inconsistent with variable domains or over-constrained")
    val = expr.value()
    if val is None:
        raise PatternAEvaluationError("expression has no value after solve")
    return bool(val)


def gate_scalar_rules(
    rules: dict[str, Any],
    state: dict[str, int | bool],
) -> tuple[bool, list[str], float]:
    """
    Evaluate each rule expression; return (allowed, violated_rule_ids, elapsed_s).

    *rules* maps rule_id -> CPMpy boolean expression (no global constraints).
    """
    t0 = time.perf_counter()
    violated: list[str] = []
    for rid, expr in rules.items():
        if not evaluate_boolean_expr(expr, state):
            violated.append(rid)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return len(violated) == 0, violated, elapsed_ms
