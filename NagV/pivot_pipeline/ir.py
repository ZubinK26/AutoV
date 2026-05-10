"""Pydantic IR for pivot policy meta-scheme (v1)."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pivot_pipeline.constants import (
    CONDITION_EXPR_MAX_DEPTH,
    PATHWAY_CAP,
    POLICY_SEMANTICS_VERSION_DEFAULT,
)


class RelationalOperator(StrEnum):
    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    LT = "LT"
    GTE = "GTE"
    LTE = "LTE"


class InclusionOperator(StrEnum):
    IN = "IN"
    NOT_IN = "NOT_IN"


class MathOperator(StrEnum):
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"


class Yields(StrEnum):
    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"


class PreemptionAction(StrEnum):
    FORCE_SATISFIED = "FORCE_SATISFIED"
    FORCE_UNSATISFIED = "FORCE_UNSATISFIED"
    BYPASS_RULE = "BYPASS_RULE"


class ExclusiveChoiceMode(StrEnum):
    EXACTLY_ONE = "exactly_one"
    AT_MOST_ONE = "at_most_one"


Scalar = Union[int, float, str, bool]


def condition_depth(obj: object, base: int = 0) -> int:
    k = getattr(obj, "kind", None)
    if k in ("atom", "varcmp", "varprod_cmp"):
        return base + 1
    if k == "not":
        return condition_depth(getattr(obj, "child"), base + 1)
    if k in ("and", "or"):
        ch = getattr(obj, "children", [])
        return max((condition_depth(c, base + 1) for c in ch), default=base + 1)
    raise ValueError(f"unknown condition kind {k!r}")


class ConditionAtom(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["atom"] = "atom"
    variable: str
    operator: RelationalOperator
    value: Scalar

    @model_validator(mode="after")
    def _chk(self) -> ConditionAtom:
        if condition_depth(self) > CONDITION_EXPR_MAX_DEPTH:
            raise ValueError(f"condition exceeds max depth {CONDITION_EXPR_MAX_DEPTH}")
        return self


class ConditionVarCmp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["varcmp"] = "varcmp"
    left_variable: str
    operator: RelationalOperator
    right_variable: str

    @model_validator(mode="after")
    def _chk(self) -> ConditionVarCmp:
        if condition_depth(self) > CONDITION_EXPR_MAX_DEPTH:
            raise ValueError(f"condition exceeds max depth {CONDITION_EXPR_MAX_DEPTH}")
        return self


class VarProdRhsVar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["var"] = "var"
    variable: str


class VarProdRhsConst(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["const"] = "const"
    value: int


VarProdRhsAnnotated = Annotated[
    Union[VarProdRhsVar, VarProdRhsConst],
    Field(discriminator="kind"),
]


class ConditionVarProductCmp(BaseModel):
    """Leaf: ``left_variable * right_variable`` compared to rhs (variable or int constant)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["varprod_cmp"] = "varprod_cmp"
    left_variable: str
    right_variable: str
    operator: RelationalOperator
    rhs: VarProdRhsAnnotated

    @model_validator(mode="after")
    def _chk(self) -> ConditionVarProductCmp:
        if condition_depth(self) > CONDITION_EXPR_MAX_DEPTH:
            raise ValueError(f"condition exceeds max depth {CONDITION_EXPR_MAX_DEPTH}")
        return self


class ConditionAnd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["and"] = "and"
    children: list[ConditionExpr] = Field(min_length=2)

    @model_validator(mode="after")
    def _chk(self) -> ConditionAnd:
        if condition_depth(self) > CONDITION_EXPR_MAX_DEPTH:
            raise ValueError(f"condition exceeds max depth {CONDITION_EXPR_MAX_DEPTH}")
        return self


