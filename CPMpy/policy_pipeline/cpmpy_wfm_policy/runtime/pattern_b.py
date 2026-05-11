"""Runtime Pattern B — SAT check with assumptions (Project_Spec §7.2)."""

from __future__ import annotations

import time
from typing import Any

import cpmpy as cp
from cpmpy.solvers.z3 import CPM_z3
from cpmpy.transformations.get_variables import get_variables


class PatternBError(RuntimeError):
    """Solver or state grounding failed."""


def _ground_state(
    expressions: list[Any],
    state: dict[str, int | bool],
) -> list[Any]:
    vs = get_variables(expressions)
    cons: list[Any] = []
    missing: list[str] = []
    for v in vs:
        if v.name in state:
            cons.append(v == state[v.name])
        else:
            missing.append(v.name)
    if missing:
        raise PatternBError(f"missing state keys: {sorted(missing)}")
    return cons


def gate_pattern_b_rules(
    rules: dict[str, Any],
    state: dict[str, int | bool],
    global_constraints: list[Any],
    *,
    solver: str = "z3",
) -> tuple[bool, list[str], float]:
    """
    Evaluate Pattern-B rules jointly: ALLOW iff all rules can hold with state + globals.

    On UNSAT, map Z3 unsat core (assumption literals) back to rule ids when possible;
    otherwise return all *rules* keys as violated (conservative).
    """
    t0 = time.perf_counter()
    if not rules:
        return True, [], (time.perf_counter() - t0) * 1000.0

    g = list(global_constraints)
    exprs = list(rules.values())
    ground = _ground_state(g + exprs, state)
    assums: list[Any] = []
    impl: list[Any] = []
    assump_to_rid: dict[int, str] = {}
    for rid, expr in rules.items():
        a = cp.boolvar(name=f"__patb_assume::{rid}::")
        assums.append(a)
        impl.append(a.implies(expr))
        assump_to_rid[id(a)] = rid

    constraints = g + ground + impl
    m = cp.Model(constraints)
    if solver != "z3":
        raise PatternBError("slice 4 Pattern B requires z3 for unsat cores")
    slv = CPM_z3(m)
    ok = slv.solve(assumptions=assums)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if ok:
        return True, [], elapsed_ms

    violated: list[str] = []
    try:
        core = slv.get_core()
    except Exception:
        violated = sorted(rules.keys())
        return False, violated, elapsed_ms

    for lit in core:
        for a in assums:
            if lit is a:
                violated.append(assump_to_rid[id(a)])
                break
    if not violated:
        violated = sorted(rules.keys())
    return False, sorted(frozenset(violated)), elapsed_ms
