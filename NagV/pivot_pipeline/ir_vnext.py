"""Pydantic models for vNext expansion templates (lowered to core IR before compile)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pivot_pipeline.constants import (
    BOUNDED_FORALL_MAX_DOMAIN,
    EXHAUSTIVE_SWITCH_MAX_CASES,
    INT_RANGE_MAX_SPAN,
    K_OF_N_MAX_CLAUSES,
    K_OF_N_MIN_CLAUSES,
    SUM_THRESHOLD_MAX_COEFF,
    SUM_THRESHOLD_MAX_TERMS,
    TABLE_BLOCK_MAX_ROWS,
)
from pivot_pipeline.ir import (
    BaseRule,
    ConditionExpr,
    RelationalOperator,
    Scalar,
    Yields,
)

VNEXT_TEMPLATE_CLASSES: frozenset[str] = frozenset(
    {
        "INT_RANGE",
        "DECISION_TABLE_ROW",
        "TABLE_BLOCK",
        "BOUNDED_FORALL",
        "K_OF_N",
        "EXHAUSTIVE_SWITCH",
        "DEFINED_AS",
        "SUM_THRESHOLD",
    }
)


class DecisionTableRowPayload(BaseModel):
    """One row inside TABLE_BLOCK (no rule_id; inherited from parent)."""

    model_config = ConfigDict(extra="forbid")

    trigger_condition: ConditionExpr
    required_condition: ConditionExpr


class SwitchCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Scalar
    consequence: ConditionExpr


class SumTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coeff: int = 1
    variable: str

    @model_validator(mode="after")
    def _coeff(self) -> SumTerm:
        if self.coeff == 0:
            raise ValueError("SUM_THRESHOLD term coeff cannot be 0")
        if abs(self.coeff) > SUM_THRESHOLD_MAX_COEFF:
            raise ValueError(f"SUM_THRESHOLD coeff exceeds cap {SUM_THRESHOLD_MAX_COEFF}")
        return self


class IntRange(BaseRule):
    template_class: Literal["INT_RANGE"] = "INT_RANGE"
    variable: str
    lo: int
    hi: int
    yields: Yields = Yields.SATISFIED

    @model_validator(mode="after")
    def _bounds(self) -> IntRange:
        if self.lo > self.hi:
            raise ValueError(f"INT_RANGE: lo ({self.lo}) > hi ({self.hi})")
        if self.hi - self.lo > INT_RANGE_MAX_SPAN:
            raise ValueError(f"INT_RANGE span exceeds cap {INT_RANGE_MAX_SPAN}")
        return self


class DecisionTableRow(BaseRule):
    template_class: Literal["DECISION_TABLE_ROW"] = "DECISION_TABLE_ROW"
    trigger_condition: ConditionExpr
    required_condition: ConditionExpr


class TableBlock(BaseRule):
    template_class: Literal["TABLE_BLOCK"] = "TABLE_BLOCK"
    table_id: str = ""
    rows: list[DecisionTableRowPayload] = Field(min_length=1)
    applies_to: str = "GLOBAL"
    overrides: str | None = None

    @model_validator(mode="after")
    def _rows_cap(self) -> TableBlock:
        if len(self.rows) > TABLE_BLOCK_MAX_ROWS:
            raise ValueError(f"TABLE_BLOCK rows exceeds cap {TABLE_BLOCK_MAX_ROWS}")
        return self


class BoundedForall(BaseRule):
    template_class: Literal["BOUNDED_FORALL"] = "BOUNDED_FORALL"
    iter_variable: str
    domain: list[Scalar] = Field(min_length=1)
    required_condition: ConditionExpr

    @model_validator(mode="after")
    def _domain_cap(self) -> BoundedForall:
        if len(self.domain) > BOUNDED_FORALL_MAX_DOMAIN:
            raise ValueError(f"BOUNDED_FORALL domain exceeds cap {BOUNDED_FORALL_MAX_DOMAIN}")
        return self


class KOfN(BaseRule):
    template_class: Literal["K_OF_N"] = "K_OF_N"
    k: int
    clauses: list[ConditionExpr] = Field(min_length=K_OF_N_MIN_CLAUSES)
    result_variable: str | None = Field(
        default=None,
        description=(
            "Optional aggregate boolean set true when at least k clauses hold; "
            "lowered to LOGICAL_IMPLICATION (k-of-n trigger → result_variable EQ true)."
        ),
    )

    @model_validator(mode="after")
    def _k_of_n(self) -> KOfN:
        n = len(self.clauses)
        if n > K_OF_N_MAX_CLAUSES:
            raise ValueError(f"K_OF_N clauses exceeds cap {K_OF_N_MAX_CLAUSES}")
        if self.k < 1 or self.k > n:
            raise ValueError(f"K_OF_N: k={self.k} must satisfy 1 <= k <= n={n}")
        if self.result_variable is not None and not str(self.result_variable).strip():
            raise ValueError("K_OF_N: result_variable must be non-empty when set")
        return self


class ExhaustiveSwitch(BaseRule):
    template_class: Literal["EXHAUSTIVE_SWITCH"] = "EXHAUSTIVE_SWITCH"
    discriminant_variable: str
    cases: list[SwitchCase] = Field(min_length=1)
    default_consequence: ConditionExpr | None = None

    @model_validator(mode="after")
    def _cases(self) -> ExhaustiveSwitch:
        if len(self.cases) > EXHAUSTIVE_SWITCH_MAX_CASES:
            raise ValueError(f"EXHAUSTIVE_SWITCH cases exceeds cap {EXHAUSTIVE_SWITCH_MAX_CASES}")
        values = [c.value for c in self.cases]
        if len(values) != len(set(values)):
            raise ValueError("EXHAUSTIVE_SWITCH: duplicate case values")
        return self


class DefinedAs(BaseRule):
    template_class: Literal["DEFINED_AS"] = "DEFINED_AS"
    variable: str
    definition: ConditionExpr
    sort: Literal["int", "bool"] | None = None


class SumThreshold(BaseRule):
    template_class: Literal["SUM_THRESHOLD"] = "SUM_THRESHOLD"
    terms: list[SumTerm] = Field(min_length=1)
    relational_operator: RelationalOperator
    limit: int
    yields: Yields = Yields.SATISFIED

    @model_validator(mode="after")
    def _terms_cap(self) -> SumThreshold:
        n = len(self.terms)
        if n > SUM_THRESHOLD_MAX_TERMS:
            raise ValueError(
                f"SUM_THRESHOLD supports at most {SUM_THRESHOLD_MAX_TERMS} terms (got {n}); "
                "split into another rule line or use a single combined variable"
            )
        return self


VNEXT_MODEL_BY_TEMPLATE: dict[str, type[BaseModel]] = {
    "INT_RANGE": IntRange,
    "DECISION_TABLE_ROW": DecisionTableRow,
    "TABLE_BLOCK": TableBlock,
    "BOUNDED_FORALL": BoundedForall,
    "K_OF_N": KOfN,
    "EXHAUSTIVE_SWITCH": ExhaustiveSwitch,
    "DEFINED_AS": DefinedAs,
    "SUM_THRESHOLD": SumThreshold,
}


def validate_vnext_rule_dict(rule: dict) -> BaseModel:
    t = rule.get("template_class")
    if t not in VNEXT_TEMPLATE_CLASSES:
        raise ValueError(f"not a vNext template_class: {t!r}")
    cls = VNEXT_MODEL_BY_TEMPLATE[str(t)]
    return cls.model_validate(rule)


__all__ = [
    "VNEXT_MODEL_BY_TEMPLATE",
    "VNEXT_TEMPLATE_CLASSES",
    "BoundedForall",
    "DecisionTableRow",
    "DefinedAs",
    "ExhaustiveSwitch",
    "IntRange",
    "KOfN",
    "SumThreshold",
    "TableBlock",
    "validate_vnext_rule_dict",
]
