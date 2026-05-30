"""Explain compatible / incompatible policy case results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from z3 import unsat

from pivot_pipeline.external_tester.schemas import (
    PolicyCaseExplanationV1,
    PolicyCaseWorldV1,
    PolicyQueryResultV1,
    UnsatCoreRule,
)
from pivot_pipeline.external_tester.world_to_z3 import build_query_world
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.template_suite.execute_z3 import _world_to_z3
from pivot_pipeline.z3_compile import build_solver_tracked


def _linearized_index(work_dir: Path) -> dict[str, str]:
    idx: dict[str, str] = {}
    for name in (
        "linearized_model_for_assessment.txt",
        "linearized_model_for_cross_critic.txt",
    ):
        path = work_dir / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or " | " not in line:
                continue
            rid = line.split(" | ", 1)[0].strip()
            if rid and rid not in idx:
                idx[rid] = line
    return idx


def _rules_from_unsat_core(aux: dict, core: Any) -> list[str]:
    trackers = aux.get("trackers") or {}
    tracker_to_rule = aux.get("tracker_to_rule") or {}
    seen: list[str] = []
    for key, tracker in trackers.items():
        if tracker in core:
            rid = tracker_to_rule.get(key, key)
            if rid not in seen and rid != "__varprod_box__":
                seen.append(rid)
    return seen


def build_explanation(
    *,
    work_dir: Path,
    meta: MetaScheme,
    world: PolicyCaseWorldV1,
    query: PolicyQueryResultV1,
    complete_world: dict[str, int | bool] | None = None,
) -> PolicyCaseExplanationV1:
    work_dir = work_dir.resolve()
    complete = complete_world
    if complete is None:
        complete, defaulted, _ = build_query_world(world, meta)
    else:
        _, defaulted, _ = build_query_world(world, meta)

    compat = query.compatibility
    note = ""
    if defaulted:
        note = f"{len(defaulted)} variables assumed false/0 at query (CWA)"

    if compat == "compatible":
        return PolicyCaseExplanationV1(
            compatibility=compat,
            witness=dict(complete),
            defaulted_variables=defaulted,
            note=note,
        )

    if compat == "incompatible":
        solver, aux = build_solver_tracked(meta)
        sym = aux["symbols"]
        sorts: dict[str, str] = aux["sorts"]
        solver.add(_world_to_z3(sym, sorts, complete))
        res = solver.check()
        unsat_rules: list[UnsatCoreRule] = []
        if res == unsat:
            core = solver.unsat_core()
            lin = _linearized_index(work_dir)
            for rid in _rules_from_unsat_core(aux, core):
                unsat_rules.append(
                    UnsatCoreRule(rule_id=rid, linearized=lin.get(rid, "")),
                )
        return PolicyCaseExplanationV1(
            compatibility=compat,
            unsat_core_rules=unsat_rules,
            defaulted_variables=defaulted,
            note=note,
        )

    return PolicyCaseExplanationV1(
        compatibility=compat,
        defaulted_variables=defaulted,
        note=note or "Z3 returned unknown",
    )


def write_explanation(work_dir: Path, explanation: PolicyCaseExplanationV1) -> Path:
    path = work_dir / "policy_case_explanation.json"
    path.write_text(
        json.dumps(explanation.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


__all__ = ["build_explanation", "write_explanation"]
