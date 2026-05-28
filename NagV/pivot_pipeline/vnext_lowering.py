"""Deterministic lowering of vNext expansion templates to core Pivot IR (v1)."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from pivot_pipeline.ir import (
    _RULE_MODEL_BY_TEMPLATE,
    ConditionAnd,
    ConditionAtom,
    ConditionExpr,
    ConditionNot,
    ConditionOr,
    RelationalOperator,
    Yields,
)
from pivot_pipeline.ir_vnext import (
    VNEXT_TEMPLATE_CLASSES,
    BoundedForall,
    DecisionTableRow,
    DefinedAs,
    ExhaustiveSwitch,
    IntRange,
    KOfN,
    SumThreshold,
    TableBlock,
    validate_vnext_rule_dict,
)


@dataclass
class LoweringStats:
    """Counts of expansion rules lowered (for run_summary / debugging)."""

    by_template: dict[str, int] = field(default_factory=dict)
    core_rules_emitted: int = 0

    def record(self, template_class: str, *, emitted: int) -> None:
        self.by_template[template_class] = self.by_template.get(template_class, 0) + 1
        self.core_rules_emitted += emitted

    def as_dict(self) -> dict[str, Any]:
        return {
            "pivot_ir_extensions": "vnext_8",
            "by_template": dict(self.by_template),
            "core_rules_emitted": self.core_rules_emitted,
        }


def _dump_rule(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _rid(base: str, suffix: str) -> str:
    return f"{base}{suffix}" if suffix else base


def _atom(variable: str, operator: RelationalOperator, value: Any) -> ConditionAtom:
    return ConditionAtom(variable=variable, operator=operator, value=value)


def _tautology_from_clauses(clauses: list[ConditionExpr]) -> ConditionExpr:
    """Classical tautology OR_i (c_i OR NOT c_i) built from clause list (non-empty)."""
    parts: list[ConditionExpr] = []
    for c in clauses:
        parts.append(ConditionOr(children=[c, ConditionNot(child=c)]))
    if len(parts) == 1:
        return parts[0]
    return ConditionOr(children=parts)


def _substitute_condition(expr: ConditionExpr, *, variable: str, value: Any) -> ConditionExpr:
    """Replace atom/varcmp references to ``variable`` with concrete ``value`` (scalar)."""
    dumped = copy.deepcopy(expr.model_dump(mode="json"))

    def walk(obj: object) -> object:
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        if not isinstance(obj, dict):
            return obj
        kind = obj.get("kind")
        if kind == "atom" and obj.get("variable") == variable:
            return {"kind": "atom", "variable": variable, "operator": obj["operator"], "value": value}
        if kind == "varcmp":
            out = dict(obj)
            if out.get("left_variable") == variable:
                out["left_variable"] = variable
            if out.get("right_variable") == variable:
                out["right_variable"] = variable
            return out
        if kind == "varprod_cmp":
            return obj
        if kind == "not":
            return {"kind": "not", "child": walk(obj["child"])}
        if kind in ("and", "or"):
            return {"kind": kind, "children": [walk(ch) for ch in obj["children"]]}
        return obj

    from pivot_pipeline.ir import (
        ConditionAnd,
        ConditionAtom,
        ConditionNot,
        ConditionOr,
        ConditionVarCmp,
        ConditionVarProductCmp,
    )

    fixed = walk(dumped)
    if isinstance(fixed, dict):
        k = fixed.get("kind")
        if k == "atom":
            return ConditionAtom.model_validate(fixed)
        if k == "varcmp":
            return ConditionVarCmp.model_validate(fixed)
        if k == "varprod_cmp":
            return ConditionVarProductCmp.model_validate(fixed)
        if k == "and":
            return ConditionAnd.model_validate(fixed)
        if k == "or":
            return ConditionOr.model_validate(fixed)
        if k == "not":
            return ConditionNot.model_validate(fixed)
    raise ValueError("substitute_condition: invalid condition tree")


def _at_least_k_of_n_conditions(clauses: list[ConditionExpr], k: int) -> ConditionExpr:
    """OR over all C(n,j) AND combinations for j in k..n (small n only)."""
    n = len(clauses)
    if k == 0:
        return _atom("__unused", RelationalOperator.EQ, 1)
    if k > n:
        raise ValueError("k > n")
    if k == 1:
        if n == 1:
            return clauses[0]
        return ConditionOr(children=list(clauses))
    if k == n:
        if n == 1:
            return clauses[0]
        return ConditionAnd(children=list(clauses))
    disjuncts: list[ConditionExpr] = []
    for j in range(k, n + 1):
        for combo in combinations(range(n), j):
            if j == 1:
                disjuncts.append(clauses[combo[0]])
            elif j == 2:
                disjuncts.append(ConditionAnd(children=[clauses[i] for i in combo]))
            else:
                disjuncts.append(ConditionAnd(children=[clauses[i] for i in combo]))
    if len(disjuncts) == 1:
        return disjuncts[0]
    return ConditionOr(children=disjuncts)


def lower_int_range(rule: IntRange) -> list[dict[str, Any]]:
    base = rule.rule_id
    applies = rule.applies_to
    overrides = rule.overrides
    y = rule.yields
    if rule.lo == rule.hi:
        from pivot_pipeline.ir import ConstantRelational

        return [
            _dump_rule(
                ConstantRelational(
                    rule_id=base,
                    applies_to=applies,
                    overrides=overrides,
                    variable=rule.variable,
                    relational_operator=RelationalOperator.EQ,
                    constant_value=rule.lo,
                    yields=y,
                )
            )
        ]
    from pivot_pipeline.ir import ConstantRelational

    return [
        _dump_rule(
            ConstantRelational(
                rule_id=_rid(base, "__gte"),
                applies_to=applies,
                overrides=overrides,
                variable=rule.variable,
                relational_operator=RelationalOperator.GTE,
                constant_value=rule.lo,
                yields=y,
            )
        ),
        _dump_rule(
            ConstantRelational(
                rule_id=_rid(base, "__lte"),
                applies_to=applies,
                overrides=overrides,
                variable=rule.variable,
                relational_operator=RelationalOperator.LTE,
                constant_value=rule.hi,
                yields=y,
            )
        ),
    ]


def lower_decision_table_row(rule: DecisionTableRow) -> list[dict[str, Any]]:
    from pivot_pipeline.ir import LogicalImplication

    return [
        _dump_rule(
            LogicalImplication(
                rule_id=rule.rule_id,
                applies_to=rule.applies_to,
                overrides=rule.overrides,
                trigger_condition=rule.trigger_condition,
                required_condition=rule.required_condition,
            )
        )
    ]


def lower_table_block(rule: TableBlock) -> list[dict[str, Any]]:
    from pivot_pipeline.ir import LogicalImplication

    tid = (rule.table_id or rule.rule_id).replace(" ", "_")
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rule.rows):
        rid = _rid(rule.rule_id, f"__{tid}_r{idx:02d}")
        out.append(
            _dump_rule(
                LogicalImplication(
                    rule_id=rid,
                    applies_to=rule.applies_to,
                    overrides=rule.overrides if idx == 0 else None,
                    trigger_condition=row.trigger_condition,
                    required_condition=row.required_condition,
                )
            )
        )
    return out


def lower_bounded_forall(rule: BoundedForall) -> list[dict[str, Any]]:
    from pivot_pipeline.ir import LogicalImplication

    out: list[dict[str, Any]] = []
    for idx, val in enumerate(rule.domain):
        trig = _atom(rule.iter_variable, RelationalOperator.EQ, val)
        req = rule.required_condition
        out.append(
            _dump_rule(
                LogicalImplication(
                    rule_id=_rid(rule.rule_id, f"__d{idx:02d}"),
                    applies_to=rule.applies_to,
                    overrides=rule.overrides if idx == 0 else None,
                    trigger_condition=trig,
                    required_condition=req,
                )
            )
        )
    return out


def lower_k_of_n(rule: KOfN) -> list[dict[str, Any]]:
    from pivot_pipeline.ir import LogicalImplication, RelationalOperator

    k_cond = _at_least_k_of_n_conditions(rule.clauses, rule.k)
    if rule.result_variable:
        rv = str(rule.result_variable).strip()
        return [
            _dump_rule(
                LogicalImplication(
                    rule_id=rule.rule_id,
                    applies_to=rule.applies_to,
                    overrides=rule.overrides,
                    trigger_condition=k_cond,
                    required_condition=_atom(rv, RelationalOperator.EQ, True),
                )
            )
        ]
    trigger = _tautology_from_clauses(rule.clauses)
    return [
        _dump_rule(
            LogicalImplication(
                rule_id=rule.rule_id,
                applies_to=rule.applies_to,
                overrides=rule.overrides,
                trigger_condition=trigger,
                required_condition=k_cond,
            )
        )
    ]


def lower_exhaustive_switch(rule: ExhaustiveSwitch) -> list[dict[str, Any]]:
    from pivot_pipeline.ir import InclusionOperator, LogicalImplication, SetInclusion

    out: list[dict[str, Any]] = []
    disc = rule.discriminant_variable
    case_values = [c.value for c in rule.cases]
    first_overrides = rule.overrides

    if rule.default_consequence is None:
        out.append(
            _dump_rule(
                SetInclusion(
                    rule_id=_rid(rule.rule_id, "__cov"),
                    applies_to=rule.applies_to,
                    overrides=first_overrides,
                    variable=disc,
                    inclusion_operator=InclusionOperator.IN,
                    constant_array=case_values,
                    yields=Yields.SATISFIED,
                )
            )
        )
        first_overrides = None

    for idx, case in enumerate(rule.cases):
        out.append(
            _dump_rule(
                LogicalImplication(
                    rule_id=_rid(rule.rule_id, f"__c{idx:02d}"),
                    applies_to=rule.applies_to,
                    overrides=first_overrides,
                    trigger_condition=_atom(disc, RelationalOperator.EQ, case.value),
                    required_condition=case.consequence,
                )
            )
        )
        first_overrides = None

    if rule.default_consequence is not None:
        case_or = ConditionOr(children=[_atom(disc, RelationalOperator.EQ, v) for v in case_values])
        out.append(
            _dump_rule(
                LogicalImplication(
                    rule_id=_rid(rule.rule_id, "__def"),
                    applies_to=rule.applies_to,
                    overrides=None,
                    trigger_condition=ConditionNot(child=case_or),
                    required_condition=rule.default_consequence,
                )
            )
        )

    return out


def lower_defined_as(rule: DefinedAs) -> list[dict[str, Any]]:
    from pivot_pipeline.ir import LogicalImplication

    trigger = _tautology_from_clauses([rule.definition])
    return [
        _dump_rule(
            LogicalImplication(
                rule_id=rule.rule_id,
                applies_to=rule.applies_to,
                overrides=rule.overrides,
                trigger_condition=trigger,
                required_condition=rule.definition,
            )
        )
    ]


def lower_sum_threshold(rule: SumThreshold) -> list[dict[str, Any]]:
    from pivot_pipeline.ir import ArithmeticEvaluation, ConstantRelational, MathOperator, RelationalOperator

    terms = rule.terms
    op = rule.relational_operator
    lim = rule.limit
    y = rule.yields
    applies = rule.applies_to
    overrides = rule.overrides
    base = rule.rule_id

    if len(terms) == 1:
        term = terms[0]
        var = term.variable
        coeff = term.coeff
        if coeff == 1:
            return [
                _dump_rule(
                    ConstantRelational(
                        rule_id=base,
                        applies_to=applies,
                        overrides=overrides,
                        variable=var,
                        relational_operator=op,
                        constant_value=lim,
                        yields=y,
                    )
                )
            ]
        return [
            _dump_rule(
                ArithmeticEvaluation(
                    rule_id=base,
                    applies_to=applies,
                    overrides=overrides,
                    operand_1=var,
                    math_operator=MathOperator.MULTIPLY,
                    operand_2=coeff,
                    relational_operator=op,
                    target_limit=lim,
                    yields=y,
                )
            )
        ]

    out: list[dict[str, Any]] = []
    first_overrides = overrides
    acc_prev: str | None = None
    for i, term in enumerate(terms):
        contrib = term.variable
        if term.coeff != 1:
            tmp = f"__{base}_t{i}"
            out.append(
                _dump_rule(
                    ArithmeticEvaluation(
                        rule_id=_rid(base, f"__t{i:02d}"),
                        applies_to=applies,
                        overrides=first_overrides,
                        operand_1=term.variable,
                        math_operator=MathOperator.MULTIPLY,
                        operand_2=term.coeff,
                        relational_operator=RelationalOperator.EQ,
                        target_limit=tmp,
                        yields=y,
                    )
                )
            )
            first_overrides = None
            contrib = tmp

        acc_name = f"__{base}_acc{i}"
        if i == 0:
            out.append(
                _dump_rule(
                    ArithmeticEvaluation(
                        rule_id=_rid(base, f"__acc{i:02d}"),
                        applies_to=applies,
                        overrides=first_overrides,
                        operand_1=contrib,
                        math_operator=MathOperator.MULTIPLY,
                        operand_2=1,
                        relational_operator=RelationalOperator.EQ,
                        target_limit=acc_name,
                        yields=y,
                    )
                )
            )
        else:
            assert acc_prev is not None
            out.append(
                _dump_rule(
                    ArithmeticEvaluation(
                        rule_id=_rid(base, f"__acc{i:02d}"),
                        applies_to=applies,
                        overrides=first_overrides,
                        operand_1=acc_prev,
                        math_operator=MathOperator.ADD,
                        operand_2=contrib,
                        relational_operator=RelationalOperator.EQ,
                        target_limit=acc_name,
                        yields=y,
                    )
                )
            )
        first_overrides = None
        acc_prev = acc_name

    assert acc_prev is not None
    out.append(
        _dump_rule(
            ConstantRelational(
                rule_id=base,
                applies_to=applies,
                overrides=None,
                variable=acc_prev,
                relational_operator=op,
                constant_value=lim,
                yields=y,
            )
        )
    )
    return out


_LOWERERS = {
    "INT_RANGE": lambda m: lower_int_range(m),  # type: ignore[arg-type]
    "DECISION_TABLE_ROW": lambda m: lower_decision_table_row(m),
    "TABLE_BLOCK": lambda m: lower_table_block(m),
    "BOUNDED_FORALL": lambda m: lower_bounded_forall(m),
    "K_OF_N": lambda m: lower_k_of_n(m),
    "EXHAUSTIVE_SWITCH": lambda m: lower_exhaustive_switch(m),
    "DEFINED_AS": lambda m: lower_defined_as(m),
    "SUM_THRESHOLD": lambda m: lower_sum_threshold(m),
}


def lower_vnext_rule(rule: dict[str, Any], *, stats: LoweringStats | None = None) -> list[dict[str, Any]]:
    model = validate_vnext_rule_dict(rule)
    tc = str(rule.get("template_class"))
    emitted = _LOWERERS[tc](model)  # type: ignore[operator]
    if stats is not None:
        stats.record(tc, emitted=len(emitted))
    return emitted


def expand_rules_to_core(
    rules: list[dict[str, Any]],
    *,
    stats: LoweringStats | None = None,
) -> list[dict[str, Any]]:
    """
    Replace vNext expansion templates with core ``template_class`` rule dicts.

    Core templates pass through unchanged. Unknown ``template_class`` values are
    left as-is for downstream validation to reject.
    """
    st = stats if stats is not None else LoweringStats()
    out: list[dict[str, Any]] = []
    for r in rules:
        tc = r.get("template_class")
        if tc in VNEXT_TEMPLATE_CLASSES:
            out.extend(lower_vnext_rule(r, stats=st))
        elif tc in _RULE_MODEL_BY_TEMPLATE:
            out.append(r)
        else:
            out.append(r)
    return out


__all__ = [
    "LoweringStats",
    "expand_rules_to_core",
    "lower_bounded_forall",
    "lower_decision_table_row",
    "lower_defined_as",
    "lower_exhaustive_switch",
    "lower_int_range",
    "lower_k_of_n",
    "lower_sum_threshold",
    "lower_table_block",
    "lower_vnext_rule",
]
