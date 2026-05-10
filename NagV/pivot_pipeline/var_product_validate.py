"""Validate `varprod_cmp` rules against the v1 variable×variable product contract."""

from __future__ import annotations

import os

from pivot_pipeline.constants import DEFAULT_PIVOT_PRODUCT_INT_CAP
from pivot_pipeline.ir import (
    AtomicRule,
    ConditionAnd,
    ConditionExpr,
    ConditionNot,
    ConditionOr,
    ConditionVarProductCmp,
    ExclusiveChoice,
    LogicalIff,
    LogicalImplication,
    Preemption,
)


def product_int_cap() -> int:
    raw = os.environ.get("PIVOT_PRODUCT_INT_CAP", "").strip()
    if not raw:
        return DEFAULT_PIVOT_PRODUCT_INT_CAP
    try:
        n = int(raw, 10)
    except ValueError:
        return DEFAULT_PIVOT_PRODUCT_INT_CAP
    return max(1, min(n, DEFAULT_PIVOT_PRODUCT_INT_CAP * 100))


def _bool_like_variable_names(rules: list[AtomicRule]) -> set[str]:
    found: set[str] = set()
    for r in rules:
        if isinstance(r, ExclusiveChoice):
            found.update(r.variables)
    return found


def _iter_condition_nodes(expr: ConditionExpr):
    yield expr
    k = expr.kind  # type: ignore[union-attr]
    if k in ("and", "or"):
        for ch in expr.children:  # type: ignore[union-attr]
            yield from _iter_condition_nodes(ch)
    elif k == "not":
        yield from _iter_condition_nodes(expr.child)  # type: ignore[union-attr]


def _conditions_in_rule(rule: AtomicRule) -> list[ConditionExpr]:
    out: list[ConditionExpr] = []
    if isinstance(rule, LogicalImplication):
        for c in _iter_condition_nodes(rule.trigger_condition):
            out.append(c)
        for c in _iter_condition_nodes(rule.required_condition):
            out.append(c)
    elif isinstance(rule, Preemption):
        for c in _iter_condition_nodes(rule.preempting_condition):
            out.append(c)
    elif isinstance(rule, LogicalIff):
        for c in _iter_condition_nodes(rule.left):
            out.append(c)
        for c in _iter_condition_nodes(rule.right):
            out.append(c)
    return out


def _count_varprod(rule: AtomicRule) -> int:
    return sum(1 for c in _conditions_in_rule(rule) if isinstance(c, ConditionVarProductCmp))


def _varprod_vars(node: ConditionVarProductCmp) -> set[str]:
    names = {node.left_variable, node.right_variable}
    rhs = node.rhs
    k = rhs.kind  # type: ignore[union-attr]
    if k == "var":
        names.add(rhs.variable)  # type: ignore[union-attr]
    return names


def validate_var_product_rules(rules: list[AtomicRule], *, rule_label: str = "rules") -> None:
    """
    Fail closed when `varprod_cmp` violates contract (counts, bool vars, sort hints).

    Call after Pydantic parse of each rule, before :func:`build_meta_scheme`.
    """
    bool_names = _bool_like_variable_names(rules)

    for r in rules:
        rid = r.rule_id
        n = _count_varprod(r)
        if n == 0:
            continue
        if n > 1:
            raise ValueError(
                f"{rid}: at most one varprod_cmp per rule ({rule_label}; found {n}). "
                "Use a single product comparison or split across rules."
            )

        for c in _conditions_in_rule(r):
            if not isinstance(c, ConditionVarProductCmp):
                continue
            for v in _varprod_vars(c):
                if not v.strip():
                    raise ValueError(f"{rid}: varprod_cmp variable name must be non-empty")
                if v in bool_names:
                    raise ValueError(
                        f"{rid}: varprod_cmp variable {v!r} is an EXCLUSIVE_CHOICE (bool) variable; "
                        "factors and rhs must be int-like slugs, not boolean choice fields."
                    )
