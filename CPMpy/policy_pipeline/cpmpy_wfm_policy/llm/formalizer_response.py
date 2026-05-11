"""Pydantic validation for Formalizer LLM JSON (Project_Spec_Agents + legacy)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class FormalizerSuccessV1(BaseModel):
    rule_name: str
    expression: str = Field(min_length=1)
    used_symbols: list[str] = Field(default_factory=list)
    uses_global_constraints: bool = False
    uses_vector_variables: bool = False
    claimed_dependencies: list[str] = Field(default_factory=list)
    out_of_scope_reason: str = ""

    @field_validator("rule_name")
    @classmethod
    def rule_name_ok(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("rule_"):
            raise ValueError("rule_name must be rule_<k>")
        return v


class FormalizerOutOfScopeV1(BaseModel):
    status: Literal["out_of_scope"] = "out_of_scope"
    rule_name: str = ""
    expression: str = ""
    used_symbols: list[str] = Field(default_factory=list)
    uses_global_constraints: bool = False
    uses_vector_variables: bool = False
    claimed_dependencies: list[str] = Field(default_factory=list)
    out_of_scope_reason: str = Field(min_length=1)


class FormalizerLegacyEnvelope(BaseModel):
    """Slice-2 style: full rule_module source."""

    rule_module: str = Field(min_length=1)
    used_symbols: list[str]
    uses_global_constraints: bool = False
    uses_vector_variables: bool = False


def normalize_formalizer_llm_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate LLM JSON; return a dict with keys: rule_module, used_symbols,
    uses_global_constraints, uses_vector_variables, claimed_dependencies (optional).
    """
    if "rule_module" in data and data.get("rule_module"):
        leg = FormalizerLegacyEnvelope.model_validate(data)
        return {
            "rule_module": leg.rule_module.strip() + ("\n" if not leg.rule_module.endswith("\n") else ""),
            "used_symbols": frozenset(str(x) for x in leg.used_symbols),
            "uses_global_constraints": leg.uses_global_constraints,
            "uses_vector_variables": leg.uses_vector_variables,
            "claimed_dependencies": frozenset[str](),
        }

    status = data.get("status")
    if status == "out_of_scope":
        oos = FormalizerOutOfScopeV1.model_validate(data)
        raise ValueError(f"out_of_scope: {oos.out_of_scope_reason}")

    ok = FormalizerSuccessV1.model_validate(data)
    expr = ok.expression.strip()
    rn = ok.rule_name.strip()
    rule_module = f"import cpmpy as cp\n{rn} = {expr}\n"
    return {
        "rule_module": rule_module,
        "used_symbols": frozenset(str(x) for x in ok.used_symbols),
        "uses_global_constraints": ok.uses_global_constraints,
        "uses_vector_variables": ok.uses_vector_variables,
        "claimed_dependencies": frozenset(str(x) for x in ok.claimed_dependencies),
    }