class ConditionOr(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["or"] = "or"
    children: list[ConditionExpr] = Field(min_length=2)

    @model_validator(mode="after")
    def _chk(self) -> ConditionOr:
        if condition_depth(self) > CONDITION_EXPR_MAX_DEPTH:
            raise ValueError(f"condition exceeds max depth {CONDITION_EXPR_MAX_DEPTH}")
        return self


class ConditionNot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["not"] = "not"
    child: ConditionExpr

    @model_validator(mode="after")
    def _chk(self) -> ConditionNot:
        if condition_depth(self) > CONDITION_EXPR_MAX_DEPTH:
            raise ValueError(f"condition exceeds max depth {CONDITION_EXPR_MAX_DEPTH}")
        return self


ConditionExpr = Annotated[
    Union[
        ConditionAtom,
        ConditionVarCmp,
        ConditionVarProductCmp,
        ConditionAnd,
        ConditionOr,
        ConditionNot,
    ],
    Field(discriminator="kind"),
]

ConditionAnd.model_rebuild()
ConditionOr.model_rebuild()
ConditionNot.model_rebuild()


class BaseRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    applies_to: str = "GLOBAL"
    overrides: str | None = None


class ConstantRelational(BaseRule):
    template_class: Literal["CONSTANT_RELATIONAL"] = "CONSTANT_RELATIONAL"
    variable: str
    relational_operator: RelationalOperator
    constant_value: Scalar
    yields: Yields


class SetInclusion(BaseRule):
    template_class: Literal["SET_INCLUSION"] = "SET_INCLUSION"
    variable: str
    inclusion_operator: InclusionOperator
    constant_array: list[Scalar] = Field(min_length=1)
    yields: Yields

    @field_validator("constant_array")
    @classmethod
    def _finite(cls, v: list[Scalar]) -> list[Scalar]:
        if len(v) > 10_000:
            raise ValueError("constant_array too large (v1 cap 10000)")
        return v


class VariableRelational(BaseRule):
    template_class: Literal["VARIABLE_RELATIONAL"] = "VARIABLE_RELATIONAL"
    left_variable: str
    relational_operator: RelationalOperator
    right_variable: str
    yields: Yields


class ArithmeticEvaluation(BaseRule):
    template_class: Literal["ARITHMETIC_EVALUATION"] = "ARITHMETIC_EVALUATION"
    operand_1: str
    math_operator: MathOperator
    operand_2: Scalar | str
    relational_operator: RelationalOperator
    target_limit: Scalar | str
    yields: Yields

    @model_validator(mode="after")
    def _guard(self) -> ArithmeticEvaluation:
        if self.math_operator == MathOperator.DIVIDE:
            if isinstance(self.operand_2, str):
                raise ValueError("DIVIDE: operand_2 must not be a variable (v1)")
            if self.operand_2 == 0:
                raise ValueError("DIVIDE: operand_2 cannot be 0")
        if self.math_operator == MathOperator.MULTIPLY:
            if isinstance(self.operand_2, str):
                raise ValueError("MULTIPLY with variable×variable not allowed (v1)")
        return self


class LogicalImplication(BaseRule):
    template_class: Literal["LOGICAL_IMPLICATION"] = "LOGICAL_IMPLICATION"
    trigger_condition: ConditionExpr
    required_condition: ConditionExpr


class Preemption(BaseRule):
    template_class: Literal["PREEMPTION"] = "PREEMPTION"
    preempting_condition: ConditionExpr
    action: PreemptionAction
    target_rule_id: str | None = None


class ExclusiveChoice(BaseRule):
    template_class: Literal["EXCLUSIVE_CHOICE"] = "EXCLUSIVE_CHOICE"
    mode: ExclusiveChoiceMode
    variables: list[str] = Field(min_length=2)


class LogicalIff(BaseRule):
    template_class: Literal["LOGICAL_IFF"] = "LOGICAL_IFF"
    left: ConditionExpr
    right: ConditionExpr


AtomicRule = Annotated[
    Union[
        ConstantRelational,
        SetInclusion,
        VariableRelational,
        ArithmeticEvaluation,
        LogicalImplication,
        Preemption,
        ExclusiveChoice,
        LogicalIff,
    ],
    Field(discriminator="template_class"),
]


class EvaluationPathway(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathway_id: str
    description: str = ""
    must_satisfy_all: list[str] = Field(default_factory=list)
    must_not_trigger: list[str] = Field(default_factory=list)


class MetaScheme(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    policy_semantics_version: str = POLICY_SEMANTICS_VERSION_DEFAULT
    baseline_evaluation: Literal["DEFAULT_UNSATISFIED"] = "DEFAULT_UNSATISFIED"
    evaluation_pathways: list[EvaluationPathway]
    rules: list[AtomicRule]
    variable_sorts: dict[str, Literal["int", "bool"]] = Field(default_factory=dict)

    @field_validator("policy_semantics_version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if v != POLICY_SEMANTICS_VERSION_DEFAULT:
            raise ValueError(
                f"unsupported policy_semantics_version {v!r} (only {POLICY_SEMANTICS_VERSION_DEFAULT!r})"
            )
        return v

    @model_validator(mode="after")
    def _cap(self) -> MetaScheme:
        if len(self.evaluation_pathways) > PATHWAY_CAP:
            raise ValueError(f"evaluation_pathways exceeds cap {PATHWAY_CAP}")
        return self


def load_rules_and_compile(policy_id: str, rules: list[dict]) -> MetaScheme:
    """Parse rule dicts from JSON and run :func:`build_meta_scheme`."""
    parsed: list[AtomicRule] = []
    for r in rules:
        t = r.get("template_class")
        if not t:
            raise ValueError(f"missing template_class: {r!r}")
        model_map: dict[str, type] = {
            "CONSTANT_RELATIONAL": ConstantRelational,
            "SET_INCLUSION": SetInclusion,
            "VARIABLE_RELATIONAL": VariableRelational,
            "ARITHMETIC_EVALUATION": ArithmeticEvaluation,
            "LOGICAL_IMPLICATION": LogicalImplication,
            "PREEMPTION": Preemption,
            "EXCLUSIVE_CHOICE": ExclusiveChoice,
            "LOGICAL_IFF": LogicalIff,
        }
        cls = model_map.get(t)
        if cls is None:
            raise ValueError(f"unknown template_class {t!r}")
        parsed.append(cls.model_validate(r))  # type: ignore[assignment]
    from pivot_pipeline.pathway_compiler import build_meta_scheme
    from pivot_pipeline.var_product_validate import validate_var_product_rules

    validate_var_product_rules(parsed)
    return build_meta_scheme(policy_id=policy_id, rules=parsed)


# Backward-compatible alias
def meta_scheme_from_rules_jsonable(policy_id: str, rules: list[dict]) -> MetaScheme:
    return load_rules_and_compile(policy_id, rules)
