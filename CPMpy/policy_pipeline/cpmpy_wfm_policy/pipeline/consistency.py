"""Pre-deployment consistency + tool coverage (Project_Spec §5.3.2–§5.3.3, §6)."""

from __future__ import annotations

import os
from typing import Any

import cpmpy as cp


class ConsistencyError(RuntimeError):
    """Joint SAT failure or required coverage missing."""


def _conjoin(exprs: list[Any]) -> Any:
    if not exprs:
        return True
    if len(exprs) == 1:
        return exprs[0]
    return cp.all(exprs)


def run_pre_deploy_consistency(
    *,
    rule_exprs: list[Any],
    rule_ids: list[str],
    global_constraints: list[Any] | None = None,
    gated_tools: list[str],
    solver: str | None = None,
    run_pairwise: bool | None = None,
) -> dict[str, Any]:
    if len(rule_exprs) != len(rule_ids):
        raise ValueError("rule_exprs and rule_ids length mismatch")
    g = list(global_constraints or [])

    joint = cp.Model(g + list(rule_exprs))
    joint_sat = bool(joint.solve(solver=solver))
    if not joint_sat:
        raise ConsistencyError(
            "joint model UNSAT — policy rules contradict each other or globals"
        )

    reach: dict[str, dict[str, bool]] = {}
    warnings: list[str] = []
    for rid, ex in zip(rule_ids, rule_exprs, strict=True):
        ok = bool(cp.Model(g + [ex]).solve(solver=solver))
        reach[rid] = {"reachable": ok}
        if not ok:
            warnings.append(f"rule {rid!r} unreachable (dead under globals)")

    conjoined = _conjoin(rule_exprs)
    legal_exists = joint_sat
    illegal_exists = bool(cp.Model(g + [~conjoined]).solve(solver=solver))

    coverage: dict[str, dict[str, bool]] = {}
    if gated_tools:
        for tname in gated_tools:
            coverage[tname] = {
                "legal_exists": legal_exists,
                "illegal_exists": illegal_exists,
            }

    missing_illegal = [k for k, v in coverage.items() if not v["illegal_exists"]]
    missing_legal = [k for k, v in coverage.items() if not v["legal_exists"]]
    if gated_tools:
        if missing_legal:
            raise ConsistencyError(
                f"coverage: no legal state for gated tools {missing_legal!r}"
            )
        if missing_illegal:
            raise ConsistencyError(
                f"coverage: no illegal state for gated tools {missing_illegal!r} "
                "(every rule forced true — policy never blocks)"
            )

    if run_pairwise is None:
        run_pairwise = os.environ.get("CPMPY_PAIRWISE_CONSISTENCY", "").strip() in (
            "1",
            "true",
            "yes",
        )

    pairwise_block: dict[str, Any] | None = None
    if run_pairwise:
        pairwise_block = {
            "status": "not_implemented",
            "note": "Contradictory pairwise verdict check deferred; enablement is CI-only per spec §6.",
        }

    return {
        "joint_sat": joint_sat,
        "per_rule_reachability": reach,
        "warnings": warnings,
        "coverage": coverage if coverage else None,
        "pairwise": pairwise_block,
    }
