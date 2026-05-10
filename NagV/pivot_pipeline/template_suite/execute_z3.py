"""Execute template instances against the real Z3 encoding (policy + scenario)."""

from __future__ import annotations

from typing import Any

from z3 import Not, Solver, is_false, is_true, sat, unsat

from pivot_pipeline.ir import MetaScheme, Preemption
from pivot_pipeline.template_suite.lower import boundary_worlds
from pivot_pipeline.template_suite.schemas import (
    BoundaryInstance,
    CounterfactualInstance,
    DecisionQueryInstance,
    ObligationInventoryInstance,
    PairwiseInstance,
    RuleAttributionInstance,
    SatUnsatInstance,
    ScenarioInstance,
    TemplateInstance,
)
from pivot_pipeline.z3_compile import _fresh_bool, _int_var, build_solver, encode_rule


def _world_to_z3(sym: dict, sorts: dict[str, str], world: dict[str, int | bool]) -> Any:
    from z3 import And

    parts: list[Any] = []
    for name, val in world.items():
        st = sorts.get(name, "int")
        if st == "bool":
            b = _fresh_bool(sym, sorts, name)
            parts.append(b if val else Not(b))
        else:
            iv = _int_var(sym, sorts, name)
            parts.append(iv == int(val))
    return And(*parts) if parts else True


def _rule_sat_with_world(meta: MetaScheme, world: dict[str, int | bool], rule_id: str) -> str:
    """Whether rule formula is consistent with fixed world (pathway-agnostic; for boundary steps)."""
    by_id = {r.rule_id: r for r in meta.rules}
    if rule_id not in by_id or isinstance(by_id[rule_id], Preemption):
        raise ValueError(f"unknown or preemption rule_id {rule_id!r}")
    sym: dict = {}
    sorts = dict(meta.variable_sorts)
    varprod_bounded: set[str] = set()
    formulas_by_id: dict[str, Any] = {}
    rule = by_id[rule_id]
    f = encode_rule(sym, sorts, rule, formulas_by_id, varprod_bounded)
    solver = Solver()
    wz = _world_to_z3(sym, sorts, world)
    solver.add(wz)
    solver.add(f)
    res = solver.check()
    if res == sat:
        return "satisfied"
    if res == unsat:
        return "unsatisfied"
    return "unknown"


def _decision_label_in_model(model: Any, formulas_by_id: dict, sym: dict, sorts: dict[str, str], query: dict[str, Any]) -> str:
    dm = query.get("decision_metric")
    if dm == "rule":
        rid = query["rule_id"]
        f = formulas_by_id[rid]
        v = model.eval(f, model_completion=True)
        if is_true(v):
            return "satisfied"
        if is_false(v):
            return "unsatisfied"
        return "unknown"
    if dm == "variable":
        vn = query["variable"]
        st = sorts.get(vn, "int")
        if st != "bool":
            raise ValueError(f"decision_metric=variable requires bool sort for {vn!r}, got {st!r}")
        b = _fresh_bool(sym, sorts, vn)
        v = model.eval(b, model_completion=True)
        if is_true(v):
            return "satisfied"
        if is_false(v):
            return "unsatisfied"
        return "unknown"
    raise ValueError(f"unknown decision_metric {dm!r}")


def _satisfied_rule_ids_in_model(
    model: Any,
    formulas_by_id: dict[str, Any],
    meta: MetaScheme,
) -> list[str]:
    by_id = {r.rule_id: r for r in meta.rules}
    out: list[str] = []
    for rid, f in formulas_by_id.items():
        if rid not in by_id:
            continue
        if isinstance(by_id[rid], Preemption):
            continue
        v = model.eval(f, model_completion=True)
        if is_true(v):
            out.append(rid)
    return sorted(out)


def _run_sat(meta: MetaScheme, world: dict[str, int | bool]) -> tuple[str, Any | None, dict[str, Any]]:
    """Return z3 status str, model or None, aux."""
    solver, aux = build_solver(meta)
    sym = aux["symbols"]
    sorts: dict[str, str] = aux["sorts"]
    wz = _world_to_z3(sym, sorts, world)
    solver.push()
    solver.add(wz)
    res = solver.check()
    model = None
    if res == sat:
        model = solver.model()
    solver.pop()
    st = str(res).lower()
    return st, model, aux


