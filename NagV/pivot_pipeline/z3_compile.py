"""Z3 encoding for MetaScheme v1 (QF_LIA-ish: Int/Bool vars)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import time

from z3 import And, Bool, Implies, Int, Not, Or, PbEq, PbLe, Solver, is_true, sat, unknown, unsat

from pivot_pipeline.ir import (
    ArithmeticEvaluation,
    AtomicRule,
    ConditionAtom,
    ConditionAnd,
    ConditionExpr,
    ConditionNot,
    ConditionOr,
    ConditionVarCmp,
    ConditionVarProductCmp,
    ConstantRelational,
    ExclusiveChoice,
    ExclusiveChoiceMode,
    InclusionOperator,
    LogicalIff,
    LogicalImplication,
    MathOperator,
    MetaScheme,
    Preemption,
    PreemptionAction,
    RelationalOperator,
    SetInclusion,
    VarProdRhsConst,
    VarProdRhsVar,
    VariableRelational,
    Yields,
)
from pivot_pipeline.var_product_validate import product_int_cap


def _fresh_bool(sym: dict[str, Any], sorts: dict[str, str], name: str) -> Any:
    sorts[name] = "bool"
    if name not in sym:
        sym[name] = Bool(name)
    return sym[name]


def _int_var(sym: dict[str, Any], sorts: dict[str, str], name: str) -> Any:
    if sorts.get(name) == "bool":
        return _fresh_bool(sym, sorts, name)
    if name not in sym:
        sym[name] = Int(name)
    return sym[name]


def _scalar_to_z3(sym: dict[str, Any], sorts: dict[str, str], v: Any) -> Any:
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        return _int_var(sym, sorts, v)
    raise TypeError(v)


def _rel(op: RelationalOperator, a: Any, b: Any) -> Any:
    if op == RelationalOperator.EQ:
        return a == b
    if op == RelationalOperator.NEQ:
        return a != b
    if op == RelationalOperator.GT:
        return a > b
    if op == RelationalOperator.LT:
        return a < b
    if op == RelationalOperator.GTE:
        return a >= b
    if op == RelationalOperator.LTE:
        return a <= b
    raise ValueError(op)


def encode_condition(
    sym: dict[str, Any],
    sorts: dict[str, str],
    c: ConditionExpr,
    varprod_bounded: set[str],
) -> Any:
    k = c.kind  # type: ignore[union-attr]
    if k == "atom":
        ca = c  # type: ignore[assignment]
        assert isinstance(ca, ConditionAtom)
        v = _int_var(sym, sorts, ca.variable)
        rhs = ca.value
        rhs_e = _int_var(sym, sorts, rhs) if isinstance(rhs, str) else _scalar_to_z3(sym, sorts, rhs)
        return _rel(ca.operator, v, rhs_e)
    if k == "varcmp":
        cv = c  # type: ignore[assignment]
        assert isinstance(cv, ConditionVarCmp)
        a = _int_var(sym, sorts, cv.left_variable)
        b = _int_var(sym, sorts, cv.right_variable)
        return _rel(cv.operator, a, b)
    if k == "varprod_cmp":
        cp = c  # type: ignore[assignment]
        assert isinstance(cp, ConditionVarProductCmp)
        a = _int_var(sym, sorts, cp.left_variable)
        b = _int_var(sym, sorts, cp.right_variable)
        varprod_bounded.add(cp.left_variable)
        varprod_bounded.add(cp.right_variable)
        rhs_m = cp.rhs
        if isinstance(rhs_m, VarProdRhsConst):
            rhs_e: Any = int(rhs_m.value)
        else:
            assert isinstance(rhs_m, VarProdRhsVar)
            rhs_e = _int_var(sym, sorts, rhs_m.variable)
            varprod_bounded.add(rhs_m.variable)
        return _rel(cp.operator, a * b, rhs_e)
    if k == "and":
        ca = c  # type: ignore[assignment]
        assert isinstance(ca, ConditionAnd)
        return And(*[encode_condition(sym, sorts, ch, varprod_bounded) for ch in ca.children])
    if k == "or":
        co = c  # type: ignore[assignment]
        assert isinstance(co, ConditionOr)
        return Or(*[encode_condition(sym, sorts, ch, varprod_bounded) for ch in co.children])
    if k == "not":
        cn = c  # type: ignore[assignment]
        assert isinstance(cn, ConditionNot)
        return Not(encode_condition(sym, sorts, cn.child, varprod_bounded))
    raise ValueError(k)


def _maybe_not(pos: Any, y: Yields) -> Any:
    return pos if y == Yields.SATISFIED else Not(pos)


def encode_rule(
    sym: dict[str, Any],
    sorts: dict[str, str],
    rule: AtomicRule,
    formulas_by_id: dict[str, Any],
    varprod_bounded: set[str],
) -> Any:
    if isinstance(rule, ConstantRelational):
        v = _int_var(sym, sorts, rule.variable)
        rhs = rule.constant_value
        rhs_e = _int_var(sym, sorts, rhs) if isinstance(rhs, str) else _scalar_to_z3(sym, sorts, rhs)
        return _maybe_not(_rel(rule.relational_operator, v, rhs_e), rule.yields)
    if isinstance(rule, VariableRelational):
        a = _int_var(sym, sorts, rule.left_variable)
        b = _int_var(sym, sorts, rule.right_variable)
        return _maybe_not(_rel(rule.relational_operator, a, b), rule.yields)
    if isinstance(rule, SetInclusion):
        v = _int_var(sym, sorts, rule.variable)
        parts = []
        for item in rule.constant_array:
            rhs = _int_var(sym, sorts, item) if isinstance(item, str) else _scalar_to_z3(sym, sorts, item)
            parts.append(v == rhs)
        inner = Or(*parts) if parts else False
        if rule.inclusion_operator == InclusionOperator.IN:
            return _maybe_not(inner, rule.yields)
        return _maybe_not(Not(inner), rule.yields)
    if isinstance(rule, ArithmeticEvaluation):
        a = _int_var(sym, sorts, rule.operand_1)
        rhs = _scalar_to_z3(sym, sorts, rule.operand_2)
        if rule.math_operator == MathOperator.ADD:
            expr = a + rhs
        elif rule.math_operator == MathOperator.SUBTRACT:
            expr = a - rhs
        elif rule.math_operator == MathOperator.MULTIPLY:
            expr = a * rhs
        elif rule.math_operator == MathOperator.DIVIDE:
            expr = a / rhs
        else:
            raise ValueError(rule.math_operator)
        lim = (
            _int_var(sym, sorts, str(rule.target_limit))
            if isinstance(rule.target_limit, str)
            else _scalar_to_z3(sym, sorts, rule.target_limit)
        )
        return _maybe_not(_rel(rule.relational_operator, expr, lim), rule.yields)
    if isinstance(rule, LogicalImplication):
        return Implies(
            encode_condition(sym, sorts, rule.trigger_condition, varprod_bounded),
            encode_condition(sym, sorts, rule.required_condition, varprod_bounded),
        )
    if isinstance(rule, LogicalIff):
        a = encode_condition(sym, sorts, rule.left, varprod_bounded)
        b = encode_condition(sym, sorts, rule.right, varprod_bounded)
        return a == b
    if isinstance(rule, ExclusiveChoice):
        for name in rule.variables:
            _fresh_bool(sym, sorts, name)
        bs = tuple(_fresh_bool(sym, sorts, name) for name in rule.variables)
        args = tuple((b, 1) for b in bs)
        if rule.mode == ExclusiveChoiceMode.EXACTLY_ONE:
            return PbEq(args, 1)
        if rule.mode == ExclusiveChoiceMode.AT_MOST_ONE:
            return PbLe(args, 1)
        raise ValueError(rule.mode)
    if isinstance(rule, Preemption):
        if rule.target_rule_id is None:
            return True
        core = encode_condition(sym, sorts, rule.preempting_condition, varprod_bounded)
        target_f = formulas_by_id.get(rule.target_rule_id)
        if target_f is None:
            raise KeyError(
                f"PREEMPTION {rule.rule_id!r}: missing formula for target_rule_id {rule.target_rule_id!r}"
            )
        if rule.action == PreemptionAction.FORCE_SATISFIED:
            return Implies(core, target_f)
        if rule.action == PreemptionAction.FORCE_UNSATISFIED:
            return Implies(core, Not(target_f))
        if rule.action == PreemptionAction.BYPASS_RULE:
            return True
        raise ValueError(rule.action)
    raise TypeError(rule)


def _validate_preemption_targets(
    meta: MetaScheme,
    *,
    formulas_by_id: dict[str, Any],
    by_id: dict[str, AtomicRule],
    sym: dict[str, Any],
    sorts: dict[str, str],
    varprod_bounded: set[str],
) -> dict[str, list[Any]]:
    """
    Ensure each PREEMPTION with a target references a non-PREEMPTION rule_id.
    Return map: target_rule_id -> list of Z3 expressions (preempting conditions) for BYPASS_RULE.
    """
    bypass_by_target: dict[str, list[Any]] = defaultdict(list)
    for r in meta.rules:
        if not isinstance(r, Preemption) or not r.target_rule_id:
            continue
        tid = r.target_rule_id
        if tid not in formulas_by_id:
            raise KeyError(
                f"PREEMPTION rule {r.rule_id!r} references unknown target_rule_id {tid!r} — "
                f"it must equal the rule_id of another rule in this policy (not a symbolic label)."
            )
        if isinstance(by_id[tid], Preemption):
            raise ValueError(
                f"PREEMPTION {r.rule_id!r}: target_rule_id {tid!r} must not name another PREEMPTION rule."
            )
        if r.action == PreemptionAction.BYPASS_RULE:
            bypass_by_target[tid].append(encode_condition(sym, sorts, r.preempting_condition, varprod_bounded))
        elif r.action not in (
            PreemptionAction.FORCE_SATISFIED,
            PreemptionAction.FORCE_UNSATISFIED,
        ):
            raise ValueError(r.action)
    return bypass_by_target


def _pathway_formula(
    rid: str,
    *,
    base_phi: Any,
    rule: AtomicRule,
    formulas_by_id: dict[str, Any],
    bypass_by_target: dict[str, list[Any]],
) -> Any:
    """Apply applies_to scoping, then BYPASS_OR disjuncts for this rule (if any)."""
    phi = base_phi
    if rule.applies_to != "GLOBAL":
        pre = formulas_by_id.get(rule.applies_to)
        if pre is None:
            raise KeyError(f"pathway rule {rid!r}: applies_to missing formula for {rule.applies_to!r}")
        phi = Implies(pre, phi)
    for core in bypass_by_target.get(rid, []):
        phi = Or(core, phi)
    return phi


def build_solver(meta: MetaScheme) -> tuple[Solver, dict[str, Any]]:
    sym: dict[str, Any] = {}
    sorts = dict(meta.variable_sorts)
    by_id: dict[str, AtomicRule] = {r.rule_id: r for r in meta.rules}
    formulas_by_id: dict[str, Any] = {}
    varprod_bounded: set[str] = set()

    for rid, r in by_id.items():
        if isinstance(r, Preemption):
            continue
        formulas_by_id[rid] = encode_rule(sym, sorts, r, formulas_by_id, varprod_bounded)

    bypass_by_target = _validate_preemption_targets(
        meta,
        formulas_by_id=formulas_by_id,
        by_id=by_id,
        sym=sym,
        sorts=sorts,
        varprod_bounded=varprod_bounded,
    )

    for rid, r in by_id.items():
        if isinstance(r, Preemption):
            formulas_by_id[rid] = encode_rule(sym, sorts, r, formulas_by_id, varprod_bounded)

    pathway_exprs: list[Any] = []
    for pw in meta.evaluation_pathways:
        conjuncts: list[Any] = []
        for rid in pw.must_satisfy_all:
            if rid not in formulas_by_id:
                raise KeyError(f"pathway references unknown rule {rid!r}")
            r = by_id[rid]
            phi = _pathway_formula(
                rid,
                base_phi=formulas_by_id[rid],
                rule=r,
                formulas_by_id=formulas_by_id,
                bypass_by_target=bypass_by_target,
            )
            conjuncts.append(phi)
        for rid in pw.must_not_trigger:
            if rid in formulas_by_id:
                r = by_id[rid]
                phi = _pathway_formula(
                    rid,
                    base_phi=formulas_by_id[rid],
                    rule=r,
                    formulas_by_id=formulas_by_id,
                    bypass_by_target=bypass_by_target,
                )
                conjuncts.append(Not(phi))
        pathway_exprs.append(And(*conjuncts) if conjuncts else True)

    base = Or(*pathway_exprs) if pathway_exprs else False
    prem: list[Any] = []
    for r in meta.rules:
        if isinstance(r, Preemption) and r.rule_id in formulas_by_id:
            prem.append(formulas_by_id[r.rule_id])
    pol = And(base, *prem) if prem else base
    cap = product_int_cap()
    if varprod_bounded:
        box = And(
            *[
                And(_int_var(sym, sorts, name) >= 0, _int_var(sym, sorts, name) <= cap)
                for name in sorted(varprod_bounded)
            ]
        )
        pol = And(pol, box)
    solver = Solver()
    solver.add(pol)
    return solver, {"symbols": sym, "policy": pol, "formulas_by_id": formulas_by_id, "sorts": sorts}


def run_z3_check(meta: MetaScheme) -> dict[str, Any]:
    """Single solver check plus timing, optional model verification, and solver statistics."""
    t0 = time.perf_counter()
    solver, aux = build_solver(meta)
    pol = aux["policy"]
    res = solver.check()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    out: dict[str, Any] = {
        "status": str(res).lower(),
        "elapsed_ms": round(elapsed_ms, 3),
    }
    if res == sat:
        m = solver.model()
        vs = {str(v): str(m[v]) for v in m}
        out["model_excerpt"] = str(vs)[:2000]
        try:
            ev = m.eval(pol, model_completion=True)
            out["model_verified"] = bool(is_true(ev))
        except Exception as ex:
            out["model_verified"] = False
            out["model_verify_error"] = str(ex)
    elif res == unsat:
        out["unsat"] = True
    elif res == unknown:
        out["unknown"] = True
        try:
            ru = solver.reason_unknown()
            if ru:
                out["reason_unknown_detail"] = str(ru)
        except Exception:
            pass

    try:
        st = solver.statistics()
        if st is not None:
            out["statistics"] = str(st)
    except Exception:
        pass

    return out