def execute_instance(meta: MetaScheme, inst: TemplateInstance) -> dict[str, Any]:
    """Return actual result dict (no golden comparison)."""
    out: dict[str, Any] = {"z3_status": None}

    if isinstance(inst, ScenarioInstance):
        st, model, _aux = _run_sat(meta, inst.world)
        out["z3_status"] = st
        out["sat"] = st == "sat"
        return out

    if isinstance(inst, SatUnsatInstance):
        st, model, _aux = _run_sat(meta, inst.world)
        out["z3_status"] = st
        if st == "sat":
            out["expect_resolved"] = "sat"
        elif st == "unsat":
            out["expect_resolved"] = "unsat"
        else:
            out["expect_resolved"] = "unknown"
        return out

    if isinstance(inst, DecisionQueryInstance):
        st, model, aux = _run_sat(meta, inst.world)
        out["z3_status"] = st
        if st != "sat":
            out["decision"] = None
            return out
        assert model is not None
        out["decision"] = _decision_label_in_model(model, aux["formulas_by_id"], aux["symbols"], aux["sorts"], inst.query)
        return out

    if isinstance(inst, RuleAttributionInstance):
        st, model, aux = _run_sat(meta, inst.world)
        out["z3_status"] = st
        if st != "sat":
            out["decision"] = None
            out["rule_ids"] = []
            return out
        assert model is not None
        out["decision"] = _decision_label_in_model(model, aux["formulas_by_id"], aux["symbols"], aux["sorts"], inst.query)
        out["rule_ids"] = _satisfied_rule_ids_in_model(model, aux["formulas_by_id"], meta)
        return out

    if isinstance(inst, BoundaryInstance):
        worlds = boundary_worlds(inst)
        decisions: list[str] = []
        for wm in worlds:
            st, model, aux = _run_sat(meta, wm)
            dm = inst.query.get("decision_metric")
            if dm == "rule":
                rid = inst.query["rule_id"]
                if st == "sat" and model is not None:
                    decisions.append(
                        _decision_label_in_model(model, aux["formulas_by_id"], aux["symbols"], aux["sorts"], inst.query)
                    )
                else:
                    decisions.append(_rule_sat_with_world(meta, wm, rid))
            else:
                if st != "sat" or model is None:
                    decisions.append("unknown")
                else:
                    decisions.append(
                        _decision_label_in_model(model, aux["formulas_by_id"], aux["symbols"], aux["sorts"], inst.query)
                    )
        out["z3_status"] = "sat"
        out["decisions"] = decisions
        return out

    if isinstance(inst, CounterfactualInstance):
        st_b, model_b, aux_b = _run_sat(meta, inst.world_base)
        out["z3_status_base"] = st_b
        st_m, model_m, aux_m = _run_sat(meta, inst.world_mutant)
        out["z3_status_mutant"] = st_m
        d0 = d1 = None
        if st_b == "sat" and model_b is not None:
            d0 = _decision_label_in_model(model_b, aux_b["formulas_by_id"], aux_b["symbols"], aux_b["sorts"], inst.query)
        if st_m == "sat" and model_m is not None:
            d1 = _decision_label_in_model(model_m, aux_m["formulas_by_id"], aux_m["symbols"], aux_m["sorts"], inst.query)
        out["base_decision"] = d0
        out["mutant_decision"] = d1
        return out

    if isinstance(inst, ObligationInventoryInstance):
        st, model, aux = _run_sat(meta, inst.world)
        out["z3_status"] = st
        ob: list[dict[str, Any]] = []
        if meta.evaluation_pathways:
            for rid in meta.evaluation_pathways[0].must_satisfy_all:
                ob.append({"key": rid, "args": []})
        ob.sort(key=lambda x: x["key"])
        out["obligations"] = ob
        return out

    if isinstance(inst, PairwiseInstance):
        wa = {**inst.world, **inst.query_a}
        wb = {**inst.world, **inst.query_b}
        st_a, model_a, aux_a = _run_sat(meta, wa)
        st_b, model_b, aux_b = _run_sat(meta, wb)
        out["z3_status_a"] = st_a
        out["z3_status_b"] = st_b
        da = db = None
        if st_a == "sat" and model_a is not None:
            da = _decision_label_in_model(model_a, aux_a["formulas_by_id"], aux_a["symbols"], aux_a["sorts"], inst.query)
        if st_b == "sat" and model_b is not None:
            db = _decision_label_in_model(model_b, aux_b["formulas_by_id"], aux_b["symbols"], aux_b["sorts"], inst.query)
        out["decision_a"] = da
        out["decision_b"] = db
        return out

    raise TypeError(inst)
